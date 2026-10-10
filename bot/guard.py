"""Code-level discipline for model answers (owner, 2026-10-10: "fix the indiscipline").

The prompt already had these rules and the local model broke them in real chats (4-8 Oct). So every model reply
passes through check() before it is sent:
  1. no private company names: a sentence naming one is dropped (known names + "X Transfers / Tours / Hikes…" +
     "X Madeira" that isn't an official body);
  2. no "I'm an independent guide" self-introduction, unless the visitor asked who runs Levadinho;
  3. a cruise passenger never gets "ask your hotel reception";
  4. bus times only as printed: model sentences with a bus word and a time are replaced by the timetable lines;
  5. a trail the visitor named gets its live status first if the reply doesn't state it;
  6. known typos ("metrotrímetro").
Each change is logged in the returned list, kept in the analytics record (what the model said vs. what we sent).
"""
import re

import answers

ALLOWED_MADEIRA = {"visit", "taxis", "táxis", "radio", "rádio", "governo", "região", "regiao", "ilha", "da", "de", "do",
                   "in", "on", "of", "to", "for", "around", "across", "about", "explore", "welcome", "enjoy", "the"}
COMPANIES = re.compile(r"\b(beyond madeira|doit madeira|do it madeira|gettohikes|get to hikes|madeira transfers?|"
                       r"happy transfers?|pico transfers|picotransfers|madeira explorers|lido tours|walkme\w*|"
                       r"madeirahiking|madeira hiking|viator|getyourguide|get your guide|civitatis|klook|uber|"
                       r"madeira adventure kingdom|madeira island tours|hike madeira|true spirit|terras de aventura)\b", re.I)
BRAND = re.compile(r"\b([A-Z][\w'&-]+(?:\s[A-Z][\w'&-]+)*)\s(Transfers?|Tours?|Hikes|Hiking|Excursions|Adventures?|"
                   r"Experiences|Trips|Travel|Shuttles?)\b")
X_MADEIRA = re.compile(r"\b([A-Z][\w'-]+)\s+Madeira\b")
WHO = re.compile(r"who (are|runs|is behind)|quem (é|e|és|es|gere)|qui (êtes|etes|gère|gere)|wer (bist|sind|steckt)|"
                 r"kim (jesteś|jestes)|kto prowadzi", re.I)
SELF_GUIDE = re.compile(r"\b(independent guide|guia independente|guide indépendant|guide independant|"
                        r"unabhängige[rn]? (guide|führer|reiseführer)|niezależny przewodnik)\b", re.I)
RECEPTION = re.compile(r"\b(hotel reception|reception of your hotel|receção do (seu )?hotel|recepção do (seu )?hotel|"
                       r"réception (de votre |de l')?h[oô]tel|hotelrezeption|rezeption (ihres|deines) hotels|recepcj\w* hotel\w*)\b", re.I)
BUS_WORD = re.compile(r"\b(bus|buses|autocarro|autocarros|autobus|autobusy|autobusem|navette|busse|linha|line)\b", re.I)
HHMM = re.compile(r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b")
TYPOS = [(re.compile(r"metrotr[ií]metro", re.I), "taxímetro"), (re.compile(r"\btaximetro\b", re.I), "taxímetro")]
# "for real-time availability check the IFCN panel / call the taxi rank" (10 Oct, Rabaçal car park): made-up advice
WORKAROUND = re.compile(r"(real[- ]time|availability|disponibilidade|en temps réel|verfügbarkeit|dostępnoś)\w*.{0,80}"
                        r"(panel|painel|panneau|tafel|tablic|call|ligue|appelez|rufen|zadzwoń)|"
                        r"(panel|painel|panneau|call|ligue|appelez|rufen|zadzwoń).{0,80}(real[- ]time|availability|disponibilidade)", re.I)
RETELL = re.compile(r"\b(open|closed|restricted|one[- ]way|both (ways|directions)|direction|status|ifcn|aberto|encerrad\w*|"
                    r"sentido|ambos|estado|ouvert|fermé|sens unique|statut|geöffnet|gesperrt|richtung|status|otwart\w*|"
                    r"zamkni\w*|kierun\w*)\b", re.I)
# "want the contact for a transfer company…?" (10 Oct): an offer to name a private company
COMPANY_OFFER = re.compile(r"(transfer|tour|shuttle|guide|guia|transfert|reiseführer|przewodnik)\w*\s+(company|companies|empresa|"
                           r"société|agence|unternehmen|firm\w*|operator\w*)", re.I)
NOT_TRAIL = re.compile(r"\b(cafe|caf[eé]s?|restaurant\w*|bar|shop|loja|market|mercado|museum|museu|cable|telef\w*|lido|toilet\w*|"
                       r"wc|car ?park|parking|parque|estacionamento|parkplatz|parking|supermarket|pharmacy|farmacia)\b", re.I)
MONTE = re.compile(r"\bmonte\b", re.I)
TAXI_ASKED = re.compile(r"\b(taxi|táxi|taxis|táxis|taksówk\w*|uber|bolt)\b", re.I)
SENT = re.compile(r"(?<=[.!?])\s+|\n")


def _sentences(text):
    """Split keeping line breaks: [(sentence, separator)]."""
    out, pos = [], 0
    for m in SENT.finditer(text):
        out.append((text[pos:m.start()], m.group(0)))
        pos = m.end()
    out.append((text[pos:], ""))
    return out


def _drop(text, pred):
    kept, dropped = [], []
    for s, sep in _sentences(text):
        if s.strip() and pred(s):
            dropped.append(s.strip())
            continue
        kept.append(s + sep)
    return re.sub(r"\n{3,}", "\n\n", "".join(kept)).strip(), dropped


def _names_company(s):
    if COMPANIES.search(s) or BRAND.search(s) or COMPANY_OFFER.search(s):
        return True
    return any(m.group(1).lower() not in ALLOWED_MADEIRA for m in X_MADEIRA.finditer(s))


def check(reply, user_text, lang, trails, context=""):
    """Returns (reply, changes)."""
    changes = []
    out = reply
    for rx, rep in TYPOS:
        out, n = rx.subn(rep, out)
        if n:
            changes.append(f"typo fixed x{n}")
    out, d = _drop(out, _names_company)
    changes += [f"company sentence dropped: {x[:80]}" for x in d]
    if not WHO.search(user_text):
        out, d = _drop(out, lambda s: bool(SELF_GUIDE.search(s)))
        if d:
            changes.append("self-introduction as independent guide removed")
    if MONTE.search(user_text) and not TAXI_ASKED.search(user_text):   # owner: Monte = cable car up, bus down; never taxis
        out, d = _drop(out, lambda s: bool(TAXI_ASKED.search(s)))
        changes += [f"taxi sentence dropped (Monte): {x[:80]}" for x in d]
        if d and not re.search(r"[A-Za-zÀ-ž]{3}", out):   # nothing left: the cable car fact from the store
            try:
                out = answers.kbtools.place("cablecar")["description"]
            except Exception:
                pass
    out, d = _drop(out, lambda s: bool(WORKAROUND.search(s)))
    changes += [f"invented workaround dropped: {x[:80]}" for x in d]
    full = answers.fold(user_text + " " + context)
    if answers.CRUISE_RE.search(full):
        out, d = _drop(out, lambda s: bool(RECEPTION.search(s)))
        if d:
            changes.append("hotel reception removed (cruise passenger)")
    # Bus times only as printed (owner rule). Work out which direction the reply is about; if it leaves out printed
    # departures (10 Oct: São Lourenço weekdays dropped) or gives a time we don't have, that direction's printed
    # timetable replaces the model's time lines. The other direction is never added unasked.
    legs = []
    for code in trails[:1]:
        for leg in ("there", "back"):
            tt = answers._bus(code, leg)
            if tt:
                pairs = re.findall(r"(\d{2}:\d{2})→(\d{2}:\d{2})", tt)
                legs.append((code, leg, tt, {a for a, _ in pairs}, {x for p in pairs for x in p}))
    said = {f"{int(h):02d}:{m}" for h, m in HHMM.findall(out)}
    if legs and len(said) >= 2:
        # the directions the reply is about: most of their departure times appear in it
        covered = [l for l in legs if l[3] and len(said & l[3]) / len(l[3]) >= 0.5] or \
                  [l for l in [max(legs, key=lambda l: len(said & l[3]))] if len(said & l[3]) >= 3]
        known = set().union(*(l[4] for l in legs))
        if covered and (any(l[3] - said for l in covered) or said - known):
            out, d = _drop(out, lambda s: bool(HHMM.search(s)) and (BUS_WORD.search(s) or len(HHMM.findall(s)) >= 3
                                                                   or len(re.sub(r"[\d:→,\s*\-–()|]", "", s)) < 25))
            out = re.sub(r"\n?\*[^*\n]{3,40}:\*\s*(?=\n|$)", "", out)     # day headings left without times
            tables = []
            for code, leg, tt, deps, every in covered:
                head = (answers.T["there_bus"] if leg == "there" else answers.T["back_bus"])[lang].format(tt="")
                tables.append(head.rstrip(": ") + ":\n" + "\n".join("• " + x.strip() for x in tt.split(" | ")))
                changes.append(f"timetable replaced with the printed one: {code} {leg}")
            table = "\n\n".join(tables)
            parts = out.rsplit("\n\n", 1)
            if len(parts) == 2 and parts[1].strip().endswith("?"):   # keep a closing question last
                out = parts[0] + "\n\n" + table + "\n\n" + parts[1]
            else:
                out += "\n\n" + table
    heads = []
    # "is the café / market / cable car open?" is not a question about a trail's status
    asked_status = bool(answers.STATUS_RE.search(answers.fold(user_text))) and not NOT_TRAIL.search(answers.fold(user_text))
    partial_rx = re.compile(r"\b(partly|partially|partial|parcialmente|partiellement|partiel|teilweise|częściowo|czesciowo)\b", re.I)
    for code in trails[:2]:
        t = answers._trail(code)
        if not t:
            continue
        if t["status"] == "PARTIAL":   # owner: never "partly open" — the full description instead
            out, d = _drop(out, lambda s: bool(partial_rx.search(s)))
            if d:
                changes.append(f"'partly open' wording replaced: {code}")
            if asked_status:
                # the official description is the answer: drop the model's own retelling of directions / status
                out, d2 = _drop(out, lambda s: bool(RETELL.search(s)))
                if d2:
                    changes.append(f"status retelling dropped: {code}")
                heads.append(answers.status_line(code, lang))
            continue
        # owner, 2026-10-10: answer only what was asked — the status goes first only when the question is about it,
        # or the trail is CLOSED (safety); never pasted in front of a parking or bus answer
        words = [answers.ST[t["status"]][lang].lower()]
        if (asked_status or t["status"] == "CLOSED") and not any(w in out.lower() for w in words):
            heads.append(answers.status_line(code, lang))
    if heads:
        changes.append("status added: " + ", ".join(trails[:2]))
        out = "\n\n".join(heads) + "\n\n" + out
    if not out.strip():
        out = "\n\n".join(answers.status_line(c, lang) for c in trails[:2]) or reply
        changes.append("reply emptied by the guard: status only")
    return out.strip(), changes
