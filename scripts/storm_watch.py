#!/usr/bin/env python3
"""Storm watch (host side, 2026-10-10): decides when to run the site update outside its daily schedule.

The daily Action starts 4-6 h late, so on storm days the board would lag. Every 10 minutes (collect/ job
storm_watch) this script compares what the official sources say with what the live site shows and, when they
differ or a warning is active, starts the update workflow (`gh workflow run update.yml`). The Action itself
re-reads the official sources (scripts/storm.py): this script only decides *when*, never *what*.

Signals:
  - IFCN AVISOS page (storm.blanket): closure / reopening notices;
  - IPMA warnings (storm.ipma_alert): orange/red for Madeira now or within 24 h;
  - IFCN Facebook + Instagram and Protecção Civil Facebook through the watcher's RSSHub (watch/, 127.0.0.1:18402):
    a post saying all classified trails close/reopen often comes before the website notice, so it starts a run
    and keeps retrying every 15 min for 3 h until the site has it (social posts never change a status by themselves).
  - IFCN's dated closures of single trails (storm.trail_closures, 2026-10-11): a new notice, the flip from "announced"
    to "closed" just after midnight on a closure day, and the day after the last one;
  - the live https://levadinho-madeira.com/status.json "alert" block and trails[].closure.

Rules: trigger when the site's blanket state or IPMA level differs from the sources; while any alert is active,
at least once an hour (fresh weather, the midnight flip from "announced" to "closed"); never more often than every
15 minutes. --dry-run prints the decision and triggers nothing (add --log to keep it in the log: shadow mode). State + log: /mnt/tank/levadinho/storm/.
"""
import datetime
import html
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storm  # noqa: E402
import ipma_forecast  # noqa: E402  "bad weather coming" outlook (2026-11-08)

REPO = "maykef/levadinho-madeira"
SITE_STATUS = "https://levadinho-madeira.com/status.json"
RSSHUB = os.environ.get("RSSHUB_URL", "http://127.0.0.1:18402")
# IFCN Instagram: RSSHub needs a login since 2026-10-08 (503); the phone capture writes this feed (watch/ig_feeds.py)
IG_FEED = "file://" + os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "watch", "state", "feeds",
                                   "instagram_ifcn_madeira.xml")
SOCIAL = [("IFCN Facebook", "/facebook/page/IFCNIP"), ("IFCN Instagram", IG_FEED),
          ("Protecção Civil Facebook", "/facebook/page/procivmadeira")]
SOCIAL_FRESH_H = 3
MIN_GAP_MIN, ACTIVE_EVERY_MIN = 15, 60
DIR = os.environ.get("STORM_DIR", "/mnt/tank/levadinho/storm")
STATE, LOG = os.path.join(DIR, "state.json"), os.path.join(DIR, "watch.jsonl")
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStormWatch/1.0; +https://levadinho-madeira.com)"}


def get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8", "replace")


BACKOFF = os.path.join(DIR, "rsshub_backoff.json")
BACKOFF_H = 3      # owner, 2026-10-12: Facebook rate-limited the home IP; after a failed RSSHub fetch, rest that page 3 h


def social_signals(now):
    """Posts from the last SOCIAL_FRESH_H hours that say all classified trails close / reopen."""
    out, errors = [], []
    try:
        rest = json.load(open(BACKOFF))
    except Exception:
        rest = {}
    for name, route in SOCIAL:
        if not route.startswith("file://") and rest.get(route, "") > now.isoformat():
            errors.append(f"{name}: resting until {rest[route][:16]} after a failed fetch")
            continue
        try:
            xml = get(route if route.startswith("file://") else RSSHUB + route, timeout=90)
        except Exception as e:
            errors.append(f"{name}: {e}")
            if not route.startswith("file://"):
                rest[route] = (now + datetime.timedelta(hours=BACKOFF_H)).isoformat(timespec="seconds")
                try:
                    json.dump(rest, open(BACKOFF, "w"))
                except Exception:
                    pass
            continue
        for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
            m = re.search(r"<pubDate>(.*?)</pubDate>", item)
            if not m:
                continue
            posted = datetime.datetime.strptime(m.group(1).strip(), "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=datetime.UTC)
            if now - posted > datetime.timedelta(hours=SOCIAL_FRESH_H):
                continue
            body = re.search(r"<description>(.*?)</description>", item, re.S)
            text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(body.group(1) if body else ""))))
            kind = storm.classify(text)
            if kind:
                link = re.search(r"<link>(.*?)</link>", item)
                out.append({"source": name, "kind": kind, "posted": posted.isoformat(), "link": link.group(1) if link else "",
                            "text": text[:200]})
    return out, errors


# Changes between IFCN notices (owner, 2026-11-09: "the thing to monitor is changes between notices"; IFCN's notices
# have no dates and pile events into one text, and the 9 Nov reopening was prepended to its standing list). Every run
# splits IFCN's AVISOS page into announcements (each "O Instituto das Florestas…" / "O IFCN informa…" sentence group)
# and compares them with the previous run: a new or removed announcement is archived in notices/ifcn.jsonl, written to
# reports/data/official_alert.md (read at every session start) and starts the site update.
NOTICES_ARCHIVE = "/mnt/tank/levadinho/notices/ifcn.jsonl"
SEEN = os.path.join(DIR, "ifcn_announcements.json")
ALERT_MD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "data", "official_alert.md")


def announcements(page_html):
    out = {}
    for item in storm.notices(page_html):
        body = re.sub(r"^.*?Categoria:\s*AVISOS\s*", "", item)
        if not re.search(r"Instituto|Institute|IFCN", body):
            continue
        body = re.split(r"O\s+IFCN\s+informa\s+que\s+os\s+seguintes\s+percursos", body)[0]   # the standing list itself: not an announcement
        for part in storm.ANNOUNCE_SPLIT.split(body):
            part = re.sub(r"\s+", " ", part).strip()
            if len(part) > 60 and re.match(r"(O\s+Instituto|O\s+IFCN)", part):
                out[hashlib.sha1(part[:500].encode()).hexdigest()[:16]] = part
    return out


def track_announcements(now, dry):
    """-> list of change lines ('new: …' / 'removed: …'); [] when nothing changed or the page can't be read."""
    try:
        cur = announcements(storm._get(storm.IFCN_AVISOS_CAT, "STORM_FIXTURE_IFCN"))
    except (Exception, SystemExit) as e:  # noqa: BLE001
        print("announcements: IFCN page unreadable:", e, file=sys.stderr)
        return []
    try:
        old = json.load(open(SEEN))
    except (OSError, ValueError):
        old = None
    if dry:
        return []
    json.dump(cur, open(SEEN, "w"), ensure_ascii=False, indent=1)
    if old is None:                       # first run: baseline only
        return []
    changes = [("new", k, v) for k, v in cur.items() if k not in old] + [("removed", k, v) for k, v in old.items() if k not in cur]
    if not changes:
        return []
    stamp = now.isoformat(timespec="seconds")
    with open(NOTICES_ARCHIVE, "a", encoding="utf-8") as f:
        for what, k, v in changes:
            f.write(json.dumps({"id": k, "first_seen" if what == "new" else "removed_at": stamp, "kind": storm.classify(v) or "notice",
                                "change": what, "text": v, "source": storm.IFCN_AVISOS_CAT}, ensure_ascii=False) + "\n")
    os.makedirs(os.path.dirname(ALERT_MD), exist_ok=True)
    fresh = not os.path.exists(ALERT_MD)
    with open(ALERT_MD, "a", encoding="utf-8") as f:
        if fresh:
            f.write("# Official notices (official_notices.py / official_alert.py / storm_watch.py)\n\n"
                    "Check IFCN / IPMA against the site status, then delete this file.\n\n")
        for what, _k, v in changes:
            f.write(f"- {stamp} IFCN announcement {what.upper()} ({storm.classify(v) or 'notice'}): {v[:400]}\n")
    return [f"{what}: {v[:120]}" for what, _k, v in changes]


def main(dry):
    now = datetime.datetime.now(datetime.UTC)
    os.makedirs(DIR, exist_ok=True)
    state = {}
    if os.path.exists(STATE):
        state = json.load(open(STATE))
    rec = {"at": now.isoformat(timespec="seconds")}
    try:
        b = storm.blanket()
    except SystemExit as e:                  # page unreadable: no decision from IFCN this round
        b = {"state": "unknown"}
        rec["ifcn_error"] = str(e)
    except Exception as e:
        b = {"state": "unknown"}
        rec["ifcn_error"] = repr(e)
    try:
        closures = storm.trail_closures()      # same page as blanket(), fetched once
    except SystemExit as e:                  # a future closure whose dates can't be read: the Action would fail too
        closures = None
        rec["closures_error"] = str(e)
    except Exception as e:
        closures = None
        rec["closures_error"] = repr(e)
    ipma = storm.ipma_alert()
    social, social_err = social_signals(now)
    try:
        site_all = json.loads(get(SITE_STATUS))
        site = site_all.get("alert") or {}
    except Exception as e:
        site_all = site = None
        rec["site_error"] = repr(e)
    board = {t["code"]: t for t in (site_all or {}).get("trails", [])}
    src_cl = sorted({(code, c["state"], json.dumps(c["ranges"])) for c in (closures or []) for code in c["codes"]
                     if code in board})
    site_cl = sorted({(code, t["closure"]["state"], json.dumps(t["closure"]["ranges"])) for code, t in board.items()
                      if t.get("closure")})

    rec.update(ifcn=b.get("state"), ipma=ipma.get("level") if ipma.get("ok") else "unknown",
               social=[f"{s['source']}:{s['kind']}" for s in social], site_blanket=(site or {}).get("blanket"),
               site_ipma=(site or {}).get("ipma_level"),
               closures=[f"{c}:{s}" for c, s, _r in src_cl] if closures is not None else "unknown",
               site_closures=[f"{c}:{s}" for c, s, _r in site_cl])
    if social_err:
        rec["social_errors"] = social_err

    # IPMA's "bad weather coming" outlook (owner, 2026-11-08): the bad days the forecast shows now vs the site's.
    try:
        src_out = ipma_forecast.outlook(ipma_forecast.fetch(), ipma.get("all") if ipma.get("ok") else [])
        src_days = [(d["date"], d["reasons"]) for d in (src_out or {}).get("days", [])]
    except Exception as e:  # noqa: BLE001
        src_days = None
        rec["outlook_error"] = repr(e)
    site_days = [(d["date"], d["reasons"]) for d in ((site_all or {}).get("outlook") or {}).get("days", [])]
    rec.update(outlook=[d for d, _r in src_days] if src_days is not None else "unknown", site_outlook=[d for d, _r in site_days])

    reasons = []
    ann = track_announcements(now, dry)
    if ann:
        rec["ifcn_changes"] = ann
        reasons.append(f"IFCN announcements changed: {len(ann)}")
    if site is not None and src_days is not None and src_days != site_days:
        reasons.append(f"IPMA outlook {[d for d, _r in src_days]} vs site {[d for d, _r in site_days]}")
    if site is not None:
        if b.get("state") != "unknown" and b.get("state") != site.get("blanket"):
            reasons.append(f"IFCN blanket {b.get('state')} vs site {site.get('blanket')}")
        if ipma.get("ok") and ipma.get("level") != site.get("ipma_level"):
            reasons.append(f"IPMA {ipma.get('level')} vs site {site.get('ipma_level')}")
        if closures is not None and src_cl != site_cl:
            reasons.append(f"IFCN trail closures {[c[:2] for c in src_cl]} vs site {[c[:2] for c in site_cl]}")
    for s in social:
        site_closed = (site or {}).get("blanket") in ("closed", "announced")
        if (s["kind"] == "closure") != site_closed:
            reasons.append(f"{s['source']} says {s['kind']} ({s['posted']})")
    active = b.get("state") in ("closed", "announced") or (ipma.get("ok") and ipma.get("level")) or bool(src_days)
    last = state.get("last_trigger")
    mins = (now - datetime.datetime.fromisoformat(last)).total_seconds() / 60 if last else 1e9
    if active and mins >= ACTIVE_EVERY_MIN:
        reasons.append(f"alert active, last run {int(mins) if last else 'never'} min ago")
    go = bool(reasons) and mins >= MIN_GAP_MIN
    rec.update(reasons=reasons, trigger=go and not dry, dry_run=dry)

    if go and not dry:
        r = subprocess.run(["gh", "workflow", "run", "update.yml", "-R", REPO], capture_output=True, text=True, timeout=60)
        rec["gh"] = (r.returncode, (r.stdout + r.stderr).strip()[:200])
        if r.returncode == 0:
            state["last_trigger"] = now.isoformat()
    state["last_check"] = rec
    if not dry:
        json.dump(state, open(STATE, "w"), indent=1)
    if not dry or "--log" in sys.argv:            # --dry-run --log = shadow mode: decisions logged, nothing triggered
        with open(LOG, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
