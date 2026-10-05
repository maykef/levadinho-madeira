import json
"""Offline tests for the Twilio WhatsApp Sandbox route (app.py POST /twilio, twilio_wa.py). No model,
no Twilio, no Postgres: brain is mocked where the reply matters, Twilio's client is a fake, the SQLite
store is a scratch file and analytics writes nothing.

  python -m pytest bot/tests/test_twilio.py -q
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("LEVADINHO_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
os.environ["DB_URL"] = ""  # analytics writes nothing

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from twilio.request_validator import RequestValidator  # noqa: E402

import app  # noqa: E402
import brain  # noqa: E402
import store  # noqa: E402
import twilio_wa  # noqa: E402

TOKEN = "test-auth-token"
URL = "https://example.test/levadinho/twilio"
PHONE = "447700900123"


class FakeTwilio:
    def __init__(self):
        self.sent = []
        self.messages = self

    def create(self, from_, to, body=None, **kw):
        self.sent.append({"from_": from_, "to": to, "body": body, **kw} if kw else {"from_": from_, "to": to, "body": body})
        return type("Msg", (), {"sid": f"SM{len(self.sent):032d}"})()


@pytest.fixture
def tw(monkeypatch):
    fake = FakeTwilio()
    monkeypatch.setattr(twilio_wa, "TWILIO_AUTH_TOKEN", TOKEN)
    monkeypatch.setattr(twilio_wa, "TWILIO_WEBHOOK_URL", URL)
    monkeypatch.setattr(twilio_wa, "TWILIO_WA_FROM", "whatsapp:+14155238886")
    monkeypatch.setattr(twilio_wa, "_client", lambda: fake)
    monkeypatch.setattr(twilio_wa, "CONTENT", {})  # plain-text menus unless a test sets the templates
    monkeypatch.setattr(app, "record", lambda *a, **k: None)
    monkeypatch.setattr(app, "graph_post", lambda payload: pytest.fail("Meta send on the Twilio channel"))
    store.reset(PHONE)
    return fake


N = [0]


def form(body="", **extra):
    N[0] += 1
    f = {"From": f"whatsapp:+{PHONE}", "To": "whatsapp:+14155238886", "Body": body, "ProfileName": "Test Walker",
         "MessageSid": f"SM{N[0]:032x}", "NumMedia": "0"}
    f.update(extra)
    return f


def post(f, signature=None):
    sig = RequestValidator(TOKEN).compute_signature(URL, f) if signature is None else signature
    return TestClient(app.app).post("/twilio", data=f, headers={"X-Twilio-Signature": sig})


def test_signed_post_normalises_and_replies_in_background(tw, monkeypatch):
    seen, calls = [], []
    real_process = app.process
    monkeypatch.setattr(app, "process", lambda message, replay=None: (seen.append(message), real_process(message, replay)))
    monkeypatch.setattr(brain, "handle", lambda user, text=None, choice=None, meta=None:
                        calls.append((user, text)) or [{"type": "text", "body": "MOCK REPLY"}])

    r = post(form("Is PR1 open today?"))

    assert r.status_code == 200
    assert r.text == "<Response/>"
    assert r.headers["content-type"].startswith("application/xml")
    assert seen == [{"from": PHONE, "id": seen[0]["id"], "channel": "twilio", "profile_name": "Test Walker",
                     "type": "text", "text": {"body": "Is PR1 open today?"}}]
    assert seen[0]["id"].startswith("SM")
    assert calls == [(PHONE, "Is PR1 open today?")]
    assert tw.sent == [{"from_": "whatsapp:+14155238886", "to": f"whatsapp:+{PHONE}", "body": "MOCK REPLY"}]


def test_bad_signature_is_403(tw, monkeypatch):
    monkeypatch.setattr(app, "process", lambda *a, **k: pytest.fail("processed an unsigned post"))
    assert post(form("hello"), signature="bm90IGEgc2lnbmF0dXJl").status_code == 403
    assert post(form("hello"), signature="").status_code == 403
    f = form("hello")
    sig = RequestValidator(TOKEN).compute_signature(URL, f)
    f["Body"] = "tampered"
    assert post(f, signature=sig).status_code == 403
    assert tw.sent == []


def test_duplicate_message_sid_processed_once(tw, monkeypatch):
    seen = []
    monkeypatch.setattr(app, "process", lambda message, replay=None: seen.append(message))
    f = form("hello")
    assert post(f).status_code == 200
    assert post(f).status_code == 200
    assert len(seen) == 1


def test_location_and_media_normalise():
    loc = twilio_wa.normalise(form("", Latitude="32.73549", Longitude="-16.9288"))
    assert loc["type"] == "location" and loc["location"] == {"latitude": "32.73549", "longitude": "-16.9288"}
    audio = twilio_wa.normalise(form("", NumMedia="1", MediaContentType0="audio/ogg"))
    assert audio["type"] == "audio"


def test_join_is_first_contact_and_keeps_web_tag():
    assert twilio_wa.normalise(form("join bark-wood"))["type"] == "request_welcome"
    m = twilio_wa.normalise(form("join bark-wood #web-pr1"))
    assert m["type"] == "text" and m["text"]["body"] == "Levadinho! 👋 #web-pr1"


def test_plain_text_picker_and_notice_flow(tw):
    """join → numbered picker → "2" → notice with the typed Accept line → "accept" → short line. No model needed."""
    post(form("join bark-wood #web-fees"))
    assert tw.sent[-1]["body"].endswith("1 Português · 2 English · 3 Français · 4 Deutsch · 5 Polski")
    assert store.get_user(PHONE)["state"] == "picking:web-fees"

    post(form("2"))
    notice = tw.sent[-1]["body"]
    assert "https://levadinho-madeira.com/privacy/#en" in notice
    assert notice.endswith("Reply *ACEITO / ACCEPT / ACCEPTER / AKZEPTIEREN / AKCEPTUJĘ* to continue, "
                           "or NÃO ACEITAR / DON'T ACCEPT / REFUSER / ABLEHNEN / NIE AKCEPTUJĘ to decline.")
    assert "Tap *Accept*" not in notice
    assert store.get_user(PHONE)["lang"] == "en"

    post(form("Akceptuję!"))
    assert tw.sent[-1]["body"] == brain.ASK["en"]
    assert store.get_user(PHONE)["consent"] == "yes"


@pytest.mark.parametrize("reply", ["Ablehnen", "don’t accept", "NÃO ACEITAR", "nie akceptuje"])
def test_typed_decline_and_withdrawal(tw, reply):
    """A decline word on the notice = Don't accept: no service; after accepting, "privacy" + decline withdraws."""
    store.set_user(PHONE, lang="en", state="notice:")
    post(form(reply))
    assert store.get_user(PHONE)["consent"] == "no"
    assert tw.sent[-1]["body"] == brain.CONSENT_NO["en"]

    store.set_user(PHONE, consent="yes", state="ready")
    post(form("privacy"))
    assert "DON'T ACCEPT" in tw.sent[-1]["body"]
    post(form(reply))
    assert store.get_user(PHONE)["consent"] == "no"
    assert tw.sent[-1]["body"] == brain.CONSENT_WITHDRAWN["en"]


def test_picker_accepts_language_word():
    store.reset(PHONE)
    store.set_user(PHONE, state="picking")
    m = twilio_wa.interpret(twilio_wa.normalise(form("français")))
    assert m["interactive"]["list_reply"]["id"] == "lang_fr"
    store.set_user(PHONE, state="ready")  # outside the picker a digit is just text
    assert twilio_wa.interpret(twilio_wa.normalise(form("3")))["type"] == "text"


def test_split_long_reply_on_paragraphs():
    paras = [f"Paragraph {i}: " + "x" * 480 for i in range(7)]  # ~3,450 characters
    parts = twilio_wa.split("\n\n".join(paras))
    assert len(parts) > 1
    assert all(len(p) <= 1500 for p in parts)
    assert "\n\n".join(parts) == "\n\n".join(paras)  # nothing lost, order kept, cuts only between paragraphs
    assert all(p.startswith("Paragraph") for p in parts)
    huge = "word " * 700  # one 3,500-character paragraph: falls back to word boundaries
    assert all(len(p) <= 1500 for p in twilio_wa.split(huge.strip()))
    assert twilio_wa.split("short") == ["short"]


def test_long_reply_sent_as_several_messages_in_order(tw):
    body = "\n\n".join(f"Part {i} " + "y" * 700 for i in range(4))
    twilio_wa.send(PHONE, {"type": "text", "body": body})
    assert len(tw.sent) >= 2
    assert all(len(m["body"]) <= 1500 for m in tw.sent)
    assert "\n\n".join(m["body"] for m in tw.sent) == body


def test_queued_while_model_asleep_replays_on_twilio(tw, monkeypatch):
    """Model down → BUSY notice via Twilio, message queued with its channel → replayed via Twilio."""
    import llm_control
    store.set_user(PHONE, lang="en", state="ready", consent="yes")
    monkeypatch.setattr(llm_control, "state", lambda: "busy")  # GPU taken: nothing is started

    def down(*a, **k):
        raise brain.LLMDown()
    monkeypatch.setattr(brain, "handle", down)
    post(form("Is PR1 open today?"))
    assert [m["body"] for m in tw.sent] == [brain.BUSY["en"]]
    (row,) = [r for r in store.pending_all() if r["user"] == PHONE]
    assert row["payload"]["message"]["channel"] == "twilio"

    monkeypatch.setattr(brain, "handle", lambda user, text=None, choice=None, meta=None:
                        [{"type": "text", "body": f"ANSWER to: {text}"}])
    app.drain(up=True)
    assert tw.sent[-1] == {"from_": "whatsapp:+14155238886", "to": f"whatsapp:+{PHONE}",
                           "body": "ANSWER to: Is PR1 open today?"}
    assert not store.has_pending(PHONE)


MENUS = {"levadinho_lang_picker": "HXlist", **{f"levadinho_consent_{l}": f"HXok{l}" for l in brain.LANGS}}


def test_tappable_menus_flow(tw, monkeypatch):
    """With the Content templates: picker = list-picker, notice = quick-reply buttons; taps come back as
    ListId / ButtonPayload and run the same branches as Meta's list_reply / button_reply."""
    monkeypatch.setattr(twilio_wa, "CONTENT", MENUS)
    post(form("Olá Levadinho! 👋"))  # the general QR: its Portuguese greeting says nothing about the language
    assert tw.sent[-1]["content_sid"] == "HXlist" and tw.sent[-1]["body"] is None
    post(form("🇬🇧 English", ListId="lang_en", ListTitle="🇬🇧 English"))
    assert store.get_user(PHONE)["lang"] == "en"
    m = tw.sent[-1]
    assert m["content_sid"] == "HXoken" and "https://levadinho-madeira.com/privacy/#en" in json.loads(m["content_variables"])["1"]
    post(form("Accept", ButtonPayload="consent_yes", ButtonText="Accept"))
    assert tw.sent[-1]["body"] == brain.ASK["en"] and store.get_user(PHONE)["consent"] == "yes"


def test_menu_send_failure_falls_back_to_text(tw, monkeypatch):
    monkeypatch.setattr(twilio_wa, "CONTENT", MENUS)

    def create(from_, to, body=None, **kw):
        if kw:
            raise RuntimeError("63016")
        tw.sent.append({"from_": from_, "to": to, "body": body})
        return type("Msg", (), {"sid": "SMx"})()
    monkeypatch.setattr(tw, "create", create)
    post(form("join bark-wood"))
    assert tw.sent[-1]["body"].endswith("1 Português · 2 English · 3 Français · 4 Deutsch · 5 Polski")
