"""Levadinho trial brain — PR1 only.

Turns one incoming visitor message into the bot's outgoing messages. It knows nothing
about WhatsApp: app.py (the webhook) and chat.py (local test chat) both call handle().

Flow:
  - New visitor, first message is a question → answer it in the language it is written
    in (PT/EN/FR/DE/PL; anything else → English).
  - New visitor, anything else (e.g. the QR's pre-filled "Olá Levadinho!") → language picker.
  - Picker reply → save the language, send the intro.
  - Known visitor → every question is answered in the language it is written in (English
    if not one of the five); the saved language is used for everything else.
  - "idioma" / "language" / "langue" / "sprache" / "język" → picker again.
"""
import json
import os
import re
import time
import urllib.request

import store

HERE = os.path.dirname(os.path.abspath(__file__))
LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:8001/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "levadinho")
STATUS_URL = os.environ.get("STATUS_URL", "https://levadinho-madeira.com/status.json")
STATUS_FILE = os.path.join(os.path.dirname(HERE), "status.json")  # fallback if the site is unreachable
STATUS_TTL = 600

LANGS = {"pt": "Português", "en": "English", "fr": "Français", "de": "Deutsch", "pl": "Polski"}
LANG_NAMES = {"pt": "European Portuguese", "en": "English", "fr": "French", "de": "German", "pl": "Polish"}
FLAGS = {"pt": "🇵🇹", "en": "🇬🇧", "fr": "🇫🇷", "de": "🇩🇪", "pl": "🇵🇱"}
CHANGE_WORDS = {"idioma", "lingua", "língua", "language", "langue", "sprache", "język", "jezyk"}
ALTERNATIVES = ("PR1.2", "PR11", "PR9")  # the fallbacks pr1_facts.md suggests

PICKER = {
    "body": "Olá! Hello! Bonjour! Hallo! Cześć! 👋\n"
            "Sou o Levadinho, o seu guia do PR1 Vereda do Areeiro.\n"
            "Escolha o seu idioma · Choose your language",
    "button": "Idioma / Language",
    "options": [(code, f"{FLAGS[code]} {name}") for code, name in LANGS.items()],
}

INTRO = {
    "pt": "Ótimo! Sou o Levadinho 🥾 Pergunte-me o que quiser sobre o PR1 Vereda do Areeiro: "
          "se está aberto hoje, bilhetes e reservas, como voltar de Achada do Teixeira, o nascer do sol, o tempo lá em cima.\n\n"
          "Por exemplo: «O PR1 está aberto hoje?»",
    "en": "Great! I'm Levadinho 🥾 Ask me anything about the PR1 Vereda do Areeiro: "
          "whether it's open today, tickets and booking, getting back from Achada do Teixeira, sunrise, the weather up top.\n\n"
          "For example: \"Is PR1 open today?\"",
    "fr": "Parfait ! Je suis Levadinho 🥾 Posez-moi vos questions sur le PR1 Vereda do Areeiro : "
          "ouvert aujourd'hui ?, billets et réservation, le retour depuis Achada do Teixeira, le lever du soleil, la météo au sommet.\n\n"
          "Par exemple : « Le PR1 est-il ouvert aujourd'hui ? »",
    "de": "Super! Ich bin Levadinho 🥾 Frag mich alles zum PR1 Vereda do Areeiro: "
          "ob er heute offen ist, Tickets und Buchung, die Rückkehr von Achada do Teixeira, Sonnenaufgang, das Wetter oben.\n\n"
          "Zum Beispiel: „Ist der PR1 heute offen?“",
    "pl": "Świetnie! Jestem Levadinho 🥾 Zapytaj mnie o wszystko na temat PR1 Vereda do Areeiro: "
          "czy jest dziś otwarty, bilety i rezerwacja, powrót z Achada do Teixeira, wschód słońca, pogoda na szczycie.\n\n"
          "Na przykład: „Czy PR1 jest dziś otwarty?”",
}

TEXT_ONLY = {
    "pt": "Por agora só consigo ler mensagens de texto ✍️ Escreva-me a sua pergunta sobre o PR1.",
    "en": "For now I can only read text messages ✍️ Type your question about PR1.",
    "fr": "Pour l'instant je ne lis que les messages texte ✍️ Écrivez-moi votre question sur le PR1.",
    "de": "Im Moment kann ich nur Textnachrichten lesen ✍️ Schreib mir deine Frage zum PR1.",
    "pl": "Na razie czytam tylko wiadomości tekstowe ✍️ Napisz mi pytanie o PR1.",
}
TEXT_ERROR = ("Desculpe, algo correu mal. Tente de novo daqui a um minuto. · "
              "Sorry, something went wrong — please try again in a minute.")

# ---------------------------------------------------------------- live data
_status_cache = {"at": 0.0, "data": None}


def live_status():
    if time.time() - _status_cache["at"] < STATUS_TTL and _status_cache["data"]:
        return _status_cache["data"]
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=10) as r:
            data = json.load(r)
    except Exception:
        data = json.load(open(STATUS_FILE, encoding="utf-8"))
    _status_cache.update(at=time.time(), data=data)
    return data


def status_block():
    s = live_status()
    trails = {t["code"]: t for t in s.get("trails", [])}
    note = s.get("note", {})
    note = note.get("en", "") if isinstance(note, dict) else note
    w = s.get("weather", {})
    lines = [f"Status checked on {s.get('date')} (official Visit Madeira/IFCN data, updated every morning).",
             f"PR1 today: {s.get('status')}.",
             f"Official note: {note or 'none'}"]
    if s.get("manual_note"):
        lines.append(f"Extra note: {s['manual_note']}")
    if w.get("ok"):
        wx = f"Measured at the Pico do Areeiro station (IPMA): {w.get('temp_c')} °C, humidity {w.get('humidity')}%, wind {w.get('wind_kmh')} km/h"
        if w.get("in_cloud"):
            wx += ", summit most likely inside cloud/fog"
        lines.append(wx + ".")
    else:
        lines.append("Summit weather reading unavailable today.")
    for code in ALTERNATIVES:
        t = trails.get(code)
        if t:
            lines.append(f"Alternative {code} {t['name']}: {t['status']}.")
    return "\n".join(lines)


# ---------------------------------------------------------------- LLM
def llm(messages, max_tokens=700, schema=None, temperature=0.3):
    body = {"model": LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": False}}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}
    req = urllib.request.Request(LLM_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {"is_question": {"type": "boolean"},
                   "language": {"type": "string", "enum": ["pt", "en", "fr", "de", "pl", "other"]}},
    "required": ["is_question", "language"],
}


def classify(text):
    """Is this a real question/request for information, and what language is it in?"""
    out = llm([
        {"role": "system", "content":
            "Classify a WhatsApp message sent to a hiking-trail assistant. "
            "is_question = true if the visitor asks something or requests information (even without a question mark); "
            "false for greetings, thanks, emojis or small talk. "
            "language = the language the message is written in: pt, en, fr, de, pl, or other."},
        {"role": "user", "content": text}], max_tokens=40, schema=CLASSIFY_SCHEMA, temperature=0)
    d = json.loads(out)
    return d["is_question"], (d["language"] if d["language"] in LANGS else "en")


FACTS = open(os.path.join(HERE, "pr1_facts.md"), encoding="utf-8").read()

SYSTEM = """You are Levadinho, a friendly, knowledgeable old Madeiran mountain guide who helps visitors on WhatsApp with ONE trail: the PR1 Vereda do Areeiro (Pico do Areeiro → Pico Ruivo) on Madeira.

LANGUAGE: {lang_rule}

HOW TO ANSWER
- Never mention which languages you speak or any language rule; just reply naturally.
- WhatsApp style: short and practical, 2–6 short lines, no headings, no markdown tables. *Bold* sparingly. At most one emoji.
- Use ONLY the facts in LIVE STATUS and PR1 KNOWLEDGE below. If something isn't there, say you don't know and point to SIMplifica or IFCN. Never invent prices, times, phone numbers, bus routes or rules.
- LIVE STATUS always wins over PR1 KNOWLEDGE. Today's open/closed state comes only from LIVE STATUS; say it's from this morning's official check.
- If PR1 is CLOSED or PARTIAL, say so plainly and suggest an alternative ONLY if LIVE STATUS shows it OPEN.
- Always remind about the one-way rule and the return from Achada do Teixeira when someone plans the full walk.
- Booking link: https://simplifica.madeira.gov.pt/services/78-82-259
- Other trails: you only cover PR1 in this trial. Say so kindly and point to https://levadinho-madeira.com/trails/ for the status of every trail. Never guess other trails' codes, distances or status.
- Off-topic requests (not Madeira hiking/visiting): politely decline in one line.
- Safety first: never encourage walking a closed trail, going without a ticket, or walking PR1 in reverse.

LIVE STATUS
{status}

PR1 KNOWLEDGE
{facts}
"""

def answer(user, text, lang):
    rule = (f"Write your reply ONLY in {LANG_NAMES[lang]}, whatever language earlier messages used. "
            f"Keep place names (Pico do Areeiro, Achada do Teixeira…) as they are.")
    system = SYSTEM.format(lang_rule=rule, status=status_block(), facts=FACTS)
    msgs = [{"role": "system", "content": system}] + store.history(user) + [{"role": "user", "content": text}]
    reply = re.sub(r"\*\*(.+?)\*\*", r"*\1*", llm(msgs))  # WhatsApp bold is *single*
    store.add_turn(user, text, reply)
    return reply


# ---------------------------------------------------------------- flow
def picker():
    return {"type": "list", **PICKER}


def handle(user, text=None, choice=None):
    """Return a list of outgoing messages: {"type": "text", "body": ...} or a picker."""
    u = store.get_user(user)

    if choice in LANGS:  # tapped a row in the picker
        store.set_user(user, lang=choice, state="ready")
        return [{"type": "text", "body": INTRO[choice]}]

    text = (text or "").strip()
    if not text:
        return [picker()] if not u or not u.get("lang") else []

    # The QR code's pre-filled greeting always (re)opens the picker — also for returning visitors.
    if "levadinho" in text.lower() and len(text) <= 40 and "?" not in text:
        store.set_user(user, state="picking")
        return [picker()]

    if text.lower().strip(" !?.") in CHANGE_WORDS:
        store.set_user(user, state="picking")
        return [picker()]

    if not u or not u.get("lang"):  # first contact, or still hasn't picked
        is_q, lang = classify(text)
        if is_q:
            store.set_user(user, lang=lang, state="ready")
            return [{"type": "text", "body": answer(user, text, lang)}]
        store.set_user(user, state="picking")
        return [picker()]

    # Questions are answered in the language they're written in; anything else in the chosen one.
    is_q, lang = classify(text)
    return [{"type": "text", "body": answer(user, text, lang if is_q else u["lang"])}]
