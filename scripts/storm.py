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

Dry test: STORM_FIXTURE_IFCN=<html file> and STORM_FIXTURE_IPMA=<json file> replace the live fetches; STORM_TODAY
(YYYY-MM-DD) and STORM_NOW (ISO) fix the clock. `python3 scripts/storm.py` prints what the updater would see.
"""
import datetime, html, json, os, re, sys, zoneinfo

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


def _get(url, fixture_env):
    fx = os.environ.get(fixture_env)
    if fx:
        return open(fx, encoding="utf-8").read()
    import requests
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
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
