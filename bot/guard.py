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
    if COMPANIES.search(s) or BRAND.search(s):
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
    full = answers.fold(user_text + " " + context)
    if answers.CRUISE_RE.search(full):
        out, d = _drop(out, lambda s: bool(RECEPTION.search(s)))
        if d:
            changes.append("hotel reception removed (cruise passenger)")
    printed = []
    for code in trails[:2]:
        for leg in ("there", "back"):
            tt = answers._bus(code, leg)
            if tt:
                printed.append((code, leg, tt))
    if printed:
        out, d = _drop(out, lambda s: bool(BUS_WORD.search(s) and HHMM.search(s)))
        if d:
            changes += [f"bus sentence replaced: {x[:80]}" for x in d]
            out += "\n\n" + "\n".join((answers.T["there_bus"] if leg == "there" else answers.T["back_bus"])[lang].format(tt=tt)
                                      for _c, leg, tt in printed)
    heads = []
    partial_rx = re.compile(r"\b(partly|partially|partial|parcialmente|partiellement|partiel|teilweise|częściowo|czesciowo)\b", re.I)
    for code in trails[:2]:
        t = answers._trail(code)
        if not t:
            continue
        if t["status"] == "PARTIAL":   # owner: never "partly open" — the full description instead
            out, d = _drop(out, lambda s: bool(partial_rx.search(s)))
            if d:
                changes.append(f"'partly open' wording replaced: {code}")
            heads.append(answers.status_line(code, lang))
            continue
        words = [answers.ST[t["status"]][lang].lower()]
        if not any(w in out.lower() for w in words):
            heads.append(answers.status_line(code, lang))
    if heads:
        changes.append("status added: " + ", ".join(trails[:2]))
        out = "\n\n".join(heads) + "\n\n" + out
    if not out.strip():
        out = "\n\n".join(answers.status_line(c, lang) for c in trails[:2]) or reply
        changes.append("reply emptied by the guard: status only")
    return out.strip(), changes
