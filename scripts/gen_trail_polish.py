#!/usr/bin/env python3
"""Trail-page polish after the generators (all trail pages, hand-authored and generated, 5 languages).

1. Trail code in the section headings (owner OK 2026-10-03, from the Gemini review):
   - weather question "What's the weather at Levada do Risco now?" -> "... at Levada do Risco (PR6.1) now?",
     changed everywhere it appears on the page, so the FAQPage question stays verbatim;
   - "By bus" -> "PR6.1 by bus" (gen_bus.py writes it that way too);
   - the facts sidebar headings: "Trail facts" -> "PR6.1 trail facts", "Trailhead" -> "PR6.1 trailhead".
   - the H1 starts with the code (owner OK 2026-10-10, weekly report fix 4): "Is the Levada do Rei open today?" ->
     "PR18: Is the Levada do Rei open today?", changed everywhere on the page (the same question is in the FAQ block
     and the FAQPage JSON-LD), so the FAQ stays verbatim. French keeps its space before the colon.
2. The main facts list in the sidebar becomes an HTML <table> (row headers + values), styled like the old
   <dl>; the TRAIL-EXTRAS list stays as it is. CSS between <!-- FTAB-HEAD --> markers.
Idempotent; gen_spokes.py calls it after the other generators.
"""
import glob, html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEATHER = {"en": r"What's the weather at (.+?) now\?", "pt": r"Como está o tempo (?:na|no|em) (.+?) agora\?",
           "fr": r"(.+?) : quelle météo maintenant \?", "de": r"(.+?): Wie ist das Wetter jetzt\?",
           "pl": r"(.+?): jaka jest teraz pogoda\?"}
SIDEBAR = {
    "en": {"Trail facts": "{c} trail facts", "Trailhead": "{c} trailhead"},
    "pt": {"Dados do percurso": "Dados do percurso {c}", "Ponto de partida": "Ponto de partida do {c}"},
    "fr": {"Infos sur le sentier": "Infos sur le sentier {c}", "Fiche du sentier": "Fiche du sentier {c}",
           "Point de départ": "Point de départ du {c}"},
    "de": {"Weg-Fakten": "Fakten zum {c}", "Wegdaten": "Wegdaten {c}", "Ausgangspunkt": "Ausgangspunkt des {c}",
           "Startpunkt": "Startpunkt des {c}"},
    "pl": {"Fakty o szlaku": "Fakty o szlaku {c}", "Informacje o szlaku": "Informacje o szlaku {c}",
           "Dane szlaku": "Dane szlaku {c}", "Początek szlaku": "Początek szlaku {c}"},
}
CSS = """<!-- FTAB-HEAD:START (scripts/gen_trail_polish.py) -->
<style>
.facts table.ftab{width:100%;border-collapse:collapse;font-size:14px;margin:0}
.facts table.ftab th{font-weight:400;color:var(--ink-soft);text-align:left;padding:2.5px 10px 2.5px 0;vertical-align:top}
.facts table.ftab td{font-weight:650;text-align:right;padding:2.5px 0;vertical-align:top}
</style>
<!-- FTAB-HEAD:END -->
"""


def bus_heading(code, text):
    return text if code in text else f"{code} {text[0].lower()}{text[1:]}"


def polish(h, lang, code):
    # 1a. weather question, everywhere on the page (visible heading, FAQ block, FAQPage JSON-LD)
    m = re.search(r'<section id="weather">\s*<h2>(' + WEATHER[lang] + r")</h2>", h)
    if m and code not in m.group(1):
        old, name = m.group(1), m.group(2)
        new = old.replace(name, f"{name} ({code})", 1)
        h = h.replace(old, new)
    # 1d. code first in the H1, everywhere the same question appears
    m = re.search(r"<h1>([^<]+)</h1>", h)
    if m and code not in m.group(1) and '<aside class="facts">' in h:  # trail pages only, not the sunrise guide
        old = m.group(1)
        new = f"{code} : {old}" if lang == "fr" else f"{code}: {old}"
        h = h.replace(old, new)
        raw_old, raw_new = html.unescape(old), html.unescape(new)
        if raw_old != old:
            h = h.replace(raw_old, raw_new)
    # 1b. bus heading
    h = re.sub(r'(<section id="bus">\s*<h2>)([^<]+)(</h2>)', lambda mm: mm.group(1) + bus_heading(code, mm.group(2)) + mm.group(3), h, count=1)
    # 1c. sidebar headings + 2. facts <dl> -> <table>
    i = h.find('<aside class="facts">')
    if i >= 0:
        j = h.find("</aside>", i)
        side = h[i:j]
        for old, new in SIDEBAR[lang].items():
            side = re.sub(r"(<h2(?: [^>]*)?>)" + re.escape(old) + r"(</h2>)", lambda mm: mm.group(1) + new.format(c=code) + mm.group(2), side)
        dl = re.search(r"  <dl>\n((?:    <dt>.*?</dt><dd>.*?</dd>\n)+)  </dl>\n", side)
        if dl:
            rows = re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", dl.group(1))
            table = '  <table class="ftab">\n' + "".join(
                f'    <tr><th scope="row">{k}</th><td>{v}</td></tr>\n' for k, v in rows) + "  </table>\n"
            side = side[:dl.start()] + table + side[dl.end():]
        h = h[:i] + side + h[j:]
    if 'class="ftab"' in h and "<!-- FTAB-HEAD:START" not in h:
        h = h.replace("</head>", CSS + "</head>", 1)
    return h


def main():
    os.chdir(ROOT)
    n = 0
    for f in sorted(glob.glob("**/*.html", recursive=True)):
        if f.split(os.sep)[0] in ("bot", "seo_research", "reports", "google_search_console", ".claude"):
            continue
        h = open(f, encoding="utf-8").read()
        m = re.search(r'id="statusCard"[^>]*data-trail="([^"]+)"', h)
        if not m or 'class="facts"' not in h and '<section id="bus">' not in h:
            continue
        lang = re.search(r'<html lang="([a-z]{2})', h).group(1)
        new = polish(h, lang, m.group(1))
        if new != h:
            open(f, "w", encoding="utf-8").write(new); n += 1
    print(f"trail pages polished: {n}")


if __name__ == "__main__":
    main()
