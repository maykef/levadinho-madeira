#!/usr/bin/env python3
"""
Levadinho daily status updater (v3).

Source: the official Visit Madeira PR1 trail page, which carries the status
(OPEN / RESTRICTED / CLOSED) and the official warning note as static HTML.
Weather from Open-Meteo. Rewrites the STATUS block and <title> in index.html,
stamps getting-back.html, and bumps sitemap.xml lastmod.

Hard rules (v3):
  1. Badge never contradicts the note. If the official note restricts access
     ("only", "between", "km 1,2", "restricted", ...), an OPEN badge is
     downgraded to PARTIAL. A final sanity check refuses to publish a block
     whose badge still contradicts its note (exit non-zero).
  2. Weather uses the real ridge elevation (1,818 m). Without the `elevation`
     param Open-Meteo returns near-coastal temperatures. Values < -10 C or
     > 30 C are treated as implausible and rejected (fallback line used).
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
AREEIRO = (32.7357, -16.9289)
RIDGE_ELEVATION_M = 1818          # real start elevation; without this Open-Meteo returns coastal temps
TEMP_MIN_PLAUSIBLE = -10.0
TEMP_MAX_PLAUSIBLE = 30.0
TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStatusBot/3.0; +https://levadinho-madeira.github.io)"}

# A note is "restrictive" when it limits where/when you may walk. This is the
# core of rule 1 -- it is what turns the live "Footpath accessible only between
# Pico do Areeiro and Pedra Rija Belvedere (km 1,2)" note into a PARTIAL badge.
RESTRICTIVE = re.compile(
    r"\b(only|between|km\s*\d|restricted|partial|closed section|"
    r"accessible only|not accessible|no access)\b",
    re.IGNORECASE,
)

WMO = {
    0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "FOG at summit level", 48: "freezing FOG at summit level",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}


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


def summit_weather():
    """Ridge weather via Open-Meteo at the real elevation. Rule 2 applies:
    reject implausible temperatures by raising, so main() uses the fallback.
    """
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": AREEIRO[0], "longitude": AREEIRO[1],
            "elevation": RIDGE_ELEVATION_M,          # rule 2: without this, temps are coastal
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "timezone": "Atlantic/Madeira",
        }, headers=UA, timeout=30,
    ).json()
    cur = r["current"]
    temp = float(cur["temperature_2m"])
    if not (TEMP_MIN_PLAUSIBLE <= temp <= TEMP_MAX_PLAUSIBLE):
        raise ValueError(f"implausible summit temperature {temp} C -- rejected")
    phrase = WMO.get(cur["weather_code"], "changeable conditions")
    wind = ""
    if cur["wind_speed_10m"] >= 40:
        wind = f", strong wind ({cur['wind_speed_10m']:.0f} km/h)"
    return (f"Summit weather now: {phrase}, {temp:.0f}°C at ~1,800 m{wind} — "
            "expect it far colder and cloudier than Funchal.")


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
    <span>Source: IFCN / Visit Madeira</span>
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
