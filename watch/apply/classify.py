"""Read a notice (Portuguese text) and decide what it says about the Funchal promenade.

classify(text, official, posted) -> dict:
  areas     list of area ids (1-8, see watch/areas.json) the notice names
  action    "closure" | "reopening" | "sea_access" | None
  starts / ends   ISO dates when the notice gives them ("de 22 a 26 de junho", "até 26 de junho")
  decision  "apply"  official source, promenade context, area(s) and one clear action
            "review" something promenade-related that a person should read
            "ignore" nothing about the promenade

The promenade itself is always open; a closure is a part closure of one or more areas.
"Acessos ao mar" (the steps and ladders into the sea) closing is a sea-access note, not an
area closure. Pure functions, no I/O except loading areas.json.
"""
import datetime as dt
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
AREAS_FILE = os.environ.get("AREAS_FILE", os.path.join(HERE, "..", "areas.json"))


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s)


def load_areas(path=AREAS_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


AREAS = load_areas()

CONTEXT = re.compile(
    r"promenade|passeio (publico )?maritimo|passeio pedonal|passadico|tunel|acessos? (ao|para o) mar"
    r"|frente mar(?! ?funchal)|frente maritima|percurso pedonal|caminho pedonal|via pedonal|zona pedonal")
CLOSE = re.compile(
    r"\bencerrad[oa]s?\b|\bencerra(m|ra|rao)?\b|encerramento|interdit[oa]s?|interdica|vedad[oa]s?\b|"
    r"\bfechad[oa]s?\b|\bcortad[oa]s?\b|condicionad[oa]s?\b|\bcondiciona(m)?\b|condicionamento|sem acesso|"
    r"(proibid|impedid)[oa] o acesso|nao (e|esta) permitido o acesso")
REOPEN = re.compile(
    r"reabert[oa]s?\b|\breabre(m)?\b|reabriu|reabriram|reabertura|volta(m|ou|ram)? a abrir|"
    r"novamente aberto|aberto ao publico|desimpedid|ja (se encontra|esta) aberto|levantad[oa] a interdicao")
# "condicionado" (restricted) alone is too weak to mark a closure: it goes to review
WEAK = re.compile(r"condicionad[oa]s?\b|\bcondiciona(m)?\b|condicionamento")
SEA_ACCESS = re.compile(r"acessos? (ao|para o) mar")

MONTHS = {m: i for i, m in enumerate(
    ["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto",
     "setembro", "outubro", "novembro", "dezembro"], 1)}
MON = r"(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"


def _date(day, month, posted, year=None):
    y = int(year) if year else posted.year
    d = dt.date(y, MONTHS[month], int(day))
    if not year and d < posted - dt.timedelta(days=60):   # "15 de janeiro" posted in December
        d = d.replace(year=y + 1)
    return d


def dates(t, posted):
    """(starts, ends) from the normalised text, or (None, None)."""
    m = re.search(r"(?:\bde |entre (?:os dias |o dia )?|dias )(\d{1,2}) (?:a|e) (\d{1,2}) de " + MON + r"(?: de (\d{4}))?", t)
    if m:
        return _date(m[1], m[3], posted, m[4]), _date(m[2], m[3], posted, m[4])
    m = re.search(r"(?:\bde |entre (?:os dias |o dia )?)(\d{1,2}) de " + MON + r" (?:a|e) (\d{1,2}) de " + MON + r"(?: de (\d{4}))?", t)
    if m:
        return _date(m[1], m[2], posted, m[5]), _date(m[3], m[4], posted, m[5])
    starts = ends = None
    m = re.search(r"\bno dia (\d{1,2}) de " + MON + r"(?: de (\d{4}))?", t)
    if m:
        d = _date(m[1], m[2], posted, m[3])
        return d, d
    m = re.search(r"ate (?:ao |a )?(?:dia )?(\d{1,2}) de " + MON + r"(?: de (\d{4}))?", t)
    if m:
        ends = _date(m[1], m[2], posted, m[3])
    m = re.search(r"a partir d[eo] (?:dia )?(\d{1,2}) de " + MON + r"(?: de (\d{4}))?", t)
    if m:
        starts = _date(m[1], m[2], posted, m[3])
    elif re.search(r"a partir de amanha|\bamanha\b", t):
        starts = posted + dt.timedelta(days=1)
    return starts, ends


def find_areas(t, areas=None):
    cfg = areas or AREAS
    found = set()
    for ph in cfg.get("phrases", []):
        rx = re.compile(ph["pattern"])
        if rx.search(t):
            found.update(ph["areas"])
            t = rx.sub(" ", t)
    for a in cfg["areas"]:
        if any(re.search(p, t) for p in a["patterns"]):
            found.add(a["id"])
    return sorted(found)


def classify(text, official, posted=None):
    posted = posted or dt.date.today()
    t = norm(text)
    areas = find_areas(t)
    context = bool(CONTEXT.search(t))
    closing, reopening = bool(CLOSE.search(t)), bool(REOPEN.search(t))
    weak = closing and not CLOSE.search(WEAK.sub(" ", t))
    sea = bool(SEA_ACCESS.search(t))
    starts, ends = dates(t, posted)

    if closing and reopening:
        # "encerra de 22 a 26 e reabre dia 27" reads fine once the dates are known
        action = "closure" if ends else None
    elif reopening:
        action = "reopening"
    elif closing:
        action = "sea_access" if sea and not re.search(r"promenade|passeio|passadico|tunel", t) else "closure"
    else:
        action = None

    if not (context or areas) or not (closing or reopening):
        decision = "ignore"
    elif official and action and not weak and (areas or action == "sea_access") and context:
        decision = "apply"
    else:
        decision = "review"
    return {"areas": areas, "action": action, "context": context,
            "starts": starts.isoformat() if starts else None,
            "ends": ends.isoformat() if ends else None, "decision": decision}
