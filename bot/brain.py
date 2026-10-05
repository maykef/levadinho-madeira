"""Levadinho brain: every PR trail on Madeira (since 2026-10-04; PR1 only before).

Turns one incoming visitor message into the bot's outgoing messages. It knows nothing
about WhatsApp: app.py (the webhook) and chat.py (local test chat) both call handle().

Flow (owner, 2026-10-05):
  - Greetings ("Hello!", "Olá", a website link's pre-filled "Hello Levadinho! 👋 #web-<page>") need no model.
    The language comes from the greeting (a website link's greeting is in the page's language) or from the
    message; the language menu is sent only when it can't be told (e.g. the general QR's Portuguese
    "Olá Levadinho!"), and only once.
  - Privacy notice: nothing is answered until the visitor taps Accept. Anything that isn't a greeting waits
    for it (question or not) and is answered right after Accept; with nothing waiting, one short line (ASK).
    A message waiting for Accept starts loading the model (app.py), so the answer comes quickly.
  - Getting from A to B (transport intent, no starting point given): first "where are you staying?"
    (ASK_BASE); the town is kept (store "base") and given to the model as "(Staying in: …)". The answer
    gets the sourced taxi table (transport_facts.md) and never names a business that isn't in the facts.
  - A website link's #web-<page> is kept as the visitor's source (store "source", analytics campaign); its
    guide (or trail) is used when a question names none.
  - Known visitor → every question is answered in the language it is written in (English if not one of
    the five); the saved language is used for everything else.
  - "idioma" / "language" / "langue" / "sprache" / "język" → picker again.
  - A campaign QR pre-fills "Olá Levadinho! 👋 #<tag>" → picker → welcome + that route's guide link.
  - "guide" / "guia"… → WhatsApp's Send location button; a location pin → the nearby route's link.
  - The model may be asleep (wake-on-demand, llm_control.py): llm() then raises LLMDown and app.py
    queues the message and tells the visitor (WAKING / BUSY).
  - "Don't accept" stops the service; app.py then keeps only an anonymous count. "privacy" /
    "privacidade"… shows the notice again (Don't accept there = stop recording and stop the service).
"""
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

import geo
import llm_control
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

PICKER = {
    "body": "Olá! Hello! Bonjour! Hallo! Cześć! 👋\n"
            "Sou o Levadinho, o seu guia dos percursos pedestres da Madeira.\n"
            "Escolha o seu idioma · Choose your language",
    "button": "Idioma / Language",
    "options": [(code, f"{FLAGS[code]} {name}") for code, name in LANGS.items()],
}

TEXT_ONLY = {
    "pt": "Por agora só consigo ler mensagens de texto ✍️ Escreva-me a sua pergunta.",
    "en": "For now I can only read text messages ✍️ Type your question.",
    "fr": "Pour l'instant je ne lis que les messages texte ✍️ Écrivez-moi votre question.",
    "de": "Im Moment kann ich nur Textnachrichten lesen ✍️ Schreib mir deine Frage.",
    "pl": "Na razie czytam tylko wiadomości tekstowe ✍️ Napisz mi pytanie.",
}
# After Accept with nothing waiting (owner, 2026-10-05: the long intro was useless): one short line.
ASK = {
    "pt": "Obrigado! Em que posso ajudar? 🥾",
    "en": "Thanks! What would you like to know? 🥾",
    "fr": "Merci ! Que voulez-vous savoir ? 🥾",
    "de": "Danke! Was möchtest du wissen? 🥾",
    "pl": "Dziękuję! Co chcesz wiedzieć? 🥾",
}
# Getting from A to B: ask first where the visitor is staying (owner, 2026-10-05). A town or area is enough.
ASK_BASE = {
    "pt": "Para lhe indicar a melhor forma, onde está alojado (ou vai ficar)? Basta a localidade, por exemplo Funchal, Caniço ou Santana.",
    "en": "To give you the best way, where are you staying (or planning to stay)? The town or area is enough, e.g. Funchal, Caniço or Santana.",
    "fr": "Pour vous indiquer le meilleur moyen, où logez-vous (ou allez-vous loger) ? La ville suffit, par exemple Funchal, Caniço ou Santana.",
    "de": "Damit ich dir den besten Weg nennen kann: Wo übernachtest du (oder wirst du übernachten)? Der Ort genügt, z. B. Funchal, Caniço oder Santana.",
    "pl": "Żebym mógł wskazać najlepszy sposób: gdzie nocujesz (lub będziesz nocować)? Wystarczy miejscowość, np. Funchal, Caniço albo Santana.",
}
# Greetings (typed, or a website link's pre-filled text): words → language. A greeting alone is not a request.
# Keep in step with scripts/gen_cta.py WA_PREFIX.
GREETING_LANG = {"ola": "pt", "bom dia": "pt", "boa tarde": "pt", "boa noite": "pt", "oi": "pt",
                 "hello": "en", "hi": "en", "hey": "en", "good morning": "en", "good afternoon": "en", "good evening": "en",
                 "bonjour": "fr", "bonsoir": "fr", "salut": "fr",
                 "hallo": "de", "guten tag": "de", "guten morgen": "de", "moin": "de", "servus": "de",
                 "czesc": "pl", "dzien dobry": "pl", "witam": "pl", "hej": "pl"}
GREETING_FILLER = {"levadinho", "there", "again", "o", "a"}
# Website page tag → the guide or trail its visitors most likely mean (used when the question names neither).
SOURCE_GUIDE = {"web-sunrise": "sunrise", "web-back": "back", "web-oneway": "oneway", "web-weather": "weather",
                "web-booking": "booking", "web-abroad": "abroad", "web-permit": "permit", "web-free": "free",
                "web-bus": "bus", "web-best": "best", "web-easy": "easy", "web-tunnels": "tunnels"}


def is_greeting(text):
    """Only greeting words (and the bot's name, #tags, emoji, punctuation): nothing to answer yet."""
    if _norm(text).startswith("join "):  # Twilio sandbox: "join <code> [#web-…]" is a first contact
        return True
    t = re.sub(r"#[\w-]+", " ", _norm(text))
    t = re.sub(r"[^\w\s]", " ", t)
    t = " " + re.sub(r"\s+", " ", t).strip() + " "
    if not t.strip():
        return True
    for g in sorted(GREETING_LANG, key=len, reverse=True):
        t = t.replace(f" {g} ", " ")
    return all(w in GREETING_FILLER for w in t.split())


def greeting_lang(text):
    t = " " + re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", re.sub(r"#[\w-]+", " ", _norm(text)))).strip() + " "
    for g in sorted(GREETING_LANG, key=len, reverse=True):
        if f" {g} " in t:
            return GREETING_LANG[g]
    return None


# ---------------------------------------------------------------- location + audio guide
GUIDE_URL = os.environ.get("GUIDE_URL", "https://microscopy-rig-system.tail53cc58.ts.net/levadinho/guide/")
AREEIRO = (32.73549, -16.92880)  # PR1 start, from the official Visit Madeira page (trail_facts.json)
CAMPAIGNS = {"ely": "ely-test", "areeiro": "pr1"}  # QR tag → guide route
WEB_TAG = re.compile(r"web-[a-z0-9-]{1,40}")  # website link tags (#web-pr1, #web-fees…): a source, not a route


def is_web_tag(tag):
    return bool(tag) and bool(WEB_TAG.fullmatch(tag))


def known_tag(tag):
    return tag in CAMPAIGNS or is_web_tag(tag)
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
    "pt": "📍 Recebido! Está a {dist} do Pico do Areeiro, onde começa o PR1. PR1 hoje: *{status}* (segundo a lista oficial do IFCN, atualizada a {updated}).\n\n"
          "O guia áudio começa no início do trilho. Quando lá estiver, envie-me de novo a sua localização (📎 → Localização).",
    "en": "📍 Got it! You're {dist} from Pico do Areeiro, where PR1 starts. PR1 today: *{status}* (according to IFCN's official list, updated {updated}).\n\n"
          "The audio guide starts at the trailhead. When you're there, send me your location again (📎 → Location).",
    "fr": "📍 Bien reçu ! Vous êtes à {dist} du Pico do Areeiro, départ du PR1. PR1 aujourd'hui : *{status}* (selon la liste officielle de l'IFCN, mise à jour le {updated}).\n\n"
          "Le guide audio démarre au début du sentier. Une fois là-bas, renvoyez-moi votre position (📎 → Position).",
    "de": "📍 Danke! Du bist {dist} vom Pico do Areeiro entfernt, wo der PR1 beginnt. PR1 heute: *{status}* (laut der offiziellen IFCN-Liste, aktualisiert am {updated}).\n\n"
          "Der Audioguide startet am Wanderweg. Wenn du dort bist, schick mir deinen Standort nochmal (📎 → Standort).",
    "pl": "📍 Dzięki! Jesteś {dist} od Pico do Areeiro, gdzie zaczyna się PR1. PR1 dziś: *{status}* (według oficjalnej listy IFCN, zaktualizowanej {updated}).\n\n"
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

# ---------------------------------------------------------------- privacy notice (GDPR)
# Accepting the notice is a condition of using the assistant: nothing is answered until the visitor
# taps Accept. The chat record rests on legitimate interest (the privacy policy says so), not on
# consent; the guide's GPS log is a separate opt-in inside the guide. Declines are counted anonymously.
CONSENT_VERSION = "2026-09-28"   # date of the privacy policy the visitor accepted
POLICY_URL = "https://levadinho-madeira.com/privacy/#{lang}"
PRIVACY_WORDS = {"privacy", "privacidade", "privacité", "confidentialité", "confidentialite", "datenschutz",
                 "prywatność", "prywatnosc", "rgpd", "gdpr", "dsgvo", "rodo"}
CONSENT_ASK = {
    "pt": "Para melhorar o Levadinho e perceber a procura nos percursos, recolhemos alguns dados sobre a forma como o usa. "
          "Mais informação na nossa política de privacidade: {url}\n\nToque em *Aceitar* para continuar.",
    "en": "To improve Levadinho and understand demand on the trails, we collect some data about how you use it. "
          "More in our privacy policy: {url}\n\nTap *Accept* to continue.",
    "fr": "Pour améliorer Levadinho et comprendre la fréquentation des sentiers, nous collectons certaines données sur votre "
          "utilisation. Plus d'infos dans notre politique de confidentialité : {url}\n\nTouchez *Accepter* pour continuer.",
    "de": "Um Levadinho zu verbessern und die Nachfrage auf den Wanderwegen zu verstehen, erfassen wir einige Daten darüber, "
          "wie du es nutzt. Mehr in unserer Datenschutzerklärung: {url}\n\nTippe auf *Akzeptieren*, um fortzufahren.",
    "pl": "Aby ulepszać Levadinho i rozumieć ruch na szlakach, zbieramy pewne dane o tym, jak z niego korzystasz. "
          "Więcej w naszej polityce prywatności: {url}\n\nDotknij *Akceptuję*, aby kontynuować.",
}
CONSENT_BUTTONS = {  # WhatsApp reply-button titles: 20 characters at most
    "pt": ("Aceitar", "Não aceitar"), "en": ("Accept", "Don't accept"), "fr": ("Accepter", "Refuser"),
    "de": ("Akzeptieren", "Ablehnen"), "pl": ("Akceptuję", "Nie akceptuję"),
}
CONSENT_NO = {
    "pt": "Compreendido. O Levadinho não pode ser usado sem aceitar. Se mudar de ideias, basta escrever-me de novo.",
    "en": "Understood. Levadinho can't be used without accepting. If you change your mind, just write to me again.",
    "fr": "C'est noté. Levadinho ne peut pas être utilisé sans accepter. Si vous changez d'avis, écrivez-moi simplement à nouveau.",
    "de": "Verstanden. Levadinho kann ohne Zustimmung nicht genutzt werden. Wenn du es dir anders überlegst, schreib mir einfach wieder.",
    "pl": "Rozumiem. Z Levadinho nie można korzystać bez akceptacji. Jeśli zmienisz zdanie, po prostu napisz do mnie ponownie.",
}
CONSENT_WITHDRAWN = {
    "pt": "Feito: nada mais fica registado e o Levadinho deixa de responder até voltar a aceitar. "
          "Para apagar o que já foi registado, escreva para hello@levadinho-madeira.com.",
    "en": "Done: nothing more is recorded, and Levadinho stops answering until you accept again. "
          "To delete what was recorded before, email hello@levadinho-madeira.com.",
    "fr": "C'est fait : plus rien n'est enregistré, et Levadinho ne répond plus tant que vous n'acceptez pas à nouveau. "
          "Pour effacer ce qui l'a déjà été, écrivez à hello@levadinho-madeira.com.",
    "de": "Erledigt: Es wird nichts mehr gespeichert, und Levadinho antwortet erst wieder, wenn du erneut akzeptierst. "
          "Um bereits Gespeichertes zu löschen, schreib an hello@levadinho-madeira.com.",
    "pl": "Gotowe: nic więcej nie jest zapisywane, a Levadinho nie odpowiada, dopóki ponownie nie zaakceptujesz. "
          "Aby usunąć to, co już zapisano, napisz na hello@levadinho-madeira.com.",
}

# ---------------------------------------------------------------- wake-on-demand notices
WAKING = {
    "pt": "O Levadinho está a carregar. Responderá em breve.",
    "en": "Levadinho is loading. It will reply shortly.",
    "fr": "Levadinho est en cours de chargement. Il répondra sous peu.",
    "de": "Levadinho wird geladen. Die Antwort folgt in Kürze.",
    "pl": "Levadinho się uruchamia. Odpowie wkrótce.",
}
BUSY = {
    "pt": "O Levadinho está muito ocupado neste momento. Escrevo-lhe aqui assim que estiver livre.",
    "en": "Levadinho is very busy right now. I'll message you here as soon as I'm free.",
    "fr": "Levadinho est très occupé en ce moment. Je vous écris ici dès que je suis libre.",
    "de": "Levadinho ist gerade sehr beschäftigt. Ich schreibe dir hier, sobald ich frei bin.",
    "pl": "Levadinho jest teraz bardzo zajęty. Napiszę do Ciebie tutaj, gdy tylko będę wolny.",
}
_LANG_HINTS = {  # a rough guess, only for the wake/busy notice (the model decides the answer's language)
    "pt": {"olá", "ola", "está", "esta", "aberto", "hoje", "bilhete", "bilhetes", "obrigado", "obrigada", "trilho",
           "não", "como", "onde", "quanto", "posso", "percurso", "bom", "dia", "tempo", "você", "vocês"},
    "en": {"is", "the", "open", "today", "how", "where", "what", "when", "can", "hello", "hi", "ticket", "tickets",
           "trail", "thanks", "do", "i", "you", "weather", "much"},
    "fr": {"est", "le", "la", "les", "ouvert", "aujourd'hui", "bonjour", "comment", "où", "quand", "billet",
           "sentier", "merci", "je", "vous", "combien", "est-ce", "il"},
    "de": {"ist", "der", "die", "das", "heute", "offen", "geöffnet", "wie", "wo", "wann", "hallo", "danke", "ich",
           "wanderweg", "karte", "tickets", "kann", "man", "und"},
    "pl": {"czy", "jest", "dziś", "dzisiaj", "otwarty", "jak", "gdzie", "kiedy", "cześć", "dzień", "dobry",
           "bilet", "szlak", "dziękuję", "ile", "można", "mogę"},
}


def guess_lang(text):
    t = (text or "").lower()
    if re.search(r"[łąęśżźńć]", t):
        return "pl"
    if re.search(r"[äöüß]", t):
        return "de"
    if re.search(r"[ãõ]", t):
        return "pt"
    words = set(re.findall(r"[\w'-]+", t))
    scores = {lang: len(words & hints) for lang, hints in _LANG_HINTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else None


def notice_lang(user, text=None):
    """Language for the wake/busy notice: a guess from the message, else the chosen language, else English."""
    return guess_lang(text) or (store.get_user(user) or {}).get("lang") or "en"


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


def _en(note):
    """A note is {"pt": original, "en": …, …} (IFCN writes Portuguese) or a plain string: English, else the
    Portuguese original, else whatever there is."""
    if not isinstance(note, dict):
        return note or ""
    return note.get("en") or note.get("pt") or next((v for v in note.values() if v), "")


def ifcn_updated(s=None):
    """The date IFCN prints on its warnings list ("ATUALIZADO: 14/09/2026"), or None."""
    s = s if s is not None else live_status()
    return (s.get("source") or {}).get("updated") or None


def status_block():
    """Today's status of every trail (IFCN list), the PR1 summit reading and the regional weather."""
    s = live_status()
    src = s.get("source") or {}
    updated = src.get("updated")
    w = s.get("weather", {})
    lines = [f"Status source: the official {src.get('name') or 'IFCN'} trail warnings list"
             + (f" (IFCN list updated {updated})" if updated else " (IFCN's update date not available)")
             + f"; Levadinho last read it on {s.get('date')}. IFCN does not update the list every day.",
             f"Counts: {', '.join(f'{k} {v}' for k, v in (s.get('counts') or {}).items())}."]
    if s.get("manual_note"):
        lines.append(f"Extra note (PR1): {s['manual_note']}")
    if w.get("ok"):
        wx = f"Measured at the Pico do Areeiro summit station (IPMA): {w.get('temp_c')} °C, humidity {w.get('humidity')}%, wind {w.get('wind_kmh')} km/h"
        if w.get("in_cloud"):
            wx += ", summit most likely inside cloud/fog"
        lines.append(wx + ".")
    else:
        lines.append("Summit weather reading unavailable today.")
    regions = s.get("regions") or []
    if regions:
        lines.append("Regional IPMA stations (region: place, °C, wind km/h, rain mm): " + "; ".join(
            f"{r['key']}: {r['place']} {r.get('temp')} °C, wind {r.get('wind') if r.get('wind') is not None else 'n/a'}, "
            f"rain {r.get('rain')}" + (", likely in cloud" if r.get("in_cloud") else "") for r in regions) + ".")
    lines.append("")
    lines.append("Every trail (code | name | TODAY'S STATUS + official note | distance | time | difficulty | type | "
                 "start → end | region | fee on your own | our page):")
    for t in s.get("trails", []):
        f = TRAIL_FACTS.get(t["code"], {})
        note = _en(t.get("note")) or (_en(s.get("note")) if t["code"] == "PR1" else "")
        fee = f"€{t['fee']}" if t.get("fee") else "no IFCN fee listed"
        dist = f.get("distance") or "?"
        alt = f" ({f['alt_min_m']}–{f['alt_max_m']} m)" if f.get("alt_min_m") and f.get("alt_max_m") else ""
        lines.append(" | ".join([t["code"], t["name"], t["status"] + (f" ({note})" if note else ""), dist,
                                 f.get("duration") or "?", (f.get("difficulty") or "?") + alt, f.get("type") or "?",
                                 f"{f.get('start') or '?'} → {f.get('end') or '?'}", t.get("region") or "?", fee,
                                 SITE + (t.get("page") or "/")]))
    return "\n".join(lines)


# ---------------------------------------------------------------- LLM
class LLMDown(Exception):
    """The model isn't running (wake-on-demand): app.py queues the message and wakes it."""


def llm(messages, max_tokens=700, schema=None, temperature=0.3):
    if llm_control.ON_DEMAND and not llm_control.is_up():
        raise LLMDown()
    body = {"model": LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": False}}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "out", "schema": schema}}
    req = urllib.request.Request(LLM_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except (ConnectionError, urllib.error.URLError) as e:
        reason = getattr(e, "reason", e)
        if llm_control.ON_DEMAND and isinstance(reason, ConnectionError):  # refused / reset: it just went down
            llm_control.mark_down()
            raise LLMDown() from e
        raise


INTENTS = ["status", "booking", "fees", "transport", "weather", "safety", "route_info", "alternatives",
           "facilities", "other"]
CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {"is_question": {"type": "boolean"},
                   "language": {"type": "string", "enum": ["pt", "en", "fr", "de", "pl", "other"]},
                   "intent": {"type": "string", "enum": INTENTS},
                   "topic": {"type": "string", "maxLength": 60},
                   "trail_code": {"type": ["string", "null"]},
                   "origin": {"type": ["string", "null"], "maxLength": 60},
                   "destination": {"type": ["string", "null"], "maxLength": 60}},
    "required": ["is_question", "language", "intent", "topic", "trail_code", "origin", "destination"],
}


def classify(text):
    """One model call: is it a question, its language, and labels for the analytics record."""
    out = llm([
        {"role": "system", "content":
            "Classify a WhatsApp message sent to a hiking-trail assistant for Madeira. "
            "is_question = true if the visitor asks something or requests information (even without a question mark); "
            "false for greetings, thanks, emojis or small talk. "
            "language = the language the message is written in: pt, en, fr, de, pl, or other. "
            "intent = what it is about: status (open/closed today), booking (tickets, SIMplifica), fees, transport "
            "(getting there/back, taxis, buses, parking), weather, safety, route_info (distance, difficulty, time, "
            "what you see), alternatives (other trails), facilities (toilets, food, water), other. "
            "topic = a short English label of the specific subject, 2-5 words (e.g. \"sunrise start time\"). "
            "trail_code = the trail's PR code if one is meant (e.g. \"PR1\"), else null. "
            "origin = for transport: the town or place the visitor says they start from or are staying in "
            "(e.g. \"Funchal\", \"the airport\"), else null. "
            "destination = for transport: the place they want to get to (e.g. \"Pico do Areeiro\"), else null."},
        {"role": "user", "content": text}], max_tokens=80, schema=CLASSIFY_SCHEMA, temperature=0)
    d = json.loads(out)
    d["lang"] = d["language"] if d["language"] in LANGS else "en"
    d.setdefault("origin", None)
    d.setdefault("destination", None)
    return d


# ---------------------------------------------------------------- knowledge
SITE = "https://levadinho-madeira.com"
FACTS = open(os.path.join(HERE, "pr1_facts.md"), encoding="utf-8").read()  # curated PR1 detail
TRAIL_FACTS = {t["code"]: t for t in json.load(open(os.path.join(HERE, "trail_facts.json"), encoding="utf-8"))["trails"]}
KB = json.load(open(os.path.join(HERE, "kb.json"), encoding="utf-8"))  # site pages as text (build_kb.py)
TRANSPORT = open(os.path.join(HERE, "transport_facts.md"), encoding="utf-8").read()  # taxis, transfers (sourced)
MAX_TRAILS, MAX_GUIDES = 3, 3
# Chat history from before this moment is ignored: replies written when the bot covered PR1 only ("I only cover
# PR1…") were copied word for word by the model. Move it forward whenever the bot's scope or rules change.
HISTORY_SINCE = 1791126000.0  # 2026-10-04 16:00 Europe/London


def _norm(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"\s+", " ", "".join(ch for ch in t if not unicodedata.combining(ch)))


def _aliases():
    """normalized name → code: full names, plus the distinctive part ("risco", "25 fontes") when it is unique."""
    full, short = {}, {}
    for code, t in TRAIL_FACTS.items():
        name = _norm(t["name"])
        full[name] = code
        core = re.sub(r"^(levada|vereda|caminho real|caminho)( (do|da|dos|das|de))? ", "", name.split(" - ")[0]).strip()
        short.setdefault(core, []).append(code)
    out = {k: v[0] for k, v in short.items() if len(v) == 1 and len(k) >= 3 and k not in {"norte", "ilha", "monte"}}
    out.update(full)
    out.update({"sao lourenco": "PR8", "vinte e cinco fontes": "PR6", "pico ruivo": "PR1.2", "areeiro": "PR1",
                "caldeirao verde": "PR9"})
    return sorted(out.items(), key=lambda kv: -len(kv[0]))


ALIASES = _aliases()
CODE_RE = re.compile(r"\bpr\s?-?(\d{1,2}(?:[.,]\d)?)\b")
# topic words (accent-free, lower case) → guide page; checked as substrings of the normalized question
TOPIC_WORDS = {
    "abroad": ["abroad", "estrangeiro", "etranger", "ausland", "zagranic", "card", "cartao", "carte", "karte", "karta",
               "error", "erro", "erreur", "fehler", "blad", "payment", "pagamento", "paiement", "zahlung", "platnos"],
    "permit": ["permit", "licen", "autoriza", "permis", "genehmigung", "pozwolen"],
    "free": ["free", "gratis", "gratuit", "sem bilhete", "kostenlos", "ohne gebuhr", "darmow", "bezplat", "non payant",
             "no ticket", "without a ticket"],
    "sunrise": ["sunrise", "nascer do sol", "lever du soleil", "sonnenaufgang", "wschod"],
    "oneway": ["one-way", "one way", "sentido unico", "sens unique", "einbahn", "jednokierun", "reverse", "backwards",
               "inverso", "a l'envers", "ruckwarts", "w druga strone"],
    "tunnels": ["tunnel", "tunel", "torch", "lanterna", "headlamp", "lampe", "latark", "czolowk"],
    "easy": ["vertig", "exposure", "exposto", "schwindel", "lek wysok", "easy", "facil", "kids", "child", "crianca",
             "enfant", "kinder", "dzieci", "family", "familia", "famille", "rodzin"],
    "best": ["best", "recommend", "melhor", "recomend", "meilleur", "conseill", "beste", "empfehl", "najlepsz", "polec"],
    "bus": ["bus", "autocarro", "onibus", "autobus", "without a car", "no car", "sem carro", "sans voiture", "ohne auto",
            "bez samochodu"],
    "booking": ["book", "reserv", "simplifica", "buch", "rezerw", "ticket", "bilhete", "billet", "bilet"],
}
PR1_GUIDES = {"sunrise", "oneway", "back", "weather"}


def trails_in(text):
    t = _norm(text)
    codes = [f"PR{m.replace(',', '.')}" for m in CODE_RE.findall(t)]
    for alias, code in ALIASES:
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", t):
            codes.append(code)
            t = t.replace(alias, " ")
    return [c for c in dict.fromkeys(codes) if c in KB["trails"]]


def pick_context(user, text, c=None):
    """→ (trail codes, guide keys) whose pages go with this question."""
    c = c or {}
    trails = trails_in(text)  # not the classifier's trail_code: it guesses (e.g. "PR1" for Levada do Moinho)
    if not trails:  # a follow-up ("and how do I get there by bus?"): the trail from the last question that named one
        for m in reversed(store.history(user, HISTORY_SINCE)):
            if m["role"] == "user" and (trails := trails_in(m["content"])):
                break
    source = (store.get_user(user) or {}).get("source") or ""
    if not trails and re.fullmatch(r"web-pr[0-9-]+", source):  # asked from a trail's page: that trail
        code = "PR" + source.removeprefix("web-pr").replace("-", ".")
        trails = [code] if code in KB["trails"] else []
    trails = trails[:MAX_TRAILS]
    t, intent = _norm(text), c.get("intent")
    g = [k for k, words in TOPIC_WORDS.items() if any(w in t for w in words)]
    if not trails and SOURCE_GUIDE.get(source):  # asked from a guide page: that guide first
        g.insert(0, SOURCE_GUIDE[source])
    if intent == "booking":
        g.append("booking")
    if intent == "alternatives":
        g.append("best")
    pr1ish = not trails or any(x in ("PR1", "PR1.2") for x in trails)
    if intent == "transport" and pr1ish and ("PR1" in trails or "PR1.2" in trails):
        g.insert(0, "back")
    if intent == "transport" and not trails:
        g.append("bus")
    if intent == "weather" and pr1ish:
        g.append("weather")
    if trails:  # the trail page already has its own bus, booking and exposure sections; an island-wide list
        # would only pull the answer away from the trail's own "Nearby trails"
        g = [k for k in g if k not in ("bus", "booking", "easy", "best") or intent == "booking" and k == "booking"]
    if not pr1ish:
        g = [k for k in g if k not in PR1_GUIDES]
    if "bus" in g:  # a "by bus" question: the bus guide is the answer; a second list only distracts
        g = [k for k in g if k not in ("best", "easy")]
    return trails, [k for k in dict.fromkeys(g) if k in KB["guides"]][:MAX_GUIDES]


def detail_block(trails, guides, transport=False):
    parts = [f"### Getting around (taxis, transfers, buses)\n{TRANSPORT}"] if transport else []
    for code in trails:
        if code == "PR1":
            parts.append(f"### PR1 Vereda do Areeiro (curated knowledge; page {SITE}/pr1/)\n{FACTS}")
        else:
            k = KB["trails"][code]
            parts.append(f"### {code} {k['name']} (our page {k['url']})\n{k['text']}")
    for key in guides:
        k = KB["guides"][key]
        parts.append(f"### Guide: {k['url']}\n{k['text']}")
    return "\n\n".join(parts) or "(no trail or topic page matched this question: use the table and the general rules)"


SYSTEM = """You are Levadinho, a friendly, knowledgeable old Madeiran mountain guide who helps visitors on WhatsApp with Madeira's official PR walking trails (the classified "Percursos Recomendados" on Madeira island, listed in the TRAIL TABLE below).

LANGUAGE: {lang_rule}

HOW TO ANSWER
- Never mention which languages you speak or any language rule; just reply naturally.
- Your earlier replies in this chat may be out of date. If one contradicts the rules or facts below, follow the rules and facts below and don't repeat it.
- WhatsApp style: short and practical, 2–8 short lines, no headings, no markdown tables. *Bold* sparingly. At most one emoji.
- Use ONLY the facts in LIVE STATUS, TRAIL TABLE, GENERAL RULES and DETAILS below. If something isn't there, say you don't know and point to SIMplifica, IFCN or the trail's page on our site. Never invent prices, times, distances, phone numbers, bus routes or rules, and never guess a fact about one trail from another.
- Today's open/closed state comes ONLY from the TRAIL TABLE status (the official IFCN list). Say it's according to IFCN's official warnings list and give the date IFCN says it was updated (e.g. "according to IFCN's list, updated 14/09/2026"). Never say it was checked this morning or today: IFCN doesn't update the list every day. The DETAILS are web pages that mention a "live badge" or "status card above": ignore those phrases; you have the status in the table.
- If a trail is CLOSED or PARTIAL, say so plainly with the official note, and suggest alternatives ONLY among trails the table shows OPEN (nearby ones from the same region or the page's "Nearby trails" list are best).
- Bus questions: give the stops, line numbers and departure times exactly as written in DETAILS for the day the visitor means (or all day types if they don't say), listing EVERY trip given there: count them and check none is missing. Name a line number only if DETAILS print it next to that trip; otherwise say "CAM's Santana-line buses" (or the operator) without a number. Mention that times at intermediate stops are approximate and to check before travelling. If DETAILS say there is no bus, say so. Never make up a connection: a trail has a bus only if its own page or the "Levadas by bus" guide says so, and "which walks can I do without a car" is answered from that guide's lists (there and back / bus + taxi / one end only).
- Copy facts exactly as the table or DETAILS give them: difficulty, distance, time, altitude, fees, which end of a walk a bus or taxi serves. Never soften or upgrade them (a "Moderate" trail is not "easy"; a page that warns of vertigo means you must not say it has no difficult sections).
- "Easy" recommendations: only trails whose difficulty is Easy in the table or DETAILS; mention any exposure/vertigo warning the DETAILS give. "Near <place>": only trails whose start is at or next to that place, or the page's "Nearby trails" list; otherwise say which region they are in instead of calling them near. When suggesting a trail "nearby" or "instead", pick ONLY from that trail's "Nearby trails" list in DETAILS (and only ones the table shows OPEN); never a trail from another region.
- PR1: always remind about the one-way rule and the return from Achada do Teixeira when someone plans the full walk.
- Booking: SIMplifica, online only. Give the link https://simplifica.madeira.gov.pt/services/78-82-259 only when the visitor asks about booking, tickets or fees, or says they are going to walk a trail.
- Don't write links to our own site (levadinho-madeira.com) for the trails you mention: they are added after your reply automatically. A guide page you used may be linked.
- A trail that isn't in the table (an unclassified levada, Porto Santo, another island): say you cover Madeira's official PR trails, and use only what GENERAL RULES say about walks outside them.
- Off-topic requests (not Madeira hiking/visiting): politely decline in one line and say that for anything else they can write to hello@levadinho-madeira.com.
- If someone wants a person, has a complaint, or asks who runs Levadinho: it is an independent guide, not affiliated with IFCN or the Regional Government (the trail status comes from IFCN's official list); a person answers at hello@levadinho-madeira.com.
- Never present yourself as IFCN, the Regional Government or any official body.
- Never name or recommend a private company: no transfer, tour or guiding company, hotel, shop or restaurant, even when DETAILS mention one by name (owner's rule: no referrals). The only contacts you may give are the official taxi numbers and taxismadeira.pt from the taxi facts, and official bodies (IFCN, SIMplifica, Visit Madeira). For transfers: say hotels and private transfer companies can arrange one, without naming any, and give the bus and taxi options. Indicative transfer prices from DETAILS are fine.
- Getting from A to B: start from where the visitor is staying ("Staying in: …" in their message, or what they said earlier). Give the public bus only if DETAILS show one from there (with its times); otherwise say there is no bus from there in our information. Give the taxi number for that town, or the nearest town in the taxi table, saying the numbers are as printed on IFCN's trailhead panels; for Funchal also mention online booking at taxismadeira.pt. Taxi fares: there is no official table, so tell them to ask for a quote.
- Safety first: never encourage walking a closed trail or section, going without a ticket, or walking PR1 in reverse.

LIVE STATUS
{status}

GENERAL RULES (fees, exemptions, refunds, fines; from our fees page)
{general}

DETAILS (pages that match this question)
{details}
"""


SITE_LINK = {
    "en": "🥾 {code} {name} on our site: {url}",
    "pt": "🥾 {code} {name} no nosso site: {url}",
    "fr": "🥾 {code} {name} sur notre site : {url}",
    "de": "🥾 {code} {name} auf unserer Website: {url}",
    "pl": "🥾 {code} {name} na naszej stronie: {url}",
}
MAX_SITE_LINKS = 2


def site_links(reply, trails, lang, named=None):
    """Our page for the trails the reply talks about (else the ones the question named), as closing lines:
    the visitor always gets the full guide, whatever links the model chose. A trail only remembered from an
    earlier message (pick_context's follow-up guess) gets a link only if the reply talks about it."""
    in_reply = trails_in(reply)
    named = trails if named is None else named
    # the question's own trail when the reply is about it; else the trails the reply recommends; else the question's
    codes = [t for t in trails if t in in_reply] or in_reply or named
    lines = []
    for code in codes:
        k = KB["trails"].get(code)
        if k and k["url"] not in reply and len(lines) < MAX_SITE_LINKS:
            lines.append(SITE_LINK[lang].format(code=code, name=k["name"], url=k["url"]))
    return "\n\n" + "\n".join(lines) if lines else ""


def answer(user, text, lang, meta=None, c=None):
    rule = (f"Write your reply ONLY in {LANG_NAMES[lang]}, whatever language earlier messages used. "
            f"Keep place and trail names (Pico do Areeiro, Levada das 25 Fontes…) as they are.")
    trails, guides = pick_context(user, text, c)
    transport = (c or {}).get("intent") == "transport" or bool(re.search(
        r"taxi|táxi|transfer|transfe|bus|autocarro|shuttle|navette|lift|boleia", _norm(text)))
    system = SYSTEM.format(lang_rule=rule, status=status_block(), general=KB["guides"]["fees"]["text"],
                           details=detail_block(trails, guides, transport))
    source = (store.get_user(user) or {}).get("source") or ""
    page = KB["guides"].get(SOURCE_GUIDE.get(source, ""), {}).get("url")
    if page:  # opened the chat from one of our guide pages
        system += (f"\nTHE VISITOR CAME FROM OUR PAGE {page}. When their question leaves the destination or the "
                   "subject open, assume it is that page's subject, say so in a few words, and include the public "
                   "bus option from that page's DETAILS if it has one.\n")
    msgs = [{"role": "system", "content": system}] + store.history(user, HISTORY_SINCE) + [{"role": "user", "content": text}]
    t0 = time.time()
    reply = re.sub(r"\*\*(.+?)\*\*", r"*\1*", llm(msgs, temperature=0))  # WhatsApp bold is *single*; 0 = stick to the facts
    reply = reply.rstrip() + site_links(reply, trails, lang, named=trails_in(text))
    if meta is not None:
        meta["answer"] = {"latency_ms": int((time.time() - t0) * 1000), "model": LLM_MODEL,
                          "context": {"trails": trails, "guides": guides}}
        meta["events"].append(("answer_sent", {"lang": lang, "latency_ms": meta["answer"]["latency_ms"]}))
    store.add_turn(user, text, reply)
    return reply


# ---------------------------------------------------------------- flow
def picker():
    return {"type": "list", **PICKER}


def consent_prompt(user, lang, pending=""):
    """The privacy notice with Accept / Don't accept. `pending` is what to do after Accept:
    "q:<question>" (answer it) or "c:<campaign tag>" (send that route's welcome). A message without
    one of its own keeps what was already waiting."""
    state = (store.get_user(user) or {}).get("state") or ""
    if not pending and state.startswith("notice:"):
        pending = state.removeprefix("notice:")
    store.set_user(user, state=f"notice:{pending}")
    yes, no = CONSENT_BUTTONS[lang]
    return {"type": "buttons", "body": CONSENT_ASK[lang].format(url=POLICY_URL.format(lang=lang)),
            "buttons": [("consent_yes", yes), ("consent_no", no)]}


def accepted(user):
    return (store.get_user(user) or {}).get("consent") == "yes"


def handle_consent(user, yes, meta=None):
    """The visitor tapped Accept / Don't accept. app.py reads the new state to decide what to record.
    After Accept, what they wrote before is answered straight away; with nothing waiting, one short line."""
    meta = meta if meta is not None else {"events": []}
    u = store.get_user(user) or {}
    lang = u.get("lang") or "en"
    was = u.get("consent")
    pending = (u.get("state") or "").removeprefix("notice:") if (u.get("state") or "").startswith("notice:") else ""
    store.set_user(user, consent="yes" if yes else "no", state="ready")
    meta["lang"] = lang
    if not yes:
        meta["events"].append(("consent_withdrawn" if was == "yes" else "consent_declined", {"version": CONSENT_VERSION}))
        return [{"type": "text", "body": (CONSENT_WITHDRAWN if was == "yes" else CONSENT_NO)[lang]}]
    meta["events"].append(("consent_given", {"version": CONSENT_VERSION}))
    if was == "yes":  # re-accepted after typing "privacy": nothing to resume
        return [{"type": "text", "body": ASK[lang]}]
    kind, _, arg = pending.partition(":")
    if kind == "c" and arg in CAMPAIGNS:
        meta["campaign"] = arg
        return [welcome(user, CAMPAIGNS[arg], lang, meta, campaign=arg)]
    if kind == "c" and is_web_tag(arg):  # came from a website link: a source only, no guide link
        meta["campaign"] = arg
        return [{"type": "text", "body": ASK[lang]}]
    if kind == "q" and arg:  # what they wrote before accepting
        try:
            c = classify(arg)
            reply = respond(user, arg, c["lang"], meta, c)
        except LLMDown:  # the model is asleep: the acceptance stands, app.py queues the question
            meta["deferred_question"] = arg
            meta.pop("answer", None)
            meta["events"] = [e for e in meta["events"] if e[0] != "answer_sent"]
            return []
        meta.update(is_question=True, intent=c["intent"], topic=c["topic"], trail=c["trail_code"])
        meta["events"].append(("question_asked", {"lang": c["lang"], "intent": c["intent"], "topic": c["topic"],
                                                  "trail_code": c["trail_code"],
                                                  "trail_status": str(live_status().get("status", ""))}))
        meta["resumed_question"] = arg
        return [{"type": "text", "body": reply}]
    return [{"type": "text", "body": ASK[lang]}]


def respond(user, text, lang, meta, c):
    """Answer a request. Getting from A to B: first ask where the visitor is staying (owner, 2026-10-05),
    unless the message gives both ends ("bus from Funchal to Pico do Areeiro") or they told us before.
    "Transfer from the airport" has no end: where they stay is the destination."""
    base = (store.get_user(user) or {}).get("base")
    if c.get("intent") == "transport" and not (c.get("origin") and c.get("destination")):
        if not base:
            store.set_user(user, state=f"base:{lang}:{text}")
            return ASK_BASE[lang]
        text = f"{text}\n(Staying in: {base})"
    return answer(user, text, lang, meta, c)


def fmt_distance(m, lang):
    if m < 1000:
        return f"{max(10, round(m, -1)):.0f} m"
    km = f"{m / 1000:.1f}" if m < 100_000 else f"{m / 1000:.0f}"
    return (km if lang == "en" else km.replace(".", ",")) + " km"


def ask_location(lang):
    return {"type": "location_request", "body": LOC_ASK[lang]}


def guide_link(user, route, lang, meta=None, via=None, campaign=None):
    """→ (personal guide link, route title in the visitor's language)."""
    token = store.new_guide_token(user, route["id"])
    if meta is not None:
        meta["events"].append(("guide_link_sent", {"session": token, "route": route["id"], "lang": lang,
                                                   "campaign": campaign, "via": via}))
    return f"{GUIDE_URL}?r={route['id']}&l={lang}&t={token}", route["title"].get(lang) or route["title"]["en"]


def offline_note(rid, lang):
    return OFFLINE_NOTE["pr1" if rid == "pr1" else "other"][lang]


def welcome(user, rid, lang, meta=None, campaign=None):
    route = geo.load_route(rid)
    if not route:
        return {"type": "text", "body": ASK[lang]}
    link, title = guide_link(user, route, lang, meta, via="campaign", campaign=campaign)
    return {"type": "text", "body": WELCOME[lang].format(title=title, link=link, note=offline_note(rid, lang))}


def handle_location(user, lat, lon, meta=None):
    """A shared pin → the guide link for the route that starts nearby, or how far PR1 is."""
    lang = (store.get_user(user) or {}).get("lang") or "en"
    if not accepted(user):
        meta = meta if meta is not None else {"events": []}
        meta["lang"] = lang
        return [consent_prompt(user, lang)]
    route, dist = geo.nearest_route(lat, lon)
    if meta is not None:
        meta["lang"] = lang
        meta["events"].append(("location_shared", {"lat": lat, "lon": lon, "lang": lang,
                                                   "nearest_route": route and route["id"],
                                                   "distance_m": None if dist is None else int(dist)}))
    if route and dist <= NEAR_M:
        link, title = guide_link(user, route, lang, meta, via="location")
        return [{"type": "text", "body": LOC_NEAR[lang].format(
            dist=fmt_distance(dist, lang), title=title, link=link, note=offline_note(route["id"], lang))}]
    status = str(live_status().get("status", "")).upper()
    word = STATUS_WORDS.get(status, {}).get(lang, status.lower() or "?")
    far = geo.distance_m(lat, lon, *AREEIRO)
    updated = ifcn_updated() or "?"
    return [{"type": "text", "body": LOC_FAR[lang].format(dist=fmt_distance(far, lang), status=word, updated=updated)}]


def handle(user, text=None, choice=None, meta=None):
    """Return a list of outgoing messages: {"type": "text", "body": ...} or a picker.

    `meta` (optional dict with an "events" list) is filled with what happened, for the
    analytics record written by app.py: language, question labels, events.

    Before Accept nothing needs the model: greetings are recognised by their words, the language from the
    greeting or the message, and anything that isn't a greeting waits for Accept and is then answered. The
    language menu is sent only when the language can't be told, and only once."""
    meta = meta if meta is not None else {"events": []}
    meta.setdefault("events", [])
    u = store.get_user(user)
    state = (u or {}).get("state") or ""

    if choice in LANGS:  # tapped a row in the picker
        rest = state.partition(":")[2]  # "picking:<campaign tag>" or "picking:q:<message waiting>"
        tag = rest if known_tag(rest) else ""
        waiting = rest if rest.startswith("q:") else ""
        store.set_user(user, lang=choice, state="ready")
        meta["lang"] = choice
        meta["events"].append(("language_selected", {"lang": choice, "campaign": tag or None}))
        if known_tag(tag):
            meta["campaign"] = tag
        if not accepted(user):
            return [consent_prompt(user, choice, waiting or (f"c:{tag}" if known_tag(tag) else ""))]
        if tag in CAMPAIGNS:
            return [welcome(user, CAMPAIGNS[tag], choice, meta, campaign=tag)]
        return [{"type": "text", "body": ASK[choice]}]

    text = (text or "").strip()
    if not text:
        return [picker()] if not u or not u.get("lang") else []

    m = re.search(r"#([a-z0-9-]+)", text.lower())
    tag = m.group(1) if m and known_tag(m.group(1)) else ""
    if is_greeting(text):
        meta["campaign"] = tag or None
        if tag in CAMPAIGNS:  # a campaign QR: picker → welcome + that route's guide link
            store.set_user(user, state=f"picking:{tag}")
            meta["campaign"] = tag
            meta["events"].append(("qr_scanned", {"campaign": tag, "source": "qr"}))
            return [picker()]
        if tag:  # a website link: the page is the source; its greeting is in the page's language
            store.set_user(user, source=tag)
            meta["campaign"] = tag
            meta["events"].append(("qr_scanned", {"campaign": tag, "source": "web"}))
        # The greeting's language counts when the visitor typed it or it came from a website page; the
        # general QR's Portuguese "Olá Levadinho!" says nothing about the visitor's language.
        g = greeting_lang(text) if (tag or "levadinho" not in text.lower()) else None
        known = (u or {}).get("lang")
        if not accepted(user):
            if g and (g != known or not state.startswith("notice:")):
                store.set_user(user, lang=g)
                meta["lang"] = g
                return [consent_prompt(user, g)]
            if known or g:
                return [] if state.startswith("notice:") else [consent_prompt(user, known or g)]
            if state.startswith("picking") and not tag:
                return []  # the menu is already on screen
            store.set_user(user, state=f"picking:{tag}" if tag else "picking")
            return [picker()]
        lang = g or known or "en"
        store.set_user(user, lang=lang, state="ready")
        meta["lang"] = lang
        return [{"type": "text", "body": ASK[lang]}]

    if text.lower().strip(" !?.") in CHANGE_WORDS:
        store.set_user(user, state="picking")
        return [picker()]

    if text.lower().strip(" !?.") in PRIVACY_WORDS:
        return [consent_prompt(user, (u or {}).get("lang") or "en")]

    word = text.lower().strip(" !?.")
    if word in GUIDE_WORDS:  # "guide" / "guia"… → ask for a location pin with WhatsApp's button
        lang = (u or {}).get("lang") or GUIDE_WORDS[word] or "en"
        meta["lang"] = lang
        if not accepted(user):
            return [consent_prompt(user, lang)]
        meta["events"].append(("location_requested", {"lang": lang}))
        return [ask_location(lang)]

    if not accepted(user):  # nothing is answered before the notice is accepted; what they wrote waits for it
        waiting = state.partition(":")[2] if state.startswith(("notice:q:", "picking:q:")) else ""
        waiting = f"{waiting}\n{text}" if waiting else f"q:{text}"
        meta["warm_up"] = True  # app.py starts the model now, so the answer is quick after Accept
        lang = guess_lang(text) or (u or {}).get("lang")
        if lang:
            store.set_user(user, lang=lang)
            meta["lang"] = lang
            return [consent_prompt(user, lang, waiting)]
        store.set_user(user, state=f"picking:{waiting}")
        return [] if state.startswith("picking") else [picker()]

    if state.startswith("base:"):  # the answer to "where are you staying?"
        _, lang, original = state.split(":", 2)
        if "?" not in text and len(text) <= 60:
            c = classify(original)  # before any change, so a replay after LLMDown starts from the same state
            store.set_user(user, base=text, state="ready")
            meta.update(lang=lang, is_question=True, intent=c["intent"], topic=c["topic"], trail=c["trail_code"])
            return [{"type": "text", "body": answer(user, f"{original}\n(Staying in: {text})", lang, meta, c)}]
        store.set_user(user, state="ready")  # a new question instead: carry on with it

    c = classify(text)
    meta.update(lang=c["lang"], is_question=c["is_question"])
    if c["is_question"]:
        meta.update(intent=c["intent"], topic=c["topic"], trail=c["trail_code"])
        meta["events"].append(("question_asked", {"lang": c["lang"], "intent": c["intent"], "topic": c["topic"],
                                                  "trail_code": c["trail_code"],
                                                  "trail_status": str(live_status().get("status", ""))}))
    if not u or not u.get("lang"):
        store.set_user(user, lang=c["lang"], state="ready")
    # Questions are answered in the language they're written in; anything else in the chosen one.
    lang = c["lang"] if c["is_question"] or not (u or {}).get("lang") else u["lang"]
    meta["lang"] = lang
    return [{"type": "text", "body": respond(user, text, lang, meta, c)}]
