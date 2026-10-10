"""Levadinho WhatsApp webhook (Meta Cloud API, and the Twilio WhatsApp Sandbox).

  GET  /webhook  — Meta's one-time verification handshake (hub.challenge).
  POST /webhook  — incoming messages. Signature-checked, de-duplicated, answered in the
                   background so Meta gets its 200 immediately.
  POST /twilio   — the same for the Twilio WhatsApp Sandbox (X-Twilio-Signature, form-encoded,
                   empty TwiML back at once). See twilio_wa.py.
  GET  /guide/   — the audio-guide web app (guide/), plus each route's data and audio from
                   routes/ (public) and routes_private/ (needs the visitor's guide token).

Config (bot/.env, never committed):
  WA_TOKEN            access token from the Meta app (WhatsApp → API Setup)
  WA_PHONE_NUMBER_ID  the bot number's Phone number ID
  WA_APP_SECRET       App settings → Basic → App secret (verifies X-Hub-Signature-256)
  WA_VERIFY_TOKEN     any string you choose; paste the same one into Meta's webhook form
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WA_FROM, TWILIO_WEBHOOK_URL   Twilio sandbox, see twilio_wa.py
  LLM_ON_DEMAND, LLM_AUTO_STOP, LLM_IDLE_MIN, LLM_GPU_FREE_GB   wake-on-demand, see llm_control.py

Wake-on-demand: the webhook runs all the time; the model is started when a message needs it and
stopped when idle. A message that needs the model while it's down is queued (store.py `pending`):
the visitor gets WAKING (GPU free, model starting) or BUSY (GPU used by another job; we write back
when it frees, inside WhatsApp's 24-hour window only). The waiter thread replays the queue.

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
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

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
import llm_control  # noqa: E402
import store  # noqa: E402
import twilio_wa  # noqa: E402

WA_TOKEN = os.environ.get("WA_TOKEN", "")
WA_PHONE_NUMBER_ID = os.environ.get("WA_PHONE_NUMBER_ID", "")
WA_APP_SECRET = os.environ.get("WA_APP_SECRET", "")
WA_VERIFY_TOKEN = os.environ.get("WA_VERIFY_TOKEN", "")
GRAPH = "https://graph.facebook.com/v23.0"
# The owner's own phones (owner, 2026-10-05): digits only, comma-separated, in bot/.env (never committed).
# A test number is never recorded in the analytics database or the guide logs; its working store is wiped
# when it writes after TEST_FRESH_S of silence, and at once when it sends "reset".
TEST_NUMBERS = {"".join(ch for ch in n if ch.isdigit()) for n in os.environ.get("TEST_NUMBERS", "").split(",") if n.strip()}
TEST_FRESH_S = 3600
TEST_RESET_WORDS = {"reset", "/reset"}
TEST_RESET_DONE = "🧪 Test number: everything about you is erased. Your next message starts as a new visitor."


def is_test(sender):
    return bool(sender) and sender in TEST_NUMBERS

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
                "rows": [{"id": f"lang_{code}", "title": label, "description": msg["notes"][code]}
                         for code, label in msg["options"]]
                        + [{"id": msg["decline"][0], "title": msg["decline"][1], "description": msg["decline"][2]}]}]}}}
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


def send(message, msg):
    """One of brain's messages → the visitor, on the channel `message` came in on."""
    if message.get("channel") == "twilio":
        twilio_wa.send(message["from"], msg)
    else:
        graph_post(to_whatsapp(message["from"], msg))


WINDOW_S = 24 * 3600 - 120  # WhatsApp's customer-service window, with a little margin


def process(message, replay=None):
    """One incoming WhatsApp message → replies + analytics record. `replay` is set when the waiter
    runs a message that was queued while the model was asleep (the stored pending payload).
    A Twilio message ("channel": "twilio") arrives in the same shape (twilio_wa.normalise); a typed
    answer to its plain-text picker / notice is turned into the list / button reply here."""
    if message.get("channel") == "twilio" and replay is None:
        message = twilio_wa.interpret(message)
    sender = message["from"]
    kind = message.get("type")
    log.info("%s %s from …%s%s", "replaying" if replay else "incoming", kind, sender[-4:],
             " (twilio)" if message.get("channel") == "twilio" else "")
    meta = {"events": []}
    if replay is None and is_test(sender):
        last = store.last_inbound(sender)
        if kind == "text" and message["text"]["body"].strip().lower() in TEST_RESET_WORDS:
            store.erase(sender)
            log.info("test number …%s: erased on request", sender[-4:])
            send(message, {"type": "text", "body": TEST_RESET_DONE})
            return
        if last and time.time() - last > TEST_FRESH_S:
            store.erase(sender)
            log.info("test number …%s: new session, working store erased", sender[-4:])
    if replay is None:
        llm_control.touch()
        store.note_inbound(sender)
        new_visitor = store.get_user(sender) is None
    else:
        new_visitor = replay.get("new_visitor", False)
    in_text, in_kind, pin = None, kind, None
    try:
        if kind == "request_welcome":  # visitor opened the chat for the first time (Meta welcome message)
            store.set_user(sender, state="picking")
            out = [brain.picker()]
        elif kind == "text":
            in_text = message["text"]["body"]
            out = brain.handle(sender, text=in_text, meta=meta)
        elif kind == "interactive" and message["interactive"].get("list_reply", {}).get("id") == "consent_no":
            in_kind, in_text = "consent_choice", "consent_no"  # the menu's "Decline" row
            out = brain.handle_consent(sender, False, meta=meta)
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
    except brain.LLMDown:
        # Nothing is recorded yet: the exchange is recorded whole when it's replayed (or expires).
        notice = defer(sender, message, new_visitor, replay)
        if notice:
            send(message, notice)
        return
    except Exception:
        log.exception("failed to handle message from %s", sender[-4:])
        out = [{"type": "text", "body": brain.TEXT_ERROR}]
    if meta.get("warm_up") and llm_control.ON_DEMAND:  # a message waits for Accept: load the model meanwhile
        try:
            llm_control.start()
        except Exception:
            log.exception("warm-up start failed")
    if meta.get("deferred_question"):  # accepted the notice; the question asked before waits for the model
        synthetic = {"from": sender, "type": "text", "id": f"deferred-{message.get('id', '')}",
                     "text": {"body": meta["deferred_question"]},
                     **({"channel": message["channel"]} if message.get("channel") else {})}
        notice = defer(sender, synthetic, False, keep_notice=False)  # the notice is recorded with this exchange
        out = out + [notice] if notice else out
    for msg in out:
        send(message, msg)
    prior = (replay or {}).get("notice")  # the wake/busy notice sent when this message was queued
    record(sender, new_visitor, in_kind, in_text, pin, meta, ([prior] if prior else []) + out)


def defer(sender, message, new_visitor, replay=None, keep_notice=True):
    """Queue a message that needs the sleeping model; start the model if the GPU has room.
    → the notice to send now (WAKING / BUSY), or None if this visitor was already told.
    keep_notice: store the notice with the message, so it's recorded when the message is."""
    already = store.has_pending(sender) or replay is not None
    st = llm_control.state()
    if st == "free":
        st = llm_control.start()
    reason = "busy" if st == "busy" else "wake"
    lang = brain.notice_lang(sender, (message.get("text") or {}).get("body"))
    notice = None if already else {"type": "text", "body": (brain.BUSY if reason == "busy" else brain.WAKING)[lang]}
    store.queue_pending(sender, reason, {
        "message": message, "new_visitor": new_visitor,
        "notice": (notice if keep_notice else None) if notice else (replay or {}).get("notice")})
    log.info("queued %s from …%s (%s, model %s)", message.get("type"), sender[-4:], reason, st)
    return notice


def drain(up):
    """Waiter pass: drop queued messages outside WhatsApp's 24-hour window; if the model is up,
    replay the rest, oldest first."""
    for row in store.pending_all():
        p, user = row["payload"], row["user"]
        last = store.last_inbound(user) or row["at"]
        if time.time() - last > WINDOW_S:
            store.drop_pending(row["id"])
            log.warning("dropped a queued message from …%s: outside the 24 h window (%s)", user[-4:], row["reason"])
            msg = p["message"]
            lang = (store.get_user(user) or {}).get("lang")
            record(user, p.get("new_visitor", False), msg.get("type"), (msg.get("text") or {}).get("body"), None,
                   {"events": [], "lang": lang}, [p["notice"]] if p.get("notice") else [])
            continue
        if up:
            store.drop_pending(row["id"])
            process(p["message"], replay=p)


@app.on_event("startup")
def start_waiter():
    if llm_control.ON_DEMAND:
        llm_control.run_waiter(store.has_pending, drain)
        log.info("wake-on-demand on: model %s, idle stop after %s min (auto-stop %s)",
                 llm_control.state(), llm_control.IDLE_MIN, llm_control.AUTO_STOP)


def record(sender, new_visitor, in_kind, in_text, pin, meta, out, channel="whatsapp"):
    """Permanent pseudonymous record of this exchange (analytics.py). Never breaks the reply.

    Only for visitors who accepted the privacy notice (brain.CONSENT_*). Anyone else leaves just an
    anonymous trace: event type, time and language, no visitor id, no text, no position. That is also
    how accepts vs. declines are counted (consent_given / consent_declined events)."""
    if is_test(sender):  # the owner's test phones leave nothing in the analytics database
        return
    try:
        lang = meta.get("lang")
        consent = (store.get_user(sender) or {}).get("consent")
        types = [etype for etype, _ in meta["events"]]
        if "consent_withdrawn" in types:  # keep the proof of withdrawal, nothing else
            vid = analytics.visitor_id_for(sender)
            analytics.set_consent(vid, "withdrawn", brain.CONSENT_VERSION)
            analytics.event(channel, "consent_withdrawn", vid=vid, lang=lang, version=brain.CONSENT_VERSION)
            return
        if consent != "yes":
            analytics.event(channel, "consent_declined" if "consent_declined" in types else "message_unrecorded",
                            lang=lang, **({} if "consent_declined" in types else {"kind": in_kind}))
            return
        new_visitor = new_visitor or not analytics.visitor_known(sender)
        vid = analytics.touch_visitor(sender, lang)
        if "consent_given" in types:
            analytics.set_consent(vid, "given", brain.CONSENT_VERSION)
        if new_visitor:
            analytics.event(channel, "conversation_started", vid=vid, lang=lang, first_text_kind=in_kind)
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
            analytics.event(channel, etype, vid=vid, session=f.pop("session", None), route=f.pop("route", None),
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
        log.info("webhook verify: accepted")
        return PlainTextResponse(q.get("hub.challenge", ""))
    log.warning("webhook verify: REJECTED (mode=%s, token %s)", q.get("hub.mode"),
                "missing" if not q.get("hub.verify_token") else "mismatch")
    raise HTTPException(403)


@app.post("/webhook")
async def receive(request: Request, background: BackgroundTasks):
    # Every delivery from Meta is logged (counts and outcome only: no phone numbers, no IPs), so a
    # silent stop — Meta not delivering vs. us rejecting — shows up in app.log. See also watchdog.sh.
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(WA_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not WA_APP_SECRET or not hmac.compare_digest(sig, expected):
        log.warning("webhook POST REJECTED: %s (%d bytes)",
                    "no app secret configured" if not WA_APP_SECRET else
                    "no signature header" if not sig else "signature mismatch", len(raw))
        raise HTTPException(401)
    try:
        data = json.loads(raw)
    except ValueError:
        log.warning("webhook POST REJECTED: body is not JSON (%d bytes)", len(raw))
        raise HTTPException(400)
    n_msg = n_new = n_status = 0
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            n_status += len(value.get("statuses", []))
            for status in value.get("statuses", []):
                if status.get("status") == "failed":   # Meta couldn't deliver one of OUR replies
                    log.warning("reply delivery FAILED: %s", json.dumps(status.get("errors", []))[:300])
            for message in value.get("messages", []):
                n_msg += 1
                if store.first_time(message["id"]):
                    n_new += 1
                    background.add_task(process, message)
    log.info("webhook POST ok: %d message(s) (%d new), %d status update(s)", n_msg, n_new, n_status)
    return {"ok": True}


@app.post("/twilio")
async def twilio_receive(request: Request, background: BackgroundTasks):
    # Twilio times the webhook out at 15 s: answer with empty TwiML at once, reply in the background
    # through the REST API (twilio_wa.send). Logged like /webhook: outcome only, no numbers or IPs.
    form = dict((await request.form()).items())
    why = twilio_wa.check_signature(form, request.headers.get("X-Twilio-Signature", ""))
    if why:
        log.warning("twilio POST REJECTED: %s (%d field(s))", why, len(form))
        raise HTTPException(403)
    message = twilio_wa.normalise(form)
    new = bool(message["from"] and message["id"]) and store.first_time(message["id"])
    if new:
        background.add_task(process, message)
    log.info("twilio POST ok: %s (%s)", message["type"], "new" if new else "duplicate or empty")
    return Response("<Response/>", media_type="application/xml")


# ---------------------------------------------------------------- the chat on our pages (2026-10-10)
# levadinho-madeira.com pages open on Levadinho's chat (chat.js); its questions come here. Same brain, same privacy
# notice (Accept first), same analytics as WhatsApp, channel "web". The visitor is "web:<code>", a random code
# chat.js keeps in the browser; no IP address is stored (only counted in memory for the rate limit).
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(CORSMiddleware, allow_origins=["https://levadinho-madeira.com", "https://www.levadinho-madeira.com"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"], max_age=3600)
WEB_SID = re.compile(r"[a-z0-9]{12,32}")
_geo = None


def web_country(ip):
    """ISO country of the visitor's IP (DB-IP Lite in bot/geoip, local lookup). Only the country is kept, never the IP."""
    global _geo
    try:
        if _geo is None:
            import maxminddb
            _geo = maxminddb.open_database(os.path.join(HERE, "geoip", "dbip-country-lite.mmdb"))
        return ((_geo.get(ip) or {}).get("country") or {}).get("iso_code")
    except Exception:
        log.exception("country lookup failed")
        return None
WEB_TAG = re.compile(r"web-[a-z0-9-]{1,40}")
_web_hits = {}


def _web_limited(key, limit, window=600):
    now = time.time()
    hits = [t for t in _web_hits.get(key, []) if now - t < window]
    _web_hits[key] = hits + [now]
    if len(_web_hits) > 5000:
        for k in [k for k, v in _web_hits.items() if not v or now - v[-1] > window]:
            _web_hits.pop(k, None)
    return len(hits) >= limit


def _web_out(msgs):
    out = []
    for m in msgs:
        if m.get("type") == "buttons":
            out.append({"type": "buttons", "body": m["body"], "buttons": [list(b) for b in m["buttons"]]})
        elif m.get("type") == "image":
            out.append({"type": "image", "url": m["url"]})
        elif m.get("body"):
            out.append({"type": "text", "body": m["body"]})
    return out


@app.post("/webchat")
async def webchat(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400)
    sid, tag = str(body.get("sid", "")), str(body.get("tag", ""))
    lang = body.get("lang") if body.get("lang") in brain.LANGS else "en"
    text, choice = str(body.get("text") or "").strip()[:500], body.get("choice")
    if not WEB_SID.fullmatch(sid) or not WEB_TAG.fullmatch(tag) or not (text or choice in ("consent_yes", "consent_no")):
        raise HTTPException(400)
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    if _web_limited("s:" + sid, 20) or _web_limited("i:" + ip, 60):
        return {"messages": [{"type": "text", "body": brain.WEB_SLOW_DOWN.get(lang, brain.WEB_SLOW_DOWN["en"])}]}
    user = "web:" + sid
    cc = web_country(ip)
    if cc:
        analytics.WEB_COUNTRY[user] = cc
    new_visitor = store.get_user(user) is None
    if new_visitor:
        store.set_user(user, lang=lang, source=tag)
    else:
        store.set_user(user, source=tag)
    llm_control.touch()
    meta = {"events": []}

    def run():
        if choice:
            return brain.handle_consent(user, choice == "consent_yes", meta)
        return brain.handle(user, text=text, meta=meta)
    try:
        out = await run_in_threadpool(run)
    except brain.LLMDown:
        st = llm_control.start()
        waking = st != "busy"
        note = (brain.WAKING if waking else brain.BUSY_WEB).get(lang) or (brain.WAKING if waking else brain.BUSY_WEB)["en"]
        return {"messages": [{"type": "text", "body": note}], "waking": waking}
    if meta.get("deferred_question"):  # accepted while the model sleeps: the question is asked again by chat.js
        st = llm_control.start()
        return {"messages": [{"type": "text", "body": brain.WAKING.get(lang, brain.WAKING["en"])}], "waking": st != "busy",
                "retry": meta["deferred_question"]}
    if meta.get("warm_up") and llm_control.ON_DEMAND:
        llm_control.start()
    record(user, new_visitor, "text" if text else "interactive", text or choice, None, meta, out, channel="web")
    return {"messages": _web_out(out)}


@app.get("/cam/{cam_id}.jpg")
def cam(cam_id: str):
    """The latest grabbed frame of one of our webcams (kbtools.WEBCAMS), for the bot's webcam answers."""
    import kbtools
    if cam_id not in kbtools.WEBCAMS:
        return Response(status_code=404)
    path, _ = kbtools.latest_frame(cam_id)
    if not path:
        return Response(status_code=404)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=300"})


@app.get("/health")
def health():
    """Webhook up; "model": whether the model answers right now. chat.js shows the chat on our pages only when it
    does (owner, 2026-10-10: model asleep → serve the page directly)."""
    return {"ok": True, "model": llm_control.is_up()}


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
    if is_test(store.guide_token_user(t)):  # a test phone's walk: neither the log file nor the database
        return {"ok": True}
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
