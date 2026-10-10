"""Twilio WhatsApp Sandbox channel (since 2026-10-02: Meta banned the WhatsApp Business account).

app.py's POST /twilio checks the signature, turns Twilio's form into the same message dict the Meta
webhook hands to process() (normalise), and answers through here (send). brain.py is unchanged:

  - The sender id is the number as digits only ("447795966209"), exactly like Meta's `from`, so the
    working store, the HMAC visitor id and privacy_request.py find the same visitor on both channels.
  - The message dict carries "channel": "twilio" (a Meta message has no channel key = "meta"). It is
    kept in the pending queue, so a reply replayed after the model wakes goes out on the same channel.
  - Menus (since 2026-10-04, own sender +44 7455 718697): the language list and the Accept / Don't accept
    buttons go out as Twilio Content templates (twilio_content.py → twilio_content.json): a tappable
    list-picker and quick-reply buttons. A tap comes back as ListId / ButtonPayload and is turned into the
    list_reply / button_reply the Meta path gets (normalise). Without the templates (or if a send fails)
    they become plain text with typed replies (render), and a typed reply is turned back the same way
    (interpret), so process() runs the same branches.
  - "join bark-wood" (the sandbox join phrase) is a first contact: the picker, like Meta's
    request_welcome. "join bark-wood #web-<page>" becomes a language-neutral greeting with that tag (picker; the tag is recorded).

Config (bot/.env): TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WA_FROM, TWILIO_WEBHOOK_URL.
"""
import json
import logging
import os
import re
import unicodedata

import brain
import store

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WA_FROM = os.environ.get("TWILIO_WA_FROM", "whatsapp:+14155238886")
# Twilio signs the URL it posts to, i.e. the public one: the Funnel strips /levadinho, so the app
# itself sees /twilio and can't rebuild it from the request.
TWILIO_WEBHOOK_URL = os.environ.get("TWILIO_WEBHOOK_URL",
                                    "https://microscopy-rig-system.tail53cc58.ts.net/levadinho/twilio")
CONTENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "twilio_content.json")
try:
    CONTENT = json.load(open(CONTENT_FILE))  # template name → Content SID (HX…)
except (OSError, ValueError):
    CONTENT = {}
MAX_CHARS = 1500  # WhatsApp via Twilio caps a body at 1,600; longer replies go out as several messages

log = logging.getLogger("levadinho")

# The privacy notice's last paragraph ("Tap *Accept* to continue.") without the buttons: the words to
# type instead. The decline words are brain's "Don't accept" button labels, so a visitor can still
# refuse or (after typing "privacy") withdraw.
ACCEPT_WORDS = "ACEITO / ACCEPT / ACCEPTER / AKZEPTIEREN / AKCEPTUJĘ"
DECLINE_WORDS = " / ".join(no.upper() for _, no in brain.CONSENT_BUTTONS.values())
REPLY_ACCEPT = {
    "pt": f"Responda *{ACCEPT_WORDS}* para continuar, ou {DECLINE_WORDS} para recusar.",
    "en": f"Reply *{ACCEPT_WORDS}* to continue, or {DECLINE_WORDS} to decline.",
    "fr": f"Répondez *{ACCEPT_WORDS}* pour continuer, ou {DECLINE_WORDS} pour refuser.",
    "de": f"Antworte *{ACCEPT_WORDS}*, um fortzufahren, oder {DECLINE_WORDS}, um abzulehnen.",
    "pl": f"Odpowiedz *{ACCEPT_WORDS}*, aby kontynuować, lub {DECLINE_WORDS}, aby odmówić.",
}


def fold(text):
    """Lower case, no accents, no emoji or punctuation: "AKCEPTUJĘ!" → "akceptuje"."""
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^\w' ]", " ", t).split())


LANG_REPLIES = {str(i): code for i, code in enumerate(brain.LANGS, 1)}
LANG_REPLIES.update({fold(name): code for code, name in brain.LANGS.items()})
LANG_REPLIES.update({code: code for code in brain.LANGS})
ACCEPT = {fold(w) for w in ACCEPT_WORDS.split(" / ")} | {"aceitar"}
ACCEPT |= {fold(yes) for yes, _ in brain.CONSENT_BUTTONS.values()}
DECLINE = {fold(w) for w in DECLINE_WORDS.split(" / ")} | {"nao aceito", "dont accept", "don t accept"}  # ’ from a phone keyboard


def configured():
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WA_FROM)


def check_signature(form, signature):
    """→ None if X-Twilio-Signature matches, else why not (for the log)."""
    from twilio.request_validator import RequestValidator
    if not TWILIO_AUTH_TOKEN:
        return "no auth token configured"
    if not signature:
        return "no signature header"
    if not RequestValidator(TWILIO_AUTH_TOKEN).validate(TWILIO_WEBHOOK_URL, form, signature):
        return "signature mismatch"
    return None


def normalise(form):
    """Twilio's form fields → the Meta-shaped message dict process() takes."""
    body = (form.get("Body") or "").strip()
    m = {"from": re.sub(r"\D", "", form.get("From", "")), "id": form.get("MessageSid", ""),
         "channel": "twilio", "profile_name": form.get("ProfileName") or None}
    if form.get("ListId"):  # a tap on the language list-picker
        m.update(type="interactive", interactive={"type": "list_reply", "list_reply": {"id": form["ListId"]}})
    elif form.get("ButtonPayload"):  # a tap on a quick-reply button (Accept / Don't accept)
        m.update(type="interactive", interactive={"type": "button_reply", "button_reply": {"id": form["ButtonPayload"]}})
    elif form.get("Latitude") and form.get("Longitude"):
        m.update(type="location", location={"latitude": form["Latitude"], "longitude": form["Longitude"]})
    elif body.lower().startswith("join "):  # the sandbox join phrase: a first contact, no question
        tag = re.search(r"#([a-z0-9-]+)", body.lower())
        if tag:
            # no greeting word: the join phrase says nothing about the visitor's language, so the picker
            m.update(type="text", text={"body": f"Levadinho! 👋 #{tag.group(1)}"})
        else:
            m.update(type="request_welcome")
    elif body:
        m.update(type="text", text={"body": body})
    elif int(form.get("NumMedia") or 0):
        m.update(type=(form.get("MediaContentType0") or "media").split("/")[0])  # "audio", "image"…
    else:
        m.update(type="unsupported")
    return m


def interpret(message):
    """A typed answer to the plain-text picker or notice → the list_reply / button_reply Meta sends."""
    if message.get("type") != "text":
        return message
    word = fold(message["text"]["body"])
    state = (store.get_user(message["from"]) or {}).get("state") or ""
    if state.startswith("picking") and (word in DECLINE or word == str(len(brain.LANGS) + 1)):  # the menu's last row
        return {**message, "type": "interactive", "interactive": {
            "type": "list_reply", "list_reply": {"id": "consent_no"}}}
    if state.startswith("picking") and word in LANG_REPLIES:
        return {**message, "type": "interactive", "interactive": {
            "type": "list_reply", "list_reply": {"id": f"lang_{LANG_REPLIES[word]}"}}}
    if state.startswith("notice:") and (word in ACCEPT or word in DECLINE):
        return {**message, "type": "interactive", "interactive": {
            "type": "button_reply", "button_reply": {"id": "consent_yes" if word in ACCEPT else "consent_no"}}}
    return message


def render(msg):
    """brain's message dict → plain text (the sandbox has no list, buttons or location request)."""
    if msg["type"] == "list":
        rows = [f"{i} {brain.LANGS[code]}" for i, (code, _) in enumerate(msg["options"], 1)]
        return msg["body"] + "\n\n" + " · ".join(rows + [f"{len(rows) + 1} {msg['decline'][1]}"])
    if msg["type"] == "buttons":
        ids = [bid for bid, _ in msg["buttons"]]
        if ids == ["consent_yes", "consent_no"]:
            yes = msg["buttons"][0][1]
            lang = next((code for code, (y, _) in brain.CONSENT_BUTTONS.items() if y == yes), "en")
            return msg["body"].rsplit("\n\n", 1)[0] + "\n\n" + REPLY_ACCEPT[lang]
        return msg["body"] + "\n\n" + "\n".join(f"{i} {title}" for i, (_, title) in enumerate(msg["buttons"], 1))
    if msg["type"] == "location_request":
        return msg["body"] + "\n📎 → 📍"
    return msg["body"]


def split(text, limit=MAX_CHARS):
    """Cut a reply into pieces of at most `limit` characters, on paragraph boundaries where possible
    (then lines, then words, then a hard cut)."""
    if len(text) <= limit:
        return [text]
    for sep in ("\n\n", "\n", " "):
        if sep in text:
            break
    else:
        return [text[i:i + limit] for i in range(0, len(text), limit)]
    parts, cur = [], ""
    for piece in text.split(sep):
        if len(piece) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.extend(split(piece, limit))
        elif not cur:
            cur = piece
        elif len(cur) + len(sep) + len(piece) <= limit:
            cur += sep + piece
        else:
            parts.append(cur)
            cur = piece
    if cur:
        parts.append(cur)
    return parts


_client_cache = []


def _client():
    if not _client_cache:
        from twilio.rest import Client
        _client_cache.append(Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    return _client_cache[0]


def content(msg):
    """brain's list / consent buttons → (Content SID, variables) for the tappable menu, or None."""
    if msg["type"] == "list" and CONTENT.get("levadinho_lang_picker"):
        return CONTENT["levadinho_lang_picker"], None
    if msg["type"] == "buttons" and [bid for bid, _ in msg["buttons"]] == ["consent_yes", "consent_no"]:
        yes = msg["buttons"][0][1]
        lang = next((code for code, (y, _) in brain.CONSENT_BUTTONS.items() if y == yes), "en")
        if CONTENT.get(f"levadinho_consent_{lang}") and len(msg["body"]) <= 1000:
            return CONTENT[f"levadinho_consent_{lang}"], {"1": msg["body"]}
    return None


def send(to, msg):
    """One of brain's messages → the visitor (digits-only number), in as many pieces as it takes, in order."""
    if msg.get("type") == "image":  # a webcam picture (served by app.py at /cam/<id>.jpg on the Funnel)
        try:
            kw = {"body": msg["body"]} if msg.get("body") else {}
            log.info("Twilio sent %s (image)", _client().messages.create(
                from_=TWILIO_WA_FROM, to=f"whatsapp:+{to}", media_url=[msg["url"]], **kw).sid)
        except Exception as e:
            log.error("Twilio image failed: %s %s", getattr(e, "code", ""), getattr(e, "msg", None) or e)
        return
    menu = content(msg)
    if menu:
        sid, variables = menu
        try:
            kw = {"content_variables": json.dumps(variables)} if variables else {}
            log.info("Twilio sent %s (menu %s)", _client().messages.create(
                from_=TWILIO_WA_FROM, to=f"whatsapp:+{to}", content_sid=sid, **kw).sid, sid)
            return
        except Exception as e:  # fall back to the typed-reply text below
            log.error("Twilio menu %s failed (%s %s); sending text", sid, getattr(e, "code", ""),
                      getattr(e, "msg", None) or e)
    for part in split(render(msg)):
        try:
            sid = _client().messages.create(from_=TWILIO_WA_FROM, to=f"whatsapp:+{to}", body=part).sid
            log.info("Twilio sent %s", sid)
        except Exception as e:  # TwilioRestException carries the HTTP status, Twilio's code and its message
            log.error("Twilio API %s: %s %s", getattr(e, "status", "?"), getattr(e, "code", ""),
                      getattr(e, "msg", None) or e)
            return
