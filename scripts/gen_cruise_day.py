#!/usr/bin/env python3
"""Large cruise ships in Funchal per day → /cruise.json on GitHub (owner, 2026-11-02).

Owner's rules: only the NUMBER of large ships and the expected number of people, never ship names; only ships of
1,500+ passengers count ("a 220-passenger expedition ship doesn't move the needle"). People = the ships' passenger
capacity (lower berths), labelled an estimate on the pages: capacity is not people on board.

Runs on the workstation (collect job cruise_day, after cruise_calls), because the APRAM schedule and the capacity
list live in the local seo_research/funchal/mobility/data/. It writes a local copy there and publishes /cruise.json
with the GitHub contents API (one-file commit, only when it changed), so the working tree is never touched; the
daily Action's update_funchal.py fills the STATIC-CRUISE lines on the pages from it.

A ship counts on a day when its stay overlaps 09:00-17:00 Madeira time that day.
  python3 scripts/gen_cruise_day.py [--no-publish]
"""
import base64
import datetime as dt
import json
import os
import subprocess
import sys
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "seo_research", "funchal", "mobility", "data")
LOCAL = os.path.join(DATA, "cruise_day.json")
REPO, PATH = "maykef/levadinho-madeira", "cruise.json"
MIN_CAPACITY = 1500
DAYS = 21
TZ = ZoneInfo("Atlantic/Madeira")


def capacities():
    cap = {s["ship"].upper(): s.get("capacity") for s in json.load(open(os.path.join(DATA, "ship_capacity.json")))["ships"]}
    manual = json.load(open(os.path.join(DATA, "ship_capacity_manual.json")))
    cap.update({k.upper(): v.get("capacity") for k, v in manual.items() if isinstance(v, dict)})
    return cap


def build(today):
    cap = capacities()
    calls = [c for c in json.load(open(os.path.join(DATA, "cruise_calls.json")))["calls"] if c["port"] == "Funchal"]
    days = []
    for i in range(DAYS):
        d = today + dt.timedelta(days=i)
        lo, hi = f"{d}T09:00", f"{d}T17:00"
        seen, people = set(), 0
        for c in calls:
            name = c["ship"].upper()
            if name in seen or not (c["arrival"][:16] < hi and c["departure"][:16] > lo):
                continue
            if (cap.get(name) or 0) >= MIN_CAPACITY:
                seen.add(name)
                people += cap[name]
        days.append({"date": d.isoformat(), "ships": len(seen), "people": round(people, -2)})
    return {"min_capacity": MIN_CAPACITY,
            "basis": "Large cruise ships (1,500+ passengers) in Funchal between 09:00 and 17:00; people = the ships' "
                     "passenger capacity, an estimate, not people on board. Source: APRAM port schedule.",
            "days": days}


def publish(body):
    gh = lambda *a: subprocess.run(["gh", "api", *a], capture_output=True, text=True)  # noqa: E731
    r = gh(f"repos/{REPO}/contents/{PATH}")
    sha, old = None, None
    if r.returncode == 0:
        j = json.loads(r.stdout)
        sha, old = j["sha"], base64.b64decode(j["content"]).decode()
    if old == body:
        return "unchanged"
    args = [f"repos/{REPO}/contents/{PATH}", "-X", "PUT", "-f", f"message=Cruise days update {dt.date.today()}",
            "-f", "content=" + base64.b64encode(body.encode()).decode()]
    r = gh(*args, *(["-f", f"sha={sha}"] if sha else []))
    if r.returncode != 0:
        sys.exit(f"publish failed: {r.stderr.strip()}")
    return "published"


def main():
    data = build(dt.datetime.now(TZ).date())
    body = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    open(LOCAL, "w", encoding="utf-8").write(body)
    state = "not published" if "--no-publish" in sys.argv else publish(body)
    t = data["days"][0]
    print(f"cruise days: today {t['ships']} large ships, ~{t['people']} people; {state}")


if __name__ == "__main__":
    main()
