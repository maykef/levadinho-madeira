"""Levadinho WhatsApp webhook (Meta Cloud API).

  GET  /webhook  — Meta's one-time verification handshake (hub.challenge).
  POST /webhook  — incoming messages. Signature-checked, de-duplicated, answered in the
                   background so Meta gets its 200 immediately.

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

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

HERE = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(HERE, ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)

import brain  # noqa: E402  (after .env so LLM_URL etc. can be overridden there)
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
        else:  # voice, photo, location, sticker… not in the trial
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
