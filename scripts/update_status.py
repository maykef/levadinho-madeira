#!/usr/bin/env python3
"""
Levadinho daily status updater (v2).
Source: the official Visit Madeira PR1 trail page, which carries the
status (OPEN / RESTRICTED / CLOSED) and the official warning note as
static HTML. Weather from Open-Meteo. Rewrites the STATUS block and
<title> in index.html, stamps getting-back.html.
Fails loudly (non-zero exit) so a red Action = yesterday's status stays
live instead of garbage. scripts/manual_note.txt adds a human line.
"""
import datetime
import re
import sys
import zoneinfo

import requests

TRAIL_PAGE = "https://visitmadeira.com/en/what-to-do/nature-seekers/activities/hiking/pr-1-vereda-do-areeiro/"
AREEIRO = (32.7357, -16.9289)
TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStatusBot/2.0; +https://levadinho-madeira.github.io)"}

WMO = {
    0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "FOG at summit level", 48: "freezing FOG at summit level",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}


def pr1_status():
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
    status = {"OPEN": "OPEN", "CLOSED": "CLOSED", "RESTRICTED": "PARTIAL"}[m.group(1)]
    window = plain[a + m.end(): a + m.end() + 1500]
    n = re.search(r"([A-Z][^.!?]*?(?:accessible|closed|restricted|only|between)[^.!?]*[.!?])", window)
    note = re.sub(r"\s+", " ", n.group(1)).strip() if n else ""
    if "SIMplifica" in note or "payment" in note.lower():
        note = ""
    return status, note


def summit_weather():
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": AREEIRO[0], "longitude": AREEIRO[1],
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "timezone": "Atlantic/Madeira",
        }, headers=UA, timeout=30,
    ).json()
    cur = r["current"]
    phrase = WMO.get(cur["weather_code"], "changeable conditions")
    wind = ""
    if cur["wind_speed_10m"] >= 40:
        wind = f", strong wind ({cur['wind_speed_10m']:.0f} km/h)"
    return (f"Summit weather now: {phrase}, {cur['temperature_2m']:.0f}°C at ~1,800 m{wind} — "
            "expect it far colder and cloudier than Funchal.")


def build_block(status, note, weather, stamp, manual_note):
    default_note = {
        "OPEN": "One-way only: Pico do Areeiro → Pico Ruivo. Book on SIMplifica before you go.",
        "PARTIAL": "Access is restricted — read the official note before planning.",
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


def main():
    now = datetime.datetime.now(TZ)
    stamp = now.strftime("%Y-%m-%d %H:%M")

    status, note = pr1_status()

    try:
        weather = summit_weather()
    except Exception as e:
        weather = "Check the mountain forecast before you go — summit conditions differ sharply from Funchal."
        print("weather fetch failed:", e, file=sys.stderr)

    manual_note = ""
    try:
        manual_note = open("scripts/manual_note.txt").read().strip()
    except FileNotFoundError:
        pass

    block = build_block(status, note, weather, stamp, manual_note)

    s = open("index.html").read()
    s = re.sub(r"<!-- STATUS:BEGIN.*?STATUS:END -->", block, s, flags=re.S)
    s = re.sub(r"<title>.*?</title>",
               f"<title>PR1 Pico do Areeiro trail status — {now:%Y-%m-%d}: {status} | sold-out fixes & rescheduling</title>",
               s, count=1)
    open("index.html", "w").write(s)

    g = open("getting-back.html").read()
    g = re.sub(r'lastUpdated: "[^"]*"', f'lastUpdated: "{now:%Y-%m-%d}"', g)
    open("getting-back.html", "w").write(g)

    print(f"PR1={status} | note={note[:80]!r} | {stamp}")


if __name__ == "__main__":
    main()
