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
  - the live https://levadinho-madeira.com/status.json "alert" block.

Rules: trigger when the site's blanket state or IPMA level differs from the sources; while any alert is active,
at least once an hour (fresh weather, the midnight flip from "announced" to "closed"); never more often than every
15 minutes. --dry-run prints the decision and triggers nothing (add --log to keep it in the log: shadow mode). State + log: /mnt/tank/levadinho/storm/.
"""
import datetime, html, json, os, re, subprocess, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storm  # noqa: E402

REPO = "maykef/levadinho-madeira"
SITE_STATUS = "https://levadinho-madeira.com/status.json"
RSSHUB = os.environ.get("RSSHUB_URL", "http://127.0.0.1:18402")
SOCIAL = [("IFCN Facebook", "/facebook/page/IFCNIP"), ("IFCN Instagram", "/instagram/user/ifcn_madeira"),
          ("Protecção Civil Facebook", "/facebook/page/procivmadeira")]
SOCIAL_FRESH_H = 3
MIN_GAP_MIN, ACTIVE_EVERY_MIN = 15, 60
DIR = os.environ.get("STORM_DIR", "/mnt/tank/levadinho/storm")
STATE, LOG = os.path.join(DIR, "state.json"), os.path.join(DIR, "watch.jsonl")
UA = {"User-Agent": "Mozilla/5.0 (compatible; LevadinhoStormWatch/1.0; +https://levadinho-madeira.com)"}


def get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8", "replace")


def social_signals(now):
    """Posts from the last SOCIAL_FRESH_H hours that say all classified trails close / reopen."""
    out, errors = [], []
    for name, route in SOCIAL:
        try:
            xml = get(RSSHUB + route, timeout=90)
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue
        for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
            m = re.search(r"<pubDate>(.*?)</pubDate>", item)
            if not m:
                continue
            posted = datetime.datetime.strptime(m.group(1).strip(), "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=datetime.timezone.utc)
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


def main(dry):
    now = datetime.datetime.now(datetime.timezone.utc)
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
    ipma = storm.ipma_alert()
    social, social_err = social_signals(now)
    try:
        site = json.loads(get(SITE_STATUS)).get("alert") or {}
    except Exception as e:
        site = None
        rec["site_error"] = repr(e)

    rec.update(ifcn=b.get("state"), ipma=ipma.get("level") if ipma.get("ok") else "unknown",
               social=[f"{s['source']}:{s['kind']}" for s in social], site_blanket=(site or {}).get("blanket"),
               site_ipma=(site or {}).get("ipma_level"))
    if social_err:
        rec["social_errors"] = social_err

    reasons = []
    if site is not None:
        if b.get("state") != "unknown" and b.get("state") != site.get("blanket"):
            reasons.append(f"IFCN blanket {b.get('state')} vs site {site.get('blanket')}")
        if ipma.get("ok") and ipma.get("level") != site.get("ipma_level"):
            reasons.append(f"IPMA {ipma.get('level')} vs site {site.get('ipma_level')}")
    for s in social:
        site_closed = (site or {}).get("blanket") in ("closed", "announced")
        if (s["kind"] == "closure") != site_closed:
            reasons.append(f"{s['source']} says {s['kind']} ({s['posted']})")
    active = b.get("state") in ("closed", "announced") or (ipma.get("ok") and ipma.get("level"))
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
