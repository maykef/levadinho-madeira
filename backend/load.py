#!/usr/bin/env python3
"""Fill the knowledge store (schema kb in levadinho-db) from what the site and the bot already hold.

  python3 backend/load.py init     apply backend/schema.sql (idempotent)
  python3 backend/load.py all      every loader (static facts + daily data)
  python3 backend/load.py daily    status, weather, history, forecasts (the daily updater's part)
  python3 backend/load.py <name>…  single loaders: sources trails status history fees facts transport bus docs forecast

Each loader replaces its own rows in one transaction, so a failed run leaves the previous data in place.
Sources: status.json, trail_extras.json, history/status-daily.jsonl, bot/trail_facts.json, bot/pr1_facts.md,
bot/transport_facts.md, scripts/gen_bus*.py, the site's pages (5 languages), reports/camtest/forecasts/ and
backend/seed.py. DB_URL comes from the environment or bot/.env.
"""
import datetime
import glob
import html
import json
import os
import re
import sys
import urllib.request
import zoneinfo

import psycopg
from psycopg.types.json import Jsonb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "scripts"), os.path.join(ROOT, "bot")]
import seed  # noqa: E402

SITE = "https://levadinho-madeira.com"
LANGS = ["en", "pt", "fr", "de", "pl"]
TS_CFG = {"en": "english", "pt": "portuguese", "fr": "french", "de": "german", "pl": "simple"}
MADEIRA = zoneinfo.ZoneInfo("Atlantic/Madeira")
NOW = datetime.datetime.now(datetime.timezone.utc)


def db_url():
    if os.environ.get("DB_URL"):
        return os.environ["DB_URL"]
    for line in open(os.path.join(ROOT, "bot", ".env"), encoding="utf-8"):
        if line.startswith("DB_URL="):
            return line.split("=", 1)[1].strip()
    sys.exit("DB_URL not set and not in bot/.env")


def rj(path):
    return json.load(open(os.path.join(ROOT, path), encoding="utf-8"))


def live(path):
    """A file the daily GitHub Action publishes (status.json, history): the live site's copy, else the local one
    (this checkout is not pulled automatically)."""
    try:
        with urllib.request.urlopen(f"{SITE}/{path}", timeout=20) as r:
            return r.read().decode("utf-8")
    except OSError as e:
        print(f"  {path}: live site unreachable ({e}), using the local copy", file=sys.stderr)
        return open(os.path.join(ROOT, path), encoding="utf-8").read()


def mtime(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(ROOT, path)), datetime.timezone.utc)


def num(s):
    m = re.search(r"\d+(?:[.,]\d+)?", s or "")
    return float(m.group().replace(",", ".")) if m else None


# ---------------------------------------------------------------- loaders: each returns (rows, detail)
def load_sources(cur):
    cur.executemany("""INSERT INTO kb.source (id, name, publisher, url, licence, kind) VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, publisher=EXCLUDED.publisher, url=EXCLUDED.url,
                       licence=EXCLUDED.licence, kind=EXCLUDED.kind""", seed.SOURCES)
    return len(seed.SOURCES), "backend/seed.py"


def load_trails(cur):
    facts = rj("bot/trail_facts.json")
    extras = rj("trail_extras.json")
    status = {t["code"]: t for t in rj("status.json")["trails"]}
    checked = datetime.datetime.fromisoformat(facts["generated"]).replace(tzinfo=MADEIRA)
    rows = []
    for t in facts["trails"]:
        e = extras.get(t["code"]) or {}
        s = status.get(t["code"], {})
        fee = s.get("fee") if s else t.get("fee_eur")
        torch = {"yes": True, "no": False}.get(e.get("torch"))
        rows.append((t["code"], t["name"], t.get("region") or s.get("region"), t.get("type"), t.get("start"), t.get("end"),
                     num(t.get("distance")), t.get("distance"), t.get("duration"), t.get("difficulty"),
                     int(num(t["alt_min_m"])) if t.get("alt_min_m") else None, int(num(t["alt_max_m"])) if t.get("alt_max_m") else None,
                     float(fee) if fee else None, e.get("tunnels"), torch, e.get("exposure"),
                     Jsonb({k: e[k] for k in ("torch", "tunnel_count", "ifcn_warning", "source", "notes") if e.get(k) is not None}) if e else None,
                     t.get("lon"), t.get("lat"), t.get("page") or (SITE + s.get("page", "/")), t.get("official_url"),
                     "visitmadeira", checked))
    cur.executemany("""INSERT INTO kb.trail (code, name, region, route_type, start_name, end_name, distance_km, distance_txt,
                       duration, difficulty, alt_min_m, alt_max_m, fee_eur, tunnels, torch, exposure, extras, trailhead,
                       page_url, official_url, source_id, checked_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                               ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,%s,%s,%s,%s)
                       ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name, region=EXCLUDED.region, route_type=EXCLUDED.route_type,
                       start_name=EXCLUDED.start_name, end_name=EXCLUDED.end_name, distance_km=EXCLUDED.distance_km,
                       distance_txt=EXCLUDED.distance_txt, duration=EXCLUDED.duration, difficulty=EXCLUDED.difficulty,
                       alt_min_m=EXCLUDED.alt_min_m, alt_max_m=EXCLUDED.alt_max_m, fee_eur=EXCLUDED.fee_eur, tunnels=EXCLUDED.tunnels,
                       torch=EXCLUDED.torch, exposure=EXCLUDED.exposure, extras=EXCLUDED.extras, trailhead=EXCLUDED.trailhead,
                       page_url=EXCLUDED.page_url, official_url=EXCLUDED.official_url, source_id=EXCLUDED.source_id,
                       checked_at=EXCLUDED.checked_at""", rows)
    return len(rows), "bot/trail_facts.json + trail_extras.json + status.json fees"


def load_status(cur):
    """Today's status per trail + the weather readings, from status.json (the updater's output)."""
    s = json.loads(live("status.json"))
    checked = datetime.datetime.strptime(s["stamp"], "%Y-%m-%d %H:%M").replace(tzinfo=MADEIRA)
    upd = (s.get("source") or {}).get("updated")
    rows = []
    for t in s["trails"]:
        note = t.get("note") or (s.get("note") if t["code"] == "PR1" else None)
        if isinstance(note, str):
            note = {"en": note}
        rows.append((t["code"], t["status"], Jsonb(note) if note else None, "ifcn_warnings", upd, checked))
    cur.execute("DELETE FROM kb.trail_status")
    cur.executemany("INSERT INTO kb.trail_status VALUES (%s,%s,%s,%s,%s,%s)", rows)
    w = s.get("weather") or {}
    wx = []
    if w.get("ok"):
        wx.append(("summit_station", "Pico do Areeiro (IPMA summit station)", checked, w.get("temp_c"), w.get("wind_kmh"), None,
                   w.get("humidity"), w.get("in_cloud"), "ipma"))
    for r in s.get("regions") or []:
        wx.append((r["key"], r["place"], checked, r.get("temp"), r.get("wind"), r.get("rain"), None, r.get("in_cloud"), "ipma"))
    cur.executemany("""INSERT INTO kb.weather_obs VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (region, observed_at) DO NOTHING""", wx)
    return len(rows) + len(wx), f"status.json {s['stamp']} ({len(rows)} trails, {len(wx)} readings)"


def load_history(cur):
    rows = []
    for line in live("history/status-daily.jsonl").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        rows += [(d["date"], code, st, d.get("source") or "IFCN") for code, st in d["trails"].items()]
    cur.execute("DELETE FROM kb.status_day")
    cur.executemany("INSERT INTO kb.status_day VALUES (%s,%s,%s,%s)", rows)
    return len(rows), "history/status-daily.jsonl"


def load_fees(cur):
    checked = mtime("backend/seed.py")
    cur.execute("DELETE FROM kb.fee")
    cur.executemany("INSERT INTO kb.fee VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    [(i, a, Jsonb(l), ap, Jsonb(c) if c else None, src, checked) for i, a, l, ap, c, src in seed.FEES])
    return len(seed.FEES), "backend/seed.py"


# pr1_facts.md section → (topic, source)
PR1_SECTIONS = {
    "The trail": ("trail", "visitmadeira"),
    "Closures and reopening": ("closures", "ifcn_warnings"),
    "One-way rule": ("one_way", "ifcn_fees_faq"),
    "Getting there and back": ("transport", "horarios_funchal_areeiro"),
    "Fees and booking": ("fees_booking", "portaria_48_2026"),
    "Sold out?": ("sold_out", "levadinho_research"),
    "Refunds and closures": ("refunds", "portaria_48_2026"),
    "Sunrise": ("sunrise", "levadinho_research"),
    "Weather and safety": ("safety", "levadinho_research"),
    "Not confirmed": ("unconfirmed", "levadinho_research"),
}


def md_sections(path):
    """[(heading, [bullet text, …])] for the '## ' sections of a markdown file; sub-bullets and continuation lines
    are joined to their top-level bullet."""
    out, cur = [], None
    for line in open(os.path.join(ROOT, path), encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("## "):
            cur = (line[3:].strip(), [])
            out.append(cur)
        elif cur is None or not line.strip():
            continue
        elif line.startswith("- "):
            cur[1].append(line[2:].strip())
        elif cur[1]:
            cur[1][-1] += " " + line.strip()
        else:
            cur[1].append(line.strip())
    return out


def section_key(heading, table):
    return next((v for k, v in table.items() if heading.startswith(k)), None)


def load_facts(cur):
    import gen_bus
    import gen_bus_hub
    checked_pr1 = mtime("bot/pr1_facts.md")
    rows = []
    for heading, bullets in md_sections("bot/pr1_facts.md"):
        key = section_key(heading, PR1_SECTIONS)
        if not key:
            continue
        topic, src = key
        for n, b in enumerate(bullets, 1):
            # the return from the end of the full walk is its own topic: tools return it with the PR1 rules
            t = "getting_back" if topic == "transport" and "Achada do Teixeira" in b else topic
            rows.append((f"pr1:{topic}:{n}", t, "PR1", Jsonb({"en": re.sub(r"\*\*(.+?)\*\*", r"\1", b)}),
                         topic != "unconfirmed", src, checked_pr1))
    checked_t = mtime("backend/seed.py")
    rows += [(f"transport:{i}", topic, subj, Jsonb({"en": text}), True, src, checked_t)
             for i, topic, subj, text, src in seed.TRANSPORT_FACTS]
    # the bus sentences each trail page shows ("no bus reaches the plateau", "the only bus of the day"…), 5 languages
    checked_b = mtime("scripts/gen_bus.py")
    for code, d in gen_bus_hub.DATA.items():
        n = 0
        for leg in ("there", "back", "nobus"):
            for item in d.get(leg, []):
                if isinstance(item, dict):
                    continue
                n += 1
                text = {lang: html.unescape(gen_bus.sentence(item, lang)) for lang in LANGS}
                rows.append((f"bus:{code}:{leg}:{n}", "bus", code, Jsonb(text), True, "siga", checked_b))
    cur.execute("DELETE FROM kb.fact")
    cur.executemany("INSERT INTO kb.fact VALUES (%s,%s,%s,%s,%s,%s,%s)", rows)
    unconf = sum(1 for r in rows if not r[4])
    return len(rows), f"pr1_facts.md + seed + bus sentences ({unconf} unconfirmed)"


def load_transport(cur):
    checked = mtime("bot/transport_facts.md")
    rows = []
    for line in open(os.path.join(ROOT, "bot/transport_facts.md"), encoding="utf-8"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3 or not cells[1].startswith("+351"):
            continue
        name, phones, trails = cells
        clean = re.sub(r"\s*\(.*?\)", "", name)
        town = re.sub(r"^Táxis\s+", "", clean)
        side = re.search(r"\((\w+) side\)", name)
        ascii_ = clean.lower().translate(str.maketrans("ãçáéíâó", "acaeiao"))
        slug = re.sub(r"[^a-z0-9]+", "_", ascii_).strip("_") + (f"_{side.group(1).lower()}" if side else "")
        rows.append((slug, "taxi", town, clean, [p.strip() for p in phones.split("/")], None,
                     [t.strip() for t in trails.split(",")], "ifcn_panels", checked))
    checked_s = mtime("backend/seed.py")
    rows += [(i, k, town, n, ph, url, None, src, checked_s) for i, k, town, n, ph, url, src in seed.ISLAND_TAXIS]
    if len(rows) < 10:
        raise SystemExit(f"transport: only {len(rows)} rows parsed from transport_facts.md; table format changed?")
    cur.execute("DELETE FROM kb.transport")
    cur.executemany("INSERT INTO kb.transport VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
    return len(rows), "bot/transport_facts.md taxi table + seed"


def load_bus(cur):
    import gen_bus_hub
    checked = mtime("scripts/gen_bus.py")
    rows = []
    for code, d in gen_bus_hub.DATA.items():
        for leg in ("there", "back"):
            for s in d.get(leg, []):
                if not isinstance(s, dict):
                    continue
                line = "Santana network" if s["n"] == "Santana" else s["n"]
                for days, trips in s["trips"].items():
                    for dep, arr, marks in trips:
                        rows.append((s["op"], line, s["new"], s["a"], s["b"], dep, arr, days, marks.split(),
                                     s["change_at"], code, leg, None, None, "siga", checked))
    checked_a = mtime("backend/seed.py")
    for dep, arr, a, b, leg, vf, vt in seed.AREEIRO_BUS:
        rows.append(("Horários do Funchal", "Pico do Areeiro", None, a, b, dep, arr, "daily", [], None, "PR1", leg, vf, vt,
                     "horarios_funchal_areeiro", checked_a))
    cur.execute("DELETE FROM kb.bus_trip")
    cur.executemany("""INSERT INTO kb.bus_trip (operator, line, new_line, from_stop, to_stop, dep, arr, days, marks, change_at,
                       trail_code, leg, valid_from, valid_to, source_id, checked_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
    return len(rows), f"gen_bus TRAILS + gen_bus_hub EXTRA + PR1 Areeiro bus ({len(gen_bus_hub.DATA)} trails)"


def chunks(text, max_chars=1800):
    """Split page text at its '## ' headings; long sections are cut at paragraph breaks."""
    out = []
    for part in re.split(r"\n(?=## )", "\n" + text):
        part = part.strip()
        if not part:
            continue
        title = part.split("\n", 1)[0].lstrip("# ").strip()
        while len(part) > max_chars:
            cut = part.rfind("\n\n", 0, max_chars)
            cut = cut if cut > 200 else max_chars
            out.append((title, part[:cut].strip()))
            part = part[cut:].strip()
        if len(part) > 40:
            out.append((title, part))
    return out


def load_docs(cur):
    import build_kb
    facts = rj("bot/trail_facts.json")
    pages = [(t["code"], t["page"].replace(SITE, "")) for t in facts["trails"]]
    pages += [(f"guide:{k}", p) for k, p in build_kb.GUIDES.items()]
    pages += [("guide:closures", "/trail-closures/"), ("guide:about", "/about/")]
    rows = []
    for subject, path in pages:
        for lang in LANGS:
            p = path if lang == "en" else f"/{lang}{path}"
            try:
                text = build_kb.page_text(p)
            except FileNotFoundError:
                continue
            checked = mtime((p.strip("/") if p.endswith(".html") else p.strip("/") + "/index.html"))
            for n, (title, body) in enumerate(chunks(text)):
                rows.append((f"page:{lang}:{subject}:{n}", "page", subject, lang, title, SITE + p, body, TS_CFG[lang],
                             "levadinho_site", checked))
    checked_pr1 = mtime("bot/pr1_facts.md")
    for heading, bullets in md_sections("bot/pr1_facts.md"):
        key = section_key(heading, PR1_SECTIONS)
        if not key or key[0] == "unconfirmed":
            continue
        body = "\n".join("- " + re.sub(r"\*\*(.+?)\*\*", r"\1", b) for b in bullets)
        rows.append((f"facts:en:PR1:{key[0]}", "facts", "PR1", "en", f"PR1 {heading}", SITE + "/pr1/", body, "english",
                     key[1], checked_pr1))
    cur.execute("DELETE FROM kb.doc")
    cur.executemany("""INSERT INTO kb.doc (id, kind, subject, lang, title, url, body, cfg, source_id, checked_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s::regconfig,%s,%s)""", rows)
    return len(rows), f"{len(pages)} pages × 5 languages + pr1_facts.md sections"


def load_forecast(cur):
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "reports/camtest/forecasts/*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        run = os.path.basename(f)[:10]
        for spot, s in d["spots"].items():
            rows.append((spot, run, s.get("latitude"), s.get("longitude"), s.get("elevation"),
                         Jsonb({"units": s.get("hourly_units"), "hourly": s["hourly"], "saved_utc": d.get("saved_utc"),
                                "timezone": s.get("timezone")}), "open_meteo"))
    cur.executemany("""INSERT INTO kb.forecast VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (spot, run_date) DO UPDATE SET hourly=EXCLUDED.hourly""", rows)
    return len(rows), "reports/camtest/forecasts/*.json"


def load_stations(cur):
    """Hourly IPMA readings of every Madeira / Porto Santo station; IPMA's API only holds the last 24 h."""
    base = "https://api.ipma.pt/open-data/observation/meteorology/stations/"
    st = json.loads(urllib.request.urlopen(base + "stations.json", timeout=60).read())
    mad = {f["properties"]["idEstacao"]: (f["properties"]["localEstacao"], *f["geometry"]["coordinates"][::-1])
           for f in st if 32.5 < f["geometry"]["coordinates"][1] < 33.2 and -17.4 < f["geometry"]["coordinates"][0] < -16.2}
    cur.executemany("""INSERT INTO kb.station VALUES (%s,%s,%s,%s)
                       ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, lat=EXCLUDED.lat, lon=EXCLUDED.lon""",
                    [(i, n, la, lo) for i, (n, la, lo) in mad.items()])
    obs = json.loads(urllib.request.urlopen(base + "observations.json", timeout=60).read())

    def v(r, k):
        x = r.get(k)
        return None if x is None or x <= -99 else x
    rows = []
    for t, by in obs.items():
        for sid, r in by.items():
            if r and int(sid) in mad:
                rows.append((int(sid), t + "Z", v(r, "temperatura"), v(r, "humidade"), v(r, "intensidadeVentoKM"),
                             v(r, "idDireccVento"), v(r, "pressao"), v(r, "precAcumulada"), v(r, "radiacao"), Jsonb(r)))
    cur.executemany("""INSERT INTO kb.station_obs VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (station_id, observed_at) DO UPDATE SET temp_c=EXCLUDED.temp_c,
                       humidity=EXCLUDED.humidity, wind_kmh=EXCLUDED.wind_kmh, wind_dir=EXCLUDED.wind_dir,
                       pressure_hpa=EXCLUDED.pressure_hpa, rain_mm=EXCLUDED.rain_mm, radiation=EXCLUDED.radiation,
                       raw=EXCLUDED.raw""", rows)
    return len(rows), f"IPMA observations, {len(mad)} stations, {len(obs)} hours"


LOADERS = {"sources": load_sources, "trails": load_trails, "status": load_status, "history": load_history,
           "fees": load_fees, "facts": load_facts, "transport": load_transport, "bus": load_bus, "docs": load_docs,
           "forecast": load_forecast, "stations": load_stations}
DAILY = ["sources", "status", "history", "forecast", "stations"]  # cron runs this every hour


def run(names):
    with psycopg.connect(db_url()) as conn:
        for name in names:
            with conn.transaction():
                with conn.cursor() as cur:
                    rows, detail = LOADERS[name](cur)
                    cur.execute("INSERT INTO kb.load_run (loader, rows, detail) VALUES (%s,%s,%s)", (name, rows, detail))
            print(f"{name:10s} {rows:6d}  {detail}")


def main(argv):
    if not argv:
        sys.exit(__doc__)
    if argv[0] == "init":
        with psycopg.connect(db_url(), autocommit=True) as conn:
            conn.execute(open(os.path.join(HERE, "schema.sql"), encoding="utf-8").read())
        print("schema kb applied")
        return
    names = list(LOADERS) if argv[0] == "all" else DAILY if argv[0] == "daily" else argv
    bad = [n for n in names if n not in LOADERS]
    if bad:
        sys.exit(f"unknown loader(s): {bad}")
    run(names)


if __name__ == "__main__":
    main(sys.argv[1:])
