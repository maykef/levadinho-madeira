"""Build bot/kb.json — the per-trail and per-guide knowledge the Levadinho bot answers from.

Re-runnable. Takes the English pages of the site (already sourced: official facts, IFCN panels, SIGA bus
timetables, Portarias) and keeps their readable text: every trail page (facts, booking, start/finish,
by bus, tunnels/exposure, nearby trails…) and every guide page (fees, booking, permit, getting back,
buses, best/easy/tunnel lists…). Dropped: navigation, the WhatsApp block, webcams, scripts, and the
updater's STATIC-STATUS / STATIC-WEATHER lines (live status comes from status.json at answer time).

Re-run after the site's pages change (e.g. after gen_spokes.py / gen_bus.py / a copy edit), then restart
the webhook so brain.py reloads it.

Run from the repo root:  python3 bot/build_kb.py
"""
import html
import json
import os
import re
import time
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "bot", "kb.json")
SITE = "https://levadinho-madeira.com"

# guide key → (page, when the bot should read it). Keys are what brain.py's topic routing uses.
GUIDES = {
    "fees": "/hiking-fees.html",
    "permit": "/do-i-need-a-permit/",
    "booking": "/simplifica-booking/",
    "abroad": "/simplifica-from-abroad.html",
    "back": "/getting-back.html",
    "sunrise": "/pr1-sunrise-transport/",
    "oneway": "/pr1-one-way/",
    "weather": "/pico-do-areeiro-weather/",
    "free": "/free-walks/",
    "bus": "/levadas-by-bus/",
    "best": "/best-levada-walks/",
    "easy": "/easy-levadas-no-vertigo/",
    "tunnels": "/levadas-with-tunnels/",
}
# Marker pairs whose contents are dropped (generated chrome, stale-by-design status lines, webcams).
DROP = ["SITE-NAV", "SITE-NAV-GUIDES", "SITE-NAV-HEAD", "LEVADINHO-CTA", "LEVADINHO-CTA-HEAD", "WEBCAM",
        "WEBCAM-HEAD", "FTAB-HEAD", r"STATIC-STATUS(?::[A-Z0-9.]+)?", r"STATIC-STATUS-BOARD",
        r"STATIC-WEATHER(?::[A-Z0-9.]+)?", "STATIC-TRAIL-INDEX"]
SKIP_TAGS = {"script", "style", "head", "nav", "footer", "iframe", "svg", "noscript", "template"}
BLOCK = {"p", "div", "section", "article", "li", "tr", "dt", "dd", "br", "table", "ul", "ol", "header",
         "main", "aside", "figure", "figcaption", "blockquote", "details", "summary"}
HEAD = {"h1", "h2", "h3", "h4"}


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        if tag in SKIP_TAGS or (self.skip and tag not in ("br", "img", "meta", "link", "input")) \
                or re.search(r"\b(langs|crumbs|lvd-cta|tcam)\b", cls):
            if tag not in ("br", "img", "meta", "link", "input"):
                self.skip += 1
            return
        if tag in HEAD:
            self.out.append("\n\n## ")
        elif tag in ("td", "th"):
            self.out.append(" | ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if self.skip:
            if tag not in ("br", "img", "meta", "link", "input"):
                self.skip -= 1
            return
        if tag in HEAD or tag in BLOCK:
            self.out.append("\n")
        elif tag == "dt":
            self.out.append(": ")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def page_text(path):
    f = os.path.join(ROOT, path.strip("/"))
    f = f if f.endswith(".html") else os.path.join(f, "index.html")
    src = open(f, encoding="utf-8").read()
    for m in DROP:
        src = re.sub(rf"<!-- {m}:START -->.*?<!-- {m}:END -->", "", src, flags=re.S)
    src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    body = re.search(r"<body[^>]*>(.*)</body>", src, re.S).group(1)
    p = Text()
    p.feed(body)
    t = html.unescape("".join(p.out))
    t = re.sub(r"[ \t ]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n- \n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    # boilerplate lines that only make sense on the web page
    t = "\n".join(l for l in t.split("\n") if not re.match(
        r"(Photo|Photos|Image|Hero photo):|Levadinho · Madeira trail answers|More guides$|Closest trailheads", l))
    return t


def main():
    facts = json.load(open(os.path.join(ROOT, "bot", "trail_facts.json"), encoding="utf-8"))
    trails = {}
    for t in facts["trails"]:
        path = t["page"].replace(SITE, "")
        trails[t["code"]] = {"name": t["name"], "url": t["page"], "text": page_text(path)}
    guides = {k: {"url": SITE + p, "text": page_text(p)} for k, p in GUIDES.items()}
    kb = {"generated": time.strftime("%F"), "source": "English pages of levadinho-madeira.com",
          "trails": trails, "guides": guides}
    json.dump(kb, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sizes = sorted(((len(v["text"]), k) for k, v in {**trails, **guides}.items()), reverse=True)
    print(f"wrote {OUT}: {len(trails)} trails, {len(guides)} guides; largest: {sizes[:5]}; smallest: {sizes[-3:]}")


if __name__ == "__main__":
    main()
