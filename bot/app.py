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
import analytics  # noqa: E402  (permanent, pseudonymous record in Postgres; fail-soft)
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
    if msg["type"] == "buttons":
        return {**base, "type": "interactive", "interactive": {
            "type": "button", "body": {"text": msg["body"]},
            "action": {"buttons": [{"type": "reply", "reply": {"id": bid, "title": title}}
                                   for bid, title in msg["buttons"]]}}}
    if msg["type"] == "location_request":
        return {**base, "type": "interactive", "interactive": {
            "type": "location_request_message", "body": {"text": msg["body"]},
            "action": {"name": "send_location"}}}
    return {**base, "type": "text", "text": {"body": msg["body"], "preview_url": False}}


def process(message):
    sender = message["from"]
    kind = message.get("type")
    log.info("incoming %s from …%s", kind, sender[-4:])
    meta = {"events": []}
    new_visitor = store.get_user(sender) is None
    in_text, in_kind, pin = None, kind, None
    try:
        if kind == "request_welcome":  # visitor opened the chat for the first time (Meta welcome message)
            store.set_user(sender, state="picking")
            out = [brain.picker()]
        elif kind == "text":
            in_text = message["text"]["body"]
            out = brain.handle(sender, text=in_text, meta=meta)
        elif kind == "interactive" and message["interactive"].get("type") == "list_reply":
            in_kind, in_text = "language_choice", message["interactive"]["list_reply"]["id"].removeprefix("lang_")
            out = brain.handle(sender, choice=in_text, meta=meta)
        elif kind == "interactive" and message["interactive"].get("type") == "button_reply":
            in_kind = "consent_choice"
            in_text = message["interactive"]["button_reply"]["id"]
            out = brain.handle_consent(sender, in_text == "consent_yes", meta=meta)
        elif kind == "location":  # a pin (live location never reaches the Cloud API)
            loc = message["location"]
            pin = (float(loc["latitude"]), float(loc["longitude"]))
            out = brain.handle_location(sender, *pin, meta=meta)
        else:  # voice, photo, sticker… not in the trial
            lang = (store.get_user(sender) or {}).get("lang") or "en"
            meta["lang"] = lang
            meta["events"].append(("non_text_received", {"kind": kind, "lang": lang}))
            out = [{"type": "text", "body": brain.TEXT_ONLY[lang]}]
    except Exception:
        log.exception("failed to handle message from %s", sender[-4:])
        out = [{"type": "text", "body": brain.TEXT_ERROR}]
    for msg in out:
        graph_post(to_whatsapp(sender, msg))
    record(sender, new_visitor, in_kind, in_text, pin, meta, out)


def record(sender, new_visitor, in_kind, in_text, pin, meta, out):
    """Permanent pseudonymous record of this exchange (analytics.py). Never breaks the reply.

    Only for visitors who accepted the privacy notice (brain.CONSENT_*). Anyone else leaves just an
    anonymous trace: event type, time and language, no visitor id, no text, no position. That is also
    how accepts vs. declines are counted (consent_given / consent_declined events)."""
    try:
        lang = meta.get("lang")
        consent = (store.get_user(sender) or {}).get("consent")
        types = [etype for etype, _ in meta["events"]]
        if "consent_withdrawn" in types:  # keep the proof of withdrawal, nothing else
            vid = analytics.visitor_id_for(sender)
            analytics.set_consent(vid, "withdrawn", brain.CONSENT_VERSION)
            analytics.event("whatsapp", "consent_withdrawn", vid=vid, lang=lang, version=brain.CONSENT_VERSION)
            return
        if consent != "yes":
            analytics.event("whatsapp", "consent_declined" if "consent_declined" in types else "message_unrecorded",
                            lang=lang, **({} if "consent_declined" in types else {"kind": in_kind}))
            return
        new_visitor = new_visitor or not analytics.visitor_known(sender)
        vid = analytics.touch_visitor(sender, lang)
        if "consent_given" in types:
            analytics.set_consent(vid, "given", brain.CONSENT_VERSION)
        if new_visitor:
            analytics.event("whatsapp", "conversation_started", vid=vid, lang=lang, first_text_kind=in_kind)
        analytics.turn(sender, "in", in_kind, in_text, lang=lang, is_question=meta.get("is_question"),
                       intent=meta.get("intent"), topic=meta.get("topic"), trail=meta.get("trail"),
                       campaign=meta.get("campaign"), llm_scrub=in_kind == "text")
        if meta.get("resumed_question"):  # asked before Accept, answered right after it
            analytics.turn(sender, "in", "text", meta["resumed_question"], lang=lang, is_question=True,
                           intent=meta.get("intent"), topic=meta.get("topic"), trail=meta.get("trail"))
        if pin:
            analytics.fix("whatsapp_pin", *pin, vid=vid)
        for etype, f in meta["events"]:
            f = dict(f)
            analytics.event("whatsapp", etype, vid=vid, session=f.pop("session", None), route=f.pop("route", None),
                            campaign=f.pop("campaign", None) or meta.get("campaign"), lang=f.pop("lang", lang),
                            lat=f.pop("lat", None), lon=f.pop("lon", None), **f)
        ans = meta.get("answer") or {}
        for msg in out:
            is_answer = bool(ans) and msg.get("type") == "text"
            analytics.turn(sender, "out", msg.get("type", "text"), msg.get("body"), lang=lang,
                           campaign=meta.get("campaign"), latency_ms=ans.get("latency_ms") if is_answer else None,
                           model=ans.get("model") if is_answer else None, llm_scrub=is_answer)
    except Exception:
        log.exception("analytics record failed")


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
async def guide_log(request: Request, background: BackgroundTasks, r: str = "", t: str = ""):
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
    events = [e for e in events if isinstance(e, dict)] if isinstance(events, list) else []
    with open(os.path.join(folder, f"{t}.jsonl"), "a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps({**e, "srv": srv}, ensure_ascii=False) + "\n")
    background.add_task(analytics.guide_events, store.guide_token_user(t), t, r, events)
    return {"ok": True}


app.mount("/guide", StaticFiles(directory=os.path.join(HERE, "guide"), html=True), name="guide")
