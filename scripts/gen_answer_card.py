#!/usr/bin/env python3
"""Quick-answers card on every trail page (owner, 2026-10-10), 5 languages.

It replaces the old status card at the top of the page with the questions people actually ask (Search Console,
the bot's chats), each answered in one or two lines:
  1. Is it open today?            the live status (status.js fills #statusCard, data-compact="1"; the updater fills
                                  the STATIC-STATUS line). Never "partly open": OPEN / CLOSED or the description.
  2. Do I need a ticket?          the IFCN fee (status.json) or "no IFCN ticket".
  3. How long and how hard?       copied from the page's own facts table, so the card never disagrees with it.
  4. How do I get there and back? the page's "by bus" section if it has one, else the taxi ranks on the trail's IFCN
                                  panel (knowledge store); one-way trails: where it ends.
  5. Where do I park?             only where the page has a sourced parking section (gen_parking.py).
  6. Vertigo or tunnels?          the page's own tunnel / exposure rows (sourced, gen_trail_extras.py).
  7. Weather now                  the STATIC-WEATHER reading (updater), refreshed by status.js. Forecast: on hold.
A row without a sourced fact is left out. Between <!-- ANSWER-CARD:START/END --> (+ ANSWER-CARD-HEAD for the CSS);
the STATIC-* markers keep whatever the updater wrote last. Idempotent; gen_spokes.py calls it; it re-places the
WhatsApp block (gen_cta.py) below the card.
"""
import glob, html as htmllib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

SKIP = ("bot", "seo_research", "reports", "google_search_console", ".claude", "trails", "q", "collect", "watch", "backend")
LP = {"en": "", "pt": "/pt", "fr": "/fr", "de": "/de", "pl": "/pl"}

Q = {
    "head": {"en": "{c} · Quick answers", "pt": "{c} · Respostas rápidas", "fr": "{c} · Réponses rapides",
             "de": "{c} · Schnelle Antworten", "pl": "{c} · Szybkie odpowiedzi"},
    "open": {"en": "Is it open today?", "pt": "Está aberto hoje?", "fr": "Est-il ouvert aujourd'hui ?",
             "de": "Ist er heute geöffnet?", "pl": "Czy jest dziś otwarty?"},
    "ticket": {"en": "Do I need a ticket?", "pt": "Preciso de bilhete?", "fr": "Faut-il un billet ?",
               "de": "Brauche ich ein Ticket?", "pl": "Czy potrzebny jest bilet?"},
    "long": {"en": "How long and how hard?", "pt": "Quanto tempo e que dificuldade?", "fr": "Quelle durée et quelle difficulté ?",
             "de": "Wie lang und wie schwer?", "pl": "Jak długo i jak trudno?"},
    "there": {"en": "How do I get there and back?", "pt": "Como chego lá e como volto?", "fr": "Comment y aller et revenir ?",
              "de": "Wie komme ich hin und zurück?", "pl": "Jak tam dojechać i wrócić?"},
    "park": {"en": "Where do I park?", "pt": "Onde estaciono?", "fr": "Où se garer ?", "de": "Wo parke ich?", "pl": "Gdzie zaparkować?"},
    "vertigo": {"en": "Vertigo or tunnels?", "pt": "Vertigens ou túneis?", "fr": "Vertige ou tunnels ?",
                "de": "Schwindel oder Tunnel?", "pl": "Ekspozycja czy tunele?"},
    "weather": {"en": "Weather there now", "pt": "Tempo lá agora", "fr": "Météo sur place", "de": "Wetter dort jetzt",
                "pl": "Pogoda tam teraz"},
}
A = {
    "fee": {"en": "Yes: <b>€{f}</b> per person on <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, online only, for a timed slot. Under-12s and residents are free but must be on the booking.",
            "pt": "Sim: <b>{f} €</b> por pessoa no <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, só online, com hora marcada. Menores de 12 anos e residentes não pagam, mas têm de constar da reserva.",
            "fr": "Oui : <b>{f} €</b> par personne sur <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, en ligne uniquement, pour un créneau horaire. Moins de 12 ans et résidents gratuits, mais inscrits sur la réservation.",
            "de": "Ja: <b>{f} €</b> pro Person bei <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, nur online, mit Zeitfenster. Unter 12-Jährige und Einheimische zahlen nichts, müssen aber auf der Buchung stehen.",
            "pl": "Tak: <b>{f} €</b> od osoby w <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, tylko online, na konkretną godzinę. Dzieci do 12 lat i mieszkańcy nie płacą, ale muszą być w rezerwacji."},
    "nofee": {"en": "No IFCN ticket: this trail is run by another body and is not on SIMplifica.",
              "pt": "Sem bilhete do IFCN: este percurso é gerido por outra entidade e não está no SIMplifica.",
              "fr": "Pas de billet IFCN : ce sentier est géré par un autre organisme et n'est pas sur SIMplifica.",
              "de": "Kein IFCN-Ticket: Diesen Weg betreibt ein anderer Träger, er ist nicht auf SIMplifica.",
              "pl": "Bez biletu IFCN: szlakiem zarządza inny podmiot i nie ma go w SIMplifica."},
    "bus": {"en": "By bus: the times are in <a href=\"#bus\">{h}</a> below.", "pt": "De autocarro: os horários estão em <a href=\"#bus\">{h}</a>, mais abaixo.",
            "fr": "En bus : les horaires sont dans <a href=\"#bus\">{h}</a>, plus bas.", "de": "Mit dem Bus: Die Zeiten stehen unten unter <a href=\"#bus\">{h}</a>.",
            "pl": "Autobusem: godziny w sekcji <a href=\"#bus\">{h}</a> poniżej."},
    "nobus": {"en": "No bus in our timetables reaches this trailhead.", "pt": "Nenhum autocarro dos nossos horários chega a este ponto de partida.",
              "fr": "Aucun bus de nos horaires ne dessert ce départ.", "de": "Laut unseren Fahrplänen fährt kein Bus zu diesem Ausgangspunkt.",
              "pl": "Według naszych rozkładów żaden autobus nie dojeżdża do początku szlaku."},
    "taxi": {"en": "Taxi: {t} (official rank{s}); fares are metered at the official tariff.", "pt": "Táxi: {t} (praça{s} oficial{s2}); o preço é pelo taxímetro, à tarifa oficial.",
             "fr": "Taxi : {t} (station{s} officielle{s}) ; course au compteur, tarif officiel.", "de": "Taxi: {t} (offizielle{s3} Standplatz{s4}); Taxameter zum offiziellen Tarif.",
             "pl": "Taksówka: {t} (oficjalny postój{s5}); opłata według taksometru, po oficjalnej taryfie."},
    "ends": {"en": "It is one way: it ends at <b>{e}</b>, so plan how you get back.", "pt": "É num só sentido: termina em <b>{e}</b>, por isso planeie o regresso.",
             "fr": "Il est à sens unique : il se termine à <b>{e}</b>, prévoyez le retour.", "de": "Er führt in eine Richtung: Ende in <b>{e}</b>, planen Sie also den Rückweg.",
             "pl": "Szlak jest w jedną stronę: kończy się w <b>{e}</b>, więc zaplanuj powrót."},
    "same": {"en": "You return the same way to the start.", "pt": "Volta pelo mesmo caminho até ao início.", "fr": "Retour par le même chemin jusqu'au départ.",
             "de": "Zurück geht es auf demselben Weg zum Start.", "pl": "Wracasz tą samą drogą do początku."},
    "src": {"en": "Status: IFCN's official warnings list · weather: IPMA", "pt": "Estado: lista oficial de avisos do IFCN · tempo: IPMA",
            "fr": "Statut : liste officielle des avis de l'IFCN · météo : IPMA", "de": "Status: offizielle Hinweisliste des IFCN · Wetter: IPMA",
            "pl": "Status: oficjalna lista komunikatów IFCN · pogoda: IPMA"},
}
LABELS = {
    "dist": {"Distance", "Distância", "Distanz", "Dystans", "Długość", "Länge"},
    "time": {"Time", "Duração", "Durée", "Dauer", "Czas"},
    "diff": {"Difficulty", "Dificuldade", "Difficulté", "Schwierigkeit", "Trudność"},
    "route": {"Route", "Trajeto", "Itinéraire", "Strecke", "Trasa"},
    "type": {"Type", "Tipo", "Typ", "Art"},
    "start": {"Start", "Início", "Départ"},
    "ret": {"Return", "Regresso", "Retour", "Rückweg", "Powrót"},
    "expo": {"Exposure", "Exposição", "Exposition", "Ausgesetztheit", "Ekspozycja"},
    "tun": {"Tunnels", "Túneis", "Tunnel", "Tunele"},
    "torch": {"Torch", "Lanterna", "Lampe", "Latarka"},
}
P2P = {"Point-to-point", "Linear", "Point à point", "Punkt zu Punkt", "Z punktu do punktu"}

CSS = """<!-- ANSWER-CARD-HEAD:START (scripts/gen_answer_card.py) -->
<style>
.qa-card{background:var(--card,#fff);border:1px solid var(--line,rgba(0,0,0,.08));border-radius:16px;padding:16px 18px 10px;margin:18px 0}
.qa-card h2{font-size:14px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 4px}
.qa-row{padding:10px 0;border-top:1px solid var(--line,rgba(0,0,0,.07))}
.qa-card h2+.qa-row{border-top:0}
.qa-q{font-weight:700;font-size:15.5px;margin:0 0 3px}
.qa-a,.qa-a p{margin:0;font-size:15px;line-height:1.45}
.qa-a .status-head{padding:0;display:flex;gap:8px;align-items:flex-start}
.qa-a .status-badge{font-size:22px}
.qa-src{font-size:12px;color:var(--ink-soft);margin:8px 0 0}
</style>
<!-- ANSWER-CARD-HEAD:END -->
"""


START = {"en": "Start", "pt": "Início", "fr": "Départ", "de": "Start", "pl": "Start"}
VERT = {"expo": {"en": "Exposure", "pt": "Exposição", "fr": "Exposition", "de": "Ausgesetztheit", "pl": "Ekspozycja"},
        "tun": {"en": "Tunnels", "pt": "Túneis", "fr": "Tunnels", "de": "Tunnel", "pl": "Tunele"},
        "torch": {"en": "Torch", "pt": "Lanterna", "fr": "Lampe", "de": "Lampe", "pl": "Latarka"}}


def facts(page):
    a = page.find('<aside class="facts">')
    side = page[a:page.find("</aside>", a)] if a >= 0 else ""
    out = {}
    for th, td in re.findall(r'<th scope="row">(.*?)</th><td>(.*?)</td>', side):
        for k, labels in LABELS.items():
            if htmllib.unescape(th) in labels:
                out.setdefault(k, td)
    for dt, dd in re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", side):   # TRAIL-EXTRAS (tunnels / exposure)
        out.setdefault("extras", []).append(f"{dt}: {dd}")
    return out


def marker(page, name, code):
    m = re.search(rf"<!--\s*{name}:{re.escape(code)}:START\s*-->.*?<!--\s*{name}:{re.escape(code)}:END\s*-->", page, re.S)
    return m.group(0) if m else f"<!-- {name}:{code}:START --><!-- {name}:{code}:END -->"


def taxis(code):
    try:
        import kbtools
        r = kbtools.transport(trail=code)
    except Exception as e:
        print(f"  {code}: no taxi data ({e})", file=sys.stderr)
        return []
    seen, out = set(), []
    for x in r.get("taxis", []):
        if "panel" not in (x.get("role") or "") and "serves" not in (x.get("role") or ""):
            continue
        key = tuple(x.get("phone") or [])
        if key in seen:
            continue
        seen.add(key)
        tel = (x.get("phone") or [""])[0]
        out.append(f'<b>{htmllib.escape(x["name"])}</b> <a href="tel:{tel.replace(" ", "")}">{htmllib.escape(tel)}</a>')
    return out[:2]


def card(page, lang, code, status):
    f = facts(page)
    rows = []
    def row(key, body):
        rows.append(f'<div class="qa-row"><p class="qa-q">{Q[key][lang]}</p><div class="qa-a">{body}</div></div>')
    row("open", f'<div id="statusCard" data-trail="{code}" data-compact="1"><p class="static-status">'
                f'{marker(page, "STATIC-STATUS", code)}</p></div>')
    fee = (status or {}).get("fee")
    row("ticket", A["fee"][lang].format(f=fee.replace(".", ",") if lang != "en" else fee) if fee else A["nofee"][lang])
    long_ = " · ".join(x for x in (f.get("dist"), f.get("time"), f.get("diff")) if x)
    route = f.get("route") or (START[lang] + ": " + f["start"] if f.get("start") else None)
    if route:
        long_ += (" · " if long_ else "") + route + (f" ({f['type']})" if f.get("type") else "")
    if long_:
        row("long", f"<p>{long_}</p>")
    there = []
    bus = re.search(r'<section id="bus">\s*<h2>([^<]+)</h2>(.*?)</section>', page, re.S)
    bus_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", bus.group(2))).strip() if bus else ""
    if bus and re.search(r"\b\d{1,2}:\d{2}\b", bus_text):
        there.append(A["bus"][lang].format(h=bus.group(1)))
    elif bus and bus_text:   # a bus section that says there is no bus (Rabaçal, Fanal…): say so, then the taxis
        there.append(htmllib.escape(re.split(r"(?<=[.!?])\s", htmllib.unescape(bus_text), maxsplit=1)[0]))
        t = taxis(code)
        if t:
            n = len(t) > 1
            there.append(A["taxi"][lang].format(t=", ".join(t), s="s" if n else "", s2="is" if n else "", s3="" if n else "r",
                                                s4="e" if n else "", s5="e" if n else ""))
    else:
        there.append(A["nobus"][lang])
        t = taxis(code)
        if t:
            n = len(t) > 1
            there.append(A["taxi"][lang].format(t=", ".join(t), s="s" if n else "", s2="is" if n else "", s3="" if n else "r",
                                                s4="e" if n else "", s5="e" if n else ""))
    end = None
    if f.get("type") in P2P and f.get("route") and "→" in f["route"]:
        end = f["route"].split("→")[-1].strip()
    if end:
        there.append(A["ends"][lang].format(e=end))
    elif f.get("type") and f["type"] not in P2P and "PR1" != code:
        there.append(A["same"][lang])
    row("there", "<p>" + " ".join(there) + "</p>")
    park = re.search(r'<section id="parking">\s*<h2>[^<]*</h2>\s*<p>(.*?)</p>', page, re.S)
    if park:
        first = re.split(r"(?<=[.!?])\s", park.group(1), maxsplit=1)[0]
        row("park", f'<p>{first} <a href="#parking">›</a></p>')
    vert = f.get("extras") or [f"{VERT[k][lang]}: {f[k]}" for k in ("expo", "tun", "torch") if f.get(k)]
    if vert:
        row("vertigo", "<p>" + " · ".join(vert) + "</p>")
    row("weather", f'<p class="static-weather" id="qaWeather">{marker(page, "STATIC-WEATHER", code)}</p>')
    return ("<!-- ANSWER-CARD:START (scripts/gen_answer_card.py) -->\n"
            f'<section class="qa-card" id="answers">\n<h2>{Q["head"][lang].format(c=code)}</h2>\n' + "\n".join(rows) +
            f'\n<p class="qa-src">{A["src"][lang]}</p>\n</section>\n<!-- ANSWER-CARD:END -->\n')


OLD_CARD = re.compile(r'<div class="status-card" id="statusCard" data-trail="([^"]+)">\s*<div class="status-body">.*?</div>\s*</div>\n', re.S)
CARD = re.compile(r"<!-- ANSWER-CARD:START.*?<!-- ANSWER-CARD:END -->\n", re.S)


def main():
    os.chdir(ROOT)
    status = {t["code"]: t for t in json.load(open("status.json", encoding="utf-8"))["trails"]}
    n = 0
    for p in sorted(glob.glob("**/index.html", recursive=True)):
        if p.split(os.sep)[0] in SKIP:
            continue
        h = open(p, encoding="utf-8").read()
        if '<aside class="facts">' not in h:
            continue
        m = CARD.search(h) or OLD_CARD.search(h)
        if not m:
            continue
        code = re.search(r'data-trail="([^"]+)"', m.group(0)).group(1)
        lang = re.search(r'<html lang="([a-z]{2})', h).group(1)
        new = h[:m.start()] + card(h, lang, code, status.get(code)) + h[m.end():]
        if "<!-- ANSWER-CARD-HEAD:START" not in new:
            new = new.replace("</head>", CSS + "</head>", 1)
        if new != h:
            open(p, "w", encoding="utf-8").write(new)
            n += 1
    print(f"answer cards written to {n} page(s)")
    import gen_cta   # the WhatsApp block goes right below the card
    gen_cta.main()


if __name__ == "__main__":
    main()
