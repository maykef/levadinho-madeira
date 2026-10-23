"""The Levadinho taxi request form (owner, 2026-10-21): conversational slot-filling in chat.

After a transport answer the bot offers once: "Want me to arrange the taxi?" (the one scoped
exception to the no-offers rule). When the visitor accepts — or asks to book a taxi outright —
`maybe_handle` takes over the conversation: the model only EXTRACTS slots from each message
(guided JSON, so the form cannot hallucinate); the questions, confirmation and final message
are deterministic, in the visitor's language.

Slots: pickup, dropoff, date, time, pax (+ free-text note). Confirmation shows the pre-agreed
price from taxi_routes.json when the route matches and a price is set (car 1-4 / van 5-10);
otherwise the approved official-meter wording. On confirm (v1, no drivers enrolled): a
ready-to-forward driver message in Portuguese + the right zone's rank numbers, and a
taxi_request analytics event with the structured itinerary and a LV-#### reference.
Dispatch to enrolled drivers (taxi_routes.json "drivers") is v1.5, not yet wired.

State lives in store.kv ("taxiform:<user>", JSON); abandoned forms expire after 2 h.
"""
import datetime
import json
import os
import re
import time
import zoneinfo

import store

HERE = os.path.dirname(os.path.abspath(__file__))
MADEIRA = zoneinfo.ZoneInfo("Atlantic/Madeira")
TTL = 2 * 3600

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "pickup": {"type": ["string", "null"], "maxLength": 80},
        "dropoff": {"type": ["string", "null"], "maxLength": 80},
        "date": {"type": ["string", "null"], "description": "YYYY-MM-DD if the visitor gave a day"},
        "time": {"type": ["string", "null"], "description": "HH:MM 24h if given"},
        "pax": {"type": ["integer", "null"], "minimum": 1, "maximum": 16},
        "note": {"type": ["string", "null"], "maxLength": 160},
        "confirmed": {"type": "boolean", "description": "true only if this message clearly confirms the summarised request"},
        "cancelled": {"type": "boolean", "description": "true if the visitor wants to stop or no longer wants the taxi"}
    },
    "required": ["pickup", "dropoff", "date", "time", "pax", "note", "confirmed", "cancelled"],
}

OFFER = {"en": "Want me to arrange the taxi? Just tell me pick-up point, date, time and how many of you.",
         "pt": "Quer que eu trate do táxi? Diga-me o local de recolha, o dia, a hora e quantos são.",
         "fr": "Voulez-vous que je m'occupe du taxi ? Indiquez-moi le lieu de prise en charge, la date, l'heure et votre nombre.",
         "de": "Soll ich das Taxi organisieren? Nennen Sie mir Abholort, Datum, Uhrzeit und wie viele Sie sind.",
         "pl": "Mam zorganizować taksówkę? Podaj miejsce odbioru, datę, godzinę i liczbę osób."}

ASK = {"pickup": {"en": "Where should the taxi pick you up?", "pt": "Onde deve o táxi apanhá-lo?",
                  "fr": "Où le taxi doit-il vous prendre ?", "de": "Wo soll das Taxi Sie abholen?",
                  "pl": "Skąd ma odebrać Cię taksówka?"},
       "dropoff": {"en": "Where to?", "pt": "Para onde?", "fr": "Pour aller où ?", "de": "Wohin?", "pl": "Dokąd?"},
       "date": {"en": "Which day?", "pt": "Em que dia?", "fr": "Quel jour ?", "de": "An welchem Tag?", "pl": "Którego dnia?"},
       "time": {"en": "At what time?", "pt": "A que horas?", "fr": "À quelle heure ?", "de": "Um wie viel Uhr?", "pl": "O której godzinie?"},
       "pax": {"en": "How many of you?", "pt": "Quantos são?", "fr": "Vous êtes combien ?", "de": "Wie viele sind Sie?", "pl": "Ile osób?"}}

CONFIRM = {"en": "Here's your request: 🚕 {sum}.\n{price}\nShall I finalise it?",
           "pt": "O seu pedido: 🚕 {sum}.\n{price}\nConfirmo?",
           "fr": "Votre demande : 🚕 {sum}.\n{price}\nJe finalise ?",
           "de": "Ihre Anfrage: 🚕 {sum}.\n{price}\nSoll ich sie abschließen?",
           "pl": "Twoje zgłoszenie: 🚕 {sum}.\n{price}\nPotwierdzam?"}

PRICE_FIXED = {"en": "Pre-agreed price for this route: *€{p}* per {veh} (not per person).",
               "pt": "Preço combinado para este trajeto: *{p} €* por {veh} (não por pessoa).",
               "fr": "Prix convenu pour ce trajet : *{p} €* par {veh} (et non par personne).",
               "de": "Vereinbarter Preis für diese Strecke: *{p} €* pro {veh} (nicht pro Person).",
               "pl": "Uzgodniona cena za tę trasę: *{p} €* za {veh} (nie od osoby)."}
VEH = {"car": {"en": "taxi", "pt": "táxi", "fr": "taxi", "de": "Taxi", "pl": "taksówkę"},
       "van": {"en": "van", "pt": "carrinha", "fr": "van", "de": "Van", "pl": "busa"}}
PRICE_SHARED = {"en": "Taxis run on the official meter; a shared ride on this route is usually €15–20 per person.",
                "pt": "Os táxis cobram pelo taxímetro oficial; uma viagem partilhada neste trajeto costuma custar 15–20 € por pessoa.",
                "fr": "Les taxis fonctionnent au compteur officiel ; un trajet partagé sur cet itinéraire coûte en général 15–20 € par personne.",
                "de": "Taxis fahren nach dem offiziellen Taxameter; eine geteilte Fahrt auf dieser Strecke kostet meist 15–20 € pro Person.",
                "pl": "Taksówki jeżdżą według oficjalnego taksometru; wspólny przejazd na tej trasie kosztuje zwykle 15–20 € od osoby."}
PRICE_METER = {"en": "Taxis run on the official meter — no fixed price per route; ask for a quote when the rank confirms.",
               "pt": "Os táxis cobram pelo taxímetro oficial — não há preço fixo por trajeto; peça uma cotação quando confirmarem.",
               "fr": "Les taxis fonctionnent au compteur officiel — pas de prix fixe par trajet ; demandez un devis à la confirmation.",
               "de": "Taxis fahren nach dem offiziellen Taxameter — kein Festpreis pro Strecke; fragen Sie bei der Bestätigung nach einem Preis.",
               "pl": "Taksówki jeżdżą według oficjalnego taksometru — bez stałych cen za trasę; poproś o wycenę przy potwierdzeniu."}

FINAL = {"en": "Done — your request is *{ref}*. Send this message to the taxi rank (tap to copy), or call:\n\n{msg}\n\n{ranks}\nThey confirm directly with you. Daytime at Achada do Teixeira, taxis often wait at the car park.",
         "pt": "Feito — o seu pedido é o *{ref}*. Envie esta mensagem à praça de táxis (toque para copiar) ou ligue:\n\n{msg}\n\n{ranks}\nEles confirmam diretamente consigo. De dia, na Achada do Teixeira, os táxis costumam esperar no estacionamento.",
         "fr": "C'est fait — votre demande est *{ref}*. Envoyez ce message à la station de taxis (appuyez pour copier) ou appelez :\n\n{msg}\n\n{ranks}\nIls confirment directement avec vous. En journée, à Achada do Teixeira, des taxis attendent souvent au parking.",
         "de": "Fertig — Ihre Anfrage ist *{ref}*. Senden Sie diese Nachricht an den Taxistand (zum Kopieren antippen) oder rufen Sie an:\n\n{msg}\n\n{ranks}\nDie Bestätigung kommt direkt von ihnen. Tagsüber warten an der Achada do Teixeira oft Taxis am Parkplatz.",
         "pl": "Gotowe — Twoje zgłoszenie to *{ref}*. Wyślij tę wiadomość do postoju taksówek (dotknij, by skopiować) albo zadzwoń:\n\n{msg}\n\n{ranks}\nPotwierdzą bezpośrednio z Tobą. W ciągu dnia na Achada do Teixeira taksówki często czekają na parkingu."}

CANCELLED = {"en": "No problem, cancelled. Ask me anything else. 🥾", "pt": "Sem problema, cancelado. Pergunte o que quiser. 🥾",
             "fr": "Pas de souci, annulé. Posez-moi une autre question. 🥾", "de": "Kein Problem, storniert. Fragen Sie gern weiter. 🥾",
             "pl": "Nie ma sprawy, anulowane. Pytaj o cokolwiek. 🥾"}

BOOK_RE = re.compile(r"(book|arrange|order|get me|need)\W+(a\s+)?(taxi|cab)|"
                     r"(reservar?|marcar|chamar|arranjar)\W+(um\s+)?t[áa]xi|"
                     r"(r[ée]server|commander)\W+(un\s+)?taxi|taxi\W+(buchen|bestellen|reservieren)|"
                     r"(zam[óo]wi[ćc]|zarezerwowa[ćc])\W+taks[óo]wk", re.I)
YES_RE = re.compile(r"^\s*(yes|yep|sure|ok(ay)?|please|sim|claro|pode ser|oui|volontiers|ja|gerne|tak|poprosz[ęe])\b", re.I)


def _cfg():
    return json.load(open(os.path.join(HERE, "taxi_routes.json"), encoding="utf-8"))


def _state(user):
    raw = store.get_flag(f"taxiform:{user}")
    if not raw:
        return None
    st = json.loads(raw)
    if time.time() - st.get("at", 0) > TTL:
        store.set_flag(f"taxiform:{user}", None)
        return None
    return st


def _save(user, st):
    st["at"] = time.time()
    store.set_flag(f"taxiform:{user}", json.dumps(st, ensure_ascii=False))


def _ref():
    n = int(store.get_flag("taxiform:seq") or "1041") + 1
    store.set_flag("taxiform:seq", str(n))
    return f"LV-{n}"


def _norm(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def match_route(slots):
    pickup, drop = _norm(slots.get("pickup")), _norm(slots.get("dropoff"))
    for r in _cfg()["routes"]:
        if any(f in pickup for f in r["from"]) and any(t in drop for t in r["to"]):
            return r
    return None


def price_line(slots, lang):
    r = match_route(slots)
    veh = "van" if (slots.get("pax") or 1) > 4 else "car"
    if r and r.get(f"{veh}_eur"):
        return PRICE_FIXED[lang].format(p=r[f"{veh}_eur"], veh=VEH[veh][lang]), r, veh, r[f"{veh}_eur"]
    if r and r["id"] == "achada-areeiro":  # the one route with an approved shared-ride figure
        return PRICE_SHARED[lang], r, veh, None
    return PRICE_METER[lang], r, veh, None


DOW = {"pt": ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"], "fr": ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"],
       "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"], "pl": ["pon", "wt", "śr", "czw", "pt", "sob", "niedz"]}


def summary(slots, lang):
    d = slots.get("date")
    try:
        dd = datetime.date.fromisoformat(d)
        d = dd.strftime("%a %d %b") if lang == "en" else f"{DOW[lang][dd.weekday()]} {dd:%d/%m}"
    except (TypeError, ValueError, KeyError):
        pass
    parts = [f"{slots['pickup']} → {slots['dropoff']}", d, slots.get("time"),
             f"{slots['pax']} {'person' if slots['pax'] == 1 else 'people'}" if lang == "en" else f"{slots['pax']} pax"]
    if slots.get("note"):
        parts.append(slots["note"])
    return ", ".join(str(p) for p in parts if p)


def driver_message(slots, ref):
    d = slots.get("date") or ""
    return (f"Pedido de táxi Levadinho {ref}: {slots['pickup']} → {slots['dropoff']}, "
            f"{d} às {slots.get('time')}, {slots['pax']} pessoa(s)."
            + (f" Nota: {slots['note']}." if slots.get("note") else ""))


def ranks_for(slots):
    r = match_route(slots)
    zones = _cfg()["zones"]
    zone = (r or {}).get("zone")
    if not zone:
        zone = "santana" if "achada" in _norm(slots.get("pickup")) or "santana" in _norm(slots.get("pickup")) else "funchal"
    return "\n".join(f"• {name}: *{phone}*" for name, phone in zones[zone]["ranks"])


def offered_recently(user):
    return store.get_flag(f"taxioffer:{user}")


def mark_offered(user):
    store.set_flag(f"taxioffer:{user}", str(int(time.time())))


def wants_form(user, text, history):
    """Entry check: an explicit booking ask, or a yes right after our offer."""
    if BOOK_RE.search(text):
        return True
    if history and YES_RE.search(text):
        last = history[-1]["content"] if history[-1]["role"] == "assistant" else ""
        return any(last.rstrip().endswith(o) for o in OFFER.values())
    return False


def maybe_handle(user, text, lang, meta=None):
    """Returns the form's reply, or None when the form is not active for this message."""
    import brain  # for llm(); imported here to avoid a cycle
    st = _state(user)
    seed = ""
    if st is None:
        hist = store.history(user)
        if not wants_form(user, text, hist):
            return None
        st = {"slots": {}, "stage": "collect"}
        # the itinerary often sits in the question that triggered our offer ("...7 people from Achada
        # back to Arieiro around 6 PM?"): extract from that message too, so we don't re-ask
        prev_user = [m["content"] for m in hist if m["role"] == "user"]
        if prev_user:
            seed = prev_user[-1] + "\n"
        if meta is not None:
            meta["events"].append(("taxi_form_started", {"lang": lang}))
    now = datetime.datetime.now(MADEIRA)
    prompt = [{"role": "system",
               "content": "Extract taxi-booking details from the visitor's message. Only what THIS message says; "
                          f"null for anything not mentioned. Today is {now:%A %Y-%m-%d}; resolve 'tomorrow' etc. "
                          "to YYYY-MM-DD. 'confirmed' only for a clear yes to a summarised request."},
              {"role": "user", "content": seed + text}]
    try:
        got = json.loads(brain.llm(prompt, max_tokens=200, schema=EXTRACT_SCHEMA, temperature=0))
    except Exception:  # noqa: BLE001 - extraction failure must not kill the chat
        got = {}
    if got.get("cancelled"):
        store.set_flag(f"taxiform:{user}", None)
        reply = CANCELLED[lang]
        store.add_turn(user, text, reply)
        return reply
    if got.get("note") and (BOOK_RE.search(got["note"]) or YES_RE.search(got["note"])):
        got["note"] = None   # the booking phrase or a bare yes is not a note for the driver
    for k in ("pickup", "dropoff", "date", "time", "pax", "note"):
        if got.get(k):
            st["slots"][k] = got[k]
    missing = [k for k in ("pickup", "dropoff", "date", "time", "pax") if not st["slots"].get(k)]
    if missing:
        st["stage"] = "collect"
        _save(user, st)
        reply = ASK[missing[0]][lang]
    elif st["stage"] != "confirm":
        st["stage"] = "confirm"
        _save(user, st)
        pl, _, _, _ = price_line(st["slots"], lang)
        reply = CONFIRM[lang].format(sum=summary(st["slots"], lang), price=pl)
    elif got.get("confirmed") or YES_RE.search(text):
        ref = _ref()
        _, route, veh, price = price_line(st["slots"], lang)
        store.set_flag(f"taxiform:{user}", None)
        reply = FINAL[lang].format(ref=ref, msg=driver_message(st["slots"], ref), ranks=ranks_for(st["slots"]))
        if meta is not None:
            meta["events"].append(("taxi_request", {"ref": ref, "lang": lang, **st["slots"],
                                                    "route_id": route["id"] if route else None,
                                                    "vehicle": veh, "price_eur": price}))
    else:  # unclear answer at the confirm step: re-show the summary
        _save(user, st)
        pl, _, _, _ = price_line(st["slots"], lang)
        reply = CONFIRM[lang].format(sum=summary(st["slots"], lang), price=pl)
    store.add_turn(user, text, reply)
    return reply


TRANSPORT_RE = re.compile(r"taxi|táxi|taks[óo]wk|transfer|getting (back|there)|way back|voltar|regress|"
                          r"retour|zurück|powr[óo]t", re.I)


def maybe_offer(user, text, reply, lang):
    """One proactive offer per conversation, only after a transport-flavoured answer."""
    if offered_recently(user) or _state(user):
        return reply
    if not (TRANSPORT_RE.search(text) or TRANSPORT_RE.search(reply)):
        return reply
    mark_offered(user)
    return reply.rstrip() + "\n\n" + OFFER[lang]
