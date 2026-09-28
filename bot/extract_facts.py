"""Build bot/trail_facts.json — the static trail knowledge the Levadinho bot is grounded in.

Re-runnable. For every PR trail on the Visit Madeira hiking index it records:
  - the official facts (distance, duration, difficulty, altitude, start/end, route type),
    scraped from the trail's official page with the same scraper the generated spokes use;
  - the trailhead coordinates from the index (used to suggest *nearby* alternatives);
  - region, fee and our spoke page from status.json / the updater's PAGES map;
  - any extra rows from our hand-authored facts sidebar (e.g. Tunnels, Exposure, Summit).

Nothing is invented: a field the official page doesn't give is left out. Live status is
NOT stored here — the bot reads it from status.json at answer time.

Run from the repo root:  python bot/extract_facts.py
"""
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gen_spokes  # noqa: E402  (scrape_facts, BASE, UA)
from update_status import PAGES  # noqa: E402

SITE = "https://levadinho-madeira.com"
OUT = os.path.join(ROOT, "bot", "trail_facts.json")
INDEX = f"{gen_spokes.BASE}/en/what-to-do/nature-seekers/activities/hiking/"
# Same embedded-JSON row the updater and generator parse, but keeping lat/lon too.
ROW = re.compile(r'\["(PR[^"]+?)",(-?\d+\.\d+),(-?\d+\.\d+),\d+,"[^"]*","([^"]*)"')
# Sidebar rows that the official scrape already covers — anything else is an extra.
COVERED = {"Distance", "Round trip", "Time", "Difficulty", "Altitude", "Type", "Route", "Fee"}
# The official pages have no reliable route-type field (the word "circular" appears in
# page chrome), so our sidebar's Type row — checked by hand on the authored spokes — wins.
TYPES = {"out-and-back": "out-and-back", "circular": "circular", "point-to-point": "point-to-point",
         "linear": "point-to-point"}


def index_rows():
    req = urllib.request.Request(INDEX, headers=gen_spokes.UA)
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    out = {}
    for name, lat, lon, url in ROW.findall(html):
        code, _, title = name.partition(" - ")
        code = code.replace(" ", "")
        out.setdefault(code, {"name": title.strip(), "lat": float(lat), "lon": float(lon), "url": url})
    if len(out) < 30:
        sys.exit(f"Only {len(out)} trails parsed from the index — page layout changed?")
    return out


def sidebar(page):
    """All rows from our own facts sidebar, keyed by label."""
    path = os.path.join(ROOT, page.strip("/"), "index.html") if page != "/" else os.path.join(ROOT, "index.html")
    try:
        html = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return {}
    m = re.search(r'<aside class="facts">(.*?)</aside>', html, re.S)
    if not m:
        return {}
    rows = re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", m.group(1))
    return {k: re.sub(r"<[^>]+>", "", v) for k, v in rows}


def route_type(f, side):
    typ = side.get("Type", "").lower()
    for word, kind in TYPES.items():
        if typ.startswith(word):
            return kind
    if f.get("round_trip") or "each way" in side.get("Distance", ""):
        return "out-and-back"
    return "circular" if f.get("circular") else "point-to-point"


def main():
    status = json.load(open(os.path.join(ROOT, "status.json"), encoding="utf-8"))
    live = {t["code"]: t for t in status["trails"]}
    rows = index_rows()

    trails = []
    for code, row in rows.items():
        f = gen_spokes.scrape_facts(row["url"])
        side = sidebar(PAGES[code]) if code in PAGES else {}
        if re.fullmatch(r"[\d.,]+ ?m", f.get("end", "")):  # PR8: altitude leaks into Start/End
            f.pop("end")
        time.sleep(0.5)  # be polite to visitmadeira.com
        t = live.get(code, {})
        entry = {
            "code": code,
            "name": t.get("name") or row["name"],
            "region": t.get("region"),
            "fee_eur": t.get("fee"),
            "lat": row["lat"],
            "lon": row["lon"],
            "distance": f.get("distance"),
            "duration": f.get("duration"),
            "difficulty": f.get("difficulty"),
            "alt_min_m": f.get("alt_min"),
            "alt_max_m": f.get("alt_max"),
            "altitude": None if f.get("alt_min") else side.get("Altitude"),
            "type": route_type(f, side),
            "start": f.get("start"),
            "end": f.get("end"),
            "page": SITE + PAGES[code] if code in PAGES else None,
            "official_url": gen_spokes.BASE + row["url"] if row["url"].startswith("/") else row["url"],
        }
        entry.update({k.lower(): v for k, v in side.items() if k not in COVERED})
        trails.append({k: v for k, v in entry.items() if v is not None})
        print(f"{code:7} {entry['name'][:38]:38} {f.get('distance', '-'):22} {f.get('difficulty', '-'):9} {f.get('duration', '-')}")

    trails.sort(key=lambda t: [float(x) for x in t["code"][2:].split(".")])
    missing = sorted(set(live) - {t["code"] for t in trails})
    if missing:
        print("WARNING: in status.json but not on the index:", missing)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"generated": time.strftime("%Y-%m-%d"), "source": INDEX, "trails": trails},
                  fh, ensure_ascii=False, indent=1)
    print(f"\nWrote {len(trails)} trails to {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
