"""Offline tests for the first-contact flow agreed with the owner on 2026-10-05, replaying the first real
website visitor (4 Oct, #web-sunrise): the request they typed before accepting was lost, the language menu went
out three times, and the bot named two transfer companies that aren't in its facts.

Now: greetings need no model; the language comes from the greeting or the message (menu at most once); anything
that isn't a greeting waits for Accept and is then answered; a getting-from-A-to-B request first asks where the
visitor is staying; the answer gets the sourced taxi facts and the guide of the page they came from.
No model, no WhatsApp, no Postgres: the model is a fake and the SQLite store is a scratch file.

  python -m pytest -q bot/tests/test_first_contact.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["LEVADINHO_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DB_URL"] = ""
os.environ["LLM_URL"] = "http://127.0.0.1:9/v1/chat/completions"

import brain  # noqa: E402
import store  # noqa: E402

assert store.DB.startswith(os.path.dirname(os.environ["LEVADINHO_DB"])), "store must be the scratch database"
brain.live_status = lambda: json.load(open(brain.STATUS_FILE, encoding="utf-8"))
CALLS = []  # (system prompt, last user message) of every answer the fake model writes


def fake_llm(messages, max_tokens=700, schema=None, temperature=0.3):
    text = messages[-1]["content"]
    if schema:  # the classifier
        t = text.lower()
        transport = any(w in t for w in ("transfer", "taxi", "bus", "get back", "get to"))
        return json.dumps({"is_question": "?" in text, "language": brain.guess_lang(text) or "en",
                           "intent": "transport" if transport else "other", "topic": "test",
                           "trail_code": None, "origin": "Funchal" if "from funchal" in t else None,
                           "destination": "Pico do Areeiro" if "to pico do areeiro" in t else None})
    CALLS.append((messages[0]["content"], text))
    return f"ANSWER to: {text}"


brain.llm = fake_llm
U = "37060000001"


def fresh():
    store.reset(U)
    CALLS.clear()


def kinds(out):
    return [m["type"] for m in out]


def test_the_lithuanian_visitor_replayed():
    fresh()
    # 1. Tapped the button on the (English) sunrise-transport page: notice in English at once, no menu.
    out = brain.handle(U, text="Hello Levadinho! 👋 #web-sunrise")
    assert kinds(out) == ["buttons"] and "#en" in out[0]["body"]
    assert store.get_user(U)["source"] == "web-sunrise" and store.get_user(U)["lang"] == "en"
    # 2. "Hello!" while the notice is on screen: nothing more (no second notice, no menu).
    assert brain.handle(U, text="Hello!") == []
    # 3. The real request, typed before accepting (no question mark): kept, the notice shown again.
    req = "I would like to order transfer for two persons 7th of october in the morrning."
    out = brain.handle(U, text=req)
    assert kinds(out) == ["buttons"] and store.get_user(U)["state"] == f"notice:q:{req}"
    # 4. Accept: the request is answered straight away by the model (since 2026-10-10 no "where are you staying?"
    #    from code: the model asks only if the answer really needs a starting point)
    out = brain.handle_consent(U, True)
    assert len(out) == 1 and out[0]["body"].startswith("ANSWER to: I would like to order transfer")
    assert store.get_user(U)["state"] == "ready"
    # 5. Another getting-there question: answered by the model, never the canned taxi list
    out = brain.handle(U, text="And how do I get back from Achada do Teixeira?")
    assert out[0]["body"].startswith("ANSWER to: And how do I get back from Achada do Teixeira?")


def test_origin_given_no_question_asked():
    fresh()
    store.set_user(U, lang="en", consent="yes", state="ready")
    out = brain.handle(U, text="Is there a bus from Funchal to Pico do Areeiro?")
    assert out[0]["body"].startswith("ANSWER to: Is there a bus from Funchal to Pico do Areeiro?")
    assert "Staying in" not in out[0]["body"] and brain.ASK_BASE["en"] not in out[0]["body"]


def test_old_portuguese_link_then_english():
    """A page cached with the old Portuguese greeting, then the visitor writes in English: switch to English."""
    fresh()
    out = brain.handle(U, text="Olá Levadinho! 👋 #web-sunrise")
    assert kinds(out) == ["buttons"] and "#pt" in out[0]["body"]
    out = brain.handle(U, text="Hello!")
    assert kinds(out) == ["buttons"] and "#en" in out[0]["body"] and store.get_user(U)["lang"] == "en"


def test_menu_at_most_once():
    """The general QR's Portuguese greeting: the menu (language unknown) with the privacy notice. Later
    greetings don't repeat it; picking a language accepts; the line after Accept asks how it can help."""
    fresh()
    out = brain.handle(U, text="Olá Levadinho! 👋")
    assert kinds(out) == ["list"] and "/privacy/" in out[0]["body"]  # the menu is also the privacy notice
    assert brain.handle(U, text="Olá Levadinho! 👋") == []
    out = brain.handle(U, choice="en")
    assert out == [{"type": "text", "body": brain.ASK["en"]}] and store.get_user(U)["consent"] == "yes"
    assert "How may I help you today?" in brain.ASK["en"]
    fresh()
    brain.handle(U, text="Olá Levadinho! 👋")
    out = brain.handle(U, text="¿Qué tal?")  # not one of our languages: never silent, the English notice
    assert kinds(out) == ["buttons"] and "#en" in out[0]["body"]
    out = brain.handle_consent(U, True)
    assert out[0]["body"] == "ANSWER to: ¿Qué tal?"  # what they wrote is answered after Accept


def test_accept_with_nothing_waiting_is_one_short_line():
    fresh()
    brain.handle(U, text="Bonjour Levadinho ! 👋 #web-fees")
    out = brain.handle_consent(U, True)
    assert out == [{"type": "text", "body": brain.ASK["fr"]}]
    assert "Levadinho" not in brain.ASK["fr"] and len(brain.ASK["fr"]) < 60


def test_greetings():
    assert brain.is_greeting("Hello Levadinho! 👋 #web-pr1") and brain.greeting_lang("Cześć Levadinho! 👋") == "pl"
    assert brain.is_greeting("Bom dia!") and brain.greeting_lang("Bom dia!") == "pt"
    assert not brain.is_greeting("Hello, is PR1 open?")
    assert not brain.is_greeting("I would like to order transfer for two persons")


def test_airport_transfer_no_stray_trail_link():
    """The owner's test on 5 Oct: "transfer from the airport" was answered with a PR11 link remembered from a chat
    the day before. Since 2026-10-10 the model answers (it asks where they stay only if it must); still no trail link
    from history."""
    fresh()
    store.set_user(U, lang="en", consent="yes", state="ready")
    store.add_turn(U, "And what is the levada that starts in ribeiro frio?", "PR11 Vereda dos Balcões starts at Ribeiro Frio.")
    out = brain.handle(U, text="How can I order a transfer from the airport")
    assert out[0]["body"].startswith("ANSWER to: How can I order a transfer from the airport")
    assert "balcoes" not in out[0]["body"]
