"""Wake-on-demand for the local model (vLLM in the Docker container `levadinho-llm`).

The webhook (app.py) runs all the time; the ~85 GB model runs only while it's needed:
  - a message that needs the model arrives while it's down → brain.llm() raises brain.LLMDown →
    app.py queues the message (store.py `pending`), tells the visitor, and calls start() if the
    GPU has room. If the GPU is busy with someone else's job, the message waits for it to free up.
  - a background waiter (run_waiter) replays the queue once the model answers, starts the model
    when the GPU frees for queued "busy" messages, and stops the model after LLM_IDLE_MIN minutes
    without an incoming message.
It never stops, kills or touches anything except its own container.

Config (env / bot/.env):
  LLM_ON_DEMAND=1     0 = old behaviour: the model is started by hand (start.sh) and never stopped here
  LLM_AUTO_STOP=1     1 = stop the idle model whoever started it (start.sh or the webhook);
                      0 = stop it only if the webhook itself started it
  LLM_IDLE_MIN=30     idle minutes (no incoming message) before the model is stopped; 0 = never
  LLM_GPU_FREE_GB=88  free GPU memory (GiB) needed to start the model (it takes ~85 GB of the 96 GB card)
  LLM_CONTAINER=levadinho-llm
  LLM_RETRY_S=300     wait at least this long before trying to start the container again
"""
import logging
import os
import subprocess
import threading
import time
import urllib.request

import store

log = logging.getLogger("levadinho.llm")

ON_DEMAND = os.environ.get("LLM_ON_DEMAND", "1") == "1"
AUTO_STOP = os.environ.get("LLM_AUTO_STOP", "1") == "1"
IDLE_MIN = float(os.environ.get("LLM_IDLE_MIN", "30"))
GPU_FREE_GB = float(os.environ.get("LLM_GPU_FREE_GB", "88"))
CONTAINER = os.environ.get("LLM_CONTAINER", "levadinho-llm")
RETRY_S = float(os.environ.get("LLM_RETRY_S", "300"))
MODELS_URL = os.environ.get("LLM_URL", "http://127.0.0.1:8001/v1/chat/completions").split("/v1/")[0] + "/v1/models"

# Same container as bot/start.sh creates (keep the two in sync).
DOCKER_RUN = ["docker", "run", "-d", "--name", CONTAINER, "--gpus", "all", "--ipc=host", "--restart", "no",
              "-p", "127.0.0.1:8001:8000", "-v", "/mnt/nvme8tb/huggingface_cache:/root/.cache/huggingface",
              "-e", "HF_HUB_OFFLINE=1", "vllm/vllm-openai:nightly", "--model", "Qwen/Qwen3.6-35B-A3B-FP8",
              "--served-model-name", "levadinho", "--max-model-len", "32768", "--gpu-memory-utilization", "0.85",
              "--kv-cache-dtype", "fp8", "--reasoning-parser", "qwen3",
              "--enable-auto-tool-choice", "--tool-call-parser", "qwen3_coder"]  # tool calling (model card: vLLM, qwen3_coder)
FLAG = "llm_started_by"  # store.py kv: "webhook" while a model this module started is running

_lock = threading.Lock()
_up_cache = {"at": 0.0, "up": False}
_state = {"activity": time.time(), "start_at": 0.0}


def _run(args, timeout=30):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def touch():
    """An incoming message: the idle clock starts again."""
    _state["activity"] = time.time()


def idle_s():
    return time.time() - _state["activity"]


def is_up(timeout=2.0):
    """The model answers GET /v1/models. A positive answer is trusted for 10 s."""
    if _up_cache["up"] and time.time() - _up_cache["at"] < 10:
        return True
    try:
        with urllib.request.urlopen(MODELS_URL, timeout=timeout) as r:
            up = r.status == 200
    except Exception:
        up = False
    _up_cache.update(at=time.time(), up=up)
    return up


def mark_down():
    _up_cache.update(at=0.0, up=False)


def container_running():
    try:
        out = _run(["docker", "ps", "--filter", f"name=^/{CONTAINER}$", "--format", "{{.Names}}"]).stdout
        return CONTAINER in out.split()
    except Exception:
        log.exception("docker ps failed")
        return False


def container_exists():
    out = _run(["docker", "ps", "-a", "--filter", f"name=^/{CONTAINER}$", "--format", "{{.Names}}"]).stdout
    return CONTAINER in out.split()


def gpu_memory():
    """→ (free GiB, total GiB) of the first GPU, or None if nvidia-smi fails."""
    try:
        out = _run(["nvidia-smi", "--query-gpu=memory.free,memory.total", "--format=csv,noheader,nounits"], 10)
        free, total = (float(x) for x in out.stdout.strip().splitlines()[0].split(","))
        return free / 1024, total / 1024
    except Exception:
        log.exception("nvidia-smi failed")
        return None


def gpu_free():
    """True if the GPU has room for the model. Unknown (nvidia-smi failed) counts as busy."""
    mem = gpu_memory()
    return bool(mem) and mem[0] >= GPU_FREE_GB


def state():
    """'up' (answers), 'loading' (our container runs but isn't answering yet), 'free' (down, GPU has
    room) or 'busy' (down, GPU used by something else)."""
    if is_up():
        return "up"
    if container_running():
        return "loading"
    return "free" if gpu_free() else "busy"


def _start_container():
    try:
        r = _run(["docker", "start", CONTAINER], 60) if container_exists() else _run(DOCKER_RUN, 300)
        if r.returncode:
            log.error("starting %s failed: %s", CONTAINER, (r.stderr or r.stdout).strip()[-500:])
            store.set_flag(FLAG, None)
        else:
            log.info("model container %s started; loading (~2 min)", CONTAINER)
    except Exception:
        log.exception("starting %s failed", CONTAINER)
        store.set_flag(FLAG, None)


def start():
    """Start the model if it's down and the GPU has room. Non-blocking (docker runs in a thread).
    → 'up' | 'loading' | 'starting' | 'busy' | 'retry-later'."""
    with _lock:
        if is_up():
            return "up"
        if container_running():
            return "loading"
        if time.time() - _state["start_at"] < RETRY_S:
            return "retry-later"
        if not gpu_free():
            return "busy"
        _state["start_at"] = time.time()
        store.set_flag(FLAG, "webhook")
        threading.Thread(target=_start_container, daemon=True, name="llm-start").start()
        return "starting"


def stop_if_idle(minutes=IDLE_MIN, pending=False):
    """docker stop our container after `minutes` without an incoming message. Only when the webhook
    started it, or LLM_AUTO_STOP=1. Never while messages are waiting. → True if it stopped it."""
    if not ON_DEMAND or minutes <= 0 or pending or idle_s() < minutes * 60:
        return False
    with _lock:
        if not container_running():
            if store.get_flag(FLAG):
                store.set_flag(FLAG, None)
            return False
        if not (AUTO_STOP or store.get_flag(FLAG) == "webhook"):
            return False
        log.info("model idle for %.0f min: stopping %s", idle_s() / 60, CONTAINER)
        r = _run(["docker", "stop", CONTAINER], 120)
        if r.returncode:
            log.error("docker stop %s failed: %s", CONTAINER, r.stderr.strip())
            return False
        store.set_flag(FLAG, None)
        mark_down()
        return True


def tick(has_pending, drain):
    """One pass of the waiter. `has_pending()` → bool; `drain(up)` expires stale messages and, when
    up is True, replays the rest."""
    if has_pending():
        up = is_up()
        drain(up)
        if not up and has_pending() and not container_running():
            start()  # GPU freed (or a start failed earlier): try again
    else:
        stop_if_idle()


def run_waiter(has_pending, drain, interval=5.0):
    def loop():
        while True:
            try:
                tick(has_pending, drain)
            except Exception:
                log.exception("llm waiter")
            time.sleep(interval)
    t = threading.Thread(target=loop, daemon=True, name="llm-waiter")
    t.start()
    return t
