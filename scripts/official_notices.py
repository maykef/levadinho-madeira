#!/usr/bin/env python3
"""Daily archive of every official announcement (owner, 2026-11-08 fire test: "all announcements from IFCN and IPMA
get scraped daily").

  - IFCN: every notice on the AVISOS category page (closures of single trails, forest roads, island-wide closures,
    works such as the PR8 requalification), read with storm.notices().
  - IPMA: every weather warning for Madeira (north coast, south coast, mountains, Porto Santo), yellow and up.

Each new item (not in the archive yet) is appended to /mnt/tank/levadinho/notices/{ifcn,ipma}.jsonl and listed in
reports/data/official_alert.md (read at the start of every Claude session) plus a fleet.event for the dashboard. This
job only records and tells; storm_watch (every 10 min) decides when the site update runs, and the update itself
re-reads IFCN and IPMA. Fails loud (exit 1) when a source can't be read, so the dashboard shows a red dot.
"""
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storm  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("NOTICES_DIR", "/mnt/tank/levadinho/notices")
ALERT_MD = os.path.join(ROOT, "reports", "data", "official_alert.md")
IPMA_AREAS = {"MCN": "north coast", "MCS": "south coast", "MRM": "mountains", "MPS": "Porto Santo"}


def seen(path):
    try:
        return {json.loads(l)["id"] for l in open(path, encoding="utf-8") if l.strip()}
    except OSError:
        return set()


def tell(lines):
    if not lines:
        return
    os.makedirs(os.path.dirname(ALERT_MD), exist_ok=True)
    fresh = not os.path.exists(ALERT_MD)
    with open(ALERT_MD, "a", encoding="utf-8") as f:
        if fresh:
            f.write("# Official notices (official_notices.py / official_alert.py)\n\n"
                    "Check IFCN / IPMA against the site status, then delete this file.\n\n")
        f.writelines(l + "\n" for l in lines)
    try:
        import psycopg
        sys.path.insert(0, os.path.join(ROOT, "seo_research", "funchal", "socialwatch", "db"))
        from swdb import db_url
        with psycopg.connect(db_url()) as c:
            for l in lines:
                c.execute("insert into fleet.event (at, name, what) values (now(), 'official-notice', %s)", (l[:200],))
    except Exception as e:  # noqa: BLE001
        print("fleet.event not written:", e, file=sys.stderr)


def main():
    os.makedirs(OUT, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    lines, n_new = [], {"ifcn": 0, "ipma": 0}

    # IFCN AVISOS (storm.notices exits non-zero when the page structure changed)
    path = os.path.join(OUT, "ifcn.jsonl")
    old = seen(path)
    items = storm.notices(storm._get(storm.IFCN_AVISOS_CAT, "STORM_FIXTURE_IFCN"))
    with open(path, "a", encoding="utf-8") as f:
        for text in items:
            body = re.sub(r"^.*?Categoria:\s*AVISOS\s*", "", text)[:4000]
            if "blog-items" in body or not re.search(r"Instituto|Institute|IFCN", body):
                continue                          # the list's wrapper, not a notice
            nid = hashlib.sha1(body[:600].encode()).hexdigest()[:16]
            if nid in old:
                continue
            kind = storm.classify(body) or "notice"
            f.write(json.dumps({"id": nid, "first_seen": now, "kind": kind, "text": body,
                                "source": storm.IFCN_AVISOS_CAT}, ensure_ascii=False) + "\n")
            n_new["ifcn"] += 1
            lines.append(f"- {now} IFCN notice ({kind}): {body[:300]}")

    # IPMA warnings (yellow and up, all Madeira areas)
    path = os.path.join(OUT, "ipma.jsonl")
    old = seen(path)
    data = json.loads(storm._get(storm.IPMA_WARNINGS, "STORM_FIXTURE_IPMA"))
    with open(path, "a", encoding="utf-8") as f:
        for w in data:
            if w.get("idAreaAviso") not in IPMA_AREAS or w.get("awarenessLevelID") in (None, "green"):
                continue
            key = f"{w['idAreaAviso']}|{w.get('awarenessTypeName')}|{w.get('awarenessLevelID')}|{w['startTime']}|{w['endTime']}"
            nid = hashlib.sha1(key.encode()).hexdigest()[:16]
            if nid in old:
                continue
            rec = {"id": nid, "first_seen": now, "area": IPMA_AREAS[w["idAreaAviso"]], "type": w.get("awarenessTypeName"),
                   "level": w.get("awarenessLevelID"), "start": w["startTime"], "end": w["endTime"],
                   "text": w.get("text") or "", "source": storm.IPMA_PAGE}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n_new["ipma"] += 1
            lines.append(f"- {now} IPMA {rec['level']} warning, {rec['area']}: {rec['type']} {rec['start']}→{rec['end']} "
                         f"{rec['text']}".rstrip())

    # IPMA's 5-day forecast for the card's five places + its outlook, one snapshot per run (how early IPMA called it)
    try:
        import ipma_forecast
        fc = ipma_forecast.fetch()
        with open(os.path.join(OUT, "forecast.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": now, "forecast": fc, "outlook": ipma_forecast.outlook(fc, storm.ipma_alert().get("all", []))},
                               ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        print("forecast snapshot failed:", e, file=sys.stderr)

    if "--seed" in sys.argv:                      # first run: archive what is already out, tell nobody
        lines = []
    tell(lines)
    print(f"notices: IFCN {len(items)} on the page ({n_new['ifcn']} new), IPMA {n_new['ipma']} new warning(s)")
    print(f"ROWS {n_new['ifcn'] + n_new['ipma']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
