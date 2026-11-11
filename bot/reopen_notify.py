"""Reopening alerts (owner, 2026-11-11): "ask tourists if they want to be notified when the trails open again. We can
send a WhatsApp message to them as soon as we detect the IFCN notice."

  1. Offer: during an IFCN island-wide closure (status.json alert.blanket = "closed") the bot's first answer to each
     WhatsApp visitor ends with OFFER ("Reply YES"); the web chat gets a wa.me link that sends NOTIFY_TEXT instead
     (the web chat has no number to write to). "Notify me…" in any of the 5 languages also signs a visitor up.
  2. List: table reopen_watch in the bot's working store (bot/levadinho.db): the number, language, time. The only place
     a number is kept for this; deleted once the message has gone out, after 30 days without a reopening, on STOP,
     and with the rest of the working store on an erasure request (store.erase).
  3. Owner first (owner: "Let me know first"): storm_watch.py calls alert_owner() on every new / removed IFCN
     announcement → a WhatsApp to OWNER_WA (bot/.env). The owner checks it and replies SEND (app.py → broadcast()).
     Nothing goes to visitors without that reply.
  4. Messages we start after WhatsApp's 24-hour window need approved templates (twilio_content.py: levadinho_reopen_<lang>,
     levadinho_owner_alert); inside the window a plain message goes out.

  python3 bot/reopen_notify.py status          # who is waiting (count per language), owner alert state
  python3 bot/reopen_notify.py test-owner      # send the owner a test alert
"""
import base64
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _env():
    """bot/.env when run outside the webhook (storm_watch.py): KEY=VALUE lines, without overriding the environment."""
    try:
        for line in open(os.path.join(HERE, ".env")):
            k, sep, v = line.strip().partition("=")
            if sep and k and not k.startswith("#"):
                os.environ.setdefault(k, v)
    except OSError:
        pass


_env()
import store  # noqa: E402  (after _env: LEVADINHO_DB may come from .env)

WA_NUMBER = "447455718697"
FROM = os.environ.get("TWILIO_WA_FROM", "whatsapp:+447455718697")
CONTENT_FILE = os.path.join(HERE, "twilio_content.json")
WINDOW_S = 24 * 3600 - 300
KEEP_S = 30 * 24 * 3600
OFFERED_S = 24 * 3600          # a YES counts within a day of the offer
SEND_VALID_S = 48 * 3600       # the owner's SEND works for two days after an alert
NOTIFY_TAG = "web-reopen"


OFFER = {
    "en": "🔔 Want a WhatsApp message as soon as IFCN reopens the trails? Reply *YES*.",
    "pt": "🔔 Quer receber uma mensagem no WhatsApp assim que o IFCN reabrir os percursos? Responda *SIM*.",
    "fr": "🔔 Voulez-vous un message WhatsApp dès que l'IFCN rouvrira les sentiers ? Répondez *OUI*.",
    "de": "🔔 Möchten Sie eine WhatsApp-Nachricht, sobald das IFCN die Wege wieder öffnet? Antworten Sie *JA*.",
    "pl": "🔔 Chcesz dostać wiadomość na WhatsAppie, gdy tylko IFCN ponownie otworzy szlaki? Odpowiedz *TAK*.",
}
OFFER_WEB = {
    "en": "🔔 Want a WhatsApp message as soon as IFCN reopens the trails? Tap here and send the message: {link}",
    "pt": "🔔 Quer receber uma mensagem no WhatsApp assim que o IFCN reabrir os percursos? Toque aqui e envie a mensagem: {link}",
    "fr": "🔔 Voulez-vous un message WhatsApp dès que l'IFCN rouvrira les sentiers ? Touchez ici et envoyez le message : {link}",
    "de": "🔔 Möchten Sie eine WhatsApp-Nachricht, sobald das IFCN die Wege wieder öffnet? Tippen Sie hier und senden Sie die Nachricht: {link}",
    "pl": "🔔 Chcesz dostać wiadomość na WhatsAppie, gdy tylko IFCN ponownie otworzy szlaki? Dotknij tutaj i wyślij wiadomość: {link}",
}
NOTIFY_TEXT = {
    "en": "Notify me when the trails reopen",
    "pt": "Avisem-me quando os percursos reabrirem",
    "fr": "Prévenez-moi quand les sentiers rouvriront",
    "de": "Benachrichtigen Sie mich, wenn die Wege wieder öffnen",
    "pl": "Powiadom mnie, gdy szlaki zostaną otwarte",
}
SUBSCRIBED = {
    "en": "🔔 Done. We'll send you one WhatsApp message as soon as IFCN reopens the trails, then delete your number from the list. Reply *STOP* to cancel.",
    "pt": "🔔 Feito. Enviamos-lhe uma única mensagem no WhatsApp assim que o IFCN reabrir os percursos e depois apagamos o seu número da lista. Responda *PARAR* para cancelar.",
    "fr": "🔔 C'est noté. Nous vous enverrons un seul message WhatsApp dès que l'IFCN rouvrira les sentiers, puis nous effacerons votre numéro de la liste. Répondez *STOP* pour annuler.",
    "de": "🔔 Erledigt. Wir schicken Ihnen eine einzige WhatsApp-Nachricht, sobald das IFCN die Wege wieder öffnet, und löschen dann Ihre Nummer von der Liste. Antworten Sie *STOPP*, um abzubrechen.",
    "pl": "🔔 Gotowe. Wyślemy jedną wiadomość na WhatsAppie, gdy tylko IFCN ponownie otworzy szlaki, a potem usuniemy Twój numer z listy. Odpowiedz *STOP*, aby anulować.",
}
CANCELLED = {
    "en": "🔕 Cancelled: your number is off the list.",
    "pt": "🔕 Cancelado: o seu número saiu da lista.",
    "fr": "🔕 Annulé : votre numéro a été retiré de la liste.",
    "de": "🔕 Abgebrochen: Ihre Nummer ist von der Liste gelöscht.",
    "pl": "🔕 Anulowano: Twój numer został usunięty z listy.",
}
NOT_CLOSED = {
    "en": "The classified trails aren't closed island-wide right now, so there's no reopening to wait for.",
    "pt": "Neste momento os percursos classificados não estão encerrados em toda a ilha, por isso não há reabertura a aguardar.",
    "fr": "Les sentiers classés ne sont pas fermés sur toute l'île en ce moment : il n'y a pas de réouverture à attendre.",
    "de": "Die klassifizierten Wege sind derzeit nicht inselweit gesperrt, es gibt also keine Wiedereröffnung, auf die man warten müsste.",
    "pl": "Sklasyfikowane szlaki nie są teraz zamknięte na całej wyspie, więc nie ma na co czekać.",
}
# The visitor message (owner's wording, 2026-11-11). Also the approved templates' text (twilio_content.py).
REOPENED = {
    "en": "We are texting you because you asked to know when the trails reopen. IFCN has now reopened Madeira's classified trails. Book your ticket on SIMplifica before you set off.",
    "pt": "Estamos a enviar-lhe esta mensagem porque pediu para saber quando os percursos reabrem. O IFCN já reabriu os percursos pedestres classificados da Madeira. Reserve o seu bilhete no SIMplifica antes de partir.",
    "fr": "Nous vous écrivons parce que vous avez demandé à savoir quand les sentiers rouvriraient. L'IFCN a rouvert les sentiers classés de Madère. Réservez votre billet sur SIMplifica avant de partir.",
    "de": "Wir schreiben Ihnen, weil Sie wissen wollten, wann die Wege wieder öffnen. Das IFCN hat die klassifizierten Wanderwege auf Madeira wieder geöffnet. Buchen Sie Ihr Ticket auf SIMplifica, bevor Sie losgehen.",
    "pl": "Piszemy w odpowiedzi na Twoją prośbę o powiadomienie o ponownym otwarciu szlaków. IFCN ponownie otworzył sklasyfikowane szlaki na Maderze. Zarezerwuj bilet w SIMplifica przed wyjściem.",
}
OWNER_ALERT = ("Levadinho alert: a new official notice was detected. {kind}: {text} Link: {link} — {n} visitors are waiting "
               "for the reopening message. Reply SEND to send it, or ignore this message.")

YES = {"yes", "yes please", "yep", "sim", "sim por favor", "claro", "oui", "oui merci", "ja", "ja bitte", "ja gerne", "tak", "tak prosze"}
STOP = {"stop", "stopp", "parar", "cancel", "cancelar", "annuler", "abbrechen", "anuluj"}
NOTIFY_RE = re.compile(r"notify me|let me know when (?:the )?trails|avise[mn]?-?me|avisa-?me|previens-moi|prevenez-moi|"
                       r"benachrichtig|powiadom")


def fold(text):
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^\w' -]", " ", t).split())


def _lang(lang):
    return lang if lang in OFFER else "en"


def is_web(user):
    return str(user).startswith("web:")


# ---------------------------------------------------------------- the list
def waiting(user):
    return store._db.execute("SELECT 1 FROM reopen_watch WHERE user=?", (user,)).fetchone() is not None


def add(user, lang):
    store._db.execute("INSERT OR REPLACE INTO reopen_watch VALUES (?,?,?)", (user, _lang(lang), time.time()))
    store._db.commit()


def remove(user):
    n = store._db.execute("DELETE FROM reopen_watch WHERE user=?", (user,)).rowcount
    store._db.commit()
    return n


def expire():
    store._db.execute("DELETE FROM reopen_watch WHERE at < ?", (time.time() - KEEP_S,))
    store._db.commit()


def everyone():
    expire()
    return store._db.execute("SELECT user, lang, at FROM reopen_watch ORDER BY at").fetchall()


# ---------------------------------------------------------------- in the conversation
def wa_link(lang):
    return f"https://wa.me/{WA_NUMBER}?text=" + urllib.parse.quote(f"{NOTIFY_TEXT[_lang(lang)]} #{NOTIFY_TAG}")


def offer(user, lang, status):
    """→ the offer line to add under an answer, or None. Once per visitor per closure, only during a blanket closure."""
    alert = (status or {}).get("alert") or {}
    if alert.get("blanket") != "closed" or (not is_web(user) and waiting(user)):
        return None
    key = f"reopen_offer:{user}"
    closure = str(alert.get("blanket_from") or "closed")
    try:
        prev = json.loads(store.get_flag(key) or "{}")
    except ValueError:
        prev = {}
    if prev.get("closure") == closure:
        return None
    store.set_flag(key, json.dumps({"closure": closure, "at": time.time()}))
    lang = _lang(lang)
    return OFFER_WEB[lang].format(link=wa_link(lang)) if is_web(user) else OFFER[lang]


def intercept(user, text, lang, status, meta=None):
    """A reply to the offer (YES), a "notify me" request or STOP → the answer; anything else → None."""
    word = fold(re.sub(r"#[\w-]+", " ", text or ""))
    lang = _lang(lang)
    asked = bool(NOTIFY_RE.search(word))
    if word in STOP and not is_web(user) and waiting(user):
        remove(user)
        if meta is not None:
            meta["events"].append(("reopen_unsubscribed", {"lang": lang}))
        return CANCELLED[lang]
    yes = False
    if word in YES and not is_web(user):
        try:
            prev = json.loads(store.get_flag(f"reopen_offer:{user}") or "{}")
        except ValueError:
            prev = {}
        yes = time.time() - prev.get("at", 0) < OFFERED_S
    if not (asked or yes):
        return None
    if ((status or {}).get("alert") or {}).get("blanket") != "closed":
        return NOT_CLOSED[lang] if asked else None
    if is_web(user):
        return OFFER_WEB[lang].format(link=wa_link(lang))
    add(user, lang)
    if meta is not None:
        meta["events"].append(("reopen_subscribed", {"lang": lang}))
    return SUBSCRIBED[lang]


# ---------------------------------------------------------------- sending (Twilio REST, no SDK: also runs from storm_watch)
def _api(path, data=None):
    sid, tok = os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/{path}",
                                 urllib.parse.urlencode(data).encode() if data else None,
                                 headers={"Authorization": "Basic " + base64.b64encode(f"{sid}:{tok}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _content():
    try:
        return json.load(open(CONTENT_FILE))
    except (OSError, ValueError):
        return {}


def _send(digits, body, template=None, variables=None):
    """In WhatsApp's 24-hour window (the person wrote to us) a plain message, else the template. → message SID."""
    last = store.last_inbound(digits)
    data = {"From": FROM, "To": f"whatsapp:+{digits}"}
    if last and time.time() - last < WINDOW_S or not template:
        data["Body"] = body
    else:
        data["ContentSid"] = template
        if variables:
            data["ContentVariables"] = json.dumps(variables, ensure_ascii=False)
    return _api("Messages.json", data)["sid"]


def _status(msid):
    try:
        return _api(f"Messages/{msid}.json").get("status")
    except Exception:  # noqa: BLE001
        return "unknown"


def owner():
    d = re.sub(r"\D", "", os.environ.get("OWNER_WA", ""))
    if d.startswith("00"):
        d = d[2:]
    elif d.startswith("0"):
        d = "44" + d[1:]
    if d.startswith("44") and len(d) != 12 or not 10 <= len(d) <= 15:   # a typo never reaches a stranger
        return ""
    return d


def _param(s, n):
    """WhatsApp template parameters: no newlines / tabs / runs of spaces."""
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def alert_owner(changes, link, arm=True):
    """storm_watch.py: IFCN announcements changed. changes = [(what, kind, text)]. Never raises."""
    to = owner()
    if not to:
        return "no OWNER_WA"
    n = len(everyone())
    what, kind, text = changes[0]
    more = f" (+{len(changes) - 1} more)" if len(changes) > 1 else ""
    kind_s = f"IFCN {kind} notice {'REMOVED' if what == 'removed' else 'new'}{more}"
    v = {"1": _param(kind_s, 80), "2": _param(text, 400), "3": link, "4": str(n)}
    body = OWNER_ALERT.format(kind=v["1"], text=v["2"], link=link, n=n)
    try:
        msid = _send(to, body, _content().get("levadinho_owner_alert"), v)
        if arm:   # SEND works for SEND_VALID_S after a real alert
            store.set_flag("reopen_alert_at", str(time.time()))
        return f"sent {msid}"
    except Exception as e:  # noqa: BLE001
        return f"failed: {e}"


def broadcast(log=print):
    """The owner replied SEND: the reopening message to everyone waiting. A number leaves the list once its message
    is accepted by WhatsApp (sent / delivered / read); failures stay for a retry. → summary line for the owner."""
    rows = everyone()
    if not rows:
        return "Nobody is waiting for the reopening message."
    tpl = _content()
    sent = []
    for user, lang, _at in rows:
        try:
            sent.append((user, lang, _send(user, REOPENED[lang], tpl.get(f"levadinho_reopen_{lang}"))))
        except Exception as e:  # noqa: BLE001
            log(f"reopen message to …{user[-4:]} failed: {e}")
            sent.append((user, lang, None))
    time.sleep(20)
    ok, bad = 0, 0
    for user, lang, msid in sent:
        st = _status(msid) if msid else "failed"
        if st in ("sent", "delivered", "read", "queued", "accepted", "sending"):
            remove(user)
            ok += 1
            try:
                import analytics
                analytics.event("whatsapp", "reopen_notified", lang=lang)
            except Exception:  # noqa: BLE001
                pass
        else:
            bad += 1
            log(f"reopen message to …{user[-4:]}: {st}")
    store.set_flag("reopen_alert_at", None)
    return f"Reopening message sent to {ok} visitor(s)" + (f"; {bad} failed and stay on the list (reply SEND to retry)." if bad else ".")


def owner_command(sender, text):
    """app.py: the owner's SEND → (reply now, start the broadcast?) or None when it isn't the owner's command."""
    if not sender or sender != owner() or fold(text) not in ("send", "enviar"):
        return None
    at = float(store.get_flag("reopen_alert_at") or 0)
    if time.time() - at > SEND_VALID_S:
        return "No alert in the last 48 hours: nothing sent.", False
    return f"Sending the reopening message to {len(everyone())} visitor(s)…", True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        rows = everyone()
        langs = {}
        for _u, lang, _a in rows:
            langs[lang] = langs.get(lang, 0) + 1
        print(f"waiting: {len(rows)} {langs}; owner set: {bool(owner())}; last alert: {store.get_flag('reopen_alert_at')}")
    elif cmd == "test-owner":
        print(alert_owner([("new", "test", "This is a test of the Levadinho reopening alert. Nothing will be sent.")],
                          "https://ifcn.madeira.gov.pt/pt/?view=category&id=146", arm=False))
