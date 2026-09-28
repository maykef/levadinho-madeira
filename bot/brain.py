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
  - A campaign QR pre-fills "Olá Levadinho! 👋 #<tag>" → picker → welcome + that route's guide link.
  - "guide" / "guia"… → WhatsApp's Send location button; a location pin → the nearby route's link.
"""
import json
import os
import re
import time
import urllib.request

import geo
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
# ---------------------------------------------------------------- location + audio guide
GUIDE_URL = os.environ.get("GUIDE_URL", "https://microscopy-rig-system.tail53cc58.ts.net/levadinho/guide/")
AREEIRO = (32.73549, -16.92880)  # PR1 start, from the official Visit Madeira page (trail_facts.json)
CAMPAIGNS = {"ely": "ely-test"}  # QR tag → guide route (the 19 Oct demo adds "areeiro": "pr1")
NEAR_M = 3000  # a route's guide is offered when the visitor is this close to its start
GUIDE_WORDS = {"guide": None, "audio guide": None, "audioguide": None, "guide audio": "fr",
               "guia": "pt", "guia audio": "pt", "guia áudio": "pt", "audioguia": "pt",
               "führer": "de", "audioführer": "de", "audioguide deutsch": "de",
               "przewodnik": "pl", "audioprzewodnik": "pl"}

LOC_ASK = {
    "pt": "Para começar o guia áudio preciso de saber onde está. Toque no botão abaixo para partilhar a sua localização 📍",
    "en": "To start the audio guide I need to know where you are. Tap the button below to share your location 📍",
    "fr": "Pour lancer le guide audio, j'ai besoin de savoir où vous êtes. Touchez le bouton ci-dessous pour partager votre position 📍",
    "de": "Um den Audioguide zu starten, muss ich wissen, wo du bist. Tippe unten auf den Button, um deinen Standort zu teilen 📍",
    "pl": "Aby uruchomić audioprzewodnik, muszę wiedzieć, gdzie jesteś. Dotknij przycisku poniżej, aby udostępnić lokalizację 📍",
}
WELCOME = {
    "pt": "Bem-vindo ao *{title}*! 🥾\n\nPara começar o guia áudio, toque no link abaixo. Abre fora do WhatsApp e usa a sua localização "
          "para tocar cada paragem quando lá chegar:\n{link}\n\n{note}\n\nEnquanto caminha, mantenha a página aberta e use o *Modo bolso*: o ecrã fica ligado no bolso. Bom passeio!",
    "en": "Welcome to the *{title}*! 🥾\n\nTo start the audio guide, tap the link below. It opens outside WhatsApp and uses your location "
          "to play each stop as you reach it:\n{link}\n\n{note}\n\nWhile you walk, keep the page open and use *Pocket mode*: the screen stays on in your pocket. Enjoy your walk!",
    "fr": "Bienvenue sur le *{title}* ! 🥾\n\nPour lancer le guide audio, touchez le lien ci-dessous. Il s'ouvre hors de WhatsApp et utilise "
          "votre position pour lancer chaque étape quand vous y arrivez :\n{link}\n\n{note}\n\nPendant la marche, gardez la page ouverte et utilisez le *Mode poche* : l'écran reste allumé dans votre poche. Bonne balade !",
    "de": "Willkommen beim *{title}*! 🥾\n\nUm den Audioguide zu starten, tippe auf den Link unten. Er öffnet sich außerhalb von WhatsApp und "
          "nutzt deinen Standort, um jeden Halt abzuspielen, sobald du ihn erreichst:\n{link}\n\n{note}\n\nLass die Seite beim Gehen offen und nutze den *Taschenmodus*: Der Bildschirm bleibt in der Tasche an. Viel Spaß!",
    "pl": "Witamy na trasie *{title}*! 🥾\n\nAby uruchomić audioprzewodnik, dotknij linku poniżej. Otworzy się poza WhatsAppem i użyje "
          "Twojej lokalizacji, by odtwarzać każdy przystanek, gdy do niego dotrzesz:\n{link}\n\n{note}\n\nPodczas marszu trzymaj stronę otwartą i użyj *trybu kieszonkowego*: ekran pozostaje włączony w kieszeni. Miłego spaceru!",
}
LOC_NEAR = {
    "pt": "📍 Recebido! Está a {dist} do início do *{title}*.\n\nToque para abrir o guia áudio. Abre fora do WhatsApp e usa a sua "
          "localização para tocar cada paragem quando lá chegar:\n{link}\n\n{note}\n\nEnquanto caminha, mantenha a página aberta e use o *Modo bolso*: o ecrã fica ligado no bolso.",
    "en": "📍 Got it! You're {dist} from the start of the *{title}*.\n\nTap to open the audio guide. It opens outside WhatsApp and uses "
          "your location to play each stop as you reach it:\n{link}\n\n{note}\n\nWhile you walk, keep the page open and use *Pocket mode*: the screen stays on in your pocket.",
    "fr": "📍 Bien reçu ! Vous êtes à {dist} du départ du *{title}*.\n\nTouchez pour ouvrir le guide audio. Il s'ouvre hors de WhatsApp "
          "et utilise votre position pour lancer chaque étape quand vous y arrivez :\n{link}\n\n{note}\n\nPendant la marche, gardez la page ouverte et utilisez le *Mode poche* : l'écran reste allumé dans votre poche.",
    "de": "📍 Danke! Du bist {dist} vom Start des *{title}* entfernt.\n\nTippe, um den Audioguide zu öffnen. Er öffnet sich außerhalb von "
          "WhatsApp und nutzt deinen Standort, um jeden Halt abzuspielen, sobald du ihn erreichst:\n{link}\n\n{note}\n\nLass die Seite beim Gehen offen und nutze den *Taschenmodus*: Der Bildschirm bleibt in der Tasche an.",
    "pl": "📍 Dzięki! Jesteś {dist} od startu trasy *{title}*.\n\nDotknij, aby otworzyć audioprzewodnik. Otworzy się poza WhatsAppem i użyje "
          "Twojej lokalizacji, by odtwarzać każdy przystanek, gdy do niego dotrzesz:\n{link}\n\n{note}\n\nPodczas marszu trzymaj stronę otwartą i użyj *trybu kieszonkowego*: ekran pozostaje włączony w kieszeni.",
}
LOC_FAR = {
    "pt": "📍 Recebido! Está a {dist} do Pico do Areeiro, onde começa o PR1. PR1 hoje: *{status}* (verificação oficial desta manhã).\n\n"
          "O guia áudio começa no início do trilho. Quando lá estiver, envie-me de novo a sua localização (📎 → Localização).",
    "en": "📍 Got it! You're {dist} from Pico do Areeiro, where PR1 starts. PR1 today: *{status}* (this morning's official check).\n\n"
          "The audio guide starts at the trailhead. When you're there, send me your location again (📎 → Location).",
    "fr": "📍 Bien reçu ! Vous êtes à {dist} du Pico do Areeiro, départ du PR1. PR1 aujourd'hui : *{status}* (vérification officielle de ce matin).\n\n"
          "Le guide audio démarre au début du sentier. Une fois là-bas, renvoyez-moi votre position (📎 → Position).",
    "de": "📍 Danke! Du bist {dist} vom Pico do Areeiro entfernt, wo der PR1 beginnt. PR1 heute: *{status}* (offizielle Prüfung von heute Morgen).\n\n"
          "Der Audioguide startet am Wanderweg. Wenn du dort bist, schick mir deinen Standort nochmal (📎 → Standort).",
    "pl": "📍 Dzięki! Jesteś {dist} od Pico do Areeiro, gdzie zaczyna się PR1. PR1 dziś: *{status}* (oficjalne sprawdzenie z dzisiejszego ranka).\n\n"
          "Audioprzewodnik startuje na początku szlaku. Gdy tam będziesz, wyślij mi ponownie swoją lokalizację (📎 → Lokalizacja).",
}
# Sent with every guide link: open it while there's signal, so the guide saves itself on the phone.
OFFLINE_NOTE = {
    "pr1": {
        "pt": "📶 O PR1 tem troços sem rede móvel. Abra o link agora, enquanto ainda tem sinal: o guia fica guardado no telemóvel e depois funciona sem rede.",
        "en": "📶 PR1 has stretches with no mobile signal. Open the link now, while you still have signal: the guide saves itself on your phone and then works offline.",
        "fr": "📶 Le PR1 a des passages sans réseau mobile. Ouvrez le lien maintenant, tant que vous avez du réseau : le guide s'enregistre sur votre téléphone et fonctionne ensuite hors ligne.",
        "de": "📶 Auf dem PR1 gibt es Abschnitte ohne Mobilfunknetz. Öffne den Link jetzt, solange du Empfang hast: Der Guide speichert sich auf deinem Handy und funktioniert dann offline.",
        "pl": "📶 Na PR1 są odcinki bez zasięgu. Otwórz link teraz, póki masz zasięg: przewodnik zapisze się w telefonie i będzie działał offline.",
    },
    "other": {
        "pt": "📶 Pode perder a rede pelo caminho. Abra o link agora, enquanto tem sinal: o guia fica guardado no telemóvel e depois funciona sem rede.",
        "en": "📶 You may lose mobile signal along the way. Open the link now, while you have signal: the guide saves itself on your phone and then works offline.",
        "fr": "📶 Vous pourriez perdre le réseau en chemin. Ouvrez le lien maintenant, tant que vous avez du réseau : le guide s'enregistre sur votre téléphone et fonctionne ensuite hors ligne.",
        "de": "📶 Unterwegs kann der Empfang abbrechen. Öffne den Link jetzt, solange du Empfang hast: Der Guide speichert sich auf deinem Handy und funktioniert dann offline.",
        "pl": "📶 Po drodze możesz stracić zasięg. Otwórz link teraz, póki masz zasięg: przewodnik zapisze się w telefonie i będzie działał offline.",
    },
}

STATUS_WORDS = {
    "OPEN": {"pt": "aberto", "en": "open", "fr": "ouvert", "de": "offen", "pl": "otwarty"},
    "PARTIAL": {"pt": "parcialmente aberto", "en": "partly open", "fr": "partiellement ouvert", "de": "teilweise offen", "pl": "częściowo otwarty"},
    "CLOSED": {"pt": "fechado", "en": "closed", "fr": "fermé", "de": "geschlossen", "pl": "zamknięty"},
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
- Other trails: you only cover PR1 in this trial. Say so kindly and point to https://levadinho-madeira.com/ for the status of every trail. Never guess other trails' codes, distances or status.
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


def fmt_distance(m, lang):
    if m < 1000:
        return f"{max(10, round(m, -1)):.0f} m"
    km = f"{m / 1000:.1f}" if m < 100_000 else f"{m / 1000:.0f}"
    return (km if lang == "en" else km.replace(".", ",")) + " km"


def ask_location(lang):
    return {"type": "location_request", "body": LOC_ASK[lang]}


def guide_link(user, route, lang):
    """→ (personal guide link, route title in the visitor's language)."""
    token = store.new_guide_token(user, route["id"])
    return f"{GUIDE_URL}?r={route['id']}&l={lang}&t={token}", route["title"].get(lang) or route["title"]["en"]


def offline_note(rid, lang):
    return OFFLINE_NOTE["pr1" if rid == "pr1" else "other"][lang]


def welcome(user, rid, lang):
    route = geo.load_route(rid)
    if not route:
        return {"type": "text", "body": INTRO[lang]}
    link, title = guide_link(user, route, lang)
    return {"type": "text", "body": WELCOME[lang].format(title=title, link=link, note=offline_note(rid, lang))}


def handle_location(user, lat, lon):
    """A shared pin → the guide link for the route that starts nearby, or how far PR1 is."""
    lang = (store.get_user(user) or {}).get("lang") or "en"
    route, dist = geo.nearest_route(lat, lon)
    if route and dist <= NEAR_M:
        link, title = guide_link(user, route, lang)
        return [{"type": "text", "body": LOC_NEAR[lang].format(dist=fmt_distance(dist, lang), title=title, link=link,
                                                              note=offline_note(route["id"], lang))}]
    status = str(live_status().get("status", "")).upper()
    word = STATUS_WORDS.get(status, {}).get(lang, status.lower() or "?")
    far = geo.distance_m(lat, lon, *AREEIRO)
    return [{"type": "text", "body": LOC_FAR[lang].format(dist=fmt_distance(far, lang), status=word)}]


def handle(user, text=None, choice=None):
    """Return a list of outgoing messages: {"type": "text", "body": ...} or a picker."""
    u = store.get_user(user)

    if choice in LANGS:  # tapped a row in the picker
        tag = ((u or {}).get("state") or "").partition(":")[2]  # "picking:<campaign tag>" after a campaign QR
        store.set_user(user, lang=choice, state="ready")
        if tag in CAMPAIGNS:
            return [welcome(user, CAMPAIGNS[tag], choice)]
        return [{"type": "text", "body": INTRO[choice]}]

    text = (text or "").strip()
    if not text:
        return [picker()] if not u or not u.get("lang") else []

    # The QR code's pre-filled greeting always (re)opens the picker — also for returning visitors.
    if "levadinho" in text.lower() and len(text) <= 40 and "?" not in text:
        tag = re.search(r"#([a-z0-9-]+)", text.lower())
        tag = tag.group(1) if tag and tag.group(1) in CAMPAIGNS else ""
        store.set_user(user, state=f"picking:{tag}" if tag else "picking")
        return [picker()]

    if text.lower().strip(" !?.") in CHANGE_WORDS:
        store.set_user(user, state="picking")
        return [picker()]

    word = text.lower().strip(" !?.")
    if word in GUIDE_WORDS:  # "guide" / "guia"… → ask for a location pin with WhatsApp's button
        lang = (u or {}).get("lang") or GUIDE_WORDS[word] or "en"
        return [ask_location(lang)]

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
