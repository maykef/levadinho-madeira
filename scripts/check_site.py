#!/usr/bin/env python3
"""Site invariants (consolidation part C, owner 2026-10-21): the rules every published page must hold,
machine-checked instead of hand-audited. Run by the checks workflow on every push and by the daily
updater Action before it commits — a page that breaks these never publishes.

  sitemap    every <loc> has a real index file, and every published page is in the sitemap
             (404, privacy, the q/ QR redirects and the trails/ stubs are deliberately outside it)
  head       self-referencing canonical and the six hreflang alternates (en, pt, fr, de, pl, x-default)
  blocks     the Levadinho CTA block (gen_cta.py) on every page except privacy/404/stubs; the site nav
  faq        every FAQPage question's name appears VERBATIM in the page's visible text
             (the 2026-09-30 audit found 190 pages failing this before it became a rule)
  lengths    <title> <= 60 chars; meta description <= 175 (the updater prefixes trail pages with
             "IFCN: OPEN. ", so generation-time 120-155 plus the prefix must still fit)

Exit 0 = clean; exit 1 = violations, listed one per line.    python3 scripts/check_site.py
"""
import html as html_mod
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://levadinho-madeira.com"
SKIP_DIRS = {"bot", "backend", "scripts", "collect", "watch", "seo_research", "reports",
             "google_search_console", "history", "img", "gpx", "q", "trails", ".git", ".github", ".claude"}
NO_CTA = {"privacy", "404.html"}


def pages():
    """Every published page: (url path, file path)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        parts = [] if rel == "." else rel.split(os.sep)
        if parts and (parts[0] in SKIP_DIRS or (len(parts) > 1 and parts[1] in SKIP_DIRS)):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not (parts == [] and d in SKIP_DIRS) and not (len(parts) == 1 and d in SKIP_DIRS)]
        for fn in filenames:
            if not fn.endswith(".html") or fn == "googleea2064b7684c2bab.html":
                continue
            p = os.path.join(dirpath, fn)
            url = "/" + os.path.relpath(p, ROOT).replace(os.sep, "/")
            url = url[: -len("index.html")] if url.endswith("/index.html") else url
            out.append((url, p))
    return out


def plain(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    return " ".join(html_mod.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def main():
    bad = []
    say = bad.append
    sitemap = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    locs = {u[len(BASE):] for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)}

    all_pages = pages()
    for loc in sorted(locs):
        f = loc.rstrip("/") + "/index.html" if loc.endswith("/") else loc
        if not os.path.exists(os.path.join(ROOT, f.lstrip("/"))):
            say(f"sitemap: {loc} has no file")
    for u, _ in all_pages:
        if u in locs:
            continue
        if any(k in u for k in ("privacy", "404")):
            continue
        say(f"sitemap: {u} is published but not in the sitemap")

    for url, path in sorted(all_pages):
        s = open(path, encoding="utf-8").read()
        name = url
        skip_chrome = any(k in url for k in ("privacy", "404"))

        # head: canonical + hreflang
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        if not canon and not skip_chrome:
            say(f"{name}: no canonical")
        elif canon and canon.group(1).rstrip("/") != (BASE + url).rstrip("/") and not skip_chrome:
            say(f"{name}: canonical is {canon.group(1)}")
        if not skip_chrome:
            langs = set(re.findall(r'hreflang="([a-z-]+)"', s))
            missing = {"en", "pt", "fr", "de", "pl", "x-default"} - langs
            if missing:
                say(f"{name}: hreflang missing {sorted(missing)}")
            if "LEVADINHO-CTA:START" not in s and "LEVADINHO-CTA" not in s:
                say(f"{name}: no Levadinho CTA block")
            if "SITE-NAV" not in s:
                say(f"{name}: no site nav markers")

        # lengths
        t = re.search(r"<title>(.*?)</title>", s, re.S)
        if t and len(html_mod.unescape(t.group(1)).strip()) > 60:
            say(f"{name}: title {len(html_mod.unescape(t.group(1)).strip())} chars (> 60)")
        d = re.search(r'<meta name="description" content="([^"]*)"', s)
        if d and len(html_mod.unescape(d.group(1))) > 175:
            say(f"{name}: description {len(html_mod.unescape(d.group(1)))} chars (> 175)")

        # FAQ questions verbatim in the visible text
        text = None
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                data = json.loads(m.group(1))
            except ValueError:
                say(f"{name}: unparseable JSON-LD")
                continue
            for node in data if isinstance(data, list) else [data]:
                if isinstance(node, dict) and node.get("@type") == "FAQPage":
                    text = plain(s) if text is None else text
                    for q in node.get("mainEntity", []):
                        qname = " ".join(str(q.get("name", "")).split())
                        if qname and qname not in text:
                            say(f"{name}: FAQ question not verbatim on the page: {qname[:70]!r}")
    for line in bad:
        print(line)
    print(f"check_site: {len(all_pages)} pages, {len(bad)} violation(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
