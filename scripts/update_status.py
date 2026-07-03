#!/usr/bin/env python3
"""
Levadinho daily status updater.
1. Finds the official 'abertos-fechados' PDF via the stable Visit Madeira listing page
2. Extracts PR1 (Madeira) status + official note
3. Fetches summit weather for Pico do Areeiro from Open-Meteo (free, no key)
4. Rewrites the STATUS block, <title>, and JSON-LD hints in index.html
5. Stamps getting-back.html
Fails loudly (non-zero exit) on any parse problem so the Action shows red
and yesterday's (still plausible) status stays live instead of garbage.
Manual note: contents of scripts/manual_note.txt, if non-empty, are shown
as an extra line — editable from a phone for things automation can't know.
"""
import datetime
import io
import re
import sys
import zoneinfo

import requests
from pypdf import PdfReader

LISTING_PAGE = "https://visitmadeira.com/en/what-to-do/nature-seekers/notice-to-walkers-and-list-of-walks/"
PDF_HINT = "abertos-fechados"
AREEIRO = (32.7357, -16.9289)  # Pico do Areeiro
TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
UA = {"User-Agent": "LevadinhoStatusBot/1.0 (+https://levadinho-madeira.github.io)"}

WMO = {  # Open-Meteo weather codes -> short phrase
    0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "FOG at summit level", 48: "freezing FOG at summit level",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}


def find_pdf_url() -> str:
    html = requests.get(LISTING_PAGE, headers=UA, timeout=30).text
    m = re.search(r'href="([^"]*' + PDF_HINT + r'[^"]*\.pdf)"', html, re.I)
    if not m:
        sys.exit("FATAL: open/closed PDF link not found on listing page")
    url = m.group(1)
    if url.startswith("/"):
        url = "https://visitmadeira.com" + url
    return url


def pr1_status_from_pdf(pdf_bytes: bytes):
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf_bytes)).pages)
    # Madeira section only — Porto Santo also has a PR 1
    madeira = text.split("PORTO SANTO")[0]
    # PR 1 entry: from 'PR 1 ' (not PR 1.x) up to the next PR code
    m = re.search(r"PR\s*1\s+(?!\.)(.*?)(?=PR\s*\d)", madeira, re.S)
    if not m:
        sys.exit("FATAL: PR 1 entry not found in PDF")
    entry = m.group(1)
    up = entry.upper()
    if "PARCIALMENTE" in up or "PARTIALLY" in up:
        status = "PARTIAL"
    elif "ENCERRADO" in up or "CLOSED" in up:
        status = "CLOSED"
    elif "ABERTO" in up or "OPEN" in up:
        status = "OPEN"
    else:
        sys.exit("FATAL: could not classify PR1 status from entry: " + entry[:200])
    note = ""
    n = re.search(r"Note:\s*(.+?)(?:\n[A-Z]|\Z)", entry, re.S)
    if n:
        note = re.sub(r"\s+", " ", n.group(1)).strip().rstrip(".") + "."
    return status, note


def summit_weather() -> str:
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
        "PARTIAL": "Only part of the trail is accessible — read the official note below before planning.",
        "CLOSED": "The trail is officially closed. See below for rescheduling your SIMplifica booking and open alternatives.",
    }[status]
    lines = [f"    <p><b>{'Official note: ' if note else ''}</b>{note or default_note}</p>"]
    if note:
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

    pdf_url = find_pdf_url()
    pdf = requests.get(pdf_url, headers=UA, timeout=60).content
    status, note = pr1_status_from_pdf(pdf)

    try:
        weather = summit_weather()
    except Exception as e:  # weather is nice-to-have, never fatal
        weather = "Check the mountain forecast before you go — summit conditions differ sharply from Funchal."
        print("weather fetch failed:", e, file=sys.stderr)

    manual_note = ""
    try:
        manual_note = open("scripts/manual_note.txt").read().strip()
    except FileNotFoundError:
        pass

    block = build_block(status, note, weather, stamp, manual_note)

    s = open("index.html").read()
    s2 = re.sub(r"<!-- STATUS:BEGIN.*?STATUS:END -->", block, s, flags=re.S)
    s2 = re.sub(r"<title>.*?</title>",
                f"<title>PR1 Pico do Areeiro trail status — {now:%Y-%m-%d}: {status} | sold-out fixes & rescheduling</title>",
                s2, count=1)
    if s2 == s:
        print("index.html unchanged")
    open("index.html", "w").write(s2)

    g = open("getting-back.html").read()
    g = re.sub(r'lastUpdated: "[^"]*"', f'lastUpdated: "{now:%Y-%m-%d}"', g)
    open("getting-back.html", "w").write(g)

    print(f"PR1={status} | note={note[:80]!r} | {stamp}")


if __name__ == "__main__":
    main()
