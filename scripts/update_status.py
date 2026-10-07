#!/usr/bin/env python3
"""
Levadinho daily status updater (v5).

Status source (since 2026-09-30): the official IFCN warnings page
"Percursos Pedestres - Avisos" (IFCN_AVISOS). Near its end it lists every
classified trail under three headings:

    ENCERRADOS/CONDICIONADOS   -> CLOSED
    PARCIALMENTE TRANSITÁVEIS  -> PARTIAL
    TRANSITÁVEIS               -> OPEN

each item like "PR 17 Caminho do Pináculo e Folhadal - percurso transitável
entre a Encumeada e a Bica da Cana". Only those three lists count; the news
paragraphs above them (some stale, e.g. an old PR10 closure) are ignored.

Mapping rules:
  * A trail listed under more than one heading (PR1: two-way Areeiro-Pedra Rija
    section under TRANSITÁVEIS, one-way Pedra Rija-Pico Ruivo section under
    ENCERRADOS/CONDICIONADOS) -> PARTIAL, with a note joining each item's text,
    prefixed by its heading ("Transitável: ... Encerrado/condicionado: ...").
  * The text after the trail name (the "qualifier") becomes the trail's note,
    whatever the heading (PR6's one-way loop, PR4, PR12, PR17 sections...).
  * "(Porto Santo)" items are EXCLUDED: their codes (PR1, PR2, PR3) collide
    with Madeira's, and the board is Madeira-only. Logged.
  * Items without a PR code are mapped through NON_PR_ALIASES
    ("Um Caminho para todos Queimadas- Pico das Pedras" -> PR9.1, which is
    Queimadas - Pico das Pedras in the IFCN table) or skipped with a log line.
  * Codes IFCN lists that the site has no page for (PR6.7, PR23) are skipped
    with a log line; the board stays the 37 PAGES trails.
  * A PAGES trail IFCN omits falls back to the Visit Madeira hiking index
    (secondary source, fetched only when needed) and is logged. More than
    MAX_MISSING omissions, or a missing fallback, is fatal.

Notes are the Portuguese originals: note = {"pt": original, "en","fr","de","pl":
MyMemory machine translations}. A failed translation falls back to the
Portuguese original. Translations are cached from the previous status.json so
an unchanged note is not re-translated (MyMemory's free quota is small).

Names come from bot/trail_facts.json (fallback: the IFCN text); lat/lon from
the same file place each trail in its nearest IPMA weather region.

Summit weather is the official IPMA observation for the Pico do Areeiro station.
Writes status.json, bumps sitemap.xml <lastmod>, the "dateModified" JSON-LD of
the homepages and PR1 pages, and the text inside any STATIC-STATUS markers
(write_static_status) -- a plain crawlable line; the live card stays status.js.

Hard rules:
  1. Badge never contradicts the note. The status comes from the IFCN heading;
     then, as a safety net, an OPEN trail whose note is restrictive
     (RESTRICTIVE, English + Portuguese phrases, checked on the Portuguese
     original and the English translation) is downgraded to PARTIAL -- this
     is what turns PR17 "percurso transitável entre a Encumeada e a Bica da
     Cana" (listed as TRANSITÁVEIS, but only part of the 15 km route) into
     PARTIAL. An informational note on an OPEN trail (PR6's one-way loop,
     PR1.2 "totalmente transitável") matches no phrase and stays OPEN.
     assert_not_contradictory() is the final gate on every trail and static
     line: it exits non-zero rather than publish a green-but-restricted lie.
  2. Weather is the real measured reading from IPMA's Pico do Areeiro station.
     IPMA -99 "missing" fields and temps < -10 C / > 30 C are rejected, and the
     weather object is marked {"ok": false} so the pages show a safe fallback.
  3. Fail loud. Any status-scrape failure (fetch error, a heading or list not
     found, too few trails, PR1 absent) exits non-zero -> red Action ->
     yesterday's honest status.json stays live. Weather, note translation,
     dateModified and the sitemap bump degrade gracefully.
  4. scripts/manual_note.txt (optional) injects a human-written line.
"""
import datetime
import glob
import html as htmllib
import json
import os
import re
import sys
import zoneinfo

import requests

IFCN_UPDATED = ""   # the "ATUALIZADO: dd/mm/yyyy" date printed on the IFCN page, set by ifcn_statuses()
IFCN_AVISOS = ("https://ifcn.madeira.gov.pt/pt/?view=article&id=627:percursos-pedestres-avisos"
               "&catid=146:avisos")
# Secondary source, used only for a PAGES trail that IFCN's lists omit.
TRAILS_INDEX = "https://visitmadeira.com/en/what-to-do/nature-seekers/activities/hiking/"
TRAIL_FACTS = "bot/trail_facts.json"      # names + lat/lon per code (read-only here)

# IPMA official surface observations (keyless open data), keyed by ISO timestamp.
IPMA_OBS = "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json"
STATION_SUMMIT = 1210974          # "Madeira, Pico do Areeiro" — the ridge start (32.735, -16.928)
STATION_WIND_FALLBACK = 1210973   # "Madeira, Areeiro" — used when the summit wind sensor is missing
IPMA_MISSING = -99.0              # IPMA codes an unavailable field as -99.0
HUMIDITY_CLOUD_PCT = 90.0         # at/above this at the summit you are most likely inside cloud/fog
WIND_STRONG_KMH = 40.0           # only flag wind when it is genuinely strong
TEMP_MIN_PLAUSIBLE = -10.0
TEMP_MAX_PLAUSIBLE = 30.0
TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStatusBot/5.0; +https://levadinho-madeira.com)"}
STATUS_JSON = "status.json"
NOTE_SOURCE_LANG = "pt"                        # IFCN notes are Portuguese originals
TRANSLATE_LANGS = ("en", "fr", "de", "pl")     # mirrored via MyMemory (en is required by bot/brain.py)
MYMEMORY_MAX_BYTES = 450                       # MyMemory rejects q > 500 bytes; chunk below that

# --- IFCN list parsing ---------------------------------------------------------
HEADINGS = [   # (regex over the raw HTML, status, heading name for logs)
    (r">\s*ENCERRADOS\s*/\s*CONDICIONADOS\s*:?\s*<", "CLOSED", "ENCERRADOS/CONDICIONADOS"),
    (r">\s*PARCIALMENTE\s+TRANSIT(?:Á|&Aacute;)VEIS\s*:?\s*<", "PARTIAL", "PARCIALMENTE TRANSITÁVEIS"),
    (r">\s*TRANSIT(?:Á|&Aacute;)VEIS\s*:?\s*<", "OPEN", "TRANSITÁVEIS"),
]
STATUS_RANK = {"OPEN": 0, "PARTIAL": 1, "CLOSED": 2}
# Heading labels prefixed to each section of a multi-heading note (PR1). Fixed
# translations: machine-translating them alone gave "Geschlossen/klimatisiert".
SECTION_LABEL = {
    "OPEN": {"pt": "Transitável", "en": "Open", "fr": "Praticable", "de": "Begehbar", "pl": "Dostępny"},
    "PARTIAL": {"pt": "Parcialmente transitável", "en": "Partly open", "fr": "Partiellement praticable",
                "de": "Teilweise begehbar", "pl": "Częściowo dostępny"},
    "CLOSED": {"pt": "Encerrado/condicionado", "en": "Closed/restricted", "fr": "Fermé/restreint",
               "de": "Gesperrt/eingeschränkt", "pl": "Zamknięty/ograniczony"},
}
ITEM_CODE_RE = re.compile(r"^PR\s*(\d+(?:\.\d+)?)\.?\s*[-–]?\s*", re.IGNORECASE)
PORTO_SANTO_RE = re.compile(r"\(\s*Porto\s+Santo\s*\)", re.IGNORECASE)
# IFCN items without a PR code -> our code (matched on the accent-folded, lowercased text).
NON_PR_ALIASES = {
    "queimadas- pico das pedras": "PR9.1",   # PR9.1 = Queimadas – Pico das Pedras (IFCN table)
}
MIN_IFCN_TRAILS = 25      # fewer Madeira trails parsed than this = the page changed -> fatal
MAX_MISSING = 5           # more PAGES trails absent from IFCN than this -> fatal

# Visit Madeira index rows: ["PR X - Name", lat, lon, n, "img", "url", "", bool, {"label":"..."}].
VM_TRAIL_RE = re.compile(
    r'\["(PR[^"]+?)",(-?\d+\.\d+),(-?\d+\.\d+),\d+,"[^"]*","[^"]*","[^"]*",'
    r'(?:true|false),\{"label":"([^"]+)"'
)
VM_STATUS_MAP = {"Open": "OPEN", "Restricted": "PARTIAL", "Closed": "CLOSED"}

POPULAR = {"PR1", "PR1.2", "PR6", "PR6.1", "PR8", "PR9", "PR11", "PR13", "PR18"}
# Regional IPMA stations for the weather strip: (key, station id, lat, lon).
REGIONS = [
    ("summit", 1210974, 32.735, -16.928),   # Pico do Areeiro
    ("north", 1210965, 32.808, -16.886),    # Santana
    ("west", 1210987, 32.757, -17.202),     # Prazeres / Rabaçal side
    ("east", 1210978, 32.747, -16.706),     # São Lourenço
    ("south", 1200522, 32.648, -16.888),    # Funchal
]
REGION_PLACE = {"summit": "Pico do Areeiro", "north": "Santana", "west": "Rabaçal",
                "east": "São Lourenço", "south": "Funchal"}
# Stations high enough that >=90% humidity usually means you're inside cloud
# (summit 1,818 m; west/Prazeres ~620 m). At coastal stations the same reading
# is just muggy sea air, so no fog flag there.
CLOUD_REGIONS = {"summit", "west"}
# Trails that have their own spoke page (the dashboard links to these).
# This is also the board: exactly these 37 codes are published.
PAGES = {
    "PR1": "/pr1/",
    "PR6": "/25-fontes/",
    "PR1.2": "/pico-ruivo/",
    "PR9": "/caldeirao-verde/",
    "PR8": "/sao-lourenco/",
    "PR11": "/balcoes/",
    "PR13": "/fanal/",
    "PR10": "/levada-do-furado/",
    "PR18": "/levada-do-rei/",
    "PR14": "/levada-dos-cedros/",
    "PR1.1": "/vereda-da-ilha/",
    "PR1.3": "/vereda-da-encumeada/",
    "PR2": "/vereda-do-urzal/",
    "PR3": "/vereda-do-burro/",
    "PR3.1": "/caminho-real-do-monte/",
    "PR4": "/levada-do-barreiro/",
    "PR5": "/vereda-das-funduras/",
    "PR6.1": "/levada-do-risco/",
    "PR6.2": "/levada-do-alecrim/",
    "PR6.3": "/vereda-da-lagoa-do-vento/",
    "PR7": "/levada-do-moinho/",
    "PR12": "/caminho-real-da-encumeada/",
    "PR15": "/vereda-da-ribeira-da-janela/",
    "PR16": "/levada-faja-do-rodrigues/",
    "PR17": "/caminho-do-pinaculo-e-folhadal/",
    "PR19": "/caminho-real-do-paul-do-mar/",
    "PR20": "/vereda-do-jardim-do-mar/",
    "PR21": "/caminho-do-norte/",
    "PR22": "/vereda-do-chao-dos-louros/",
    "PR27": "/glaciar-de-planalto/",
    "PR6.6": "/vereda-do-tunel-do-cavalo/",
    "PR28": "/levada-da-rocha-vermelha/",
    "PR6.8": "/levada-do-paul-ii-um-caminho-para-todos/",
    "PR6.4": "/levada-velha-do-rabacal/",
    "PR6.5": "/vereda-do-pico-fernandes/",
    "PR13.1": "/vereda-da-palha-carga/",
    "PR9.1": "/levada-do-caldeirao-verde-um-caminho-para-todos/",
}

# A note is "restrictive" when it limits where/when you may walk. Rule 1's
# safety net: an OPEN trail with such a note becomes PARTIAL.
#
# Match *phrases*, never bare words. The earlier version matched a lone "only",
# "between" or "partial", which on 2026-08-14 began firing on IFCN's rewritten
# note -- "can be completed in two ways: partially, between ... or in full,
# between ..." -- a note that describes two legitimate ways to walk an OPEN
# trail rather than restricting it. That downgraded PR1 to PARTIAL for 20 days
# while the official badge read OPEN. Rule 1 exists to stop a "green but
# restricted" lie; it must not manufacture the inverse.
#
# Portuguese: a bare "entre ... e" is NOT restrictive (PR1.2's "totalmente
# transitável o troço compreendido entre ..." and PR6's one-way loop are
# informational). "transitável entre/desde/até", "apenas/somente/só entre",
# "até ao km", "encerrad-", "condicionad-", "interdit-" are.
RESTRICTIVE = re.compile(
    r"(accessible only|open only|only between|only from|only the section|"
    r"partially closed|temporarily closed|closed section|closed between|"
    r"not accessible|no access|restricted|passable only|"
    # Portuguese (IFCN originals)
    r"transit[aá]vel\s+(?:apenas\s+|somente\s+|s[oó]\s+)?(?:entre|desde|at[eé])\b|"
    r"\b(?:apenas|somente|s[oó])\s+(?:entre|desde|at[eé]|no\s+tro[cç]o|na\s+sec[cç][aã]o)\b|"
    r"\bat[eé]\s+ao\s+km\b|\bencerrad[oa]s?\b|\bcondicionad[oa]s?\b|\binterdit[oa]s?\b|"
    r"\bparcialmente\b)",
    re.IGNORECASE,
)

# A sentence ends at . ! or ? -- but NOT at the dot inside a decimal.
SENTENCE_END = re.compile(r"[.!?](?!\d)(?= |$)")


def is_restrictive(note) -> bool:
    """True if a note (str, or {lang: text}) limits access -> badge must not read OPEN.
    For a dict only the Portuguese original and the English translation are checked."""
    if isinstance(note, dict):
        return any(is_restrictive(note.get(k, "")) for k in (NOTE_SOURCE_LANG, "en"))
    return bool(note) and bool(RESTRICTIVE.search(note))


def _fold(s):
    """Lowercase + strip Portuguese accents, for alias matching."""
    tr = str.maketrans("áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ", "aaaaeeiooouc" + "aaaaeeiooouc")
    return s.translate(tr).lower()


LINK_MARK = "\u0000"


def _li_text(li_html):
    """Plain text of one IFCN <li>: tags stripped, entities decoded, whitespace
    collapsed. A sentence that carries a link ("... ver o MAPA") is dropped,
    since the link itself can't travel into the note."""
    s = re.sub(r"(?s)<a\b[^>]*>.*?</a>", LINK_MARK, li_html)
    s = re.sub(r"(?i)</?(p|br|div)[^>]*>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s).replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\.(?=[A-ZÁÉÍÓÚ])", ". ", s)          # "sentidos.Trajeto" -> "sentidos. Trajeto"
    if LINK_MARK in s:
        parts, start = [], 0
        for e in SENTENCE_END.finditer(s + " "):
            parts.append(s[start:e.end()])
            start = e.end()
        parts.append(s[start:])
        s = " ".join(p.strip() for p in parts if p.strip() and LINK_MARK not in p)
    return s.strip()


def _split_item(text):
    """'PR 17 Caminho do Pináculo e Folhadal - percurso transitável entre ...'
    -> ('PR17', 'Caminho do Pináculo e Folhadal', 'percurso transitável entre ...').
    Returns (None, text, '') for an item with no PR code."""
    m = ITEM_CODE_RE.match(text)
    if not m:
        return None, text, ""
    code = "PR" + m.group(1)
    rest = text[m.end():].strip()
    # The name ends at the first spaced hyphen (en dashes belong to names:
    # "Levada do Paul II – Um caminho para todos").
    name, _, qual = rest.partition(" - ")
    qual = qual.strip()
    if qual.startswith("("):                          # PR6: "(circulação ... Bypass.)"
        qual = re.sub(r"\)\.?$", "", qual[1:]).strip()
    if qual and not qual.endswith((".", "!", "?")):
        qual += "."
    if qual:
        qual = qual[0].upper() + qual[1:]
    return code, name.strip(" -–"), qual


def ifcn_statuses():
    """Parse the IFCN warnings page -> {code: {"status", "name", "segments"}}.

    segments = [(section status or None, Portuguese text), ...]: one unlabelled
    segment per qualifier for a single-heading trail, or one labelled segment per
    heading for a trail listed under several (PR1). note_text() joins them.

    Fails loud (rule 3) on any fetch or structure problem. Porto Santo items
    and codes outside PAGES are excluded with a log line.
    """
    r = requests.get(IFCN_AVISOS, headers=UA, timeout=30)
    r.raise_for_status()
    page = r.text

    upd = re.search(r"ATUALIZADO:\s*(\d{1,2}/\d{1,2}/\d{4})", page)
    print(f"IFCN avisos page: ATUALIZADO {upd.group(1) if upd else '(no date found)'}", file=sys.stderr)
    # IFCN is the authority and doesn't update the list daily: publish its own date, in its own
    # wording, so the site never implies a fresher status than IFCN's ("ATUALIZADO: 14/09/2026").
    global IFCN_UPDATED
    IFCN_UPDATED = upd.group(1) if upd else ""

    # entries[code] = list of (status, label, name, qualifier)
    entries = {}
    for pattern, status, label in HEADINGS:
        hits = list(re.finditer(pattern, page))
        if len(hits) != 1:
            sys.exit(f"FATAL: IFCN heading {label!r} found {len(hits)} times (expected 1) — page changed?")
        ul = re.compile(r"(?s)<ul\b[^>]*>(.*?)</ul>").search(page, hits[0].end())
        if not ul:
            sys.exit(f"FATAL: no list after IFCN heading {label!r}")
        items = re.findall(r"(?s)<li\b[^>]*>(.*?)</li>", ul.group(1))
        if not items:
            sys.exit(f"FATAL: empty list under IFCN heading {label!r}")
        for li in items:
            text = _li_text(li)
            if not text:
                continue
            if PORTO_SANTO_RE.search(text):
                print(f"ifcn: skip Porto Santo item ({label}): {text!r}", file=sys.stderr)
                continue
            code, name, qual = _split_item(text)
            if code is None:
                folded = _fold(text)
                code = next((c for k, c in NON_PR_ALIASES.items() if k in folded), None)
                if code is None:
                    print(f"ifcn: skip item without PR code ({label}): {text!r}", file=sys.stderr)
                    continue
                print(f"ifcn: mapped {text!r} -> {code}", file=sys.stderr)
                name, qual = text, ""
            if code not in PAGES:
                print(f"ifcn: skip {code} ({name}) — no page on the site ({label})", file=sys.stderr)
                continue
            entries.setdefault(code, []).append((status, label, name, qual))

    if len(entries) < MIN_IFCN_TRAILS:
        sys.exit(f"FATAL: only {len(entries)} Madeira trails parsed from IFCN — refusing to publish")
    if "PR1" not in entries:
        sys.exit("FATAL: PR1 not found in the IFCN lists — refusing to publish")

    out = {}
    for code, rows in entries.items():
        statuses = {s for s, *_ in rows}
        if len(statuses) > 1:
            # Listed under more than one heading (PR1): some section open, some not.
            status = "PARTIAL"
            segments = [(st, qual or name + ".") for st, _label, name, qual in
                        sorted(rows, key=lambda r: STATUS_RANK[r[0]])]
        else:
            status = rows[0][0]
            segments = [(None, q) for *_x, q in rows if q]
        out[code] = {"status": status, "name": rows[0][2], "segments": segments}
    return out


def note_text(segments, lang=NOTE_SOURCE_LANG, texts=None):
    """Join note segments: 'Label: text. Label: text.' (labels from SECTION_LABEL).
    texts overrides the segment texts (their translations), same order."""
    texts = texts or [t for _st, t in segments]
    return " ".join(f"{SECTION_LABEL[st][lang]}{' :' if lang == 'fr' else ':'} {t}" if st else t
                    for (st, _t), t in zip(segments, texts))


def visit_madeira_statuses():
    """Secondary source: {code: status} from the Visit Madeira hiking index.
    Called only when IFCN omits a PAGES trail; fails loud if unusable."""
    r = requests.get(TRAILS_INDEX, headers=UA, timeout=30)
    r.raise_for_status()
    out = {}
    for m in VM_TRAIL_RE.finditer(r.text):
        raw = m.group(1)
        code = raw.split(" - ", 1)[0].replace(" ", "")
        out.setdefault(code, VM_STATUS_MAP.get(m.group(4), "PARTIAL"))
    if len(out) < 20:
        sys.exit(f"FATAL: only {len(out)} trails parsed from the Visit Madeira fallback index")
    return out


def load_trail_facts():
    """{code: {name, lat, lon, region}} from bot/trail_facts.json. Fatal if absent:
    without it no trail can be placed in a weather region."""
    try:
        with open(TRAIL_FACTS, encoding="utf-8") as f:
            rows = json.load(f)["trails"]
    except (OSError, ValueError, KeyError) as e:
        sys.exit(f"FATAL: cannot read {TRAIL_FACTS}: {e}")
    return {t["code"]: t for t in rows}


def _latest_reading(obs, station_id):
    """Most recent non-empty reading for a station. IPMA keys observations by
    ISO timestamp and a station can be absent/empty at the very latest hour, so
    walk backwards from newest until we find data. Returns the record or None.
    """
    sid = str(station_id)
    for ts in sorted(obs.keys(), reverse=True):
        rec = obs[ts].get(sid)
        if rec:
            return rec
    return None


def _field(rec, key):
    """A numeric field, or None if absent or the IPMA -99 'missing' sentinel."""
    if not rec:
        return None
    v = rec.get(key)
    if v is None:
        return None
    v = float(v)
    return None if v <= IPMA_MISSING + 0.5 else v


def summit_weather():
    """Official measured summit weather from IPMA's Pico do Areeiro station,
    as a structured dict for status.js to phrase in each language.

    Rule 2: a missing or implausible temperature raises, so main() records
    {"ok": False} and the pages show a generic fallback rather than garbage.
    """
    obs = requests.get(IPMA_OBS, headers=UA, timeout=30).json()

    rec = _latest_reading(obs, STATION_SUMMIT)
    temp = _field(rec, "temperatura")
    if temp is None or not (TEMP_MIN_PLAUSIBLE <= temp <= TEMP_MAX_PLAUSIBLE):
        raise ValueError(f"no plausible IPMA summit temperature (got {temp!r}) -- rejected")

    humidity = _field(rec, "humidade")

    # Wind: the summit sensor is frequently missing (-99); fall back to the
    # neighbouring Areeiro station before giving up on a wind reading.
    wind_kmh = _field(rec, "intensidadeVentoKM")
    if wind_kmh is None:
        wind_kmh = _field(_latest_reading(obs, STATION_WIND_FALLBACK), "intensidadeVentoKM")

    return {
        "ok": True,
        "temp_c": round(temp, 1),
        "humidity": round(humidity) if humidity is not None else None,
        "in_cloud": bool(humidity is not None and humidity >= HUMIDITY_CLOUD_PCT),
        "wind_kmh": round(wind_kmh) if wind_kmh is not None else None,
        "wind_strong": bool(wind_kmh is not None and wind_kmh >= WIND_STRONG_KMH),
    }


def _region_weather():
    """Latest measured conditions per regional station for the weather strip:
    temp (°C), wind (km/h), rain over the last hour (mm) and a likely-in-cloud
    flag for the high stations (CLOUD_REGIONS). Every field degrades to
    None/False on a missing sensor — like all weather, this must never take
    the run down."""
    obs = requests.get(IPMA_OBS, headers=UA, timeout=30).json()
    out = {}
    for key, sid, _lat, _lon in REGIONS:
        rec = _latest_reading(obs, sid)
        temp = _field(rec, "temperatura")
        humidity = _field(rec, "humidade")
        rain = _field(rec, "precAcumulada")
        wind = _field(rec, "intensidadeVentoKM")
        if wind is None and sid == STATION_SUMMIT:
            # Same fallback as summit_weather(): the summit wind sensor is
            # frequently missing; the neighbouring Areeiro station is close.
            wind = _field(_latest_reading(obs, STATION_WIND_FALLBACK), "intensidadeVentoKM")
        out[key] = {
            "temp": round(temp) if temp is not None else None,
            "wind": round(wind) if wind is not None else None,
            "rain": round(rain, 1) if rain is not None else None,
            "in_cloud": bool(key in CLOUD_REGIONS and humidity is not None
                             and humidity >= HUMIDITY_CLOUD_PCT),
        }
    return out


_REGION_WX_EMPTY = {"temp": None, "wind": None, "rain": None, "in_cloud": False}


def _nearest_region(lat, lon):
    """Region key of the closest regional station (flat lat/lon is fine here)."""
    return min(REGIONS, key=lambda r: (lat - r[2]) ** 2 + (lon - r[3]) ** 2)[0]


def build_trails():
    """The 37-trail board: IFCN status + note (pt), names and regions from
    trail_facts.json. A PAGES trail IFCN omits takes its status from the Visit
    Madeira index (logged); more than MAX_MISSING omissions is fatal (rule 3).
    Returns (trails, {code: note segments})."""
    ifcn = ifcn_statuses()
    facts = load_trail_facts()
    missing = [c for c in PAGES if c not in ifcn]
    vm = {}
    if missing:
        if len(missing) > MAX_MISSING:
            sys.exit(f"FATAL: IFCN omits {len(missing)} site trails ({', '.join(missing)}) — page changed?")
        print(f"ifcn: omits {', '.join(missing)} — using the Visit Madeira index for these", file=sys.stderr)
        vm = visit_madeira_statuses()
    trails, notes = [], {}
    for code in PAGES:
        f = facts.get(code)
        if not f or f.get("lat") is None:
            sys.exit(f"FATAL: {code} has no lat/lon in {TRAIL_FACTS}")
        if code in ifcn:
            status, segments, name = ifcn[code]["status"], ifcn[code]["segments"], ifcn[code]["name"]
        elif code in vm:
            status, segments, name = vm[code], [], f.get("name", code)
        else:
            sys.exit(f"FATAL: {code} is in neither IFCN nor the Visit Madeira index")
        trails.append({
            "code": code,
            "name": f.get("name") or name,
            "status": status,
            "fee": None if code in NO_IFCN_FEE else ("10.50" if code == "PR1" else "4.50"),
            "region": _nearest_region(float(f["lat"]), float(f["lon"])),
            "popular": code in POPULAR,
        })
        if segments:
            notes[code] = segments
    return trails, notes


def _chunks(text, limit=MYMEMORY_MAX_BYTES):
    """Split text at sentence ends into pieces of <= limit UTF-8 bytes."""
    pieces, cur = [], ""
    starts = [0] + [e.end() for e in SENTENCE_END.finditer(text)] + [len(text)]
    for a, b in zip(starts, starts[1:]):
        sent = text[a:b]
        if cur and len((cur + sent).encode()) > limit:
            pieces.append(cur.strip())
            cur = ""
        cur += sent
    if cur.strip():
        pieces.append(cur.strip())
    return pieces


def _mymemory(text, lang):
    """One MyMemory translation pt->lang, or None if unusable."""
    out = []
    for piece in _chunks(text):
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": piece, "langpair": f"{NOTE_SOURCE_LANG}|{lang}"},
            headers=UA, timeout=20,
        ).json()
        t = (r.get("responseData") or {}).get("translatedText", "").strip()
        # MyMemory returns UPPERCASE warnings (quota, invalid) instead of text.
        if r.get("responseStatus") != 200 or not t or "MYMEMORY WARNING" in t.upper() or "INVALID" in t.upper():
            return None
        out.append(htmllib.unescape(t))
    return " ".join(out)


def _previous_translations():
    """{pt original: {lang: text}} from the last status.json, so unchanged notes
    are not re-translated. A stored text equal to the original (a past fallback)
    is not reused, so it gets retried."""
    cache = {}
    try:
        with open(STATUS_JSON, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return cache
    for note in [old.get("note")] + [t.get("note") for t in old.get("trails", [])]:
        if isinstance(note, dict) and note.get(NOTE_SOURCE_LANG):
            src = note[NOTE_SOURCE_LANG]
            cache[src] = {k: v for k, v in note.items() if k in TRANSLATE_LANGS and v and v != src}
    return cache


_TRANSLATION_CACHE = None


def translate_note(segments):
    """Mirror an official Portuguese note (list of segments, see note_text) into
    each site language via MyMemory (free, keyless); section labels use the fixed
    SECTION_LABEL translations. Any per-language failure falls back to the
    Portuguese original, so a page never shows an empty note. Machine translation
    — the Portuguese original stays authoritative.
    """
    note = note_text(segments) if segments else ""
    global _TRANSLATION_CACHE
    if _TRANSLATION_CACHE is None:
        _TRANSLATION_CACHE = _previous_translations()
    out = {NOTE_SOURCE_LANG: note}
    cached = _TRANSLATION_CACHE.get(note, {})
    for lang in TRANSLATE_LANGS:
        if not note:
            out[lang] = ""
            continue
        if lang in cached:
            out[lang] = cached[lang]
            continue
        out[lang] = note  # fallback = Portuguese original
        try:
            texts = [_mymemory(t, lang) for _st, t in segments]
            if all(texts):
                out[lang] = note_text(segments, lang, texts)
            else:
                print(f"note translate {lang}: unusable response, kept Portuguese", file=sys.stderr)
        except Exception as e:
            print(f"note translate {lang} failed: {e} — kept Portuguese", file=sys.stderr)
    return out


def apply_rule1(code, status, note):
    """Rule 1 safety net: OPEN + restrictive note -> PARTIAL (logged)."""
    if status == "OPEN" and is_restrictive(note):
        shown = note.get(NOTE_SOURCE_LANG) if isinstance(note, dict) else note
        print(f"rule1: {code} downgraded OPEN->PARTIAL because note is restrictive: {shown!r}", file=sys.stderr)
        return "PARTIAL"
    return status


def assert_not_contradictory(status, note, what="PR1"):
    """Rule 1, final sanity gate: refuse to publish a status whose badge still
    contradicts its note. Should be unreachable after apply_rule1, but if it
    ever fires we fail loud rather than publish a green-but-restricted lie.
    """
    if status == "OPEN" and is_restrictive(note):
        sys.exit(f"FATAL: contradictory status refused for {what} — OPEN badge with restrictive note: {note!r}")


def site_pages():
    """Every published *.html (bot/, seo_research/ etc. excluded)."""
    return [p for p in sorted(glob.glob("**/*.html", recursive=True))
            if p.split(os.sep)[0] not in ("bot", ".git", "node_modules", "seo_research")]


def snapshot():
    """{path: content} of every page, taken before this run writes anything."""
    return {p: open(p, encoding="utf-8").read() for p in site_pages()}


def _stable(html):
    """The page without the weather reading, which changes on every run by design (2026-10-05, LLM audit item B):
    a new temperature is not a new page, so it no longer moves dateModified, <lastmod> or IndexNow."""
    return STATIC_WX_RE.sub("", html)


def changed_pages(before):
    return [p for p in site_pages() if _stable(before.get(p, "")) != _stable(open(p, encoding="utf-8").read())]


def _url_to_file(loc):
    path = re.sub(r"^https?://[^/]+/", "", loc)
    return path + "index.html" if path == "" or path.endswith("/") else path


def bump_sitemap(today, changed):
    """Set <lastmod> to today only for URLs whose page changed in this run (2026-10-03: a lastmod that
    is always "today" teaches Google to ignore it). Skipped if the sitemap is absent."""
    changed = set(changed)
    try:
        s = open("sitemap.xml").read()
    except FileNotFoundError:
        print("sitemap.xml not found — skipping lastmod bump", file=sys.stderr)
        return

    def url_sub(m):
        block = m.group(0)
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        if loc and _url_to_file(loc.group(1)) in changed:
            block = re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{today}</lastmod>", block)
        return block
    open("sitemap.xml", "w").write(re.sub(r"<url>.*?</url>", url_sub, s, flags=re.S))


# Classified PR trails managed by a body other than IFCN (IFCN trail list, ENTIDADE GESTORA column):
# not on SIMplifica, no IFCN fee (IFCN FAQ 1.7). Their "fee" is null; dashboard.js shows "No IFCN fee".
NO_IFCN_FEE = {"PR3", "PR3.1", "PR4", "PR23"}


def write_indexnow_urls(changed):
    """The URLs of the pages that really changed this run, for scripts/indexnow.py (the Action pings them after
    GitHub Pages has published). Git-ignored, never committed; an empty file means nothing to ping."""
    urls = []
    for p in changed:
        p = p.replace(os.sep, "/")
        url = "https://levadinho-madeira.com/" + (p[: -len("index.html")] if p.endswith("index.html") else p)
        urls.append(url)
    with open("indexnow_urls.txt", "w", encoding="utf-8") as f:
        f.write("".join(u + "\n" for u in urls))


def bump_date_modified(when, changed):
    """Set "dateModified" to this run's time on every page whose content changed in this run
    (2026-10-03; it was a fixed list of 10 pages bumped daily). Degrades gracefully (warns)."""
    for name in changed:
        try:
            s = open(name, encoding="utf-8").read()
        except FileNotFoundError:
            print(f"{name} not found — skipping dateModified", file=sys.stderr)
            continue
        new, n = re.subn(r'("dateModified":\s*")[^"]*(")', rf"\g<1>{when}\g<2>", s, count=1)
        if n != 1:
            continue
        open(name, "w", encoding="utf-8").write(new)


# --- Static (crawlable) status lines ------------------------------------------------
# Any page may carry  <!-- STATIC-STATUS:PR6:START -->...<!-- STATIC-STATUS:PR6:END -->
# (one trail) or  <!-- STATIC-STATUS-BOARD:START -->...<!-- STATIC-STATUS-BOARD:END -->
# (all-trail counts, used on the homepages). The inner text is replaced by a short
# plain line in the page's <html lang>. No markers anywhere = no-op.
# No dates on the site (owner, 2026-10-05): IFCN's "updated" date was weeks old and Google printed it in front of
# the snippets. status.json keeps it as data (source.updated); the pages never show it.
STATIC_I18N = {
    "en": {"on": "Official IFCN list:", "st": {"OPEN": "OPEN", "PARTIAL": "PARTLY OPEN", "CLOSED": "CLOSED"},
           "board": "Official IFCN list: {o} trails open, {p} partly open, {c} closed.",
           "months": ["January", "February", "March", "April", "May", "June", "July", "August",
                      "September", "October", "November", "December"], "date": "{day} {month} {year}"},
    "pt": {"on": "Lista oficial do IFCN:", "st": {"OPEN": "ABERTO", "PARTIAL": "PARCIALMENTE ABERTO", "CLOSED": "ENCERRADO"},
           "board": "Lista oficial do IFCN: {o} percursos abertos, {p} parcialmente abertos, {c} encerrados.",
           "months": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                      "setembro", "outubro", "novembro", "dezembro"], "date": "{day} de {month} de {year}"},
    "fr": {"on": "Liste officielle de l'IFCN :", "st": {"OPEN": "OUVERT", "PARTIAL": "PARTIELLEMENT OUVERT", "CLOSED": "FERMÉ"},
           "board": "Liste officielle de l'IFCN : {o} sentiers ouverts, {p} partiellement ouverts, {c} fermés.",
           "months": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                      "septembre", "octobre", "novembre", "décembre"], "date": "{day} {month} {year}"},
    "de": {"on": "Offizielle IFCN-Liste:", "st": {"OPEN": "GEÖFFNET", "PARTIAL": "TEILWEISE GEÖFFNET", "CLOSED": "GESCHLOSSEN"},
           "board": "Offizielle IFCN-Liste: {o} Wege geöffnet, {p} teilweise geöffnet, {c} geschlossen.",
           "months": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
                      "September", "Oktober", "November", "Dezember"], "date": "{day}. {month} {year}"},
    "pl": {"on": "Oficjalna lista IFCN:", "st": {"OPEN": "OTWARTY", "PARTIAL": "CZĘŚCIOWO OTWARTY", "CLOSED": "ZAMKNIĘTY"},
           "board": "Oficjalna lista IFCN: otwarte {o}, częściowo otwarte {p}, zamknięte {c}.",
           "months": ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
                      "września", "października", "listopada", "grudnia"], "date": "{day} {month} {year}"},
}
# Trail cards also carry  <!-- STATIC-WEATHER:PR6:START -->...<!-- STATIC-WEATHER:PR6:END -->: the measured
# IPMA reading of the trail's regional station at run time (crawlable "weather near the trail").
STATIC_WX_I18N = {
    "en": ("Weather near the trail (IPMA {place} station, {when}): {t} °C", ", wind {w} km/h", ", likely in cloud", ", rain {r} mm in the last hour"),
    "pt": ("Tempo perto do percurso (estação IPMA {place}, {when}): {t} °C", ", vento {w} km/h", ", provavelmente dentro das nuvens", ", chuva {r} mm na última hora"),
    "fr": ("Météo près du sentier (station IPMA {place}, {when}) : {t} °C", ", vent {w} km/h", ", probablement dans les nuages", ", pluie {r} mm sur la dernière heure"),
    "de": ("Wetter am Weg (IPMA-Station {place}, {when}): {t} °C", ", Wind {w} km/h", ", wahrscheinlich in Wolken", ", Regen {r} mm in der letzten Stunde"),
    "pl": ("Pogoda przy szlaku (stacja IPMA {place}, {when}): {t} °C", ", wiatr {w} km/h", ", prawdopodobnie w chmurach", ", deszcz {r} mm w ostatniej godzinie"),
}
# The weather page's summit reading (LLM audit item D, 2026-10-07): <!-- STATIC-WEATHER:SUMMIT:START/END --> in
# #wxSrc, so a crawler without JavaScript reads the measured figures instead of "–". The page script replaces it live.
STATIC_SUMMIT_I18N = {
    "en": ("Last measured reading, Pico do Areeiro summit (IPMA station, {when}): {t} °C", ", humidity {h}%", ", wind {w} km/h", ", likely in cloud"),
    "pt": ("Última leitura medida no cume do Pico do Areeiro (estação IPMA, {when}): {t} °C", ", humidade {h}%", ", vento {w} km/h", ", provavelmente dentro das nuvens"),
    "fr": ("Dernière mesure au sommet du Pico do Areeiro (station IPMA, {when}) : {t} °C", ", humidité {h} %", ", vent {w} km/h", ", probablement dans les nuages"),
    "de": ("Letzter Messwert am Gipfel des Pico do Areeiro (IPMA-Station, {when}): {t} °C", ", Luftfeuchte {h} %", ", Wind {w} km/h", ", wahrscheinlich in Wolken"),
    "pl": ("Ostatni pomiar na szczycie Pico do Areeiro (stacja IPMA, {when}): {t} °C", ", wilgotność {h}%", ", wiatr {w} km/h", ", prawdopodobnie w chmurach"),
}


def static_summit_line(weather, lang, hhmm):
    """The measured summit reading as one sentence, or '' when IPMA had no valid reading."""
    if not weather or not weather.get("ok") or weather.get("temp_c") is None:
        return ""
    head, hum, wind, cloud = STATIC_SUMMIT_I18N.get(lang, STATIC_SUMMIT_I18N["en"])
    t = str(weather["temp_c"]) if lang == "en" else str(weather["temp_c"]).replace(".", ",")
    line = head.format(when=hhmm, t=t)
    if weather.get("humidity") is not None:
        line += hum.format(h=weather["humidity"])
    if weather.get("wind_kmh") is not None:
        line += wind.format(w=weather["wind_kmh"])
    if weather.get("in_cloud"):
        line += cloud
    return line + "."


# Board line, 2026-10-03: also name the closed / partly open trails (crawlable answer to
# "percursos encerrados madeira", "madère sentier fermé", "które szlaki zamknięte").
STATIC_BOARD_LISTS = {
    "en": ("Closed: {}.", "Partly open: {}."), "pt": ("Encerrados: {}.", "Parcialmente abertos: {}."),
    "fr": ("Fermés : {}.", "Partiellement ouverts : {}."), "de": ("Geschlossen: {}.", "Teilweise geöffnet: {}."),
    "pl": ("Zamknięte: {}.", "Częściowo otwarte: {}."),
}
# Trail pages' meta description starts with the live IFCN status (2026-10-03), e.g.
# "IFCN: OPEN. Is the Levada do Rei open today? ..." — the prefix is replaced on every run.
# No date in any description (owner, 2026-10-05): IFCN's "updated" date can be weeks old and made the
# snippets look stale in search results. The dated (pre-2026-10-05) prefix is still matched so it gets replaced.
DESC_STATUS_RE = re.compile(r'(<meta name="description" content=")(?:IFCN(?: \d{2}[./]\d{2}[./]\d{4})?: [^."]+\. )?')
TRAIL_CARD_RE = re.compile(r'id="statusCard"[^>]*data-trail="([^"]+)"')
STATIC_NOTE_MAX = 220
STATIC_TRAIL_RE = re.compile(r"(<!--\s*STATIC-STATUS:([A-Za-z0-9.]+):START\s*-->)(.*?)(<!--\s*STATIC-STATUS:\2:END\s*-->)", re.S)
STATIC_BOARD_RE = re.compile(r"(<!--\s*STATIC-STATUS-BOARD:START\s*-->)(.*?)(<!--\s*STATIC-STATUS-BOARD:END\s*-->)", re.S)
# Status word after each link in the homepages' static trail list (gen_trail_index.py), 2026-10-05.
STATIC_BADGE_RE = re.compile(r"(<!--\s*STATIC-BADGE:([A-Za-z0-9.]+):START\s*-->)(.*?)(<!--\s*STATIC-BADGE:\2:END\s*-->)", re.S)
STATIC_WX_RE = re.compile(r"(<!--\s*STATIC-WEATHER:([A-Za-z0-9.]+):START\s*-->)(.*?)(<!--\s*STATIC-WEATHER:\2:END\s*-->)", re.S)
# The answer to "Is X open today?" (2026-10-05, LLM audit item A): one plain sentence per trail page, between
# <!-- STATIC-ANSWER:<CODE>:START/END --> markers in the page lead and in the visible FAQ answer, and the same
# words (no markers) at the start of the FAQ JSON-LD answer, so the FAQ stays verbatim. No dates (owner, 2026-10-05).
STATIC_ANSWER_I18N = {
    "en": "{name} ({code}) is {st} on IFCN's official trail-warnings list.",
    "pt": "{name} ({code}): {st} na lista oficial de avisos do IFCN.",
    "fr": "{name} ({code}) : {st} sur la liste officielle des avis de l'IFCN.",
    "de": "{name} ({code}): {st} laut der offiziellen Hinweisliste des IFCN.",
    "pl": "{name} ({code}): {st} według oficjalnej listy komunikatów IFCN.",
}
STATIC_ANSWER_RE = re.compile(r"(<!--\s*STATIC-ANSWER:([A-Za-z0-9.]+):START\s*-->)(.*?)(<!--\s*STATIC-ANSWER:\2:END\s*-->)", re.S)
LD_JSON_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
# /trail-closures/ (2026-10-07, LLM audit item F): a table of the trails that are closed or partly open today, with
# IFCN's note in the page language. No dates (owner's rule); the dated history is in trail-status.xml / history/.
STATIC_CLOSURES_RE = re.compile(r"(<!--\s*STATIC-CLOSURES:START\s*-->)(.*?)(<!--\s*STATIC-CLOSURES:END\s*-->)", re.S)
CLOSURES_I18N = {
    "en": ("Trail", "Status", "IFCN's note", "No trail is closed or partly open on IFCN's list right now."),
    "pt": ("Percurso", "Estado", "Nota do IFCN", "Neste momento nenhum percurso está encerrado ou parcialmente aberto na lista do IFCN."),
    "fr": ("Sentier", "État", "Note de l'IFCN", "Aucun sentier n'est fermé ni partiellement ouvert sur la liste de l'IFCN en ce moment."),
    "de": ("Weg", "Status", "Hinweis des IFCN", "Derzeit ist kein Weg auf der IFCN-Liste gesperrt oder teilweise geöffnet."),
    "pl": ("Szlak", "Stan", "Nota IFCN", "Obecnie żaden szlak na liście IFCN nie jest zamknięty ani częściowo otwarty."),
}
LANG_PREFIX = {"en": "", "pt": "/pt", "fr": "/fr", "de": "/de", "pl": "/pl"}


def closures_table(data, lang):
    """The closed / partly open trails as an HTML table in the page language (Rule 1 gate on every row)."""
    th_trail, th_st, th_note, none = CLOSURES_I18N.get(lang, CLOSURES_I18N["en"])
    L = STATIC_I18N.get(lang, STATIC_I18N["en"])
    rows = []
    for st in ("CLOSED", "PARTIAL"):
        for t in data["trails"]:
            if t["status"] != st:
                continue
            note = t.get("note") or {}
            assert_not_contradictory(t["status"], note, what=f"closures {t['code']}")
            text = note.get(lang) or note.get("en") or note.get(NOTE_SOURCE_LANG) or ""
            href = LANG_PREFIX.get(lang, "") + t["page"]
            rows.append(f'<tr><td><a href="{href}">{htmllib.escape(t["name"])} ({t["code"]})</a></td>'
                        f'<td><b>{L["st"][st]}</b></td><td>{htmllib.escape(text) or "—"}</td></tr>')
    if not rows:
        return f"<p>{none}</p>"
    return (f'<div class="tbl-wrap"><table><thead><tr><th>{th_trail}</th><th>{th_st}</th><th>{th_note}</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def answer_sentence(trail, lang):
    """'Levada do Risco (PR6.1) is OPEN on IFCN's official trail-warnings list.' in the page language."""
    lang = lang if lang in STATIC_ANSWER_I18N else "en"
    assert_not_contradictory(trail["status"], trail.get("note") or {}, what=f"answer {trail['code']}")  # Rule 1
    L = STATIC_I18N[lang]
    return STATIC_ANSWER_I18N[lang].format(name=trail["name"], code=trail["code"], st=L["st"][trail["status"]])


def answer_any_status_re(trail, lang):
    """The answer sentence with whatever status word it carried before (to find it in the JSON-LD)."""
    lang = lang if lang in STATIC_ANSWER_I18N else "en"
    head, tail = STATIC_ANSWER_I18N[lang].format(name=trail["name"], code=trail["code"], st="\0").split("\0")
    words = "|".join(re.escape(w) for w in sorted(STATIC_I18N[lang]["st"].values(), key=len, reverse=True))
    return re.compile(re.escape(head) + "(?:" + words + ")" + re.escape(tail))


def sync_answers(html, lang, by_code):
    """Fill the STATIC-ANSWER markers and put the same sentence (any previous status word) in the FAQ JSON-LD,
    so the FAQ answer stays verbatim with the visible one."""
    codes = {m.group(2) for m in STATIC_ANSWER_RE.finditer(html)}
    if not codes:
        return html
    def answer_sub(mm):
        t = by_code.get(mm.group(2))
        return mm.group(0) if not t else mm.group(1) + htmllib.escape(answer_sentence(t, lang), quote=False) + mm.group(4)
    html = STATIC_ANSWER_RE.sub(answer_sub, html)
    for code in codes:
        t = by_code.get(code)
        if not t:
            continue
        rx, new = answer_any_status_re(t, lang), answer_sentence(t, lang)
        found = [0]
        def ld_sub(mm):
            body, n = rx.subn(new.replace("\\", "\\\\"), mm.group(2))
            found[0] += n
            return mm.group(1) + body + mm.group(3)
        html = LD_JSON_RE.sub(ld_sub, html)  # 0 matches = the sentence is only in the lead, not in a FAQ answer
    return html


HTML_LANG_RE = re.compile(r"<html[^>]*\blang=[\"']?([a-zA-Z]{2})", re.I)


def _short_note(text):
    """Whole sentences of a note up to STATIC_NOTE_MAX characters (so PR1 keeps both
    its open and its restricted section); a too-long first sentence is cut with '…'."""
    if not text:
        return ""
    s = ""
    for e in list(SENTENCE_END.finditer(text)) + [None]:
        cand = text[: e.end()] if e else text
        if s and len(cand) > STATIC_NOTE_MAX:
            break
        s = cand
        if len(s) > STATIC_NOTE_MAX:
            break
    if len(s) > STATIC_NOTE_MAX:
        s = s[: STATIC_NOTE_MAX - 1].rsplit(" ", 1)[0] + "…"
    return s.strip()


def static_line(trail, lang, date):
    """One localized plain line for a trail, e.g. 'Status on 30 September 2026: OPEN — ...'."""
    L = STATIC_I18N.get(lang, STATIC_I18N["en"])
    note = trail.get("note") or {}
    text = note.get(lang) or note.get("en") or note.get(NOTE_SOURCE_LANG) or ""
    # Rule 1 applies to these lines too.
    assert_not_contradictory(trail["status"], note, what=f"static line {trail['code']}")
    line = f"{L['on'].format(d=_fmt_date(date, L))} {L['st'][trail['status']]}"
    short = _short_note(text)
    return f"{line} — {short}" if short else line


def static_weather_line(region, lang, date, hhmm):
    """'Weather near the trail (IPMA Santana station, 3 October 2026 06:10): 15 °C, wind 9 km/h.' or ''."""
    if not region or region.get("temp") is None:
        return ""
    head, wind, cloud, rain = STATIC_WX_I18N.get(lang, STATIC_WX_I18N["en"])
    when = hhmm  # the reading's time only: no dates on the site (owner, 2026-10-05)
    line = head.format(place=region["place"], when=when, t=region["temp"])
    if region.get("wind") is not None:
        line += wind.format(w=region["wind"])
    if region.get("in_cloud"):
        line += cloud
    if region.get("rain"):
        line += rain.format(r=str(region["rain"]).replace(".", "," if lang != "en" else "."))
    return line + "."


def _fmt_date(date, L):
    """IFCN's own "ATUALIZADO" date (dd/mm/yyyy, as IFCN prints it) when known — the site never
    implies a fresher status than the authority's; otherwise our check date."""
    if IFCN_UPDATED:
        return IFCN_UPDATED
    return L["date"].format(day=date.day, month=L["months"][date.month - 1], year=date.year)


def write_static_status(data):
    """Fill every STATIC-STATUS marker pair in the site's *.html (bot/ excluded) with
    a plain, crawlable status line in the page's language. No-op when no markers
    exist. Unknown codes are left untouched with a warning. Returns changed files."""
    date = datetime.date.fromisoformat(data["date"])
    by_code = {t["code"]: t for t in data["trails"]}
    regions = {r["key"]: r for r in data.get("regions", [])}
    hhmm = (data.get("stamp") or "")[-5:]
    changed = []
    for path in sorted(glob.glob("**/*.html", recursive=True)):
        if path.split(os.sep)[0] in ("bot", ".git", "node_modules", "seo_research"):
            continue
        with open(path, encoding="utf-8") as f:
            s = f.read()
        if not any(k in s for k in ("STATIC-STATUS", "STATIC-WEATHER", "STATIC-BADGE", "STATIC-ANSWER", "STATIC-CLOSURES")):
            continue
        m = HTML_LANG_RE.search(s)
        lang = m.group(1).lower() if m else "en"
        L = STATIC_I18N.get(lang, STATIC_I18N["en"])

        def trail_sub(mm):
            t = by_code.get(mm.group(2))
            if not t:
                print(f"{path}: STATIC-STATUS code {mm.group(2)} not on the board — left as is", file=sys.stderr)
                return mm.group(0)
            return mm.group(1) + htmllib.escape(static_line(t, lang, date), quote=False) + mm.group(4)

        def board_sub(mm):
            c = data["counts"]
            line = L["board"].format(d=_fmt_date(date, L), o=c.get("OPEN", 0),
                                     p=c.get("PARTIAL", 0), c=c.get("CLOSED", 0))
            for st, fmt in zip(("CLOSED", "PARTIAL"), STATIC_BOARD_LISTS.get(lang, STATIC_BOARD_LISTS["en"])):
                names = [f"{t['name']} ({t['code']})" for t in data["trails"] if t["status"] == st]
                if names:
                    line += " " + fmt.format(", ".join(names))
            return mm.group(1) + htmllib.escape(line, quote=False) + mm.group(3)

        def wx_sub(mm):
            if mm.group(2) == "SUMMIT":
                return mm.group(1) + htmllib.escape(static_summit_line(data.get("weather"), lang, hhmm), quote=False) + mm.group(4)
            t = by_code.get(mm.group(2))
            r = regions.get(t["region"]) if t else None
            return mm.group(1) + htmllib.escape(static_weather_line(r, lang, date, hhmm), quote=False) + mm.group(4)

        def badge_sub(mm):
            t = by_code.get(mm.group(2))
            if not t:
                return mm.group(0)
            assert_not_contradictory(t["status"], t.get("note") or {}, what=f"badge {t['code']}")
            return mm.group(1) + htmllib.escape(": " + L["st"][t["status"]], quote=False) + mm.group(4)

        new = STATIC_WX_RE.sub(wx_sub, STATIC_BOARD_RE.sub(board_sub, STATIC_TRAIL_RE.sub(trail_sub, s)))
        new = STATIC_BADGE_RE.sub(badge_sub, new)
        new = sync_answers(new, lang, by_code)
        new = STATIC_CLOSURES_RE.sub(lambda mm: mm.group(1) + closures_table(data, lang) + mm.group(3), new)
        card = TRAIL_CARD_RE.search(new)
        if card and card.group(1) in by_code and IFCN_UPDATED and "STATIC-WEATHER" in new:  # trail pages only
            t = by_code[card.group(1)]
            assert_not_contradictory(t["status"], t.get("note") or {}, what=f"description {t['code']}")
            prefix = f"IFCN: {L['st'][t['status']]}. "
            new = DESC_STATUS_RE.sub(lambda mm: mm.group(1) + prefix, new, count=1)
        if new != s:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            changed.append(path)
    print(f"static status: {len(changed)} page(s) updated", file=sys.stderr)
    return changed


def main():
    now = datetime.datetime.now(TZ)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    today = now.strftime("%Y-%m-%d")

    # Status board from IFCN (fails loud on scrape/parse error).
    trails, notes = build_trails()
    for t in trails:
        if t["code"] in notes:
            t["note"] = translate_note(notes[t["code"]])
        t["status"] = apply_rule1(t["code"], t["status"], t.get("note"))
        # Rule 1 final gate before we write anything.
        assert_not_contradictory(t["status"], t.get("note"), what=t["code"])

    pr1 = next(t for t in trails if t["code"] == "PR1")
    status = pr1["status"]
    note_i18n = pr1.get("note") or translate_note([])

    try:
        weather = summit_weather()
    except Exception as e:
        weather = {"ok": False}
        print("weather fetch failed/rejected:", e, file=sys.stderr)

    manual_note = ""
    try:
        manual_note = open("scripts/manual_note.txt").read().strip()
    except FileNotFoundError:
        pass

    try:
        region_wx = _region_weather()
    except Exception as e:
        region_wx = {}
        print("regional weather fetch failed:", e, file=sys.stderr)
    for t in trails:
        t["temp"] = region_wx.get(t["region"], _REGION_WX_EMPTY)["temp"]
        t["page"] = PAGES[t["code"]]
        if "note" in t:                       # keep "note" last, as before
            t["note"] = t.pop("note")
    counts = {"OPEN": 0, "PARTIAL": 0, "CLOSED": 0}
    for t in trails:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    regions = [dict({"key": k, "place": REGION_PLACE[k]}, **region_wx.get(k, _REGION_WX_EMPTY))
               for k, _sid, _lat, _lon in REGIONS]

    data = {
        # Top-level = the detailed PR1 flagship data (status.js on the PR1 pages).
        "status": status,
        "note": note_i18n,
        "manual_note": manual_note,
        "weather": weather,
        "stamp": stamp,
        "date": today,
        # The official source and the date IFCN itself last updated its list (not our check time).
        "source": {"name": "IFCN", "url": IFCN_AVISOS, "updated": IFCN_UPDATED},
        # Added for the dashboard (dashboard.js).
        "counts": counts,
        "regions": regions,
        "trails": trails,
    }
    with open(STATUS_JSON, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    before = snapshot()
    write_static_status(data)
    changed = changed_pages(before)
    bump_date_modified(now.isoformat(timespec="minutes"), changed)
    bump_sitemap(today, changed)
    print(f"dates: {len(changed)} page(s) changed -> dateModified + sitemap lastmod", file=sys.stderr)
    write_indexnow_urls(changed)

    # Machine-readable editions (owner, 2026-10-07): history line, RSS of changes, llms.txt / llms-full.txt.
    # Derived from the data just written, so they degrade gracefully: a failure here never blocks the status.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import gen_ai_feeds
        gen_ai_feeds.run(data)
    except Exception as e:
        print("ai feeds failed (status.json is still written):", e, file=sys.stderr)

    print(f"PR1={status} | trails={len(trails)} | "
          f"open={counts['OPEN']} partial={counts['PARTIAL']} closed={counts['CLOSED']} | {stamp}")


if __name__ == "__main__":
    main()
