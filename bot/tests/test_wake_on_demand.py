"""Offline tests for wake-on-demand (llm_control.py) and #web-<page> tags. No model, no Docker, no
GPU, no WhatsApp, no Postgres: docker/nvidia-smi, the model, Graph API and analytics are all fakes,
and the SQLite store is a scratch file.

  python bot/tests/test_wake_on_demand.py
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOT = os.path.dirname(HERE)
sys.path.insert(0, BOT)
os.environ["LEVADINHO_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DB_URL"] = ""                                         # analytics writes nothing
os.environ["LLM_URL"] = "http://127.0.0.1:9/v1/chat/completions"  # nothing listens there
os.environ.setdefault("LLM_ON_DEMAND", "1")
for k in ("WA_TOKEN", "WA_PHONE_NUMBER_ID", "WA_APP_SECRET", "WA_VERIFY_TOKEN"):
    os.environ[k] = "test"  # set before app.py reads bot/.env (setdefault keeps these)

import llm_control  # noqa: E402


class FakeHost:
    """docker + nvidia-smi."""
    def __init__(self):
        self.running, self.exists, self.free_gib, self.cmds = False, True, 95.0, []

    def run(self, args, timeout=30):
        self.cmds.append(" ".join(args[:3]))
        out, rc = "", 0
        if args[:2] == ["docker", "ps"]:
            show = self.running or ("-a" in args and self.exists)
            out = llm_control.CONTAINER + "\n" if show else ""
        elif args[:2] == ["docker", "start"]:
            self.running = True
        elif args[:2] == ["docker", "stop"]:
            self.running = False
        elif args[:2] == ["docker", "run"]:
            self.running = self.exists = True
        elif args[0] == "nvidia-smi":
            out = f"{self.free_gib * 1024:.0f}, {97887}\n"
        else:
            raise AssertionError(f"unexpected command {args}")
        return type("R", (), {"stdout": out, "stderr": "", "returncode": rc})()


host = FakeHost()
llm_control._run = host.run
model = {"up": False}
llm_control.is_up = lambda timeout=2.0: model["up"]

import threading  # noqa: E402
_real_thread = threading.Thread


class SyncThread:  # run llm_control's docker thread inline, so tests are deterministic
    def __init__(self, target=None, daemon=None, name=None, **kw):
        self.target = target

    def start(self):
        self.target()


llm_control.threading = type("T", (), {"Thread": SyncThread, "Lock": threading.Lock})

import app  # noqa: E402
import analytics  # noqa: E402
import brain  # noqa: E402
import store  # noqa: E402

sent, recorded = [], []
app.graph_post = lambda payload: sent.append(payload)
brain.live_status = lambda: json.load(open(brain.STATUS_FILE, encoding="utf-8"))
for name in ("event", "turn", "set_consent", "fix"):
    setattr(analytics, name, (lambda n: lambda *a, **k: recorded.append((n, a, k)))(name))
analytics.touch_visitor = lambda phone, lang=None: "vid"
analytics.visitor_known = lambda phone: True
analytics.visitor_id_for = lambda phone: "vid"

real_llm = brain.llm


def fake_llm(messages, max_tokens=700, schema=None, temperature=0.3):
    if not model["up"]:
        raise brain.LLMDown()
    text = messages[-1]["content"]
    if schema:
        q = "?" in text
        lang = brain.guess_lang(text) or "en"
        return json.dumps({"is_question": q, "language": lang, "intent": "status" if q else "other",
                           "topic": "pr1 open today", "trail_code": "PR1" if q else None})
    return f"ANSWER to: {text}"


brain.llm = fake_llm
brain.site_links = lambda reply, trails, lang, named=None: ""  # these tests check queueing; the page links are tested in test_followups
N = [0]


def msg(user, text=None, **kw):
    N[0] += 1
    m = {"from": user, "id": f"wamid.{N[0]}"}
    if text is not None:
        m.update(type="text", text={"body": text})
    m.update(kw)
    return m


def button(user, yes=True):
    return msg(user, type="interactive", interactive={"type": "button_reply", "button_reply": {
        "id": "consent_yes" if yes else "consent_no"}})


def pick(user, lang):
    return msg(user, type="interactive", interactive={"type": "list_reply", "list_reply": {"id": f"lang_{lang}"}})


def bodies():
    out = []
    for p in sent:
        if p["type"] == "text":
            out.append(p["text"]["body"])
        elif p["interactive"]["type"] == "list":
            out.append("<PICKER>")
        elif p["interactive"]["type"] == "button":
            out.append("<NOTICE>")
        else:
            out.append("<" + p["interactive"]["type"] + ">")
    sent.clear()
    return out


def tick():
    llm_control.tick(store.has_pending, app.drain)


def reset():
    sent.clear(), recorded.clear()
    store._db.execute("DELETE FROM pending")
    store._db.commit()
    host.running, host.free_gib, host.cmds[:] = False, 95.0, []
    model["up"] = False
    llm_control._state["start_at"] = 0.0
    store.set_flag(llm_control.FLAG, None)


def accepted_user(uid, lang="en"):
    store.reset(uid)
    store.set_user(uid, lang=lang, state="ready", consent="yes")


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        raise SystemExit(1)


# ---------------------------------------------------------------- tests
def test_real_llm_raises_when_down():
    reset()
    check(isinstance(_raises(lambda: real_llm([{"role": "user", "content": "x"}])), brain.LLMDown),
          "brain.llm() raises LLMDown when /v1/models is down")
    model["up"] = True  # 'up' per the probe, but the port refuses: it just went down
    check(isinstance(_raises(lambda: real_llm([{"role": "user", "content": "x"}])), brain.LLMDown),
          "brain.llm() raises LLMDown on connection refused")


def _raises(fn):
    try:
        fn()
    except Exception as e:
        return e


def test_down_gpu_free_new_visitor():
    """Before Accept nothing needs the model: a question gets the notice at once and the model starts loading;
    after Accept the question waits for the model (WAKING) and is answered when it's up."""
    reset()
    u = "351910000001"
    store.reset(u)
    app.process(msg(u, "Is PR1 open today?"))
    b = bodies()
    check(b == ["<NOTICE>"], f"down+free: privacy notice at once, no model needed {b}")
    check("docker start levadinho-llm" in host.cmds and host.running, "down+free: model warm-up started")
    check(store.get_user(u)["state"].startswith("notice:q:"), "question waits for Accept")
    app.process(msg(u, "And the weather?"))
    check(bodies() == ["<NOTICE>"], "second message before Accept: notice again, both waiting")
    check(store.get_user(u)["state"] == "notice:q:Is PR1 open today?\nAnd the weather?", "both questions kept")
    check(not any(r[0] == "turn" for r in recorded), "nothing recorded before acceptance")
    app.process(button(u, True))
    b = bodies()
    check(b == [brain.WAKING["en"]] and len(store.pending_all()) == 1, f"Accept while loading → WAKING, queued {b}")
    model["up"] = True
    tick()
    b = bodies()
    check(len(b) == 1 and b[0].startswith("ANSWER to: Is PR1 open today?") and not store.pending_all(),
          f"model up → the waiting questions answered {b}")


def test_down_gpu_busy_callback():
    reset()
    u = "351910000002"
    accepted_user(u, "de")
    host.free_gib = 20.0  # someone else's job holds the GPU
    app.process(msg(u, "Ist der PR1 heute offen?"))
    b = bodies()
    check(b == [brain.BUSY["de"]], f"down+busy: BUSY (de) sent {b}")
    check("docker start levadinho-llm" not in host.cmds, "down+busy: model NOT started")
    check(store.pending_all()[0]["reason"] == "busy", "callback queued with reason busy")
    check(not any(r[0] == "turn" for r in recorded), "not recorded yet (recorded whole on replay)")
    tick()
    check(bodies() == [] and not host.running, "GPU still busy: waiter waits, starts nothing")
    host.free_gib = 95.0
    tick()
    check(host.running and not model["up"], "GPU freed: waiter starts the model")
    model["up"] = True
    tick()
    b = bodies()
    check(len(b) == 1 and b[0] == "ANSWER to: Ist der PR1 heute offen?", f"callback answer sent {b}")
    outs = [r[2].get("msg_kind") or r[1][2] for r in recorded if r[0] == "turn" and r[1][1] == "out"]
    texts = [r[1][3] for r in recorded if r[0] == "turn" and r[1][1] == "out"]
    check(texts[0] == brain.BUSY["de"] and texts[1].startswith("ANSWER"),
          "record: BUSY notice + answer recorded as out turns")
    check(any(r[0] == "turn" and r[1][1] == "in" for r in recorded), "record: incoming question recorded")


def test_callback_expiry():
    reset()
    u = "351910000003"
    accepted_user(u)
    host.free_gib = 20.0
    app.process(msg(u, "Is PR1 open today?"))
    bodies()
    store._db.execute("UPDATE last_inbound SET at=? WHERE user=?", (time.time() - 25 * 3600, u))
    store._db.commit()
    host.free_gib = 95.0
    model["up"] = True
    recorded.clear()
    tick()
    check(bodies() == [] and not store.pending_all(), "outside the 24 h window: dropped, nothing sent")
    check(any(r[0] == "turn" and r[1][1] == "in" for r in recorded), "dropped message still recorded (accepted user)")


def test_web_tag_flow():
    """A website link's greeting is in the page's language: straight to the notice in that language
    (no menu, no model); the page is kept as the source; Accept → the short line, no guide link."""
    reset()
    u = "351910000004"
    store.reset(u)
    for text, tag, lang in (("Olá Levadinho! 👋 #web-pr1", "web-pr1", "pt"),
                            ("Hello Levadinho! 👋 #web-sunrise", "web-sunrise", "en"),
                            ("Cześć Levadinho! 👋 #web-simplifica-from-abroad", "web-simplifica-from-abroad", "pl")):
        store.reset(u)
        meta = {"events": []}
        out = brain.handle(u, text=text, meta=meta)  # model is DOWN: must not need it
        check(out[0]["type"] == "buttons" and meta["campaign"] == tag, f"{tag}: notice at once, campaign recorded")
        check(store.get_user(u)["lang"] == lang and store.get_user(u)["source"] == tag, f"{tag}: language {lang}, source kept")
        check(meta["events"][0] == ("qr_scanned", {"campaign": tag, "source": "web"}), f"{tag}: qr_scanned source=web")
        meta = {"events": []}
        out = brain.handle_consent(u, True, meta=meta)
        check(out == [{"type": "text", "body": brain.ASK[lang]}], f"{tag}: Accept → short line")
        check(not any(e[0] == "guide_link_sent" for e in meta["events"]), f"{tag}: no guide link")
    meta = {"events": []}
    brain.handle(u, text="Olá Levadinho! 👋 #bogus", meta=meta)
    check(meta["campaign"] is None, "unknown non-web tag ignored")


def test_no_llm_paths_while_down():
    reset()
    u = "351910000005"
    store.reset(u)
    app.process(msg(u, type="request_welcome"))
    app.process(msg(u, "Olá Levadinho! 👋 #ely"))
    app.process(pick(u, "en"))
    app.process(button(u, True))
    b = bodies()
    check(b[:3] == ["<PICKER>", "<PICKER>", "<NOTICE>"] and "?r=ely-test" in b[3],
          f"campaign QR → picker → notice → guide link, model down {b[:3]}")
    app.process(msg(u, "guia"))
    app.process(msg(u, type="location", location={"latitude": 32.7355, "longitude": -16.9288}))
    b = bodies()
    check(b[0] == "<location_request_message>" and "📍" in b[1],
          "guide word + location pin handled with the model down")
    check(not store.pending_all() and "docker start levadinho-llm" not in host.cmds, "nothing queued, model not woken")


def test_deferred_question_after_accept():
    reset()
    u = "351910000006"
    store.reset(u)
    model["up"] = True
    app.process(msg(u, "Czy PR1 jest dziś otwarty?"))
    check(bodies() == ["<NOTICE>"], "question before Accept → notice")
    model["up"] = False
    recorded.clear()
    app.process(button(u, True))
    b = bodies()
    check(b == [brain.WAKING["pl"]], f"Accept while down → consent kept, WAKING (pl) {b}")
    check(store.get_user(u)["consent"] == "yes", "consent stored")
    check(any(r[0] == "event" and r[1][1] == "consent_given" for r in recorded), "consent_given recorded now")
    model["up"] = True
    tick()
    b = bodies()
    check(len(b) == 1 and b[0] == "ANSWER to: Czy PR1 jest dziś otwarty?", f"question answered once up {b}")


def test_normal_flow_up():
    reset()
    u = "351910000007"
    accepted_user(u, "fr")
    model["up"] = True
    app.process(msg(u, "Le PR1 est-il ouvert aujourd'hui ?"))
    b = bodies()
    check(b == ["ANSWER to: Le PR1 est-il ouvert aujourd'hui ?"] and not store.pending_all(), "model up: answered directly")


def test_idle_stop():
    reset()
    host.running = True
    llm_control._state["activity"] = time.time()
    check(not llm_control.stop_if_idle(30), "not idle yet: kept")
    llm_control._state["activity"] = time.time() - 31 * 60
    check(not llm_control.stop_if_idle(30, pending=True), "idle but messages pending: kept")
    llm_control.AUTO_STOP = False
    check(not llm_control.stop_if_idle(30), "AUTO_STOP=0 and started by start.sh: kept")
    store.set_flag(llm_control.FLAG, "webhook")
    check(llm_control.stop_if_idle(30) and not host.running, "AUTO_STOP=0, started by webhook: stopped")
    llm_control.AUTO_STOP = True
    host.running = True
    check(llm_control.stop_if_idle(30) and not host.running, "AUTO_STOP=1: stopped after 30 idle min")
    check(all(c.startswith(("docker ps", "docker stop levadinho-llm")) for c in host.cmds),
          "only our container is ever stopped")


def test_on_demand_off():
    reset()
    llm_control.ON_DEMAND = False
    e = _raises(lambda: real_llm([{"role": "user", "content": "x"}]))
    check(not isinstance(e, brain.LLMDown), f"LLM_ON_DEMAND=0: old behaviour, plain error ({type(e).__name__})")
    llm_control._state["activity"] = 0
    host.running = True
    check(not llm_control.stop_if_idle(30) and host.running, "LLM_ON_DEMAND=0: never stops the model")
    llm_control.ON_DEMAND = True


def test_guess_lang():
    cases = {"Is PR1 open today?": "en", "O PR1 está aberto hoje?": "pt", "Ist der PR1 heute offen?": "de",
             "Le PR1 est-il ouvert aujourd'hui ?": "fr", "Czy PR1 jest dziś otwarty?": "pl"}
    check(all(brain.guess_lang(t) == l for t, l in cases.items()), "notice language guess for 5 languages")



def test_owner_test_number_leaves_nothing():
    """bot/.env TEST_NUMBERS (owner, 2026-10-05): nothing recorded in analytics; "reset" erases the working
    store at once; after an hour of silence the next message starts as a new visitor."""
    reset()
    u = "447000000099"
    store.reset(u)
    app.TEST_NUMBERS.add(u)
    try:
        model["up"] = True
        app.process(msg(u, "Hello!"))
        app.process(button(u, True))
        app.process(msg(u, "Is PR1 open today?"))
        b = bodies()
        check(b[0] == "<NOTICE>" and b[-1].startswith("ANSWER to:"), f"test number: normal conversation {b}")
        check(recorded == [], f"test number: nothing in analytics {recorded}")
        check(store.get_user(u)["consent"] == "yes", "test number: working store used during the session")
        app.process(msg(u, "reset"))
        check(bodies() == [app.TEST_RESET_DONE] and store.get_user(u) is None and store.history(u) == [],
              "reset: erased at once, told so")
        app.process(msg(u, "Hello!"))
        store._db.execute("UPDATE last_inbound SET at = at - 7200 WHERE user = ?", (u,))
        store.set_user(u, consent="yes", base="Funchal")
        store._db.commit()
        app.process(msg(u, "Hello!"))
        check(store.get_user(u)["consent"] is None and store.get_user(u)["base"] is None,
              "after an hour of silence: starts as a new visitor")
        check(recorded == [], "still nothing in analytics")
        app.process(msg("447000000098", "Hello!"))  # not a test number: recorded as before
        check(recorded != [], "other numbers still recorded")
    finally:
        app.TEST_NUMBERS.discard(u)
        model["up"] = False

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            print(f"\n== {name}")
            fn()
    print("\nALL PASSED")
