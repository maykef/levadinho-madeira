#!/usr/bin/env python3
"""One-off generator for the long-tail trail spoke pages.

Builds a lightweight, live-status-first spoke page (en/pt/fr/de/pl) for every PR
trail that doesn't already have a hand-authored spoke. Facts (distance,
difficulty, duration, altitude, start/end) are scraped from each trail's
official Visit Madeira page so nothing is invented. Trails in PHOTOS get a
photo hero (served as .webp, the .jpg is the og:image); the rest a plain hero.

Each page carries: a <=60-char title built from a short trail name (SHORT_NAMES /
short_name()), a 120-155-char description, og/twitter image tags, a FAQPage whose
questions are the visible headings and whose answers are the visible paragraphs
(same strings, verbatim), a TouristAttraction block (scraped facts + trailhead geo
from the Visit Madeira index, via gen_site_nav.trail_coords) and a trailhead map
(OSM embed + links) when the coordinates are known.

Run from the repo root:  python scripts/gen_spokes.py
It writes the HTML files, prints the PAGES entries to add, and prints the
sitemap <url> blocks to append. Wiring into update_status.py / sitemap.xml is
done by the caller (kept out of here so the scrape stays side-effect-light).

Test without touching the repo (renders one trail in all 5 languages, skips
gen_site_nav / gen_cta, and prints every trail's title/description lengths):

    python scripts/gen_spokes.py --dry-run PR6.1 /path/to/outdir
"""
import html as htmllib, json, os, re, sys, unicodedata, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_trail_extras  # noqa: E402  tunnels / exposure rows (IFCN panels)

UA = {"User-Agent": "LevadinhoBot/1.0 (https://levadinho-madeira.com)"}
BASE = "https://visitmadeira.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Sourced tunnel / torch / exposure data (scripts/gen_trail_extras.py). A row is
# omitted when its value is null: we never guess.
EXTRAS = gen_trail_extras.load(os.path.join(ROOT, "trail_extras.json"))

# Trails that already have a hand-authored spoke (leave these alone).
HAVE = {"PR1", "PR6", "PR1.2", "PR9", "PR8", "PR11", "PR13", "PR10", "PR18", "PR14"}

# Long-tail trails that have a self-hosted hero photo (Wikimedia Commons,
# credited in img/CREDITS.txt). Everything else uses the plain hero.
PHOTOS = {
    "PR6.1": {"file": "levada-do-risco.jpg", "author": "GualdimG", "lic": "CC BY-SA 4.0"},
    "PR7":   {"file": "levada-do-moinho.jpg", "author": "Gerda Arendt", "lic": "CC BY-SA 4.0"},
    "PR16":  {"file": "levada-faja-do-rodrigues.jpg", "author": "Gerda Arendt", "lic": "CC0"},
    "PR6.2": {"file": "levada-do-alecrim.jpg", "author": "Asurnipal", "lic": "CC BY-SA 4.0"},
    "PR1.3": {"file": "vereda-da-encumeada.jpg", "author": "Gerda Arendt", "lic": "CC0"},
    "PR3": {"file": "vereda-do-burro.jpg", "author": "muffinn from Worcester, UK", "lic": "CC BY 2.0"},
    "PR3.1": {"file": "caminho-real-do-monte.jpg", "author": "Krzysztof Pop\u0142awski", "lic": "CC BY 4.0"},
    "PR6.3": {"file": "vereda-da-lagoa-do-vento.jpg", "author": "OlDie1966", "lic": "CC BY-SA 4.0"},
    "PR6.4": {"file": "levada-velha-do-rabacal.jpg", "author": "Jos\u00e9 Lemos Silva", "lic": "CC BY-SA 4.0"},
    "PR9.1": {"file": "levada-do-caldeirao-verde-um-caminho-para-todos.jpg", "author": "G\u00fcnter Seggeb\u00e4ing, Coesfeld", "lic": "CC BY-SA 3.0"},
    "PR12": {"file": "caminho-real-da-encumeada.jpg", "author": "Gerda Arendt", "lic": "CC0"},
    "PR15": {"file": "vereda-da-ribeira-da-janela.jpg", "author": "VillageHero from Ulm, Germany", "lic": "CC BY-SA 2.0"},
    "PR17": {"file": "caminho-do-pinaculo-e-folhadal.jpg", "author": "Gerda Arendt", "lic": "CC BY-SA 4.0"},
    "PR19": {"file": "caminho-real-do-paul-do-mar.jpg", "author": "Harald Lordick", "lic": "CC BY-SA 3.0"},
    "PR27": {"file": "glaciar-de-planalto.jpg", "author": "Rikki Mitterer", "lic": "CC BY-SA 4.0"},
    "PR28": {"file": "levada-da-rocha-vermelha.jpg", "author": "Mark Skarratts", "lic": "CC BY 2.0"},
    "PR6.8": {"file": "levada-do-paul-ii-um-caminho-para-todos.jpg", "author": "Asurnipal", "lic": "CC BY-SA 4.0"},
}
SITE = "https://levadinho-madeira.com"
OG_DEFAULT = f"{SITE}/img/og-default.jpg"

# Short names for titles / H1 / headings (the full official name stays in the
# subtitle, the facts and the TouristAttraction block). short_name() applies the
# generic rule; these overrides pin the result for the long official names.
SHORT_NAMES = {
    "PR9.1": "Levada do Caldeirão Verde",   # "... - um caminho para todos"
    "PR6.8": "Levada do Paul II",           # "... - Um caminho para todos"
}


def short_name(code, name):
    if code in SHORT_NAMES:
        return SHORT_NAMES[code]
    s = re.sub(r"\s+[-–]\s+um caminho para todos\s*$", "", name, flags=re.I)
    if len(s) > 35:
        s = re.split(r"\s+[-–]\s+", s)[0]
    return s.strip()


PHOTO_CREDIT = {
    "en": ("Photo", "resized"), "pt": ("Foto", "redimensionada"), "fr": ("Photo", "redimensionnée"),
    "de": ("Foto", "verkleinert"), "pl": ("Zdjęcie", "przeskalowane"),
}


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def trail_urls():
    idx = f"{BASE}/en/what-to-do/nature-seekers/activities/hiking/"
    html = urllib.request.urlopen(urllib.request.Request(idx, headers=UA), timeout=60).read().decode("utf-8", "replace")
    rows = re.findall(r'\["(PR[^"]+?)",-?\d+\.\d+,-?\d+\.\d+,\d+,"[^"]*","([^"]*)"', html)
    out = {}
    for name, url in rows:
        code = name.split(" - ")[0].replace(" ", "")
        out.setdefault(code, url)
    return out


def scrape_facts(url):
    if url.startswith("/"):
        url = BASE + url
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    f = {}
    m = re.search(r"Distance:\s*([\d.,]+)\s*km(\s*\([^)]*round trip[^)]*\))?", text)
    if m:
        f["distance"] = f"{m.group(1)} km" + (f" {m.group(2).strip()}" if m.group(2) else "")
        f["round_trip"] = bool(m.group(2))
    m = re.search(r"Difficulty:\s*([A-Za-z]+)", text)
    if m: f["difficulty"] = m.group(1)
    # Duration comes in many shapes: "3:30 hours", "2 hours", "1h30", "45 minutes".
    dm = re.search(r"Duration:\s*(\d{1,2})\s*[:h]\s*(\d{2})\s*(?:hours?)?", text)
    if dm:
        f["duration"] = f"{int(dm.group(1))}:{dm.group(2)} h"
    else:
        dm = re.search(r"Duration:\s*(\d{1,2})\s*hours?", text)
        if dm:
            f["duration"] = f"{dm.group(1)} h"
        else:
            dm = re.search(r"Duration:\s*(\d{1,3})\s*minutes?", text)
            if dm: f["duration"] = f"{dm.group(1)} min"
    m = re.search(r"Max\.?\s*Altitude\s*/\s*Min\.?\s*Altitude:\s*:?\s*([\d.,]+)\s*m(?:etres)?\s*/\s*([\d.,]+)\s*m", text)
    if m: f["alt_max"], f["alt_min"] = m.group(1), m.group(2)
    f["circular"] = bool(re.search(r"\bcircular\b", text, re.I))
    # Bound the capture at "Max. Altitude" / "How to get there" — otherwise a
    # non-greedy .+? runs to EOF and swallows the whole page into `end`.
    m = re.search(r"Start\s*/\s*End:\s*(.+?)\s*(?:Max\.?\s*Altitude|How to get there|Route type|Nature of)", text)
    if m:
        se = re.sub(r"\s*\([^)]*\)\s*", " ", m.group(1))   # drop (road refs) like (E.R. 101)
        parts = [p.strip(" .,") for p in re.split(r"\s*/\s*", se) if p.strip(" .,")]
        if len(parts) >= 2:
            f["start"], f["end"] = parts[0], parts[-1]
        elif parts:
            f["start"] = parts[0]
    # Official track download, when the page offers one (none did on 2026-09-30).
    m = re.search(r'href="([^"]+\.(gpx|kml|kmz))(?:\?[^"]*)?"', html, re.I)
    if m:
        g = m.group(1)
        f["gpx"] = g if g.startswith("http") else BASE + ("" if g.startswith("/") else "/") + g
        f["gpx_kind"] = m.group(2).upper()
    return f


# ---- localised strings -------------------------------------------------------
DIFF = {
    "Easy":       {"en": "Easy", "pt": "Fácil", "fr": "Facile", "de": "Leicht", "pl": "Łatwa"},
    "Moderate":   {"en": "Moderate", "pt": "Moderada", "fr": "Modérée", "de": "Mittel", "pl": "Umiarkowana"},
    "Difficult":  {"en": "Hard", "pt": "Difícil", "fr": "Difficile", "de": "Schwer", "pl": "Trudna"},
    "Hard":       {"en": "Hard", "pt": "Difícil", "fr": "Difficile", "de": "Schwer", "pl": "Trudna"},
}
OAB = {"en": "Out-and-back", "pt": "Ida e volta", "fr": "Aller-retour", "de": "Hin und zurück", "pl": "Tam i z powrotem"}
P2P = {"en": "Point-to-point", "pt": "Linear", "fr": "Point à point", "de": "Punkt zu Punkt", "pl": "Z punktu do punktu"}
CIRC = {"en": "Circular", "pt": "Circular", "fr": "Boucle", "de": "Rundweg", "pl": "Pętla"}
TYP = {"oab": OAB, "circ": CIRC, "p2p": P2P}
LBL = {
    "distance":   {"en": "Distance", "pt": "Distância", "fr": "Distance", "de": "Distanz", "pl": "Dystans"},
    "time":       {"en": "Time", "pt": "Duração", "fr": "Durée", "de": "Dauer", "pl": "Czas"},
    "difficulty": {"en": "Difficulty", "pt": "Dificuldade", "fr": "Difficulté", "de": "Schwierigkeit", "pl": "Trudność"},
    "altitude":   {"en": "Altitude", "pt": "Altitude", "fr": "Altitude", "de": "Höhe", "pl": "Wysokość"},
    "route":      {"en": "Route", "pt": "Trajeto", "fr": "Itinéraire", "de": "Strecke", "pl": "Trasa"},
    "type":       {"en": "Type", "pt": "Tipo", "fr": "Type", "de": "Typ", "pl": "Typ"},
    "fee":        {"en": "Fee", "pt": "Taxa", "fr": "Tarif", "de": "Gebühr", "pl": "Opłata"},
    "facts":      {"en": "Trail facts", "pt": "Dados do percurso", "fr": "Infos sur le sentier", "de": "Weg-Fakten", "pl": "Fakty o szlaku"},
    "hours":      {"en": "h", "pt": "h", "fr": "h", "de": "Std.", "pl": "godz."},
}
BRAND = {
    "en": "Levadinho · Madeira trail answers",
    "pt": "Levadinho · Respostas sobre os percursos da Madeira",
    "fr": "Levadinho · Réponses sur les sentiers de Madère",
    "de": "Levadinho · Antworten zu Madeiras Wanderwegen",
    "pl": "Levadinho · Odpowiedzi o szlakach Madery",
}
LANGS = ("en", "pt", "fr", "de", "pl")   # switcher / hreflang order
PREFIX = {"en": "", "pt": "/pt", "fr": "/fr", "de": "/de", "pl": "/pl"}
SEE = {"en": "See", "pt": "Veja", "fr": "Voir", "de": "Siehe", "pl": "Zobacz"}


def pt_g(name):
    """European Portuguese article forms for a trail name: Vereda/Levada are
    feminine, Caminho/Glaciar masculine. Returns (Art, art, de+art, adj ending)."""
    fem = name.split()[0].lower() in ("vereda", "levada")
    return ("A", "a", "da", "a") if fem else ("O", "o", "do", "o")


def fr_g(name):
    """French: (Art, art, pronoun, adj ending) — la Levada/Vereda, le Caminho/Glaciar."""
    fem = pt_g(name)[1] == "a"
    return ("La", "la", "elle", "e") if fem else ("Le", "le", "il", "")


def de_g(name):
    """German: (Art, art, pronoun, accusative art) — die Levada/Vereda, der Caminho/Glaciar."""
    fem = pt_g(name)[1] == "a"
    return ("Die", "die", "Sie", "die") if fem else ("Der", "der", "Er", "den")


import datetime as _dt, zoneinfo as _zi
GENERATED_AT = _dt.datetime.now(_zi.ZoneInfo("Atlantic/Madeira")).isoformat(timespec="minutes")


def region_place(code):
    """IPMA station place of a trail's weather region (status.json trails[].region), or None."""
    from update_status import REGION_PLACE
    try:
        trails = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "status.json")))["trails"]
    except (OSError, ValueError, KeyError):
        return None
    r = next((t.get("region") for t in trails if t["code"] == code), None)
    return REGION_PLACE.get(r)


def weather_qa(lang, name, place):
    """(heading, answer) for the "weather now?" question on trail pages (2026-10-03): people on the
    island search "<trail> weather / tempo / météo / Wetter / pogoda". The answer is static (the FAQ
    schema must match the visible text); the measured reading is the STATIC-WEATHER line under it."""
    if lang == "en":
        return (f"What's the weather at {name} now?",
                f"The status card above shows the latest measured reading from the IPMA {place} station, the regional "
                "weather station nearest the trail: temperature, wind and whether it is likely in cloud. Expect the "
                "mountains cooler and cloudier than Funchal.")
    if lang == "pt":
        return (f"Como está o tempo n{pt_g(name)[1]} {name} agora?",
                f"O cartão de estado acima mostra a última leitura medida pela estação do IPMA em {place}, a estação "
                "regional mais próxima do percurso: temperatura, vento e se é provável estar dentro das nuvens. Conte "
                "com a montanha mais fresca e nublada do que o Funchal.")
    if lang == "fr":
        return (f"{name} : quelle météo maintenant ?",
                f"La carte d'état ci-dessus affiche le dernier relevé mesuré par la station IPMA de {place}, la station "
                "régionale la plus proche du sentier : température, vent et risque d'être dans les nuages. En montagne, "
                "attendez-vous à plus frais et plus nuageux qu'à Funchal.")
    if lang == "de":
        return (f"{name}: Wie ist das Wetter jetzt?",
                f"Die Statuskarte oben zeigt den letzten Messwert der IPMA-Station {place}, der nächstgelegenen "
                "regionalen Wetterstation: Temperatur, Wind und ob der Weg wahrscheinlich in Wolken liegt. In den "
                "Bergen ist es kühler und wolkiger als in Funchal.")
    return (f"{name}: jaka jest teraz pogoda?",
            f"Karta stanu powyżej pokazuje ostatni pomiar ze stacji IPMA {place}, najbliższej regionalnej stacji "
            "pogodowej: temperaturę, wiatr i to, czy szlak jest prawdopodobnie w chmurach. W górach jest chłodniej "
            "i bardziej pochmurno niż w Funchal.")


# IPMA's official weather warnings, "Madeira - Mountain" region (pt / en pages only).
WARN = {"en": ("Official weather warnings for the Madeira mountains:", "en"),
        "pt": ("Avisos meteorológicos oficiais para a montanha da Madeira:", "pt"),
        "fr": ("Avis météo officiels pour la montagne de Madère :", "en"),
        "de": ("Offizielle Wetterwarnungen für die Berge Madeiras:", "en"),
        "pl": ("Oficjalne ostrzeżenia pogodowe dla gór Madery:", "en")}


def warnings_p(lang):
    label, il = WARN[lang]
    return (f'  <p class="wx-warn">{htmllib.escape(label, quote=False)} <a href="https://www.ipma.pt/{il}/otempo/prev-sam/?p=MRM" '
            f'rel="noopener">IPMA</a>.</p>\n')


def weather_section(lang, name, code, place):
    h, a = weather_qa(lang, name, place)
    return (f'<section id="weather">\n  <h2>{htmllib.escape(h, quote=False)}</h2>\n  <p>{htmllib.escape(a, quote=False)}</p>\n'
            f'  <p class="static-weather"><!-- STATIC-WEATHER:{code}:START --><!-- STATIC-WEATHER:{code}:END --></p>\n'
            + warnings_p(lang) + '</section>\n\n')


def webpage_ld(name, url, lang):
    """WebPage JSON-LD carrying "dateModified" (bumped by update_status.py when the page's content changes)."""
    return {"@context": "https://schema.org", "@type": "WebPage", "name": name, "url": url,
            "inLanguage": lang, "dateModified": GENERATED_AT}


def fit(cands, lo=0, hi=60):
    """First candidate whose plain-text length is within [lo, hi]; else the
    shortest one (titles) — callers keep the list ordered longest-first."""
    for c in cands:
        if lo <= len(c) <= hi:
            return c
    return min(cands, key=len) if lo == 0 else min(cands, key=lambda c: abs(len(c) - (lo + hi) / 2))


def titles(lang, code, n):
    """Title (plain text, <=60 chars target) and description (120-155)."""
    A, a, o = (*pt_g(n)[:2], pt_g(n)[3])
    fA, fa, fpr, fe = fr_g(n)
    dA, da_, _, _ = de_g(n)
    c = code
    if lang == "en":
        # Trail code + "Madeira" first (2026-10-03): people on the island search the bare code ("pr9.1", "pr18 madeira").
        t = [f"{c} Madeira: {n}, open today? Booking", f"{c} Madeira: {n}, open today?", f"{c} Madeira: {n} open today?",
             f"{c}: {n}, open today?", f"{c}: {n} open?"]
        d = [f"Is the {n} ({c}) open today? Status from the official IFCN warnings list. Check live status, fees and booking on SIMplifica.",
             f"Is the {n} ({c}) open today? From the official IFCN list. Check live status, fees and booking on SIMplifica."]
    elif lang == "pt":
        t = [f"{c} Madeira: {n} está abert{o} hoje? Reserva", f"{c} Madeira: {n} está abert{o} hoje?",
             f"{c} Madeira: {n}, abert{o} hoje?", f"{c}: {n}, abert{o} hoje?", f"{c}: {n} abert{o}?"]
        d = [f"{A} {n} ({c}) está abert{o} hoje? Estado segundo a lista oficial de avisos do IFCN. Veja o estado em direto, as taxas e a reserva no SIMplifica.",
             f"{A} {n} ({c}) está abert{o} hoje? Estado segundo a lista oficial do IFCN. Veja o estado em direto, taxas e reserva no SIMplifica.",
             f"{A} {n} ({c}) está abert{o} hoje? Segundo a lista oficial do IFCN. Estado em direto, taxas e reserva no SIMplifica."]
    elif lang == "fr":
        t = [f"{c} Madère : {n}, ouvert{fe} aujourd'hui ? Réservation", f"{c} Madère : {n}, ouvert{fe} aujourd'hui ?",
             f"{c} Madère : {n} ouvert{fe} ?", f"{c} : {n}, ouvert{fe} aujourd'hui ?", f"{c} : {n} ouvert{fe} ?"]
        d = [f"{fA} {n} ({c}) est-{fpr} ouvert{fe} aujourd'hui ? Selon la liste officielle des avis de l'IFCN. Statut en direct, tarifs et réservation sur SIMplifica.",
             f"{fA} {n} ({c}) est-{fpr} ouvert{fe} aujourd'hui ? Selon la liste officielle de l'IFCN. Statut en direct, tarifs et réservation sur SIMplifica.",
             f"{fA} {n} ({c}) ouvert{fe} aujourd'hui ? Selon la liste officielle de l'IFCN. Statut en direct, tarifs, réservation sur SIMplifica."]
    elif lang == "de":
        t = [f"{c} Madeira: {n} heute geöffnet? Buchung", f"{c} Madeira: {n} heute geöffnet?",
             f"{c}: {n} heute geöffnet?", f"{c}: {n} geöffnet?"]
        d = [f"Ist {da_} {n} ({c}) heute geöffnet? Status laut offizieller Hinweisliste des IFCN. Live-Status, Gebühren und Buchung auf SIMplifica prüfen.",
             f"Ist {da_} {n} ({c}) heute geöffnet? Laut offizieller IFCN-Liste. Live-Status, Gebühren und Buchung auf SIMplifica prüfen."]
    else:  # pl
        t = [f"{c} Madera: {n} – czy dziś otwarta? Rezerwacja", f"{c} Madera: {n} – czy dziś otwarta?",
             f"{c} Madera: {n} – dziś otwarta?", f"{c}: {n} – dziś otwarta?", f"{c}: {n} – otwarta?"]
        d = [f"Czy {n} ({c}) jest dziś otwarta? Status z oficjalnej listy komunikatów IFCN. Sprawdź status na żywo, opłaty i rezerwację w SIMplifica.",
             f"Czy {n} ({c}) jest dziś otwarta? Wg oficjalnej listy IFCN. Sprawdź status na żywo, opłaty i rezerwację w SIMplifica."]
    return fit(t), fit(d, 120, 155)


MAP = {
    "en": ("Trailhead", "Map of the {} trailhead", "Open in OpenStreetMap", "Google Maps", "Official {} (Visit Madeira)",
           "Trailhead location from the Visit Madeira trail index."),
    "pt": ("Ponto de partida", "Mapa do ponto de partida: {}", "Abrir no OpenStreetMap", "Google Maps", "{} oficial (Visit Madeira)",
           "Localização do ponto de partida segundo o índice de percursos do Visit Madeira."),
    "fr": ("Point de départ", "Carte du point de départ : {}", "Ouvrir dans OpenStreetMap", "Google Maps", "{} officiel (Visit Madeira)",
           "Emplacement du départ selon l'index des sentiers de Visit Madeira."),
    "de": ("Ausgangspunkt", "Karte des Ausgangspunkts: {}", "In OpenStreetMap öffnen", "Google Maps", "Offizielles {} (Visit Madeira)",
           "Lage des Ausgangspunkts laut Wanderweg-Index von Visit Madeira."),
    "pl": ("Początek szlaku", "Mapa początku szlaku: {}", "Otwórz w OpenStreetMap", "Mapy Google", "Oficjalny {} (Visit Madeira)",
           "Położenie początku szlaku według indeksu szlaków Visit Madeira."),
}


def map_block(lang, n, geo, f):
    """Trailhead map for the facts aside (only when coordinates are known)."""
    if not geo:
        return ""
    lat, lon = geo
    h, ttl, osm_l, g_l, gpx_l, note = MAP[lang]
    bbox = f"{lon - 0.01:.5f},{lat - 0.006:.5f},{lon + 0.01:.5f},{lat + 0.006:.5f}"
    src = f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}&amp;layer=mapnik&amp;marker={lat:.5f},{lon:.5f}"
    osm = f"https://www.openstreetmap.org/?mlat={lat:.5f}&amp;mlon={lon:.5f}#map=15/{lat:.5f}/{lon:.5f}"
    gm = f"https://www.google.com/maps?q={lat:.5f},{lon:.5f}"
    links = [f'<a class="plain" href="{osm}" target="_blank" rel="noopener">{osm_l}</a>',
             f'<a class="plain" href="{gm}" target="_blank" rel="noopener">{g_l}</a>']
    if f.get("gpx"):
        links.append(f'<a class="plain" href="{htmllib.escape(f["gpx"])}" target="_blank" rel="noopener">{gpx_l.format(f.get("gpx_kind", "GPX"))}</a>')
    return (f'  <h2 style="margin-top:14px">{h}</h2>\n'
            f'  <iframe loading="lazy" title="{htmllib.escape(ttl.format(n))}" src="{src}" '
            f'style="width:100%;height:170px;border:1px solid var(--line);border-radius:8px"></iframe>\n'
            f'  <p style="font-size:13px;margin:6px 0 0">{" · ".join(links)}</p>\n'
            f'  <p style="font-size:12px;color:var(--ink-soft);margin:4px 0 0">{note}</p>\n')


# Classified PR trails managed by a body other than IFCN (IFCN trail list, ENTIDADE GESTORA): not on
# SIMplifica and no IFCN fee (IFCN FAQ 1.7). Their pages must never say "paid, booking-only, €4.50".
NO_IFCN_FEE = {"PR3": "Câmara Municipal do Funchal", "PR3.1": "Câmara Municipal do Funchal",
               "PR4": "Câmara Municipal do Funchal"}
IFCN_FAQ = ("https://ifcn.madeira.gov.pt/en/atividades-de-natureza/percursos-pedestres-recomendados/"
            "faq-s-taxas-percursos-pedestres-classificados/frequently-asked-questions-fees-classified-walking-routes.html")
NOFEE_ROW = {"en": "No IFCN fee", "pt": "Sem taxa IFCN", "fr": "Sans taxe IFCN", "de": "Keine IFCN-Gebühr", "pl": "Bez opłaty IFCN"}


def no_fee_texts(lang, code, name, full, body):
    """Override every booking/fee slot for a trail in NO_IFCN_FEE."""
    faq = f'<a class="plain" href="{IFCN_FAQ}" target="_blank" rel="noopener">IFCN FAQ 1.7</a>'
    free = f'<a class="plain" href="{PREFIX[lang]}/free-walks/">'
    board = f'<a class="plain" href="{PREFIX[lang]}/">'
    if lang == "en":
        return dict(
            sub=f"Today's status is shown live below, taken from the official IFCN warnings list, which carries IFCN's own “updated” date. {full} ({code}) is a classified PR trail managed by the {body}, not by IFCN: it is not on SIMplifica and carries no IFCN fee.",
            book_h=f"Do you need to book the {name}?",
            book=f"No. {code} is managed by the {body}, so it is not on the SIMplifica booking portal and there is no IFCN fee ({faq}). We found no charge of its own. If your walk joins an IFCN-managed PR trail, that stretch needs a SIMplifica ticket. More in {free}free walks in Madeira</a>.",
            cl_h=f"What if {code} is closed?",
            cl=f"If {code} shows closed, don't walk it: closures apply to everyone, ticket or not. For open alternatives, {board}check the live board</a>.",
            kn0=f"<b>No ticket needed.</b> SIMplifica booking and the IFCN fee apply only to trails managed by IFCN; {code} is managed by the {body} ({faq}).",
            desc=[f"Is the {name} ({code}) open today? Live status from the official IFCN list. Run by Funchal council: no SIMplifica ticket, no IFCN fee.",
                  f"Is the {name} ({code}) open today? Live IFCN status. Run by Funchal council: no SIMplifica ticket and no IFCN fee."])
    if lang == "pt":
        return dict(
            sub=f"O estado de hoje aparece em direto abaixo, com base na lista oficial de avisos do IFCN, com a data de «atualizado» do próprio IFCN. O percurso {full} ({code}) é um PR classificado gerido pela {body}, não pelo IFCN: não está no SIMplifica e não tem taxa do IFCN.",
            book_h=f"É preciso reservar o percurso {name}?",
            book=f"Não. O {code} é gerido pela {body}, por isso não está no portal de reservas SIMplifica e não tem taxa do IFCN ({faq}). Não encontrámos nenhuma cobrança própria. Se o seu percurso entrar num PR gerido pelo IFCN, esse troço precisa de bilhete SIMplifica. Mais em {free}trilhos gratuitos na Madeira</a>.",
            cl_h=f"E se o {code} estiver encerrado?",
            cl=f"Se o {code} aparecer como encerrado, não o percorra: os encerramentos aplicam-se a todos, com ou sem bilhete. Para alternativas abertas, {board}consulte o quadro em direto</a>.",
            kn0=f"<b>Sem bilhete.</b> A reserva no SIMplifica e a taxa do IFCN aplicam-se só aos percursos geridos pelo IFCN; o {code} é gerido pela {body} ({faq}).",
            desc=[f"O percurso {name} ({code}) está aberto hoje? Estado em direto da lista oficial do IFCN. Gerido pela Câmara do Funchal: sem bilhete nem taxa IFCN.",
                  f"O {name} ({code}) está aberto hoje? Estado em direto do IFCN. Gerido pela Câmara do Funchal: sem bilhete SIMplifica nem taxa IFCN."])
    if lang == "fr":
        return dict(
            sub=f"Le statut du jour est affiché en direct ci-dessous, issu de la liste officielle des avis de l'IFCN, avec sa propre date de « mise à jour ». Le sentier {full} ({code}) est un PR classé géré par la {body}, pas par l'IFCN : il n'est pas sur SIMplifica et n'a pas de taxe IFCN.",
            book_h=f"Faut-il réserver le sentier {name} ?",
            book=f"Non. Le {code} est géré par la {body} : il n'est pas sur le portail de réservation SIMplifica et n'a pas de taxe IFCN ({faq}). Nous n'avons trouvé aucun tarif propre. Si votre itinéraire rejoint un PR géré par l'IFCN, ce tronçon demande un billet SIMplifica. Plus d'infos : {free}randonnées gratuites à Madère</a>.",
            cl_h=f"Et si le {code} est fermé ?",
            cl=f"Si le {code} est indiqué fermé, ne l'empruntez pas : les fermetures valent pour tous, avec ou sans billet. Pour des alternatives ouvertes, {board}consultez le tableau en direct</a>.",
            kn0=f"<b>Pas de billet.</b> La réservation SIMplifica et la taxe IFCN ne concernent que les sentiers gérés par l'IFCN ; le {code} est géré par la {body} ({faq}).",
            desc=[f"Le sentier {name} ({code}) est-il ouvert aujourd'hui ? Statut en direct selon l'IFCN. Géré par la mairie de Funchal : sans billet ni taxe IFCN.",
                  f"{name} ({code}) ouvert aujourd'hui ? Statut en direct selon l'IFCN. Géré par la mairie de Funchal : pas de billet SIMplifica ni de taxe IFCN."])
    if lang == "de":
        return dict(
            sub=f"Der heutige Status wird unten live angezeigt und stammt aus der offiziellen Hinweisliste des IFCN, mit dessen eigenem „aktualisiert“-Datum. Der Weg {full} ({code}) ist ein klassifizierter PR-Weg der {body}, nicht des IFCN: Er steht nicht auf SIMplifica und kostet keine IFCN-Gebühr.",
            book_h=f"Muss man den {name} buchen?",
            book=f"Nein. Der {code} wird von der {body} verwaltet, steht daher nicht im Buchungsportal SIMplifica und kostet keine IFCN-Gebühr ({faq}). Eine eigene Gebühr haben wir nicht gefunden. Führt Ihre Route auf einen vom IFCN verwalteten PR-Weg, braucht dieser Abschnitt ein SIMplifica-Ticket. Mehr unter {free}Wandern auf Madeira ohne Gebühr</a>.",
            cl_h=f"Was, wenn der {code} gesperrt ist?",
            cl=f"Zeigt der {code} gesperrt, gehen Sie ihn nicht: Sperrungen gelten für alle, mit oder ohne Ticket. Für offene Alternativen {board}die Live-Übersicht prüfen</a>.",
            kn0=f"<b>Kein Ticket nötig.</b> SIMplifica-Buchung und IFCN-Gebühr gelten nur für vom IFCN verwaltete Wege; der {code} gehört zur {body} ({faq}).",
            desc=[f"Ist der {name} ({code}) heute geöffnet? Live-Status laut offizieller IFCN-Liste. Von der Stadt Funchal verwaltet: ohne Ticket und ohne IFCN-Gebühr.",
                  f"{name} ({code}) heute geöffnet? Live-Status laut IFCN. Von der Stadt Funchal verwaltet: kein SIMplifica-Ticket, keine IFCN-Gebühr."])
    return dict(
        sub=f"Dzisiejszy status jest pokazywany na żywo poniżej, pochodzi z oficjalnej listy komunikatów IFCN i ma datę „aktualizacji” podaną przez IFCN. {full} ({code}) to sklasyfikowany szlak PR zarządzany przez {body}, a nie przez IFCN: nie ma go w SIMplifica i nie ma opłaty IFCN.",
        book_h=f"Czy {name} trzeba rezerwować?",
        book=f"Nie. {code} zarządza {body}, więc szlaku nie ma w portalu rezerwacji SIMplifica i nie ma opłaty IFCN ({faq}). Nie znaleźliśmy też własnej opłaty. Jeśli trasa wchodzi na szlak PR zarządzany przez IFCN, ten odcinek wymaga biletu SIMplifica. Więcej: {free}darmowe szlaki na Maderze</a>.",
        cl_h=f"Co jeśli {code} jest zamknięty?",
        cl=f"Jeśli {code} jest oznaczony jako zamknięty, nie wchodź na niego: zamknięcia dotyczą wszystkich, z biletem lub bez. Otwarte alternatywy znajdziesz na {board}tablicy na żywo</a>.",
        kn0=f"<b>Bez biletu.</b> Rezerwacja w SIMplifica i opłata IFCN dotyczą tylko szlaków zarządzanych przez IFCN; {code} zarządza {body} ({faq}).",
        desc=[f"Czy {name} ({code}) jest dziś otwarty? Status na żywo z oficjalnej listy IFCN. Zarządza nim gmina Funchal: bez biletu SIMplifica i bez opłaty IFCN.",
              f"Czy {name} ({code}) jest dziś otwarty? Status na żywo wg IFCN. Szlak gminy Funchal: bez biletu SIMplifica i bez opłaty IFCN."])


def T(lang, code, name, full, f, linear, start, end, typ):
    """Return a dict of every localised text slot for one language. `name` is
    the short name (headings, copy), `full` the official name (subtitle)."""
    allt = {"en": "all Madeira trails", "pt": "todos os percursos da Madeira", "fr": "tous les sentiers de Madère",
            "de": "alle Wanderwege Madeiras", "pl": "wszystkie szlaki Madery"}[lang]
    route = f"{start} → {end}" if (linear and start and end) else (start or "—")
    d = {}
    if lang == "en":
        d.update(
            h1=f"Is the {name} open today?",
            sub=f"Today's status is shown live below, taken from the official IFCN warnings list, which carries IFCN's own “updated” date. {full} ({code}) is a paid, booking-only PR trail; access is €4.50 through the SIMplifica portal.",
            loading="Trail status comes from the official IFCN warnings list, which IFCN updates when conditions change and dates itself (\"updated\"). It is shown here as a live badge (it needs JavaScript). If it doesn't appear, check the official sources linked below.",
            book_h=f"Do you need to book the {name}?",
            book=(f"Yes. {code} is booking-only: once it shows open, book your <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">€4.50 slot on SIMplifica</a> in advance. "
                  f"Under-12s and residents are free but must still be named on the booking. {code} is paid on its own separate booking and <b>not included</b> in the multi-day passes — check the live status above before you pay."),
            gt_h=f"Where does the {name} start and finish?",
            gt=(f"The {name} runs from <b>{start}</b> to <b>{end}</b>. It's a point-to-point walk, so it doesn't finish where you parked — sort your return first (two cars, a pre-booked taxi, or a guided walk with transfers)."
                if linear and start and end else
                f"The {name} starts and finishes at <b>{start or 'the trailhead'}</b>, so you return the way you came — no return transport to arrange."),
            gt_fact="It's a long mountain drive from the coast, with no shop or reliable signal at most trailheads. Bring water, warm and waterproof layers, and a torch — the weather turns fast up high.",
            cl_h=f"What if {code} is closed or fully booked?",
            cl=(f"If IFCN closes {code} (weather, landslip, works) or you can't get a slot: <b>reschedule</b> via the SIMplifica call centre before your date — you can move date/time freely, and switch trail only if yours was officially closed. "
                f"For open alternatives, <a class=\"plain\" href=\"{PREFIX[lang]}/\">check the live board</a>."),
            kn_h="Before you go",
            kn=[
                "<b>Booking-only.</b> Walking an IFCN classified trail without a valid SIMplifica ticket is an administrative offence (Portaria 801/2025 art. 10; DLR 24/2022/M art. 13); the law sets fines for individuals of €250–€2,500.",
                ("<b>It doesn't loop back.</b> You finish somewhere else — fix your return before you set off."
                 if linear and start and end else
                 "<b>It's out-and-back.</b> Turn around with enough time and daylight to walk out the way you came."),
                "<b>Check the live badge the morning you go.</b> Mountain trails close fast for weather, rockfall or works.",
            ],
            footer="Status comes from the official <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">IFCN warnings list</a>. Booking via <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, summit weather from <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. <a href=\"/privacy/#en\">Privacy policy</a>",
        )
    elif lang == "pt":
        A, a, da, o = pt_g(name)
        d.update(
            h1=f"{A} {name} está abert{o} hoje?",
            sub=f"O estado de hoje aparece em direto abaixo, com base na lista oficial de avisos do IFCN, com a data de «atualizado» do próprio IFCN. {pt_g(full)[0]} {full} ({code}) é um percurso PR pago e só com reserva; o acesso custa 4,50 € através do portal SIMplifica.",
            loading="O estado do percurso vem da lista oficial de avisos do IFCN, que o IFCN atualiza quando as condições mudam e data (\"atualizado\"). É mostrado aqui em direto (requer JavaScript). Se não aparecer, consulte as fontes oficiais indicadas abaixo.",
            book_h=f"É preciso reservar {a} {name}?",
            book=(f"Sim. O {code} só se faz com reserva: assim que aparecer como aberto, reserve com antecedência a sua <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">vaga de 4,50 € no SIMplifica</a>. "
                  f"Menores de 12 anos e residentes não pagam, mas têm de constar nominalmente da reserva. O {code} paga-se numa reserva própria e <b>não está incluído</b> nos passes de vários dias — confirme o estado em direto acima antes de pagar."),
            gt_h=f"Onde começa e termina {a} {name}?",
            gt=(f"{A} {name} vai de <b>{start}</b> até <b>{end}</b>. É um percurso linear, por isso não termina onde estacionou — trate primeiro do regresso (dois carros, um táxi reservado ou uma caminhada guiada com transporte incluído)."
                if linear and start and end else
                f"{A} {name} começa e termina " + (f"em <b>{start}</b>" if start else "no mesmo ponto de partida") + ", por isso regressa pelo mesmo caminho — não há transporte de regresso a organizar."),
            gt_fact="É uma longa viagem de montanha a partir da costa, sem loja nem rede fiável na maioria dos pontos de partida. Leve água, roupa quente e impermeável e uma lanterna — o tempo muda depressa em altitude.",
            cl_h=f"E se o {code} estiver fechado ou esgotado?",
            cl=(f"Se o IFCN fechar o {code} (mau tempo, derrocada, obras) ou se não conseguir vaga: <b>reagende</b> através da linha de apoio do SIMplifica antes da data — pode alterar livremente a data e a hora, e trocar de percurso apenas se o seu tiver sido oficialmente fechado. "
                f"Para alternativas abertas, <a class=\"plain\" href=\"{PREFIX[lang]}/\">consulte o quadro em direto</a>."),
            kn_h="Antes de ir",
            kn=[
                "<b>Só com reserva.</b> Percorrer um percurso classificado pelo IFCN sem bilhete SIMplifica válido é uma contraordenação (Portaria 801/2025, art. 10.º; DLR 24/2022/M, art. 13.º); a lei prevê coimas para particulares de 250 € a 2500 €.",
                ("<b>Não é circular.</b> Termina noutro local — trate do regresso antes de partir."
                 if linear and start and end else
                 "<b>É de ida e volta.</b> Dê meia-volta com tempo e luz do dia suficientes para regressar pelo mesmo caminho."),
                "<b>Confirme o indicador em direto na manhã em que for.</b> Os percursos de montanha fecham depressa por mau tempo, queda de pedras ou obras.",
            ],
            footer="O estado vem da <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">lista oficial de avisos do IFCN</a>. Reservas no <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, tempo no cume do <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. <a href=\"/privacy/#pt\">Política de privacidade</a>",
        )
    elif lang == "fr":
        fA, fa, fpr, fe = fr_g(name)
        d.update(
            h1=f"{fA} {name} est-{fpr} ouvert{fe} aujourd'hui ?",
            sub=f"Le statut du jour est affiché en direct ci-dessous, issu de la liste officielle des avis de l'IFCN, avec sa propre date de « mise à jour ». {fr_g(full)[0]} {full} ({code}) est un sentier PR payant, sur réservation ; l'accès coûte 4,50 € via le portail SIMplifica.",
            loading="L'état du sentier provient de la liste officielle des avis de l'IFCN, que l'IFCN met à jour quand les conditions changent et qu'il date lui-même (« mise à jour »). Il s'affiche ici en direct (JavaScript requis). S'il n'apparaît pas, consultez les sources officielles indiquées ci-dessous.",
            book_h=f"Faut-il réserver {fa} {name} ?",
            book=(f"Oui. Le {code} se fait uniquement sur réservation : une fois indiqué ouvert, réservez à l'avance votre <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">créneau à 4,50 € sur SIMplifica</a>. "
                  f"Les moins de 12 ans et les résidents sont gratuits mais doivent tout de même figurer sur la réservation. Le {code} se paie sur sa propre réservation distincte et n'est <b>pas inclus</b> dans les forfaits de plusieurs jours — vérifiez le statut en direct ci-dessus avant de payer."),
            gt_h=f"Où commence et où finit {fa} {name} ?",
            gt=(f"{fA} {name} va de <b>{start}</b> à <b>{end}</b>. C'est une randonnée point à point : elle ne se termine pas là où vous vous êtes garé — organisez d'abord votre retour (deux voitures, un taxi réservé, ou une randonnée guidée avec transferts)."
                if linear and start and end else
                f"{fA} {name} démarre et se termine à <b>{start or 'le départ'}</b> ; vous revenez par le même chemin — aucun transport de retour à organiser."),
            gt_fact="C'est un long trajet en montagne depuis la côte, sans magasin ni réseau fiable à la plupart des départs. Emportez de l'eau, des couches chaudes et imperméables, et une lampe — la météo change vite en altitude.",
            cl_h=f"Et si le {code} est fermé ou complet ?",
            cl=(f"Si l'IFCN ferme le {code} (météo, glissement, travaux) ou si vous ne trouvez pas de créneau : <b>reprogrammez</b> via le centre d'appels SIMplifica avant votre date — vous pouvez modifier librement date et heure, et changer de sentier uniquement si le vôtre a été officiellement fermé. "
                f"Pour des alternatives ouvertes, <a class=\"plain\" href=\"{PREFIX[lang]}/\">consultez le tableau en direct</a>."),
            kn_h="Avant de partir",
            kn=[
                "<b>Sur réservation uniquement.</b> Parcourir un sentier classé par l'IFCN sans billet SIMplifica valide est une infraction administrative (Portaria 801/2025 art. 10 ; DLR 24/2022/M art. 13) ; la loi prévoit pour les particuliers des amendes de 250 € à 2 500 €.",
                (f"<b>{fpr.capitalize()} ne boucle pas.</b> Vous finissez ailleurs — réglez votre retour avant de partir."
                 if linear and start and end else
                 "<b>C'est un aller-retour.</b> Faites demi-tour avec assez de temps et de lumière pour revenir par le même chemin."),
                "<b>Vérifiez le badge en direct le matin même.</b> Les sentiers de montagne ferment vite pour météo, chutes de pierres ou travaux.",
            ],
            footer="L'état provient de la <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">liste officielle des avis de l'IFCN</a>. Réservation via <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, météo du sommet fournie par l'<a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. <a href=\"/privacy/#fr\">Politique de confidentialité</a>",
        )
    elif lang == "de":
        dA, da_, dpr, dacc = de_g(name)
        d.update(
            h1=f"Ist {da_} {name} heute geöffnet?",
            sub=f"Der heutige Status wird unten live angezeigt und stammt aus der offiziellen Hinweisliste des IFCN, mit dessen eigenem „aktualisiert“-Datum. {de_g(full)[0]} {full} ({code}) ist ein kostenpflichtiger PR-Weg nur mit Buchung; der Zugang kostet 4,50 € über das SIMplifica-Portal.",
            loading="Der Wegestatus stammt aus der offiziellen Hinweisliste des IFCN, die das IFCN bei Änderungen aktualisiert und selbst datiert („aktualisiert“). Er wird hier live angezeigt (dafür ist JavaScript nötig). Falls er nicht erscheint, prüfen Sie die unten verlinkten offiziellen Quellen.",
            book_h=f"Muss man {dacc} {name} buchen?",
            book=(f"Ja. Der {code} ist nur mit Buchung begehbar: Sobald er als geöffnet angezeigt wird, buchen Sie Ihren <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">4,50-€-Slot auf SIMplifica</a> im Voraus. "
                  f"Kinder unter 12 und Einwohner sind frei, müssen aber trotzdem namentlich in der Buchung stehen. Der {code} wird als eigene, gesonderte Buchung bezahlt und ist <b>nicht</b> in den Mehrtagespässen enthalten — prüfen Sie den Live-Status oben, bevor Sie bezahlen."),
            gt_h=f"Wo beginnt und endet {da_} {name}?",
            gt=(f"{dA} {name} verläuft von <b>{start}</b> nach <b>{end}</b>. Es ist eine Streckenwanderung, sie endet also nicht dort, wo Sie geparkt haben — klären Sie zuerst den Rückweg (zwei Autos, ein vorab gebuchtes Taxi oder eine geführte Wanderung mit Transfers)."
                if linear and start and end else
                f"{dA} {name} beginnt und endet an <b>{start or 'dem Ausgangspunkt'}</b>, Sie kehren also denselben Weg zurück — kein Rücktransport zu organisieren."),
            gt_fact="Es ist eine lange Bergfahrt von der Küste, an den meisten Ausgangspunkten ohne Laden oder verlässlichen Empfang. Nehmen Sie Wasser, warme und wasserdichte Kleidung sowie eine Lampe mit — das Wetter schlägt oben schnell um.",
            cl_h=f"Was tun, wenn der {code} gesperrt oder ausgebucht ist?",
            cl=(f"Wenn die IFCN den {code} sperrt (Wetter, Erdrutsch, Arbeiten) oder Sie keinen Slot bekommen: <b>Umbuchen</b> über das SIMplifica-Callcenter vor Ihrem Termin — Datum und Uhrzeit frei änderbar, den Weg wechseln nur, wenn Ihrer offiziell gesperrt war. "
                f"Offene Alternativen finden Sie auf der <a class=\"plain\" href=\"{PREFIX[lang]}/\">Live-Tafel</a>."),
            kn_h="Vor dem Start",
            kn=[
                "<b>Nur mit Buchung.</b> Einen vom IFCN klassifizierten Weg ohne gültiges SIMplifica-Ticket zu gehen ist eine Ordnungswidrigkeit (Portaria 801/2025 Art. 10; DLR 24/2022/M Art. 13); das Gesetz sieht für Privatpersonen Bußgelder von 250 € bis 2.500 € vor.",
                (f"<b>{dpr} führt nicht im Kreis zurück.</b> Sie enden woanders — regeln Sie den Rückweg vor dem Start."
                 if linear and start and end else
                 "<b>Hin und zurück.</b> Drehen Sie mit genug Zeit und Tageslicht um, um denselben Weg zurückzugehen."),
                "<b>Prüfen Sie das Live-Abzeichen am Morgen Ihrer Tour.</b> Bergwege werden schnell wegen Wetter, Steinschlag oder Arbeiten gesperrt.",
            ],
            footer="Der Status stammt aus der <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">offiziellen IFCN-Warnliste</a>. Buchung über <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, Gipfelwetter von <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. <a href=\"/privacy/#de\">Datenschutzerklärung</a>",
        )
    else:  # pl
        d.update(
            h1=f"Czy {name} jest dziś otwarta?",
            sub=f"Dzisiejszy status jest pokazywany na żywo poniżej, pochodzi z oficjalnej listy komunikatów IFCN i ma datę „aktualizacji” podaną przez IFCN. {full} ({code}) to płatny szlak PR wyłącznie na rezerwację; wstęp kosztuje 4,50 € przez portal SIMplifica.",
            loading="Stan szlaku pochodzi z oficjalnej listy komunikatów IFCN, którą IFCN aktualizuje, gdy zmieniają się warunki, i sam datuje („aktualizacja”). Jest pokazywany tutaj na żywo (wymaga JavaScriptu). Jeśli się nie pojawi, sprawdź oficjalne źródła podane poniżej.",
            book_h=f"Czy trzeba rezerwować {name}?",
            book=(f"Tak. {code} jest wyłącznie na rezerwację: gdy pokaże się jako otwarty, zarezerwuj z wyprzedzeniem swój <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">slot za 4,50 € w SIMplifica</a>. "
                  f"Dzieci poniżej 12 lat i mieszkańcy są bezpłatnie, ale i tak muszą być imiennie w rezerwacji. {code} jest płatny jako osobna rezerwacja i <b>nie jest wliczony</b> w karnety wielodniowe — sprawdź status na żywo powyżej, zanim zapłacisz."),
            gt_h=f"Gdzie zaczyna się i kończy {name}?",
            gt=(f"{name} biegnie od <b>{start}</b> do <b>{end}</b>. To trasa z punktu do punktu, więc nie kończy się tam, gdzie zaparkowałeś — najpierw załatw powrót (dwa auta, zamówiona taksówka lub wędrówka z przewodnikiem i transferami)."
                if linear and start and end else
                f"{name} zaczyna się i kończy w <b>{start or 'punkcie startowym'}</b>, więc wracasz tą samą drogą — nie trzeba organizować powrotu."),
            gt_fact="To długi górski dojazd od wybrzeża, przy większości początków szlaków bez sklepu i pewnego zasięgu. Weź wodę, ciepłe i wodoodporne warstwy oraz latarkę — pogoda w górach zmienia się szybko.",
            cl_h=f"Co zrobić, gdy {code} jest zamknięty lub pełny?",
            cl=(f"Jeśli IFCN zamknie {code} (pogoda, osuwisko, prace) lub nie zdobędziesz slotu: <b>przełóż termin</b> przez infolinię SIMplifica przed swoją datą — datę i godzinę zmieniasz dowolnie, a szlak tylko wtedy, gdy twój został oficjalnie zamknięty. "
                f"Otwarte alternatywy znajdziesz na <a class=\"plain\" href=\"{PREFIX[lang]}/\">tablicy na żywo</a>."),
            kn_h="Zanim wyruszysz",
            kn=[
                "<b>Wyłącznie na rezerwację.</b> Przejście szlaku sklasyfikowanego przez IFCN bez ważnego biletu SIMplifica to wykroczenie administracyjne (Portaria 801/2025 art. 10; DLR 24/2022/M art. 13); przepisy przewidują dla osób fizycznych grzywny od 250 € do 2500 €.",
                ("<b>Nie wraca pętlą.</b> Kończysz w innym miejscu — załatw powrót przed wyruszeniem."
                 if linear and start and end else
                 "<b>Trasa tam i z powrotem.</b> Zawracaj z zapasem czasu i światła, by wrócić tą samą drogą."),
                "<b>Sprawdź plakietkę na żywo w dniu wyjścia.</b> Górskie szlaki szybko zamyka się z powodu pogody, obrywów lub prac.",
            ],
            footer="Stan pochodzi z <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">oficjalnej listy ostrzeżeń IFCN</a>. Rezerwacja przez <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, pogoda na szczycie z <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. <a href=\"/privacy/#pl\">Polityka prywatności</a>",
        )
    d["title"], d["desc"] = titles(lang, code, name)
    if code in NO_IFCN_FEE:
        nf = no_fee_texts(lang, code, name, full, NO_IFCN_FEE[code])
        d["desc"] = fit(nf.pop("desc"), 120, 155)
        d["kn"][0] = nf.pop("kn0")
        d.update(nf)
        d["title"] = d["title"].replace(" & booking", "").replace(" e reserva", "").replace(" et réservation", "") \
            .replace(" ? Réservation", " ?").replace(" & Buchung", "").replace(" i rezerwacja", "") \
            .replace("? Booking", "?").replace("? Reserva", "?").replace("? Buchung", "?").replace("? Rezerwacja", "?")
    d["typ"] = typ
    d["route"] = route
    d["allt"] = allt
    return d


CSS = """*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:var(--paper); color:var(--ink); line-height:1.55; padding:0 0 40px}
.waymark{height:14px;background:linear-gradient(180deg,var(--way-yellow) 0 50%,var(--way-red) 50% 100%)}
.wrap{max-width:960px;margin:0 auto;padding:0 20px;
  display:grid;grid-template-columns:minmax(0,1fr) 240px;column-gap:32px;align-items:start}
.wrap > :not(.facts){grid-column:1}
header{padding:18px 0 6px}
.langs{display:flex;gap:6px;margin:0 0 4px;list-style:none;padding:0}
.langs a{font-size:12px;font-weight:700;letter-spacing:.04em;text-decoration:none;color:var(--ink-soft);
  padding:3px 9px;border:1px solid var(--line);border-radius:999px}
.langs a[aria-current="page"]{background:var(--ink);color:#fff;border-color:var(--ink)}
.brand{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-soft);font-weight:600}
h1{font-size:clamp(26px,7vw,34px);line-height:1.12;font-weight:800;letter-spacing:-.02em;margin:6px 0 2px}
.sub{color:var(--ink-soft);font-size:15px}
.sub a{color:var(--ink);font-weight:600}
.status-card{background:var(--card);border:1px solid var(--line);border-radius:14px;
  margin-top:18px;overflow:hidden;box-shadow:0 1px 3px rgba(22,52,42,.06)}
.status-head{display:flex;align-items:center;gap:14px;padding:18px 18px 12px}
.status-badge{font-size:clamp(30px,9vw,42px);font-weight:900;letter-spacing:-.01em}
.status-badge.OPEN{color:var(--open)}.status-badge.PARTIAL{color:var(--partial)}.status-badge.CLOSED{color:var(--closed)}
.status-dot{width:16px;height:16px;border-radius:50%;flex:0 0 auto}
.status-dot.OPEN{background:var(--open)}.status-dot.PARTIAL{background:var(--partial)}.status-dot.CLOSED{background:var(--closed)}
.status-body{padding:0 18px 16px;font-size:15px}
.status-body p{margin-bottom:8px}
.stamp{border-top:1px dashed var(--line);padding:10px 18px;font-size:13px;color:var(--ink-soft);
  font-variant-numeric:tabular-nums;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.stamp b{color:var(--ink)}
.facts{grid-column:2;grid-row:2 / span 8;align-self:start;margin-top:18px;background:var(--card);
  border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:0 1px 3px rgba(22,52,42,.06)}
.facts h2{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-soft);font-weight:700;margin-bottom:8px}
.facts dl{display:grid;grid-template-columns:auto 1fr;gap:5px 10px;font-size:14px;margin:0}
.facts dt{color:var(--ink-soft)}
.facts dd{font-weight:650;text-align:right}
section{margin-top:30px}
h2{font-size:20px;font-weight:800;letter-spacing:-.01em;margin-bottom:10px}
h2 .q{color:var(--way-red)}
p{margin-bottom:10px;font-size:15.5px}
ol,ul{padding-left:22px;margin-bottom:10px}
li{margin-bottom:8px;font-size:15.5px}
.fact{background:#F2F1E9;border-left:4px solid var(--way-yellow);padding:10px 14px;border-radius:0 8px 8px 0;font-size:14.5px;margin:12px 0}
.waymark.thin{height:8px;margin:28px 0;border-radius:2px}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);font-size:12.5px;color:var(--ink-soft)}
footer a{color:var(--ink-soft)}
a.plain{color:var(--ink);font-weight:600}
@media (max-width:760px){
  .wrap{grid-template-columns:1fr;padding:0 16px}
  .wrap > *{grid-column:1}
  .facts{grid-row:auto}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}"""


def facts_rows(lang, f, linear, typ, code=None):
    rows = []
    if f.get("distance"):
        rows.append((LBL["distance"][lang], f["distance"]))
    if f.get("duration"):
        rows.append((LBL["time"][lang], f["duration"]))
    if f.get("difficulty"):
        rows.append((LBL["difficulty"][lang], DIFF.get(f["difficulty"], {}).get(lang, f["difficulty"])))
    if f.get("alt_min") and f.get("alt_max"):
        rows.append((LBL["altitude"][lang], f'{f["alt_min"]}–{f["alt_max"]} m'))
    if linear and f.get("start") and f.get("end"):
        rows.append((LBL["route"][lang], f'{f["start"]} → {f["end"]}'))
    rows.append((LBL["type"][lang], typ))
    rows.append((LBL["fee"][lang], NOFEE_ROW[lang] if code in NO_IFCN_FEE else ("4,50 €" if lang == "pt" else "€4.50")))
    return "".join(f"    <dt>{k}</dt><dd>{v}</dd>\n" for k, v in rows)


def plain(s):
    """Visible text of an HTML snippet (for the FAQ JSON-LD: same words as the page)."""
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def attr(s):
    return htmllib.escape(s, quote=True)


def attraction(lang, code, full, canon, f, linear, typ, geo, image):
    """TouristAttraction JSON-LD: only the facts shown in the page's facts box."""
    props = []
    names = {"en": ("Distance", "Difficulty", "Duration", "Altitude", "Route type"),
             "pt": ("Distância", "Dificuldade", "Duração", "Altitude", "Tipo de percurso"),
             "fr": ("Distance", "Difficulté", "Durée", "Altitude", "Type d'itinéraire"),
             "de": ("Distanz", "Schwierigkeit", "Dauer", "Höhe", "Streckentyp"),
             "pl": ("Dystans", "Trudność", "Czas", "Wysokość", "Typ trasy")}[lang]
    vals = (f.get("distance"),
            DIFF.get(f["difficulty"], {}).get(lang, f["difficulty"]) if f.get("difficulty") else None,
            f.get("duration"),
            f'{f["alt_min"]}–{f["alt_max"]} m' if f.get("alt_min") and f.get("alt_max") else None,
            typ)
    for k, v in zip(names, vals):
        if v:
            props.append({"@type": "PropertyValue", "name": k, "value": v})
    o = {"@context": "https://schema.org", "@type": "TouristAttraction",
         "name": f"{full} ({code})", "alternateName": code, "url": canon, "touristType": "Hikers",
         # PR3 / PR3.1 / PR4 / PR23 are run by other bodies: no IFCN fee, no SIMplifica ticket.
         "isAccessibleForFree": code in NO_IFCN_FEE}
    if image:
        o["image"] = image
    if geo:
        o["geo"] = {"@type": "GeoCoordinates", "latitude": round(geo[0], 6), "longitude": round(geo[1], 6)}
    o["additionalProperty"] = props
    return o


def build(lang, code, full, slug, f, linear, typ, geo=None):
    name = short_name(code, full)
    start, end = f.get("start"), f.get("end")
    t = T(lang, code, name, full, f, linear, start, end, typ)
    photo = PHOTOS.get(code)
    preload = ""
    if photo:
        webp = "/img/" + re.sub(r"\.jpe?g$", ".webp", photo["file"])
        og_img = f"{SITE}/img/{photo['file']}"
        og_alt = f"{name} ({code}), Madeira"
        preload = f'<link rel="preload" as="image" href="{webp}" fetchpriority="high">\n'
        hero_rule = (f".hero{{height:210px;background:#20573a url({webp}) center/cover}}\n"
                     "@media (max-width:640px){.hero{height:150px}}")
        word, resized = PHOTO_CREDIT[lang]
        lic = photo["lic"] + ((" (domínio público)" if lang == "pt" else " (public domain)") if photo["lic"] == "CC0" else "")
        sep = " :" if lang == "fr" else ":"
        footer_extra = (f'\n  <p style="margin-top:6px">{word}{sep} {photo["author"]}, '
                        f'<a href="https://commons.wikimedia.org/wiki/Main_Page" target="_blank" rel="noopener">Wikimedia Commons</a>, {lic}, {resized}.</p>')
    else:
        og_img, og_alt = OG_DEFAULT, BRAND[lang]
        hero_rule = ".hero{height:130px;background:#20573a}"
        footer_extra = ""
    canon = f"https://levadinho-madeira.com{PREFIX[lang]}/{slug}/"
    alts = "\n".join(
        f'<link rel="alternate" hreflang="{hl}" href="https://levadinho-madeira.com{PREFIX[hl]}/{slug}/">'
        for hl in LANGS
    ) + f'\n<link rel="alternate" hreflang="x-default" href="https://levadinho-madeira.com/{slug}/">'
    langnav = "\n".join(
        f'    <a href="{PREFIX[hl]}/{slug}/" hreflang="{hl}"{" aria-current=\"page\"" if hl==lang else ""}>{hl.upper()}</a>'
        for hl in LANGS
    )
    # FAQ = the visible question headings + the visible paragraph under each.
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": plain(q), "acceptedAnswer": {"@type": "Answer", "text": plain(a)}}
            for q, a in ((t["h1"], t["sub"]), (t["book_h"], t["book"]), (t["gt_h"], t["gt"]), (t["cl_h"], t["cl"]))
        ],
    }
    place = region_place(code)
    wx_section = ""
    if place:
        wq, wa = weather_qa(lang, name, place)
        faq["mainEntity"].append({"@type": "Question", "name": wq, "acceptedAnswer": {"@type": "Answer", "text": wa}})
        wx_section = weather_section(lang, name, code, place)
    ta = attraction(lang, code, full, canon, f, linear, typ, geo, og_img if photo else None)
    know = "\n".join(f"    <li>{b}</li>" for b in t["kn"])
    P = PREFIX[lang]
    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<!-- CONFIG — analytics only. Live status is loaded from /status.json. -->
<script>
const CONFIG = {{ goatcounterCode: "madeira-levadinho" }};
</script>

<title>{htmllib.escape(t['title'], quote=False)}</title>
<meta name="description" content="{attr(t['desc'])}">

<link rel="canonical" href="{canon}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{attr(t['title'])}">
<meta property="og:description" content="{attr(t['desc'])}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:alt" content="{attr(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/img/icon-180.png">
{preload}
{alts}

<script src="/status.js" defer></script>

<script type="application/ld+json">
{json.dumps(faq, ensure_ascii=False, indent=2)}
</script>
<script type="application/ld+json">
{json.dumps(ta, ensure_ascii=False, indent=2)}
</script>
<script type="application/ld+json">
{json.dumps(webpage_ld(t['title'], canon, lang), ensure_ascii=False, indent=2)}
</script>

<style>
:root{{
  --paper:#FAFAF7; --ink:#16342A; --ink-soft:#4A5F56;
  --way-yellow:#E8B71A; --way-red:#BE3A2B;
  --open:#1E7A45; --partial:#946000; --closed:#B3372E;
  --card:#FFFFFF; --line:#E3E1D8;
}}
{CSS}
{hero_rule}
</style>
</head>
<body>
<div class="waymark" aria-hidden="true"></div>
<div class="hero" aria-hidden="true"></div>

<div class="wrap">
<header>
  <nav class="langs" aria-label="Language">
{langnav}
  </nav>
  <div class="brand">{BRAND[lang]}</div>
  <h1>{t['h1']}</h1>
  <p class="sub">{t['sub']} {SEE[lang]} <a href="{P}/">{t['allt']}</a> · <a href="{P}/pr1/">PR1</a>.</p>
</header>

<div class="status-card" id="statusCard" data-trail="{code}">
  <div class="status-body"><p class="static-status"><!-- STATIC-STATUS:{code}:START --><!-- STATIC-STATUS:{code}:END --></p><p class="static-weather"><!-- STATIC-WEATHER:{code}:START --><!-- STATIC-WEATHER:{code}:END --></p><p>{t['loading']}</p></div>
</div>

<aside class="facts">
  <h2>{LBL['facts'][lang]}</h2>
  <dl>
{facts_rows(lang, f, linear, t['typ'], code)}  </dl>
{gen_trail_extras.facts_block(code, lang, EXTRAS)}{map_block(lang, name, geo, f)}</aside>

<div class="waymark thin" aria-hidden="true"></div>

<section id="book">
  <h2>{t['book_h']}</h2>
  <p>{t['book']}</p>
</section>

<section id="getting-there">
  <h2>{t['gt_h']}</h2>
  <p>{t['gt']}</p>
  <div class="fact">{t['gt_fact']}</div>
</section>

{wx_section}<section id="closed">
  <h2>{t['cl_h']}</h2>
  <p>{t['cl']}</p>
</section>

<section id="know">
  <h2>{t['kn_h']}</h2>
  <ul>
{know}
  </ul>
</section>

<footer>
  <p>{t['footer']}</p>{footer_extra}
</footer>
</div>

<script>
(function(){{
  var c = CONFIG;
  try {{ if (location.hash === '#skipgc') localStorage.setItem('gc-skip','1');
        if (location.hash === '#countme') localStorage.removeItem('gc-skip'); }} catch(e){{}}
  var SKIP = (function(){{ try {{ return localStorage.getItem('gc-skip')==='1'; }} catch(e){{ return false; }} }})();
  if (c.goatcounterCode && !SKIP){{
    var s = document.createElement('script');
    s.dataset.goatcounter = 'https://' + c.goatcounterCode + '.goatcounter.com/count';
    s.async = true; s.src = '//gc.zgo.at/count.js';
    document.body.appendChild(s);
  }}
}})();
</script>
</body>
</html>
"""
    return html


def route_kind(f):
    start, end = f.get("start"), f.get("end")
    if f.get("round_trip"):
        return "oab"
    if f.get("circular"):
        return "circ"
    if start and end and slugify(start) != slugify(end):
        return "p2p"
    return "oab"


def render(code, name, url, geo):
    """-> (slug, kind, facts, {lang: html}) for one trail."""
    try:
        f = scrape_facts(url)
    except Exception as e:
        print("  scrape failed", code, e); f = {}
    kind = route_kind(f)
    linear = kind == "p2p"          # "one-way": you don't finish where you started
    slug = slugify(name)
    pages = {lang: build(lang, code, name, slug, f, linear, TYP[kind][lang], geo) for lang in LANGS}
    return slug, kind, f, pages


def coords():
    # Same trailhead lookup as the "Nearby trails" block (Visit Madeira index).
    import gen_site_nav
    return gen_site_nav.trail_coords()


def dry_run(code, out):
    """Render one trail in all 5 languages into `out` (never the repo) and print
    the title / description of every generated trail with their lengths."""
    if os.path.abspath(out).startswith(ROOT + os.sep) or os.path.abspath(out) == ROOT:
        sys.exit("dry-run output must be outside the repo")
    urls = trail_urls()
    geo = coords()
    data = json.load(open(os.path.join(ROOT, "status.json")))
    names = {t["code"]: t["name"] for t in data["trails"]}
    slug, kind, f, pages = render(code, names[code], urls[code], geo.get(code))
    for lang, h in pages.items():
        d = os.path.join(out, lang, slug)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(h)
    print(f"{code} facts: {f}\ngeo: {geo.get(code)}\nwrote {out}/<lang>/{slug}/index.html")
    for t in data["trails"]:
        if t["code"] in HAVE:
            continue
        n = short_name(t["code"], t["name"])
        for lang in LANGS:
            ti, de = titles(lang, t["code"], n)
            print(f"  {t['code']:6} {lang} T{len(ti):3} D{len(de):3} | {ti}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        if len(sys.argv) != 4:
            sys.exit("usage: gen_spokes.py --dry-run CODE OUTDIR")
        return dry_run(sys.argv[2], sys.argv[3])
    urls = trail_urls()
    geo = coords()
    data = json.load(open(os.path.join(ROOT, "status.json")))
    targets = [t for t in data["trails"] if t["code"] not in HAVE]
    pages_map, sitemap_blocks, summary = {}, [], []
    for t in targets:
        code, name = t["code"], t["name"]
        url = urls.get(code)
        if not url:
            print("  SKIP (no url):", code); continue
        slug, kind, f, pages = render(code, name, url, geo.get(code))
        pages_map[code] = f"/{slug}/"
        for lang in LANGS:
            d = os.path.join(ROOT, PREFIX[lang].lstrip("/"), slug) if PREFIX[lang] else os.path.join(ROOT, slug)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(pages[lang])
        for lang in LANGS:
            loc = f"https://levadinho-madeira.com{PREFIX[lang]}/{slug}/"
            block = [f"  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>2026-07-08</lastmod>",
                     f"    <changefreq>daily</changefreq>", f"    <priority>0.7</priority>"]
            for hl in LANGS:
                block.append(f'    <xhtml:link rel="alternate" hreflang="{hl}" href="https://levadinho-madeira.com{PREFIX[hl]}/{slug}/"/>')
            block.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="https://levadinho-madeira.com/{slug}/"/>')
            block.append("  </url>")
            sitemap_blocks.append("\n".join(block))
        summary.append((code, kind, f.get("distance", "?"), f.get("duration", "?"), f.get("difficulty", "-")))
    json.dump({"pages": pages_map, "sitemap": sitemap_blocks}, open("/tmp/gen_out.json", "w"))
    print(f"\nGenerated {len(pages_map)} trails × {len(LANGS)} langs = {len(pages_map)*len(LANGS)} pages")
    for row in summary:
        print("  ", row)
    # The pages were just rewritten from scratch: put the nav, breadcrumbs and
    # nearby-trails blocks back (see gen_site_nav.py).
    import gen_site_nav
    gen_site_nav.main()
    # ...and the Levadinho WhatsApp block (see gen_cta.py). The STATIC-STATUS markers in
    # each card start empty; the next `python scripts/update_status.py` fills them.
    import gen_cta
    gen_cta.main()
    # ...and the "By bus" sections from the operators' timetables (see gen_bus.py).
    import gen_bus
    gen_bus.main()
    # ...and the car-park webcams (see gen_webcam.py).
    import gen_webcam
    gen_webcam.main()
    # ...and complete the TouristAttraction blocks (description, address, image; see gen_schema.py).
    # ...trail code in the headings and the facts list as a table (see gen_trail_polish.py).
    import gen_trail_polish
    gen_trail_polish.main()
    import gen_schema
    gen_schema.main()


if __name__ == "__main__":
    main()
