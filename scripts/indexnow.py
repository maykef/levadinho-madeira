#!/usr/bin/env python3
"""Tell the IndexNow search engines (Bing, Yandex, Seznam, Naver, Yep, Internet Archive, Amazonbot; one
submission is shared with all of them) which pages changed. Google doesn't use IndexNow.
LLM audit item C, 2026-10-05. https://www.indexnow.org/documentation

  python scripts/indexnow.py          # the URLs update_status.py wrote to indexnow_urls.txt (the daily Action)
  python scripts/indexnow.py --all    # every URL in sitemap.xml (once, when the key first goes live)

The key isn't secret: IndexNow checks that https://levadinho-madeira.com/<KEY>.txt (committed at the repo root)
contains it. Run this only after GitHub Pages serves the new pages, or the engines fetch the old ones.
Never fails the Action: errors are printed and the exit code is 0.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

HOST = "levadinho-madeira.com"
KEY = "88c245a73d02fd6d11ed930f21f45079"
ENDPOINT = "https://api.indexnow.org/indexnow"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URLS_FILE = os.path.join(ROOT, "indexnow_urls.txt")


def sitemap_urls():
    return re.findall(r"<loc>([^<]+)</loc>", open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read())


def main():
    known = set(sitemap_urls())
    if "--all" in sys.argv:
        urls = sorted(known)
    else:
        if not os.path.exists(URLS_FILE):
            print("IndexNow: no indexnow_urls.txt, nothing changed")
            return
        urls = [u.strip() for u in open(URLS_FILE, encoding="utf-8") if u.strip() in known]
    if not urls:
        print("IndexNow: nothing to submit")
        return
    body = {"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls[:10000]}
    req = urllib.request.Request(ENDPOINT, json.dumps(body).encode(), {"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: HTTP {r.status}, {len(urls)} URL(s) submitted")
    except urllib.error.HTTPError as e:  # 400 bad request, 403 key not found/invalid, 422 wrong host, 429 too many
        print(f"IndexNow: HTTP {e.code} {e.reason}, {len(urls)} URL(s) not accepted")
    except OSError as e:
        print(f"IndexNow: request failed ({e})")


if __name__ == "__main__":
    main()
