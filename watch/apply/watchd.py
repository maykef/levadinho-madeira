"""Levadinho watch: turn official notices into part closures of the Funchal promenade.

Two inputs, one classifier (classify.py):
  * a poll loop over watch/sources.json (the council's WordPress API, RSS, and Facebook /
    Instagram accounts through the RSSHub container), every `poll_minutes`;
  * a webhook, POST /cd, for changedetection.io alerts on pages without a feed
    (watch/watches.json: Câmara de Lobos news, Proteção Civil, the lidos' hours).

Outputs, in DATA_DIR (shaped like the backend's kb.notice table):
  notices.json            every applied notice (closure / sea-access restriction), with status
  promenade_status.json   the 8 areas now: open, or part-closed with the notices behind it
  review.jsonl            promenade-related items a person should read (press, unclear, hours)
  events.jsonl            log of everything that wasn't ignored
State (seen items) lives in STATE_DIR. GET / shows a short status page.

Rules: the promenade is always open; only an official notice that names an area and says
closed/reopened changes it. Storm closures without an end date expire after STORM_DAYS;
other open-ended closures stay until a reopening notice and go to review after STALE_DAYS.
"""
import datetime as dt
import html
import http.server
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import AREAS, classify, norm  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.environ.get("DATA_DIR", "/data")
STATE = os.environ.get("STATE_DIR", "/state")
RSSHUB = os.environ.get("RSSHUB", "http://rsshub:1200")
PORT = int(os.environ.get("PORT", "8080"))
FIRST_RUN_DAYS = 30      # on first sight of a source, read back this far
STORM_DAYS = 2
STALE_DAYS = 21
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
      "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"}
STORM = re.compile(r"agitacao maritima|mau tempo|tempestade|depressao|ondulacao|vento forte|aviso (amarelo|laranja|vermelho)")
LOCK = threading.Lock()
LAST = {"poll": None, "errors": {}}


def now():
    return dt.datetime.now(dt.timezone.utc)


def jload(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def jsave(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def append(name, rec):
    with open(os.path.join(DATA, name), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def text_of(s):
    s = re.sub(r"<(br|/p|/div|/li)[^>]*>", "\n", s or "", flags=re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def items_of(src):
    """[(item_id, posted_date, url, text)] newest first."""
    raw = fetch(src["url"].replace("{RSSHUB}", RSSHUB))
    out = []
    if src["type"] == "wp":
        for p in json.loads(raw):
            text = text_of(p["title"]["rendered"]) + "\n" + text_of(p.get("content", {}).get("rendered", ""))[:4000]
            out.append((str(p["id"]), dt.date.fromisoformat(p["date"][:10]), p["link"], text))
    else:
        root = ET.fromstring(raw)
        for it in root.iter("item"):
            g = (it.findtext("guid") or it.findtext("link") or it.findtext("title") or "").strip()
            pd = it.findtext("pubDate")
            try:
                posted = parsedate_to_datetime(pd).date() if pd else dt.date.today()
            except (TypeError, ValueError):
                posted = dt.date.today()
            text = text_of(it.findtext("title")) + "\n" + text_of(it.findtext("description"))[:4000]
            out.append((g, posted, (it.findtext("link") or "").strip(), text))
    return out


def area_by_id():
    return {a["id"]: a for a in AREAS["areas"]}


def record(src_id, src_name, official, item_id, posted, url, text):
    """Classify one item and update the notice store. Caller holds LOCK."""
    r = classify(text, official, posted)
    if r["decision"] == "ignore":
        return r
    ev = {"at": now().isoformat(timespec="seconds"), "source_id": src_id, "source": src_name, "official": official,
          "item": item_id, "posted": posted.isoformat(), "url": url, "text": text[:1200], **r}
    append("events.jsonl", ev)
    if r["decision"] == "review":
        append("review.jsonl", ev)
        return r
    notices = jload(os.path.join(DATA, "notices.json"), [])
    areas = area_by_id()
    t = norm(text)
    if r["action"] == "reopening":
        for n in notices:
            if n["status"] == "active" and n.get("area") in r["areas"]:
                n["status"], n["ends"], n["ended_by"] = "ended", posted.isoformat(), url
    else:
        ends = r["ends"]
        if not ends and STORM.search(t):
            ends = (posted + dt.timedelta(days=STORM_DAYS)).isoformat()
        subjects = [("sea-access", None)] if r["action"] == "sea_access" else [(areas[a]["slug"], a) for a in r["areas"]]
        for slug, a in subjects:
            nid = f"{src_id}:{item_id}:{slug}"
            if any(n["id"] == nid for n in notices):
                continue
            notices.append({
                "id": nid, "subject": f"promenade:{slug}", "area": a,
                "kind": "restriction" if a is None else "closure",
                "starts": r["starts"] or posted.isoformat(), "ends": ends,
                "text": {"pt": text[:1200]}, "source_id": src_id, "source": src_name, "url": url,
                "posted": posted.isoformat(), "checked_at": now().isoformat(timespec="seconds"), "status": "active"})
    write_status(notices)
    return r


def write_status(notices):
    today = dt.date.today().isoformat()

    def active(n):
        return (n["status"] == "active" and (n["starts"] or "") <= today
                and (not n["ends"] or n["ends"] >= today))

    for n in notices:   # open-ended non-storm closures: ask a person after STALE_DAYS
        if active(n) and not n["ends"] and not n.get("stale_flagged") and \
                n["posted"] < (dt.date.today() - dt.timedelta(days=STALE_DAYS)).isoformat():
            n["stale_flagged"] = True
            append("review.jsonl", {"at": now().isoformat(timespec="seconds"), "decision": "review",
                                    "reason": f"closure still open after {STALE_DAYS} days, no reopening seen", **n})
    jsave(os.path.join(DATA, "notices.json"), notices)
    cur = [n for n in notices if active(n)]
    out = {"generated": now().isoformat(timespec="seconds"),
           "note": "The promenade is always open; listed areas have a part closure from an official notice.",
           "areas": [], "sea_access": [
               {k: n[k] for k in ("starts", "ends", "source", "url")} for n in cur if n["area"] is None]}
    for a in AREAS["areas"]:
        ns = [n for n in cur if n["area"] == a["id"]]
        out["areas"].append({"id": a["id"], "slug": a["slug"], "name_pt": a["name_pt"], "name_en": a["name_en"],
                             "km": a["km"], "part_closed": bool(ns),
                             "notices": [{k: n[k] for k in ("starts", "ends", "source", "url")} for n in ns]})
    jsave(os.path.join(DATA, "promenade_status.json"), out)


def poll_once():
    cfg = jload(os.path.join(ROOT, "sources.json"), {"sources": []})
    seen_path = os.path.join(STATE, "seen.json")
    seen = jload(seen_path, {})
    for src in cfg["sources"]:
        try:
            items = items_of(src)
            LAST["errors"].pop(src["id"], None)
        except Exception as e:  # one broken source never stops the others
            LAST["errors"][src["id"]] = f"{type(e).__name__}: {e}"[:200]
            continue
        known = set(seen.get(src["id"], []))
        first = src["id"] not in seen
        cutoff = dt.date.today() - dt.timedelta(days=FIRST_RUN_DAYS)
        with LOCK:
            for item_id, posted, url, text in reversed(items):   # oldest first, so reopenings follow closures
                if item_id in known or (first and posted < cutoff):
                    known.add(item_id)
                    continue
                record(src["id"], src["name"], src["official"], item_id, posted, url, text)
                known.add(item_id)
        seen[src["id"]] = sorted(known)[-500:]
        jsave(seen_path, seen)
        time.sleep(5)
    with LOCK:
        write_status(jload(os.path.join(DATA, "notices.json"), []))
    LAST["poll"] = now().isoformat(timespec="seconds")


def poll_loop():
    while True:
        try:
            poll_once()
        except Exception:
            traceback.print_exc()
        minutes = jload(os.path.join(ROOT, "sources.json"), {}).get("poll_minutes", 45)
        time.sleep(minutes * 60)


def changedetection_alert(body):
    """Apprise json:// payload; message = our template: title / url / --- / added lines."""
    msg = body.get("message", "")
    lines = msg.split("\n")
    title, url = (lines + ["", ""])[0].strip(), (lines + ["", ""])[1].strip()
    added = "\n".join(lines[3:]).strip()
    m = re.match(r"\[(official|press|hours)\]\s*(.*)", title)
    kind, name = (m[1], m[2]) if m else ("press", title)
    item_id = f"cd:{int(time.time())}"
    with LOCK:
        if kind == "hours":
            rec = {"at": now().isoformat(timespec="seconds"), "decision": "review", "reason": "opening hours / prices changed",
                   "source": name, "url": url, "text": added[:1500]}
            append("events.jsonl", rec)
            append("review.jsonl", rec)
            return rec
        return record("cd:" + re.sub(r"\W+", "_", name.lower()).strip("_"), name, kind == "official",
                      item_id, dt.date.today(), url, added)


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            r = changedetection_alert(body) if self.path.startswith("/cd") else {"error": "unknown path"}
            self.send_response(200)
        except Exception as e:
            traceback.print_exc()
            r = {"error": str(e)}
            self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(r, ensure_ascii=False).encode())

    def do_GET(self):
        st = jload(os.path.join(DATA, "promenade_status.json"), {})
        lines = [f"levadinho watch · last poll {LAST['poll']}", ""]
        for a in st.get("areas", []):
            lines.append(f"{a['id']} {a['name_en']:34s} {'PART CLOSED' if a['part_closed'] else 'open'}")
        lines.append(f"sea access notes: {len(st.get('sea_access', []))}")
        try:
            with open(os.path.join(DATA, "review.jsonl"), encoding="utf-8") as f:
                lines.append(f"review log: {sum(1 for _ in f)} items")
        except FileNotFoundError:
            lines.append("review log: 0 items")
        for k, v in LAST["errors"].items():
            lines.append(f"ERROR {k}: {v}")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("\n".join(lines).encode())


def main():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(STATE, exist_ok=True)
    threading.Thread(target=poll_loop, daemon=True).start()
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
