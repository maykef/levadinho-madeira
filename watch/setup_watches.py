"""Create / update the changedetection.io watches from watch/watches.json (idempotent; matches by URL).
Run on the host after `docker compose up -d`: python3 watch/setup_watches.py
Removes watches not in the file (a fresh install ships two examples)."""
import json
import os
import subprocess
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "http://127.0.0.1:18401/api/v1"
NOTIFY = ["json://lw-apply:8080/cd"]
BODY = "{{watch_title}}\n{{watch_url}}\n---\n{{diff_added}}"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
      "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"}


def key():
    for _ in range(30):
        try:   # the datastore is root-owned, so read it through the container
            raw = subprocess.run(["docker", "exec", "lw-changedetection", "cat", "/datastore/changedetection.json"],
                                 capture_output=True, check=True).stdout
            return json.loads(raw)["settings"]["application"]["api_access_token"]
        except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError):
            time.sleep(2)
    raise SystemExit("changedetection datastore not found: is the container up?")


def call(method, path, data=None):
    req = urllib.request.Request(API + path, method=method, headers={"x-api-key": K, "Content-Type": "application/json"},
                                 data=json.dumps(data).encode() if data is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode()
    return json.loads(body) if body.strip().startswith(("{", "[")) else body


K = key()
cfg = json.load(open(os.path.join(HERE, "watches.json"), encoding="utf-8"))
existing = call("GET", "/watch")
by_url = {w["url"]: uuid for uuid, w in existing.items()}
wanted = set()
for w in cfg["watches"]:
    rx = cfg.get(w["extract"] + "_regex", w["extract"])
    d = {"url": w["url"], "title": w["title"],
         "fetch_backend": "html_webdriver" if w["browser"] else "html_requests",
         "extract_text": [rx], "trim_text_whitespace": True,
         "notification_urls": NOTIFY, "notification_format": "text",
         "notification_title": "{{watch_title}}", "notification_body": BODY,
         "time_between_check": {"weeks": 0, "days": 0, "hours": w["hours"], "minutes": 0, "seconds": 0},
         "time_between_check_use_default": False}
    if not w["browser"]:
        d["headers"] = UA
    wanted.add(w["url"])
    if w["url"] in by_url:
        call("PUT", f"/watch/{by_url[w['url']]}", d)
        print("updated", w["title"])
    else:
        print("created", w["title"], call("POST", "/watch", d))
for url, uuid in by_url.items():
    if url not in wanted:
        call("DELETE", f"/watch/{uuid}")
        print("removed", url)
