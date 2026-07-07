#!/usr/bin/env python3
"""
Levadinho daily status updater (v4).

Source: the official Visit Madeira PR1 trail page carries the status
(OPEN / RESTRICTED / CLOSED) and the official warning note as static HTML.
Summit weather is the official IPMA observation for the Pico do Areeiro station.

v4 change: instead of rewriting HTML, this writes a single language-neutral
`status.json`. Every homepage (en/fr/de/pl) renders the status card from it via
`status.js`, so one data file drives all languages. It also bumps sitemap.xml.

Hard rules:
  1. Badge never contradicts the note. If the official note restricts access
     ("only", "between", "km 1,2", "restricted", ...), an OPEN badge is
     downgraded to PARTIAL. A final gate refuses to publish a contradictory
     status (exit non-zero).
  2. Weather is the real measured reading from IPMA's Pico do Areeiro station.
     IPMA -99 "missing" fields and temps < -10 C / > 30 C are rejected, and the
     weather object is marked {"ok": false} so the pages show a safe fallback.
  3. Fail loud. Any status-scrape failure exits non-zero -> red Action ->
     yesterday's honest status.json stays live instead of garbage.
  4. scripts/manual_note.txt (optional) injects a human-written line.
"""
import datetime
import json
import re
import sys
import zoneinfo

import requests

TRAIL_PAGE = "https://visitmadeira.com/en/what-to-do/nature-seekers/activities/hiking/pr-1-vereda-do-areeiro/"

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
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStatusBot/4.0; +https://madeira.maykef.info)"}
STATUS_JSON = "status.json"
TRANSLATE_LANGS = ("fr", "de", "pl")   # note is scraped in English; mirror it into these

# --- Multi-trail dashboard ---------------------------------------------------
# The Visit Madeira hiking index embeds every trail as a JSON row
# ["PR X - Name", lat, lon, n, "img", "url", "", bool, {"label":"Open|Restricted|Closed"}].
TRAILS_INDEX = "https://visitmadeira.com/en/what-to-do/nature-seekers/activities/hiking/"
TRAIL_RE = re.compile(
    r'\["(PR[^"]+?)",(-?\d+\.\d+),(-?\d+\.\d+),\d+,"[^"]*","[^"]*","[^"]*",'
    r'(?:true|false),\{"label":"([^"]+)"'
)
STATUS_MAP = {"Open": "OPEN", "Restricted": "PARTIAL", "Closed": "CLOSED"}
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
# Trails that have their own spoke page (the dashboard links to these).
PAGES = {
    "PR1": "/",
    "PR6": "/25-fontes/",
    "PR1.2": "/pico-ruivo/",
    "PR9": "/caldeirao-verde/",
    "PR8": "/sao-lourenco/",
}

# A note is "restrictive" when it limits where/when you may walk. This is the
# core of rule 1 -- it is what turns the live "Footpath accessible only between
# Pico do Areeiro and Pedra Rija Belvedere (km 1,2)" note into a PARTIAL badge.
RESTRICTIVE = re.compile(
    r"\b(only|between|km\s*\d|restricted|partial|closed section|"
    r"accessible only|not accessible|no access)\b",
    re.IGNORECASE,
)


def is_restrictive(note: str) -> bool:
    """True if the official note limits access -> badge must not read OPEN."""
    return bool(note) and bool(RESTRICTIVE.search(note))


def pr1_status():
    """Return (status, note). status in {OPEN, PARTIAL, CLOSED}.

    Applies rule 1: an OPEN scraped from the page is downgraded to PARTIAL
    when the accompanying official note restricts access.
    """
    r = requests.get(TRAIL_PAGE, headers=UA, timeout=30)
    r.raise_for_status()
    html = r.text
    html = re.sub(r"(?s)<head.*?</head>", " ", html)
    html = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", html)
    plain = re.sub(r"<[^>]+>", " ", html)

    a = plain.find("Vereda do Areeiro")
    if a == -1:
        sys.exit("FATAL: trail name not found on page")

    m = re.search(r"\b(OPEN|CLOSED|RESTRICTED)\b", plain[a:])
    if not m:
        sys.exit("FATAL: no status word found after trail name")
    raw = {"OPEN": "OPEN", "CLOSED": "CLOSED", "RESTRICTED": "PARTIAL"}[m.group(1)]

    window = plain[a + m.end(): a + m.end() + 1500]
    n = re.search(r"([A-Z][^.!?]*?(?:accessible|closed|restricted|only|between)[^.!?]*[.!?])", window)
    note = re.sub(r"\s+", " ", n.group(1)).strip() if n else ""
    if "SIMplifica" in note or "payment" in note.lower():
        note = ""

    # Rule 1: downgrade OPEN -> PARTIAL when the note restricts access.
    status = raw
    if status == "OPEN" and is_restrictive(note):
        status = "PARTIAL"
        print(f"rule1: downgraded OPEN->PARTIAL because note is restrictive: {note!r}", file=sys.stderr)

    return status, note


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


def _region_temps():
    """Latest temperature (rounded °C, or None) for each regional station."""
    obs = requests.get(IPMA_OBS, headers=UA, timeout=30).json()
    out = {}
    for key, sid, _lat, _lon in REGIONS:
        t = _field(_latest_reading(obs, sid), "temperatura")
        out[key] = round(t) if t is not None else None
    return out


def _nearest_region(lat, lon):
    """Region key of the closest regional station (flat lat/lon is fine here)."""
    return min(REGIONS, key=lambda r: (lat - r[2]) ** 2 + (lon - r[3]) ** 2)[0]


def scrape_trails():
    """Every Madeira PR trail from the Visit Madeira hiking index: code, name,
    coarse status (OPEN/PARTIAL/CLOSED), fee and nearest weather region. Fails
    loud if the index can't be parsed (rule 3)."""
    r = requests.get(TRAILS_INDEX, headers=UA, timeout=30)
    r.raise_for_status()
    trails, seen = [], set()
    for m in TRAIL_RE.finditer(r.text):
        try:
            raw = json.loads('"' + m.group(1) + '"')   # decode JSON \uXXXX escapes (São, Balcões, …)
        except Exception:
            raw = m.group(1)
        lat, lon, label = float(m.group(2)), float(m.group(3)), m.group(4)
        code_part, name = (raw.split(" - ", 1) + [raw])[:2] if " - " in raw else (raw, raw)
        code = code_part.replace(" ", "")
        if code in seen:          # the index lists some trails (e.g. PR1) twice
            continue
        seen.add(code)
        trails.append({
            "code": code,
            "name": name.strip(),
            "status": STATUS_MAP.get(label, "PARTIAL"),
            "fee": "10.50" if code == "PR1" else "4.50",
            "region": _nearest_region(lat, lon),
            "popular": code in POPULAR,
        })
    if len(trails) < 20:
        sys.exit(f"FATAL: only {len(trails)} trails parsed from hiking index — refusing to publish")
    return trails


def translate_note(note):
    """Mirror the official English note into each site language via MyMemory
    (free, keyless). English is always kept; any per-language failure falls back
    to the English text, so a localized page never shows an empty note. This is
    machine translation — the engine preserves the proper nouns well, but the
    English original stays authoritative.
    """
    out = {"en": note}
    for lang in TRANSLATE_LANGS:
        out[lang] = note  # fallback = English original
        if not note:
            out[lang] = ""
            continue
        try:
            r = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": note, "langpair": f"en|{lang}"},
                headers=UA, timeout=20,
            ).json()
            t = (r.get("responseData") or {}).get("translatedText", "").strip()
            # MyMemory returns UPPERCASE warnings (quota, invalid) instead of text.
            if r.get("responseStatus") == 200 and t and "WARNING" not in t.upper() and "INVALID" not in t.upper():
                out[lang] = t
            else:
                print(f"note translate {lang}: unusable response, kept English", file=sys.stderr)
        except Exception as e:
            print(f"note translate {lang} failed: {e} — kept English", file=sys.stderr)
    return out


def assert_not_contradictory(status, note):
    """Rule 1, final sanity gate: refuse to publish a status whose badge still
    contradicts its note. Should be unreachable after the downgrade, but if it
    ever fires we fail loud rather than publish a green-but-restricted lie.
    """
    if status == "OPEN" and is_restrictive(note):
        sys.exit(f"FATAL: contradictory status refused — OPEN badge with restrictive note: {note!r}")


def bump_sitemap(today):
    """Bump every <lastmod> in sitemap.xml to today. Skipped if absent."""
    try:
        s = open("sitemap.xml").read()
    except FileNotFoundError:
        print("sitemap.xml not found — skipping lastmod bump", file=sys.stderr)
        return
    s = re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{today}</lastmod>", s)
    open("sitemap.xml", "w").write(s)


def main():
    now = datetime.datetime.now(TZ)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    today = now.strftime("%Y-%m-%d")

    status, note = pr1_status()
    note_i18n = translate_note(note)

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

    # Rule 1 final gate before we write anything.
    assert_not_contradictory(status, note)

    # Multi-trail board for the dashboard (fails loud on scrape/parse error).
    trails = scrape_trails()
    region_temps = _region_temps()
    for t in trails:
        t["temp"] = region_temps.get(t["region"])
        if t["code"] in PAGES:
            t["page"] = PAGES[t["code"]]
        if t["code"] == "PR1":
            # Use our accurate detailed PR1 status + translated note.
            t["status"] = status
            t["note"] = note_i18n
    counts = {"OPEN": 0, "PARTIAL": 0, "CLOSED": 0}
    for t in trails:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    regions = [{"key": k, "place": REGION_PLACE[k], "temp": region_temps.get(k)}
               for k, _sid, _lat, _lon in REGIONS]

    data = {
        # Top-level = the detailed PR1 flagship data (status.js on the PR1 pages).
        "status": status,
        "note": note_i18n,
        "manual_note": manual_note,
        "weather": weather,
        "stamp": stamp,
        "date": today,
        # Added for the dashboard (dashboard.js).
        "counts": counts,
        "regions": regions,
        "trails": trails,
    }
    with open(STATUS_JSON, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    bump_sitemap(today)

    print(f"PR1={status} | trails={len(trails)} | "
          f"open={counts['OPEN']} partial={counts['PARTIAL']} closed={counts['CLOSED']} | {stamp}")


if __name__ == "__main__":
    main()
