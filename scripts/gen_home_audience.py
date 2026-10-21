#!/usr/bin/env python3
"""The homepage's two-audience block (owner, 2026-10-21: "the landing page is too trails centric … information
for both demographics"). Injected into the five homepages between HOME-AUDIENCE markers, right after the weather
strip and before the trail search: two cards side by side (stacked on phones) —

  Here to hike        the owner's top 5 trails, each with a live STATIC-BADGE status word
                      (prefilled from status.json here, refreshed daily by the updater like the board's badges)
  Here for a day or two   the cruise/short-stay cluster: one day, two days, cruise port, Monte,
                      Botanical Garden, the short PR1 walk, Funchal today

The live board below stays untouched — it is the ranking asset. Idempotent; re-run after changing the lists.
    python3 scripts/gen_home_audience.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_trail_index import STATUS_WORD  # noqa: E402  (the board's localized status words)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOMES = {"en": "index.html", "pt": "pt/index.html", "fr": "fr/index.html", "de": "de/index.html", "pl": "pl/index.html"}
PREFIX = {"en": "", "pt": "/pt", "fr": "/fr", "de": "/de", "pl": "/pl"}

# the owner's top 5 (2026-10-21): four classics + one easy, deliberately
TRAILS = [
    ("PR1", "/pr1/", {"en": "PR1 Areeiro → Pico Ruivo", "pt": "PR1 Areeiro → Pico Ruivo", "fr": "PR1 Areeiro → Pico Ruivo",
                      "de": "PR1 Areeiro → Pico Ruivo", "pl": "PR1 Areeiro → Pico Ruivo"}),
    ("PR6", "/25-fontes/", {"en": "25 Fontes (PR6)", "pt": "25 Fontes (PR6)", "fr": "25 Fontes (PR6)",
                            "de": "25 Fontes (PR6)", "pl": "25 Fontes (PR6)"}),
    ("PR9", "/caldeirao-verde/", {"en": "Caldeirão Verde (PR9)", "pt": "Caldeirão Verde (PR9)", "fr": "Caldeirão Verde (PR9)",
                                  "de": "Caldeirão Verde (PR9)", "pl": "Caldeirão Verde (PR9)"}),
    ("PR8", "/sao-lourenco/", {"en": "Ponta de São Lourenço (PR8)", "pt": "Ponta de São Lourenço (PR8)",
                               "fr": "Ponta de São Lourenço (PR8)", "de": "Ponta de São Lourenço (PR8)",
                               "pl": "Ponta de São Lourenço (PR8)"}),
    ("PR11", "/balcoes/", {"en": "Balcões (PR11, the easy one)", "pt": "Balcões (PR11, o fácil)",
                           "fr": "Balcões (PR11, le facile)", "de": "Balcões (PR11, der leichte)",
                           "pl": "Balcões (PR11, ten łatwy)"}),
]

DAY = [
    ("/one-day-in-madeira/", {"en": "One day in Madeira: the top 5", "pt": "Um dia na Madeira: o top 5",
                              "fr": "Madère en un jour : le top 5", "de": "Ein Tag auf Madeira: die Top 5",
                              "pl": "Jeden dzień na Maderze: top 5"}),
    ("/two-days-in-madeira/", {"en": "Two days: the timed itinerary", "pt": "Dois dias: roteiro com horários",
                               "fr": "Deux jours : l'itinéraire minuté", "de": "Zwei Tage: Route mit Uhrzeiten",
                               "pl": "Dwa dni: plan z godzinami"}),
    ("/madeira-cruise-port/", {"en": "From the cruise port", "pt": "Do porto de cruzeiros",
                               "fr": "Depuis le port de croisière", "de": "Vom Kreuzfahrthafen",
                               "pl": "Z portu wycieczkowego"}),
    ("/monte/", {"en": "Monte: cable car, palace, toboggans", "pt": "Monte: teleférico, palácio, carros de cesto",
                 "fr": "Monte : téléphérique, palais, luges", "de": "Monte: Seilbahn, Palast, Schlitten",
                 "pl": "Monte: kolejka, pałac, sanie"}),
    ("/botanical-garden/", {"en": "The Botanical Garden: worth it?", "pt": "O Jardim Botânico: vale a pena?",
                            "fr": "Le Jardin botanique : ça vaut le coup ?", "de": "Der Botanische Garten: lohnt er sich?",
                            "pl": "Ogród Botaniczny: czy warto?"}),
    ("/areeiro-pedra-rija/", {"en": "The short PR1 walk, €4.50", "pt": "O PR1 curto, 4,50 €",
                              "fr": "Le PR1 court, 4,50 €", "de": "Der kurze PR1, 4,50 €",
                              "pl": "Krótki PR1, 4,50 €"}),
    ("/funchal/", {"en": "Funchal today", "pt": "Funchal hoje", "fr": "Funchal aujourd'hui",
                   "de": "Funchal heute", "pl": "Funchal dziś"}),
]

H = {
    "en": ("Here to hike", "Here for a day or two", "All 37 trails on the live board below.", "Best levada walks"),
    "pt": ("Veio para caminhar", "Veio por um dia ou dois", "Os 37 percursos no quadro em direto abaixo.", "Melhores levadas"),
    "fr": ("Ici pour randonner", "Ici pour un jour ou deux", "Les 37 sentiers sur le tableau en direct ci-dessous.", "Meilleures levadas"),
    "de": ("Zum Wandern hier", "Für ein, zwei Tage hier", "Alle 37 Wege auf dem Live-Board unten.", "Schönste Levadas"),
    "pl": ("Tu, by wędrować", "Tu na dzień lub dwa", "Wszystkie 37 szlaków na tablicy na żywo poniżej.", "Najlepsze lewady"),
}
BEST = "/best-levada-walks/"
MARK = ("<!-- HOME-AUDIENCE:START (generated by scripts/gen_home_audience.py) -->", "<!-- HOME-AUDIENCE:END -->")
ANCHOR = '<div class="weather" id="weatherStrip"></div>'

CSS = ('<style>.aud{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:14px 0}'
       '@media(max-width:719px){.aud{grid-template-columns:1fr}}'
       '.aud .card{background:var(--card,#fffdf6);border:1px solid rgba(27,58,45,.18);border-radius:10px;padding:14px 16px}'
       '.aud h2{margin:0 0 8px;font-size:1.05rem}'
       '.aud ul{margin:0;padding-left:1.1em}.aud li{margin:4px 0}'
       '.aud .st{font-size:.78em;letter-spacing:.02em;opacity:.75;white-space:nowrap}'
       '.aud .foot{margin:8px 0 0;font-size:.88em;opacity:.85}</style>')


def badge(code, status, lang):
    word = STATUS_WORD[lang if lang != "en" else ""].get(status, "")
    return ('<span class="st"><!-- STATIC-BADGE:{c}:START -->{w}<!-- STATIC-BADGE:{c}:END --></span>'
            .format(c=code, w=": " + word if word else ""))


def main():
    status = json.load(open(os.path.join(ROOT, "status.json"), encoding="utf-8"))
    by_code = {t["code"]: t.get("status") for t in status.get("trails", [])}
    for lang, rel in HOMES.items():
        p = os.path.join(ROOT, rel)
        s = open(p, encoding="utf-8").read()
        h1, h2, foot1, best = H[lang]
        # prefill with the words the page's board badges already carry (the updater's own), so the two never differ
        current = dict(re.findall(r"<!-- STATIC-BADGE:([A-Za-z0-9.]+):START -->(.*?)<!-- STATIC-BADGE:", s))
        def word(code):
            return current.get(code) or badge(code, by_code.get(code), lang)
        hike = "\n".join('      <li><a href="{}{}">{}</a><span class="st"><!-- STATIC-BADGE:{}:START -->{}<!-- STATIC-BADGE:{}:END --></span></li>'
                          .format(PREFIX[lang], path, names[lang], code, current.get(code, ""), code)
                          for code, path, names in TRAILS)
        day = "\n".join(f'      <li><a href="{PREFIX[lang]}{path}">{names[lang]}</a></li>' for path, names in DAY)
        block = (f"{MARK[0]}{CSS}\n"
                 f'<div class="aud">\n'
                 f'  <div class="card">\n    <h2>{h1}</h2>\n    <ul>\n{hike}\n    </ul>\n'
                 f'    <p class="foot">{foot1} · <a href="{PREFIX[lang]}{BEST}">{best}</a></p>\n  </div>\n'
                 f'  <div class="card">\n    <h2>{h2}</h2>\n    <ul>\n{day}\n    </ul>\n  </div>\n'
                 f"</div>\n{MARK[1]}")
        s = re.sub(re.escape(MARK[0]) + r".*?" + re.escape(MARK[1]), lambda _: block, s, flags=re.S) \
            if MARK[0] in s else s.replace(ANCHOR, ANCHOR + "\n\n" + block, 1)
        open(p, "w", encoding="utf-8").write(s)
        print(f"{rel}: audience block {'replaced' if MARK[0] in s else 'inserted'}")


if __name__ == "__main__":
    main()
