"""Levadinho WhatsApp webhook (Meta Cloud API).

  GET  /webhook  — Meta's one-time verification handshake (hub.challenge).
  POST /webhook  — incoming messages. Signature-checked, de-duplicated, answered in the
                   background so Meta gets its 200 immediately.
  GET  /guide/   — the audio-guide web app (guide/), plus each route's data and audio from
                   routes/ (public) and routes_private/ (needs the visitor's guide token).

Config (bot/.env, never committed):
  WA_TOKEN            access token from the Meta app (WhatsApp → API Setup)
  WA_PHONE_NUMBER_ID  the bot number's Phone number ID
  WA_APP_SECRET       App settings → Basic → App secret (verifies X-Hub-Signature-256)
  WA_VERIFY_TOKEN     any string you choose; paste the same one into Meta's webhook form

Run:  cd bot && uvicorn app:app --host 127.0.0.1 --port 5020
"""
import hashlib
import hmac
import json
import logging
import os
import urllib.request

import re
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(HERE, ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)

import brain  # noqa: E402  (after .env so LLM_URL etc. can be overridden there)
import geo  # noqa: E402
import store  # noqa: E402

WA_TOKEN = os.environ.get("WA_TOKEN", "")
WA_PHONE_NUMBER_ID = os.environ.get("WA_PHONE_NUMBER_ID", "")
WA_APP_SECRET = os.environ.get("WA_APP_SECRET", "")
WA_VERIFY_TOKEN = os.environ.get("WA_VERIFY_TOKEN", "")
GRAPH = "https://graph.facebook.com/v23.0"

log = logging.getLogger("levadinho")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI()


def graph_post(payload):
    req = urllib.request.Request(
        f"{GRAPH}/{WA_PHONE_NUMBER_ID}/messages", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except urllib.error.HTTPError as e:
        log.error("Graph API %s: %s", e.code, e.read().decode(errors="replace"))


def to_whatsapp(to, msg):
    """brain's message dict → Cloud API payload."""
    base = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": to}
    if msg["type"] == "list":
        return {**base, "type": "interactive", "interactive": {
            "type": "list",
            "body": {"text": msg["body"]},
            "action": {"button": msg["button"], "sections": [{
                "title": "Idioma / Language",
                "rows": [{"id": f"lang_{code}", "title": label} for code, label in msg["options"]]}]}}}
    if msg["type"] == "location_request":
        return {**base, "type": "interactive", "interactive": {
            "type": "location_request_message", "body": {"text": msg["body"]},
            "action": {"name": "send_location"}}}
    return {**base, "type": "text", "text": {"body": msg["body"], "preview_url": False}}


def process(message):
    sender = message["from"]
    kind = message.get("type")
    log.info("incoming %s from …%s", kind, sender[-4:])
    try:
        if kind == "request_welcome":  # visitor opened the chat for the first time (Meta welcome message)
            store.set_user(sender, state="picking")
            out = [brain.picker()]
        elif kind == "text":
            out = brain.handle(sender, text=message["text"]["body"])
        elif kind == "interactive" and message["interactive"].get("type") == "list_reply":
            out = brain.handle(sender, choice=message["interactive"]["list_reply"]["id"].removeprefix("lang_"))
        elif kind == "location":  # a pin (live location never reaches the Cloud API)
            loc = message["location"]
            out = brain.handle_location(sender, float(loc["latitude"]), float(loc["longitude"]))
        else:  # voice, photo, sticker… not in the trial
            lang = (store.get_user(sender) or {}).get("lang") or "en"
            out = [{"type": "text", "body": brain.TEXT_ONLY[lang]}]
    except Exception:
        log.exception("failed to handle message from %s", sender[-4:])
        out = [{"type": "text", "body": brain.TEXT_ERROR}]
    for msg in out:
        graph_post(to_whatsapp(sender, msg))


@app.get("/webhook")
def verify(request: Request):
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and WA_VERIFY_TOKEN and q.get("hub.verify_token") == WA_VERIFY_TOKEN:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(403)


@app.post("/webhook")
async def receive(request: Request, background: BackgroundTasks):
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(WA_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not WA_APP_SECRET or not hmac.compare_digest(sig, expected):
        raise HTTPException(401)
    data = json.loads(raw)
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if store.first_time(message["id"]):
                    background.add_task(process, message)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------- audio guide
SAFE = re.compile(r"^[a-z0-9-]+$")


def _route_file(rid, rel, token):
    folder, private = geo.route_dir(rid) if SAFE.match(rid) else (None, None)
    if not folder or (private and not store.guide_token_ok(token, rid)):
        raise HTTPException(404)
    return FileResponse(os.path.join(folder, rel), headers={"Cache-Control": "no-cache"})


@app.get("/guide/r/{rid}/route.json")
def guide_route(rid: str, t: str = ""):
    return _route_file(rid, "route.json", t)


@app.get("/guide/r/{rid}/audio/{lang}/{clip}")
def guide_audio(rid: str, lang: str, clip: str, t: str = ""):
    if lang not in brain.LANGS or not re.fullmatch(r"[a-z0-9-]+\.mp3", clip):
        raise HTTPException(404)
    return _route_file(rid, f"audio/{lang}/{clip}", t)


TRACKLOG = os.path.join(HERE, "tracklog")


@app.post("/guide/log")
async def guide_log(request: Request, r: str = "", t: str = ""):
    """Lock-screen test: the guide posts GPS fixes, stop/clip events and heartbeats here."""
    if not SAFE.match(r) or not store.guide_token_ok(t, r):
        raise HTTPException(404)
    raw = await request.body()
    if len(raw) > 256_000:
        raise HTTPException(413)
    events = json.loads(raw)
    folder = os.path.join(TRACKLOG, r)
    os.makedirs(folder, exist_ok=True)
    srv = int(time.time() * 1000)
    with open(os.path.join(folder, f"{t}.jsonl"), "a", encoding="utf-8") as f:
        for e in events if isinstance(events, list) else []:
            if isinstance(e, dict):
                f.write(json.dumps({**e, "srv": srv}, ensure_ascii=False) + "\n")
    return {"ok": True}


app.mount("/guide", StaticFiles(directory=os.path.join(HERE, "guide"), html=True), name="guide")
