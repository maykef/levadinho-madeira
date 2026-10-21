#!/usr/bin/env python3
"""Storm-ready status (owner, 2026-10-10): blanket trail closures and IPMA warnings.

IFCN closes ALL classified trails when IPMA issues weather warnings (Jan, Mar, May 2026). It announces that as a
separate notice ("todos os percursos pedestres classificados da RAM estarão encerrados no dia 03 de março de 2026")
in its AVISOS category, then a reopening notice ("a partir de amanhã, dia 05 de março de 2026, os percursos pedestres
classificados da RAM ... já se encontram transitáveis"). The trail list we scrape (article 627) is not necessarily
updated, so on exactly those days the board would still say OPEN.

Two signals, both official:
1. blanket():  the newest closure / reopening notice on IFCN's AVISOS category page (newest first). A closure that
   is in force (its day has come and no newer reopening is in force) closes every trail on the board. A closure
   announced for a later day is reported as "announced" (the board keeps today's statuses). FAILS LOUD when the page
   can't be read or parsed, like the main status scrape: a wrong "all open" is worse than yesterday's board.
2. ipma_alert(): orange/red IPMA warnings for Madeira (north coast, south coast, mountains; not Porto Santo), in force
   now or starting within 24 h. Degrades gracefully ({"ok": False}): it only drives the banner, never a status.

3. trail_closures() (2026-10-11, owner: "show closure dates"): IFCN's dated closures of ONE trail or a section of it
   ("nos dias 14 a 17 e 21 a 22 de setembro de 2026, estará encerrado o troço do PR1 ..."), found in any notice on
   the same page, also inside the long standing article. Each becomes "announced" (before its first day), "closed"
   (on one of its days: the updater closes that trail, or marks it PARTIAL when only a section closes) or is dropped
   once all its days are past. FAILS LOUD when a notice closes a trail but its dates can't be read.

Dry test: STORM_FIXTURE_IFCN=<html file> and STORM_FIXTURE_IPMA=<json file> replace the live fetches; STORM_TODAY
(YYYY-MM-DD) and STORM_NOW (ISO) fix the clock. `python3 scripts/storm.py` prints what the updater would see.
"""
import datetime
import html
import json
import os
import re
import sys
import zoneinfo

TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
IFCN_AVISOS_CAT = "https://ifcn.madeira.gov.pt/pt/?view=category&id=146"
IPMA_WARNINGS = "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json"
IPMA_PAGE = "https://www.ipma.pt/pt/otempo/prev-sam/?p=MAD"
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStatusBot/5.0; +https://levadinho-madeira.com)"}
MADEIRA_AREAS = {"MCN": "north", "MCS": "south", "MRM": "mountains"}   # MPS = Porto Santo, no trails on our board
LEVELS = {"orange": 2, "red": 3}

MONTHS = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
          "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
DATE_RE = re.compile(r"(\d{1,2})\s+de\s+(" + "|".join(MONTHS) + r")(?:\s+de\s+(\d{4}))?", re.I)
RAM = r"(?:RAM|Regi[aã]o\s+Aut[oó]noma\s+da\s+Madeira)"
CLOSURE_RE = re.compile(r"todos\s+os\s+percursos\s+pedestres\s+classificados.{0,160}?encerr"
                        r"|encerr\w*\s+(?:de\s+)?todos\s+os\s+percursos\s+pedestres\s+classificados", re.I | re.S)
REOPEN_RE = re.compile(r"(?:os|todos\s+os)\s+percursos\s+pedestres\s+classificados\s+da\s+" + RAM +
                       r".{0,200}?(?:transit[aá]veis|reabert|reabr)", re.I | re.S)
# IFCN's standing trail list (article 627, the source of the normal board) sits in the same category.
STANDING_LIST_RE = re.compile(r"seguintes\s+percursos\s+pedestres\s+classificados\s+se\s+encontram|ENCERRADOS\s*/\s*CONDICIONADOS")
UNTIL_WARNING_RE = re.compile(r"enquanto\s+se\s+mantiver|at[eé]\s+(?:nova\s+)?(?:indica|aviso|informa)", re.I)


def _today():
    return datetime.date.fromisoformat(os.environ["STORM_TODAY"]) if os.environ.get("STORM_TODAY") else datetime.datetime.now(TZ).date()


def _now():
    return datetime.datetime.fromisoformat(os.environ["STORM_NOW"]).replace(tzinfo=TZ) if os.environ.get("STORM_NOW") else datetime.datetime.now(TZ)


_PAGES = {}


def _get(url, fixture_env):
    fx = os.environ.get(fixture_env)
    if fx:
        return open(fx, encoding="utf-8").read()
    if url in _PAGES:                      # one fetch per run: blanket() and trail_closures() read the same page
        return _PAGES[url]
    import requests
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
    _PAGES[url] = r.text
    return r.text


def _text(fragment):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", fragment, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def _dates(text, today):
    out = []
    for d, m, y in DATE_RE.findall(text):
        try:
            out.append(datetime.date(int(y) if y else today.year, MONTHS[m.lower()], int(d)))
        except ValueError:
            pass
    return out


def notices(page_html):
    """IFCN AVISOS category page -> [notice text], newest first. Fatal if the page structure changed."""
    parts = page_html.split("com-content-category-blog__item")[1:]
    if not parts:
        sys.exit("FATAL: IFCN AVISOS category page has no notice items — page changed?")
    return [_text(p.split("com-content-category-blog__item")[0]) for p in parts]


def classify(text):
    if STANDING_LIST_RE.search(text) and not CLOSURE_RE.search(text[:400]):
        return None
    if REOPEN_RE.search(text) and not re.search(r"estar[aã]o\s+encerrad|ser[aã]o\s+encerrad", text, re.I):
        return "reopen"
    if CLOSURE_RE.search(text):
        return "closure"
    return None


def blanket(page_html=None):
    """{"state": None|"closed"|"announced", "from": date|None, "reopen": date|None, "text": pt notice, "source": url}"""
    today = _today()
    items = notices(page_html if page_html is not None else _get(IFCN_AVISOS_CAT, "STORM_FIXTURE_IFCN"))
    out = {"state": None, "from": None, "reopen": None, "text": "", "source": IFCN_AVISOS_CAT}
    for text in items:                       # newest first: the first closure/reopening notice decides
        kind = classify(text)
        if kind == "reopen":
            ds = _dates(text, today)
            reopen = max(ds) if ds else None
            if reopen and reopen > today:    # announced for a later day: still closed until then
                out.update(state="closed", reopen=reopen.isoformat(), text=text)
            return out
        if kind == "closure":
            ds = _dates(text, today)
            start = min(ds) if ds else None
            if start and start > today:
                out.update(state="announced", **{"from": start.isoformat()}, text=text)
            else:
                out.update(state="closed", **{"from": start.isoformat() if start else None}, text=text)
            return out
    return out


# ---- dated closures of one trail (2026-10-11) -------------------------------------------------------------------
MON = "|".join(MONTHS)
ANNOUNCE_SPLIT = re.compile(r"(?=O\s+Instituto\s+das\s+Florestas|O\s+IFCN\s+(?:informa|vem|comunica))")
TRAIL_CODE_RE = re.compile(r"\bPR\s?(\d{1,2}(?:\.\d{1,2})?)\b")
TRAIL_CLOSE_RE = re.compile(r"(?:estar[aáã]o?|ser[aáã]o?|ficar[aáã]o?|permanecer[aáã]o?|encontra-se|encontram-se)\s+"
                            r"(?:temporariamente\s+)?encerrad|\bencerramento\b", re.I)
FUTURE_CLOSE_RE = re.compile(r"(?:estar[aá]|ser[aá]|estar[aã]o|ser[aã]o|ficar[aá]|ficar[aã]o)\s+"
                             r"(?:temporariamente\s+)?encerrad|encerramento\s+(?:ter[aá]|vai)", re.I)
NOT_CLOSURE_RE = re.compile(r"mantendo-se\s+o\s+percurso\s+aberto|percurso\s+mant[eé]m-se\s+aberto", re.I)
CROSS_RE = re.compile(rf"(\d{{1,2}})\s+de\s+({MON})(?:\s+de\s+(\d{{4}}))?\s*(?:a|até(?:\s+ao?)?(?:\s+dia)?|-|–)\s*"
                      rf"(\d{{1,2}})\s+de\s+({MON})(?:\s+de\s+(\d{{4}}))?", re.I)
LIST_RE = re.compile(rf"(\d{{1,2}}(?:\s*(?:a|-|–|e|,)\s*\d{{1,2}})*)\s+de\s+({MON})(?:\s+de\s+(\d{{4}}))?", re.I)
PERIOD_RE = re.compile(rf"in[ií]cio\s+(?:no\s+dia\s+)?(\d{{1,2}})\s+de\s+({MON})(?:\s+de\s+(\d{{4}}))?.{{0,120}}?"
                       rf"per[ií]odo\s+(?:m[ií]nimo\s+)?(?:de\s+|previsto\s+de\s+)?(\d{{1,3}})\s+dias", re.I | re.S)
FROM_RE = re.compile(rf"a\s+partir\s+d[eo]\s+(?:dia\s+)?(\d{{1,2}})\s+de\s+({MON})(?:\s+de\s+(\d{{4}}))?", re.I)


def _day(d, m, y, today):
    return datetime.date(int(y) if y else today.year, MONTHS[m.lower()], int(d))


def closure_ranges(text, today):
    """Portuguese closure dates -> [(first, last)] (last None = until IFCN says otherwise). Empty when none."""
    m = PERIOD_RE.search(text)
    if m:
        first = _day(m[1], m[2], m[3], today)
        return [(first, first + datetime.timedelta(days=int(m[4]) - 1))]
    out, rest = [], text
    for m in CROSS_RE.finditer(text):
        out.append((_day(m[1], m[2], m[3] or m[6], today), _day(m[4], m[5], m[6], today)))
    rest = CROSS_RE.sub(" ", text)
    for m in LIST_RE.finditer(rest):
        for a, b in re.findall(r"(\d{1,2})(?:\s*(?:a|-|–)\s*(\d{1,2}))?", m[1]):
            out.append((_day(a, m[2], m[3], today), _day(b or a, m[2], m[3], today)))
    if not out:
        m = FROM_RE.search(text)
        if m:
            out.append((_day(m[1], m[2], m[3], today), None))
    return sorted(set(out), key=lambda r: r[0])


def _sentence(chunk, code):
    """The notice's own words about the closure (from its closure sentence on), without the 'IFCN informs that' opening."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", chunk)
    i = next((n for n, s in enumerate(parts) if re.search(rf"\bPR\s?{re.escape(code[2:])}\b", s) and TRAIL_CLOSE_RE.search(s)),
             next((n for n, s in enumerate(parts) if TRAIL_CLOSE_RE.search(s)), 0))
    # the closure sentence and what follows it (what stays open), without the closing thanks; at most 4 sentences
    pick = " ".join(s for s in parts[i:i + 4] if not re.search(r"agradece|compreens[aã]o|colabora[cç][aã]o", s, re.I))
    pick = re.sub(r"^O\s+(?:Instituto\s+das\s+Florestas\s+e\s+Conserva[cç][aã]o\s+da\s+Natureza(?:,\s*IP-RAM)?|IFCN)"
                  r"(?:\s+vem,?\s+por\s+este\s+meio(?:\s+e\s+para\s+os\s+devidos\s+efeitos)?,?)?\s+informa(?:r)?\s+que,?\s*",
                  "", pick.strip(), flags=re.I)
    return pick[:1].upper() + pick[1:]


def trail_closures(page_html=None):
    """[{"codes", "ranges": [[first, last|None]], "state": "announced"|"closed", "section": bool, "text": pt sentence,
    "source"}], dated closures of single trails that are in force today or still to come (past ones dropped)."""
    today = _today()
    items = notices(page_html if page_html is not None else _get(IFCN_AVISOS_CAT, "STORM_FIXTURE_IFCN"))
    out, seen = [], set()
    for item in items:
        for chunk in ANNOUNCE_SPLIT.split(item):
            if STANDING_LIST_RE.search(chunk) or CLOSURE_RE.search(chunk) or NOT_CLOSURE_RE.search(chunk):
                continue                  # the standing list, island-wide closures (blanket()), open-with-detours
            codes = sorted({"PR" + c for c in TRAIL_CODE_RE.findall(chunk)})
            if not codes or not TRAIL_CLOSE_RE.search(chunk):
                continue
            sentence = _sentence(chunk, codes[0])
            ranges = closure_ranges(sentence, today) or closure_ranges(chunk, today)
            if not ranges and not FUTURE_CLOSE_RE.search(chunk):
                continue                  # "encontra-se encerrado", no dates: today's state, the standing list has it
            if not ranges:
                sys.exit(f"FATAL: IFCN notice closes {', '.join(codes)} but its dates can't be read: {chunk[:300]!r}")
            ranges = [(f, l) for f, l in ranges if l is None or l >= today]   # the days still to come (or today)
            if not ranges:
                continue                  # all its days are past
            key = (tuple(codes), tuple(ranges))
            if key in seen:
                continue
            seen.add(key)
            closed = any(first <= today and (last is None or today <= last) for first, last in ranges)
            out.append({"codes": codes, "ranges": [[f.isoformat(), l.isoformat() if l else None] for f, l in ranges],
                        "state": "closed" if closed else "announced",
                        "section": bool(re.search(r"\btro[cç]o\b|\bsec[cç][aã]o\b|\bentre\s+o", sentence, re.I)),
                        "text": sentence, "source": IFCN_AVISOS_CAT})
    return out


# Closure dates in each site language (owner, 2026-10-11: closure dates are shown; no other dates on the site).
MONTH_NAMES = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "pt": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "pl": ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"],
}
AND = {"en": " and ", "pt": " e ", "fr": " et ", "de": " und ", "pl": " i "}
FROM = {"en": "from {d}", "pt": "a partir de {d}", "fr": "à partir du {d}", "de": "ab {d}", "pl": "od {d}"}


def fmt_ranges(ranges, lang):
    """[[first, last]] -> '14–17 and 21–22 September' / '14 a 17 e 21 a 22 de setembro' / ... (no year)."""
    lang = lang if lang in MONTH_NAMES else "en"
    M = MONTH_NAMES[lang]
    rs = [(datetime.date.fromisoformat(f), datetime.date.fromisoformat(l) if l else None) for f, l in ranges]

    def day(d):
        return f"{d.day}." if lang == "de" else str(d.day)

    def full(d):
        return {"pt": f"{d.day} de {M[d.month - 1]}", "de": f"{d.day}. {M[d.month - 1]}"}.get(lang, f"{d.day} {M[d.month - 1]}")

    def span(f, l, month=True):
        if l is None:
            return FROM[lang].format(d=full(f))
        if f == l:
            return full(f) if month else day(f)
        if f.month != l.month:
            sep = " a " if lang == "pt" else "–"
            return full(f) + sep + full(l)
        sep = " a " if lang == "pt" else "–"
        if lang == "fr":
            return f"du {f.day} au {l.day}" + (f" {M[l.month - 1]}" if month else "")
        return day(f) + sep + (full(l) if month else day(l))

    same = len({(f.month, (l or f).month) for f, l in rs}) == 1 and all(l and f.month == l.month for f, l in rs)
    if same and len(rs) > 1:          # one month: '14–17 and 21–22 September'
        parts = [span(f, l, month=False) for f, l in rs]
        tail = {"pt": f" de {M[rs[0][0].month - 1]}"}.get(lang, f" {M[rs[0][0].month - 1]}")
        return ", ".join(parts[:-1]) + AND[lang] + parts[-1] + tail
    parts = [span(f, l) for f, l in rs]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + AND[lang] + parts[-1]


CLOSURE_HEAD = {
    "announced": {"en": "IFCN has announced a closure: {d}.", "pt": "O IFCN anunciou um encerramento: {d}.",
                  "fr": "L'IFCN a annoncé une fermeture : {d}.", "de": "Das IFCN hat eine Sperrung angekündigt: {d}.",
                  "pl": "IFCN zapowiedział zamknięcie: {d}."},
    "closed": {"en": "Closed today by an IFCN notice ({d}).", "pt": "Encerrado hoje por aviso do IFCN ({d}).",
               "fr": "Fermé aujourd'hui par un avis de l'IFCN ({d}).", "de": "Heute laut IFCN-Hinweis gesperrt ({d}).",
               "pl": "Dziś zamknięty zgodnie z komunikatem IFCN ({d})."},
    "section": {"en": "Section closed today by an IFCN notice ({d}).", "pt": "Troço encerrado hoje por aviso do IFCN ({d}).",
                "fr": "Tronçon fermé aujourd'hui par un avis de l'IFCN ({d}).", "de": "Abschnitt heute laut IFCN-Hinweis gesperrt ({d}).",
                "pl": "Odcinek dziś zamknięty zgodnie z komunikatem IFCN ({d})."},
}


def closure_text(c, detail):
    """{lang: head + IFCN's sentence}: the head carries our formatted dates, `detail` is IFCN's sentence per language."""
    kind = c["state"] if c["state"] == "announced" else ("section" if c["section"] else "closed")
    return {l: (CLOSURE_HEAD[kind][l].format(d=fmt_ranges(c["ranges"], l)) + " " + (detail.get(l) or detail.get("pt") or "")).strip()
            for l in CLOSURE_HEAD[kind]}


def ipma_alert(raw=None):
    """Orange/red IPMA warnings for Madeira in force now or within 24 h -> {"ok", "level", "warnings": [...]}."""
    try:
        data = json.loads(raw if raw is not None else _get(IPMA_WARNINGS, "STORM_FIXTURE_IPMA"))
        now = _now()
        horizon = now + datetime.timedelta(hours=24)
        found = []
        for w in data:
            area, level = w.get("idAreaAviso"), w.get("awarenessLevelID")
            if area not in MADEIRA_AREAS or level not in LEVELS:
                continue
            start = datetime.datetime.fromisoformat(w["startTime"]).replace(tzinfo=TZ)
            end = datetime.datetime.fromisoformat(w["endTime"]).replace(tzinfo=TZ)
            if end <= now or start > horizon:
                continue
            found.append({"area": MADEIRA_AREAS[area], "type": w.get("awarenessTypeName", ""), "level": level,
                          "start": w["startTime"], "end": w["endTime"], "now": start <= now})
        top = max((LEVELS[f["level"]] for f in found), default=0)
        return {"ok": True, "level": {2: "orange", 3: "red"}.get(top), "warnings": found, "source": IPMA_PAGE}
    except Exception as e:
        print("ipma warnings failed (banner skipped):", e, file=sys.stderr)
        return {"ok": False}


# Fixed wording (no machine translation): the note every trail gets during a blanket closure, and its reopening day.
BLANKET_NOTE = {
    "pt": "O IFCN encerrou todos os percursos pedestres classificados devido aos avisos meteorológicos do IPMA.",
    "en": "IFCN has closed all classified trails because of IPMA weather warnings.",
    "fr": "L'IFCN a fermé tous les sentiers classés en raison des avis météorologiques de l'IPMA.",
    "de": "Das IFCN hat wegen der Wetterwarnungen des IPMA alle klassifizierten Wege gesperrt.",
    "pl": "IFCN zamknął wszystkie sklasyfikowane szlaki z powodu ostrzeżeń pogodowych IPMA.",
}
REOPEN_TOMORROW = {
    "pt": " Reabrem amanhã, segundo o IFCN.", "en": " IFCN says they reopen tomorrow.",
    "fr": " Selon l'IFCN, ils rouvrent demain.", "de": " Laut IFCN öffnen sie morgen wieder.",
    "pl": " Według IFCN zostaną otwarte jutro.",
}


def blanket_note(b):
    tomorrow = (_today() + datetime.timedelta(days=1)).isoformat()
    extra = REOPEN_TOMORROW if b.get("reopen") == tomorrow else {}
    return {l: BLANKET_NOTE[l] + extra.get(l, "") for l in BLANKET_NOTE}


def apply(trails, b):
    """During a blanket closure every trail is CLOSED with the fixed note (IFCN's own per-trail status is kept
    as ifcn_status, so the board can return to it when the reopening notice is in force)."""
    if b.get("state") != "closed":
        return False
    note = blanket_note(b)
    for t in trails:
        t["ifcn_status"] = t["status"]
        t["status"] = "CLOSED"
        t["note"] = dict(note)
    return True


def alert(b, ipma):
    """The status.json "alert" block that status.js / dashboard.js show as a banner (None = no banner)."""
    a = {"blanket": b.get("state"), "blanket_from": b.get("from"), "blanket_reopen": b.get("reopen"),
         "ifcn_source": b.get("source"), "ipma_level": ipma.get("level") if ipma.get("ok") else None,
         "ipma_types": sorted({w["type"] for w in ipma.get("warnings", [])}) if ipma.get("ok") else [],
         "ipma_now": any(w["now"] for w in ipma.get("warnings", [])) if ipma.get("ok") else False,
         "ipma_source": IPMA_PAGE}
    return a if (a["blanket"] or a["ipma_level"]) else None


if __name__ == "__main__":
    b = blanket()
    i = ipma_alert()
    print(json.dumps({"blanket": b, "ipma": i, "alert": alert(b, i)}, ensure_ascii=False, indent=1, default=str))


# Crawlable wording for the updater's static lines (status.js / dashboard.js carry the same sentences live).
ANNOUNCED = {
    "pt": "O IFCN anunciou o encerramento de todos os percursos pedestres classificados{w} devido aos avisos meteorológicos do IPMA.",
    "en": "IFCN has announced that all classified trails will close{w} because of IPMA weather warnings.",
    "fr": "L'IFCN a annoncé la fermeture de tous les sentiers classés{w} en raison des avis météorologiques de l'IPMA.",
    "de": "Das IFCN hat angekündigt, alle klassifizierten Wege{w} wegen der Wetterwarnungen des IPMA zu sperren.",
    "pl": "IFCN zapowiedział zamknięcie wszystkich sklasyfikowanych szlaków{w} z powodu ostrzeżeń pogodowych IPMA.",
}
WHEN_TOMORROW = {"pt": " amanhã", "en": " tomorrow", "fr": " demain", "de": " morgen", "pl": " jutro"}
IPMA_LINE = {
    "pt": "Aviso {lvl} do IPMA para a Madeira{w}. Em avisos anteriores o IFCN encerrou todos os percursos classificados: confirme antes de ir.",
    "en": "IPMA {lvl} warning for Madeira{w}. During past warnings IFCN closed all classified trails: check before you go.",
    "fr": "Avis {lvl} de l'IPMA pour Madère{w}. Lors d'avis précédents, l'IFCN a fermé tous les sentiers classés : vérifiez avant de partir.",
    "de": "IPMA-Warnstufe {lvl} für Madeira{w}. Bei früheren Warnungen hat das IFCN alle klassifizierten Wege gesperrt: Prüfen Sie vor dem Losgehen.",
    "pl": "Ostrzeżenie IPMA ({lvl}) dla Madery{w}. Podczas wcześniejszych ostrzeżeń IFCN zamykał wszystkie sklasyfikowane szlaki: sprawdź przed wyjściem.",
}
LEVEL_NAME = {"orange": {"pt": "laranja", "en": "orange", "fr": "orange", "de": "Orange", "pl": "pomarańczowe"},
              "red": {"pt": "vermelho", "en": "red", "fr": "rouge", "de": "Rot", "pl": "czerwone"}}
IPMA_WHEN = {True: {"pt": " em vigor", "en": " in force", "fr": " en vigueur", "de": " in Kraft", "pl": " obowiązuje"},
             False: {"pt": " nas próximas 24 horas", "en": " in the next 24 hours", "fr": " dans les prochaines 24 heures",
                     "de": " in den nächsten 24 Stunden", "pl": " w ciągu najbliższych 24 godzin"}}


def static_alert(a, lang):
    """One sentence for the crawlable board line, or "" (the blanket-closed case replaces the board line instead)."""
    if not a:
        return ""
    lang = lang if lang in BLANKET_NOTE else "en"
    if a.get("blanket") == "announced":
        tomorrow = (_today() + datetime.timedelta(days=1)).isoformat()
        return ANNOUNCED[lang].format(w=WHEN_TOMORROW[lang] if a.get("blanket_from") == tomorrow else "")
    if a.get("blanket") == "closed":
        return ""
    if a.get("ipma_level"):
        w = IPMA_WHEN[bool(a.get("ipma_now"))][lang]
        return IPMA_LINE[lang].format(lvl=LEVEL_NAME[a["ipma_level"]][lang], w=w)
    return ""
