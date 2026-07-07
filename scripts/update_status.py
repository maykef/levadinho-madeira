#!/usr/bin/env python3
"""
Levadinho daily status updater (v3).

Source: the official Visit Madeira PR1 trail page, which carries the status
(OPEN / RESTRICTED / CLOSED) and the official warning note as static HTML.
Summit weather is the official IPMA observation for the Pico do Areeiro station.
Rewrites the STATUS block and <title> in index.html, stamps getting-back.html,
and bumps sitemap.xml lastmod.

Hard rules (v3):
  1. Badge never contradicts the note. If the official note restricts access
     ("only", "between", "km 1,2", "restricted", ...), an OPEN badge is
     downgraded to PARTIAL. A final sanity check refuses to publish a block
     whose badge still contradicts its note (exit non-zero).
  2. Weather is the real measured reading from IPMA's Pico do Areeiro station
     (no model, no elevation guessing). IPMA carries no sky code, so we report
     temperature plus a humidity-derived "likely in cloud" note. IPMA -99
     "missing" fields and temps < -10 C / > 30 C are rejected (fallback used).
  3. Fail loud. Any scrape failure exits non-zero -> red Action -> yesterday's
     honest status stays live instead of garbage.
  4. scripts/manual_note.txt (optional) injects a human-written line.
"""
import datetime
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
WIND_STRONG_KMH = 40.0           # only mention wind when it is genuinely strong
TEMP_MIN_PLAUSIBLE = -10.0
TEMP_MAX_PLAUSIBLE = 30.0
TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStatusBot/3.0; +https://madeira.maykef.info)"}

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
    """Official measured summit weather from IPMA's Pico do Areeiro station.

    IPMA observations carry no sky/weather code, so we report the measured
    temperature, a "likely in cloud" note derived from very high humidity, and
    wind when it is strong. Rule 2: a missing or implausible temperature raises,
    so main() falls back to a generic line rather than publish garbage.
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

    cloud = ""
    if humidity is not None and humidity >= HUMIDITY_CLOUD_PCT:
        cloud = f", likely in cloud/fog (humidity {humidity:.0f}%)"
    wind = ""
    if wind_kmh is not None and wind_kmh >= WIND_STRONG_KMH:
        wind = f", strong wind ({wind_kmh:.0f} km/h)"

    return (f"Summit weather now: {temp:.0f}°C measured at the Pico do Areeiro "
            f"station (~1,800 m){cloud}{wind} — expect it far colder and "
            "cloudier than Funchal.")


def build_block(status, note, weather, stamp, manual_note):
    default_note = {
        "OPEN": "One-way only: Pico do Areeiro → Pico Ruivo. Book on SIMplifica before you go.",
        "PARTIAL": "Access is restricted — read the official note above before planning.",
        "CLOSED": "The trail is officially closed. See below for rescheduling your SIMplifica booking and open alternatives.",
    }[status]
    lines = []
    if note:
        lines.append(f"    <p><b>Official note:</b> {note}</p>")
    lines.append(f"    <p>{default_note}</p>")
    if manual_note:
        lines.append(f"    <p>{manual_note}</p>")
    lines.append(f"    <p>{weather}</p>")
    lines.append(
        '    <p class="advisory">The webcam shows you a snippet of the summit right now — '
        "don't assume conditions will stay that way. Pack a good anorak and fleece, carry "
        "enough water, and wear adequate footwear.</p>"
    )
    body = "\n".join(lines)
    return f"""<!-- STATUS:BEGIN (rewritten daily by scripts/update_status.py — do not edit by hand) -->
  <div class="status-head">
    <span class="status-dot {status}"></span>
    <span class="status-badge {status}">{status}</span>
  </div>
  <div class="status-body">
{body}
  </div>
  <div class="stamp">
    <span>Last checked: <b>{stamp}</b> (Madeira time)</span>
    <span>Source: IFCN / Visit Madeira · IPMA</span>
  </div>
<!-- STATUS:END -->"""


def assert_not_contradictory(status, note):
    """Rule 1, final sanity gate: refuse to publish a block whose badge still
    contradicts its note. Should be unreachable after the downgrade, but if it
    ever fires we fail loud rather than publish a green-but-restricted lie.
    """
    if status == "OPEN" and is_restrictive(note):
        sys.exit(f"FATAL: contradictory block refused — OPEN badge with restrictive note: {note!r}")


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

    try:
        weather = summit_weather()
    except Exception as e:
        weather = "Check the mountain forecast before you go — summit conditions differ sharply from Funchal."
        print("weather fetch failed/rejected:", e, file=sys.stderr)

    manual_note = ""
    try:
        manual_note = open("scripts/manual_note.txt").read().strip()
    except FileNotFoundError:
        pass

    # Rule 1 final gate before we touch any file.
    assert_not_contradictory(status, note)

    block = build_block(status, note, weather, stamp, manual_note)

    s = open("index.html").read()
    s = re.sub(r"<!-- STATUS:BEGIN.*?STATUS:END -->", block, s, flags=re.S)
    s = re.sub(r"<title>.*?</title>",
               f"<title>PR1 Pico do Areeiro trail status — {today}: {status} | sold-out fixes & rescheduling</title>",
               s, count=1)
    open("index.html", "w").write(s)

    g = open("getting-back.html").read()
    g = re.sub(r'lastUpdated: "[^"]*"', f'lastUpdated: "{today}"', g)
    open("getting-back.html", "w").write(g)

    bump_sitemap(today)

    print(f"PR1={status} | note={note[:80]!r} | {stamp}")


if __name__ == "__main__":
    main()
