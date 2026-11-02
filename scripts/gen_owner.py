#!/usr/bin/env python3
"""Say who is behind the site (owner, 2026-10-05).

Writes, between marker comments (idempotent, re-run any time):
  * OWNER-LINE  -- a last line inside every page's <footer>, in the page's language:
                   "© Mayke De Freitas Santos 2026. All Rights Reserved.
                   Enquiries: hello@levadinho-madeira.com" (a mailto link).
  * OWNER-SIG   -- the owner's name under "Why I built this" on the five homepages.
  * ENGAGE       -- the /engage.js script (cookie-free engagement events) and /alert.js (storm banner, 2026-10-10)
                   before </body> on every page with GoatCounter.
  * OWNER-SCHEMA -- a WebSite + Person JSON-LD block in the head of the five homepages (the WebSite carries the
                   site_entity.ENTITY sentence as its description) and the RSS link to trail-status.xml.
  * LANGMATCH    -- right after <meta charset> on every page that exists in all five languages (owner, 2026-11-02):
                   a visitor arriving from outside the site gets the same page in their browser's language (else
                   English, or the language they last picked on the switcher). Crawlers, visits from our own pages
                   and pages already in that language are left alone; GoatCounter keeps the original referrer.
                   Dry test 2 Nov: +37 ms (fast 4G) to +197 ms (slow 4G) to first paint, only when it switches.

Called by gen_spokes.py and gen_bus_hub.py after they rewrite pages. Skips bot/, the
trails/ forwarding stubs and the local-only folders.

    python scripts/gen_owner.py
"""

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from site_entity import ENTITY  # noqa: E402  (the one-sentence description, LLM audit item G)

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = "Mayke De Freitas Santos"
SKIP = ("bot", "seo_research", "reports", "google_search_console", "trails", ".git", ".claude", "q")

MAIL = '<a href="mailto:hello@levadinho-madeira.com" style="color:inherit">hello@levadinho-madeira.com</a>'
LINE = {
    "en": f"© {NAME} 2026. All Rights Reserved. Enquiries: {MAIL}",
    "pt": f"© {NAME} 2026. Todos os direitos reservados. Contactos: {MAIL}",
    "fr": f"© {NAME} 2026. Tous droits réservés. Contact : {MAIL}",
    "de": f"© {NAME} 2026. Alle Rechte vorbehalten. Anfragen: {MAIL}",
    "pl": f"© {NAME} 2026. Wszelkie prawa zastrzeżone. Kontakt: {MAIL}",
}
ABOUT = {"en": ("/about/", "About Levadinho"), "pt": ("/pt/about/", "Sobre o Levadinho"), "fr": ("/fr/about/", "À propos"),
         "de": ("/de/about/", "Über Levadinho"), "pl": ("/pl/about/", "O Levadinho")}   # footer link (LLM audit item H)
# Price disclaimer (owner, 2026-10-21): shown above the owner line on every page with a footer.
PRICES = {
    "en": "Prices and timetables come from the official operators and are checked regularly, but they can change without notice: please confirm them before you buy or book. We cannot be held accountable for any price discrepancy.",
    "pt": "Os preços e horários vêm dos operadores oficiais e são verificados regularmente, mas podem mudar sem aviso: confirme-os antes de comprar ou reservar. Não nos responsabilizamos por diferenças de preços.",
    "fr": "Les prix et horaires proviennent des opérateurs officiels et sont vérifiés régulièrement, mais ils peuvent changer sans préavis : confirmez-les avant d'acheter ou de réserver. Nous déclinons toute responsabilité en cas d'écart de prix.",
    "de": "Preise und Fahrpläne stammen von den offiziellen Betreibern und werden regelmäßig geprüft, können sich aber ohne Ankündigung ändern: Bitte bestätigen Sie sie vor jedem Kauf oder jeder Buchung. Für Preisabweichungen übernehmen wir keine Haftung.",
    "pl": "Ceny i rozkłady pochodzą od oficjalnych operatorów i są regularnie sprawdzane, ale mogą się zmienić bez zapowiedzi: potwierdź je przed zakupem lub rezerwacją. Nie odpowiadamy za rozbieżności cen.",
}
HOMES = {"index.html": "en", "pt/index.html": "pt", "fr/index.html": "fr", "de/index.html": "de", "pl/index.html": "pl"}
HOME_URL = {"en": "/", "pt": "/pt/", "fr": "/fr/", "de": "/de/", "pl": "/pl/"}
BASE = "https://levadinho-madeira.com"
LANGS = ("pt", "fr", "de", "pl")
LANGMATCH = r"""<script>
/* Levadinho: open the page in the visitor's language (owner, 2026-11-02, scripts/gen_owner.py). Runs first in <head>, before anything is drawn. */
(function () {
  try {
    var L = ["en", "pt", "fr", "de", "pl"], ss = window.sessionStorage, ls = window.localStorage;
    var keep = ss && ss.getItem("lv-ref");                 /* we switched: give GoatCounter the original referrer */
    if (keep !== null && keep !== undefined) { ss.removeItem("lv-ref"); window.goatcounter = window.goatcounter || {}; window.goatcounter.referrer = keep; return; }
    if (/bot|crawl|spider|slurp|preview|lighthouse|headless|google-|chatgpt|gptbot|oai-|perplexity|claude|bytespider|facebookexternalhit/i.test(navigator.userAgent)) return;
    var r = document.referrer;
    if (r && r.indexOf("//" + location.host + "/") > 0) return;   /* came from one of our pages (incl. the switcher) */
    var want = ls && ls.getItem("lv-lang");                    /* chosen on the switcher earlier */
    if (L.indexOf(want) < 0) {
      want = "en";
      var p = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || "en"];
      for (var i = 0; i < p.length; i++) { var c = String(p[i]).slice(0, 2).toLowerCase(); if (L.indexOf(c) >= 0) { want = c; break; } }
    }
    var m = location.pathname.match(/^\/(pt|fr|de|pl)(\/.*|$)/), have = m ? m[1] : "en", rest = m ? (m[2] || "/") : location.pathname;
    if (want === have) return;
    ss.setItem("lv-ref", r || "");
    location.replace((want === "en" ? "" : "/" + want) + rest + location.search + location.hash);
  } catch (e) {}
})();
document.addEventListener("click", function (e) {           /* remember a language picked on the switcher */
  var a = e.target.closest && e.target.closest(".langs a[hreflang]");
  if (a) try { localStorage.setItem("lv-lang", a.getAttribute("hreflang")); } catch (x) {}
});
</script>"""


def has_all_languages(rel):
    """True when the page exists at the same path in all five languages (the switch never lands on a missing page)."""
    parts = rel.parts[1:] if rel.parts[0] in LANGS else rel.parts
    return all((ROOT / pathlib.Path(*parts)).exists() and (ROOT / l / pathlib.Path(*parts)).exists() for l in LANGS)


def mark(key):
    return f"<!-- {key}:START (generated by scripts/gen_owner.py) -->", f"<!-- {key}:END -->"


def put(html, key, content, anchor_re, before=True):
    """Replace the marked block, or insert it before/after the first anchor match."""
    start, end = mark(key)
    block = start + content + end
    pat = re.compile(re.escape(start.split(" (")[0]) + r".*?" + re.escape(end), re.S)
    if pat.search(html):
        return pat.sub(lambda m: block, html, count=1)
    m = re.search(anchor_re, html)
    if not m:
        return html
    i = m.start() if before else m.end()
    return html[:i] + block + html[i:]


def schema(lang):
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": BASE + "/#website", "name": "Levadinho", "alternateName": "Levadinho Madeira",
             "url": BASE + HOME_URL[lang], "inLanguage": lang, "description": ENTITY[lang],
             "about": {"@type": "Place", "name": "Madeira", "containedInPlace": {"@type": "Country", "name": "Portugal"}},
             "publisher": {"@id": BASE + "/#owner"}},
            {"@type": "Person", "@id": BASE + "/#owner", "name": NAME, "url": BASE + "/"},
        ],
    }
    rss = (f'\n<link rel="alternate" type="application/rss+xml" title="Madeira trail status changes" '
           f'href="{BASE}/trail-status.xml">')
    return rss + '\n<script type="application/ld+json">\n' + json.dumps(data, ensure_ascii=False, indent=1) + "\n</script>\n"


def main():
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in SKIP or (len(rel.parts) > 1 and rel.parts[1] == "trails"):
            continue
        s = path.read_text(encoding="utf-8")
        if "</footer>" not in s:
            continue
        m = re.search(r"<html[^>]*\blang=[\"']?([a-zA-Z]{2})", s)
        lang = (m.group(1).lower() if m else "en")
        lang = lang if lang in LINE else "en"
        about = f' · <a href="{ABOUT[lang][0]}" style="color:inherit">{ABOUT[lang][1]}</a>'
        new = put(s, "OWNER-LINE", f'<span class="prices" style="display:block;margin-top:6px;opacity:.85">{PRICES[lang]}</span>'
                  f'<span class="owner" style="display:block;margin-top:6px">{LINE[lang]}{about}</span>',
                  r"</footer>")
        if "goatcounterCode" in new:  # engagement events (owner, 2026-10-07): /engage.js, sends only when GoatCounter loaded
            new = put(new, "ENGAGE", '<script src="/engage.js" defer></script><script src="/alert.js" defer></script>', r"</body>")
        if has_all_languages(rel):
            new = put(new, "LANGMATCH", "\n" + LANGMATCH + "\n", r'<meta charset="UTF-8">', before=False)
        if str(rel) in HOMES:
            new = put(new, "OWNER-SIG", f'<p class="sig" style="text-align:right;font-style:italic">— {NAME}</p>',
                      r'(?s)<div class="why">.*?</p>\s*', before=False)
            new = put(new, "OWNER-SCHEMA", schema(HOMES[str(rel)]), r"</head>")
        if new != s:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"gen_owner: {changed} page(s) updated")


if __name__ == "__main__":
    main()
