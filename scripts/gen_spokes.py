#!/usr/bin/env python3
"""One-off generator for the long-tail trail spoke pages.

Builds a lightweight, live-status-first spoke page (en/fr/de/pl) for every PR
trail that doesn't already have a hand-authored spoke. Facts (distance,
difficulty, duration, altitude, start/end) are scraped from each trail's
official Visit Madeira page so nothing is invented. Long-tail pages use a
plain hero (no photo) — the hand-authored flagship spokes keep their photos.

Run from the repo root:  python scripts/gen_spokes.py
It writes the HTML files, prints the PAGES entries to add, and prints the
sitemap <url> blocks to append. Wiring into update_status.py / sitemap.xml is
done by the caller (kept out of here so the scrape stays side-effect-light).
"""
import json, os, re, sys, unicodedata, urllib.request

UA = {"User-Agent": "LevadinhoBot/1.0 (https://madeira.maykef.info)"}
BASE = "https://visitmadeira.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
PHOTO_CREDIT = {
    "en": ("Photo", "resized"), "fr": ("Photo", "redimensionnée"),
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
    m = re.search(r"Start\s*/\s*End:\s*(.+?)\s+(?:Route|Nature|Recommended|Duration|Distance|Type|Level|$)", text)
    if m:
        se = m.group(1)
        parts = [p.strip() for p in se.split("/") if p.strip()]
        # split on ' / ' but road refs contain '/', so rebuild by the last standalone name
        se2 = re.split(r"\s/\s", se)
        if len(se2) >= 2:
            f["start"] = re.sub(r"\s*\(.*?\)\s*", "", se2[0]).strip()
            f["end"] = re.sub(r"\s*\(.*?\)\s*", "", se2[-1]).strip()
    return f


# ---- localised strings -------------------------------------------------------
DIFF = {
    "Easy":       {"en": "Easy", "fr": "Facile", "de": "Leicht", "pl": "Łatwa"},
    "Moderate":   {"en": "Moderate", "fr": "Modérée", "de": "Mittel", "pl": "Umiarkowana"},
    "Difficult":  {"en": "Hard", "fr": "Difficile", "de": "Schwer", "pl": "Trudna"},
    "Hard":       {"en": "Hard", "fr": "Difficile", "de": "Schwer", "pl": "Trudna"},
}
OAB = {"en": "Out-and-back", "fr": "Aller-retour", "de": "Hin und zurück", "pl": "Tam i z powrotem"}
P2P = {"en": "Point-to-point", "fr": "Point à point", "de": "Punkt zu Punkt", "pl": "Z punktu do punktu"}
CIRC = {"en": "Circular", "fr": "Boucle", "de": "Rundweg", "pl": "Pętla"}
TYP = {"oab": OAB, "circ": CIRC, "p2p": P2P}
LBL = {
    "distance":   {"en": "Distance", "fr": "Distance", "de": "Distanz", "pl": "Dystans"},
    "time":       {"en": "Time", "fr": "Durée", "de": "Dauer", "pl": "Czas"},
    "difficulty": {"en": "Difficulty", "fr": "Difficulté", "de": "Schwierigkeit", "pl": "Trudność"},
    "altitude":   {"en": "Altitude", "fr": "Altitude", "de": "Höhe", "pl": "Wysokość"},
    "route":      {"en": "Route", "fr": "Itinéraire", "de": "Strecke", "pl": "Trasa"},
    "type":       {"en": "Type", "fr": "Type", "de": "Typ", "pl": "Typ"},
    "fee":        {"en": "Fee", "fr": "Tarif", "de": "Gebühr", "pl": "Opłata"},
    "facts":      {"en": "Trail facts", "fr": "Infos sur le sentier", "de": "Weg-Fakten", "pl": "Fakty o szlaku"},
    "hours":      {"en": "h", "fr": "h", "de": "Std.", "pl": "godz."},
}
BRAND = {
    "en": "Levadinho · Madeira trail answers",
    "fr": "Levadinho · Réponses sur les sentiers de Madère",
    "de": "Levadinho · Antworten zu Madeiras Wanderwegen",
    "pl": "Levadinho · Odpowiedzi o szlakach Madery",
}
PREFIX = {"en": "", "fr": "/fr", "de": "/de", "pl": "/pl"}
SEE = {"en": "See", "fr": "Voir", "de": "Siehe", "pl": "Zobacz"}


def T(lang, code, name, f, linear, start, end, typ):
    """Return a dict of every localised text slot for one language."""
    allt = {"en": "all Madeira trails", "fr": "tous les sentiers de Madère",
            "de": "alle Wanderwege Madeiras", "pl": "wszystkie szlaki Madery"}[lang]
    route = f"{start} → {end}" if (linear and start and end) else (start or "—")
    d = {}
    if lang == "en":
        d.update(
            title=f"Is the {name} open today? {name} ({code}) status &amp; booking",
            desc=f"Live status for the {name} ({code}) — is it open today? How to book the €4.50 SIMplifica slot, the trail facts, and open alternatives if it's closed.",
            h1=f"Is the {name} open today?",
            sub=f"{name} ({code}) — a paid, booking-only PR trail. Checked every morning against official IFCN status.",
            loading=f"Loading today's status for the {name}… if it doesn't appear, check the official sources linked below.",
            book_h=f'<span class="q">Book it.</span> {code} on SIMplifica',
            book=(f"Once it shows open, book your <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">€4.50 slot on SIMplifica</a> in advance. "
                  f"Under-12s and residents are free but must still be named on the booking. {code} is paid on its own separate booking and <b>not included</b> in the multi-day passes — check the live status above before you pay."),
            gt_h=f'<span class="q">Getting there.</span> Start &amp; finish',
            gt=(f"The {name} runs from <b>{start}</b> to <b>{end}</b>. It's a point-to-point walk, so it doesn't finish where you parked — sort your return first (two cars, a pre-booked taxi, or a guided walk with transfers)."
                if linear and start and end else
                f"The {name} starts and finishes at <b>{start or 'the trailhead'}</b>, so you return the way you came — no return transport to arrange."),
            gt_fact="It's a long mountain drive from the coast, with no shop or reliable signal at most trailheads. Bring water, warm and waterproof layers, and a torch — the weather turns fast up high.",
            cl_h=f'<span class="q">Closed or full?</span> Your options',
            cl=(f"If IFCN closes {code} (weather, landslip, works) or you can't get a slot: <b>reschedule</b> via the SIMplifica call centre before your date — you can move date/time freely, and switch trail only if yours was officially closed. "
                f"For open alternatives, <a class=\"plain\" href=\"{PREFIX[lang]}/trails/\">check the live board</a>."),
            kn_h="Before you go",
            kn=[
                "<b>Booking-only.</b> Walking a paid PR trail without a valid SIMplifica ticket is an infraction, with fines reported up to €250.",
                ("<b>It doesn't loop back.</b> You finish somewhere else — fix your return before you set off."
                 if linear and start and end else
                 "<b>It's out-and-back.</b> Turn around with enough time and daylight to walk out the way you came."),
                "<b>Check the live badge the morning you go.</b> Mountain trails close fast for weather, rockfall or works.",
            ],
            footer="Status compiled each morning from IFCN (ifcn.madeira.gov.pt) and SIMplifica, with weather from IPMA (ipma.pt). Independent — not affiliated with the Madeira Regional Government. Conditions change fast in the mountains; always use your own judgement on the trail.",
        )
    elif lang == "fr":
        d.update(
            title=f"La {name} est-elle ouverte aujourd'hui ? {name} ({code}) : statut et réservation",
            desc=f"Statut en direct de la {name} ({code}) — est-elle ouverte aujourd'hui ? Comment réserver le créneau SIMplifica à 4,50 €, les infos du sentier et les alternatives ouvertes.",
            h1=f"La {name} est-elle ouverte aujourd'hui ?",
            sub=f"{name} ({code}) — un sentier PR payant, sur réservation. Vérifié chaque matin par rapport au statut officiel de l'IFCN.",
            loading=f"Chargement du statut du jour pour la {name}… s'il ne s'affiche pas, consultez les sources officielles indiquées ci-dessous.",
            book_h=f'<span class="q">Réservez.</span> Le {code} sur SIMplifica',
            book=(f"Une fois indiqué ouvert, réservez à l'avance votre <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">créneau à 4,50 € sur SIMplifica</a>. "
                  f"Les moins de 12 ans et les résidents sont gratuits mais doivent tout de même figurer sur la réservation. Le {code} se paie sur sa propre réservation distincte et n'est <b>pas inclus</b> dans les forfaits de plusieurs jours — vérifiez le statut en direct ci-dessus avant de payer."),
            gt_h=f'<span class="q">Y aller.</span> Départ &amp; arrivée',
            gt=(f"La {name} va de <b>{start}</b> à <b>{end}</b>. C'est une randonnée point à point : elle ne se termine pas là où vous vous êtes garé — organisez d'abord votre retour (deux voitures, un taxi réservé, ou une randonnée guidée avec transferts)."
                if linear and start and end else
                f"La {name} démarre et se termine à <b>{start or 'le départ'}</b> ; vous revenez par le même chemin — aucun transport de retour à organiser."),
            gt_fact="C'est un long trajet en montagne depuis la côte, sans magasin ni réseau fiable à la plupart des départs. Emportez de l'eau, des couches chaudes et imperméables, et une lampe — la météo change vite en altitude.",
            cl_h=f'<span class="q">Fermé ou complet ?</span> Vos options',
            cl=(f"Si l'IFCN ferme le {code} (météo, glissement, travaux) ou si vous ne trouvez pas de créneau : <b>reprogrammez</b> via le centre d'appels SIMplifica avant votre date — vous pouvez modifier librement date et heure, et changer de sentier uniquement si le vôtre a été officiellement fermé. "
                f"Pour des alternatives ouvertes, <a class=\"plain\" href=\"{PREFIX[lang]}/trails/\">consultez le tableau en direct</a>."),
            kn_h="Avant de partir",
            kn=[
                "<b>Sur réservation uniquement.</b> Marcher sur un sentier PR payant sans billet SIMplifica valide est une infraction, avec des amendes signalées jusqu'à 250 €.",
                ("<b>Elle ne boucle pas.</b> Vous finissez ailleurs — réglez votre retour avant de partir."
                 if linear and start and end else
                 "<b>C'est un aller-retour.</b> Faites demi-tour avec assez de temps et de lumière pour revenir par le même chemin."),
                "<b>Vérifiez le badge en direct le matin même.</b> Les sentiers de montagne ferment vite pour météo, chutes de pierres ou travaux.",
            ],
            footer="Statut compilé chaque matin à partir de l'IFCN (ifcn.madeira.gov.pt) et de SIMplifica, avec la météo de l'IPMA (ipma.pt). Indépendant — non affilié au Gouvernement régional de Madère. Les conditions changent vite en montagne ; fiez-vous toujours à votre propre jugement sur le sentier.",
        )
    elif lang == "de":
        d.update(
            title=f"Ist die {name} heute geöffnet? {name} ({code}): Status &amp; Buchung",
            desc=f"Live-Status der {name} ({code}) — heute geöffnet? Wie man den 4,50-€-Slot auf SIMplifica bucht, die Weg-Fakten und offene Alternativen.",
            h1=f"Ist die {name} heute geöffnet?",
            sub=f"{name} ({code}) — ein kostenpflichtiger PR-Weg, nur mit Buchung. Jeden Morgen gegen den offiziellen IFCN-Status geprüft.",
            loading=f"Der heutige Status der {name} wird geladen… falls er nicht erscheint, prüfen Sie die unten verlinkten offiziellen Quellen.",
            book_h=f'<span class="q">Buchen.</span> Der {code} auf SIMplifica',
            book=(f"Sobald er als geöffnet angezeigt wird, buchen Sie Ihren <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">4,50-€-Slot auf SIMplifica</a> im Voraus. "
                  f"Kinder unter 12 und Einwohner sind frei, müssen aber trotzdem namentlich in der Buchung stehen. Der {code} wird als eigene, gesonderte Buchung bezahlt und ist <b>nicht</b> in den Mehrtagespässen enthalten — prüfen Sie den Live-Status oben, bevor Sie bezahlen."),
            gt_h=f'<span class="q">Anreise.</span> Start &amp; Ziel',
            gt=(f"Die {name} verläuft von <b>{start}</b> nach <b>{end}</b>. Es ist eine Streckenwanderung, sie endet also nicht dort, wo Sie geparkt haben — klären Sie zuerst den Rückweg (zwei Autos, ein vorab gebuchtes Taxi oder eine geführte Wanderung mit Transfers)."
                if linear and start and end else
                f"Die {name} beginnt und endet an <b>{start or 'dem Ausgangspunkt'}</b>, Sie kehren also denselben Weg zurück — kein Rücktransport zu organisieren."),
            gt_fact="Es ist eine lange Bergfahrt von der Küste, an den meisten Ausgangspunkten ohne Laden oder verlässlichen Empfang. Nehmen Sie Wasser, warme und wasserdichte Kleidung sowie eine Lampe mit — das Wetter schlägt oben schnell um.",
            cl_h=f'<span class="q">Gesperrt oder ausgebucht?</span> Ihre Optionen',
            cl=(f"Wenn die IFCN den {code} sperrt (Wetter, Erdrutsch, Arbeiten) oder Sie keinen Slot bekommen: <b>Umbuchen</b> über das SIMplifica-Callcenter vor Ihrem Termin — Datum und Uhrzeit frei änderbar, den Weg wechseln nur, wenn Ihrer offiziell gesperrt war. "
                f"Offene Alternativen finden Sie auf der <a class=\"plain\" href=\"{PREFIX[lang]}/trails/\">Live-Tafel</a>."),
            kn_h="Vor dem Start",
            kn=[
                "<b>Nur mit Buchung.</b> Einen kostenpflichtigen PR-Weg ohne gültiges SIMplifica-Ticket zu gehen ist ein Verstoß, mit gemeldeten Bußgeldern bis zu 250 €.",
                ("<b>Sie führt nicht im Kreis zurück.</b> Sie enden woanders — regeln Sie den Rückweg vor dem Start."
                 if linear and start and end else
                 "<b>Hin und zurück.</b> Drehen Sie mit genug Zeit und Tageslicht um, um denselben Weg zurückzugehen."),
                "<b>Prüfen Sie das Live-Abzeichen am Morgen Ihrer Tour.</b> Bergwege werden schnell wegen Wetter, Steinschlag oder Arbeiten gesperrt.",
            ],
            footer="Status jeden Morgen aus IFCN (ifcn.madeira.gov.pt) und SIMplifica zusammengestellt, mit Wetter von IPMA (ipma.pt). Unabhängig — nicht mit der Regionalregierung von Madeira verbunden. Die Bedingungen ändern sich in den Bergen schnell; verlassen Sie sich auf dem Weg immer auf Ihr eigenes Urteil.",
        )
    else:  # pl
        d.update(
            title=f"Czy {name} jest dziś otwarta? {name} ({code}): status i rezerwacja",
            desc=f"Status na żywo {name} ({code}) — czy jest dziś otwarta? Jak zarezerwować slot za 4,50 € w SIMplifica, fakty o szlaku i otwarte alternatywy.",
            h1=f"Czy {name} jest dziś otwarta?",
            sub=f"{name} ({code}) — płatny szlak PR, wyłącznie na rezerwację. Sprawdzany każdego ranka względem oficjalnego statusu IFCN.",
            loading=f"Ładowanie dzisiejszego statusu {name}… jeśli się nie pojawi, sprawdź oficjalne źródła podane poniżej.",
            book_h=f'<span class="q">Zarezerwuj.</span> {code} w SIMplifica',
            book=(f"Gdy pokaże się jako otwarty, zarezerwuj z wyprzedzeniem swój <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">slot za 4,50 € w SIMplifica</a>. "
                  f"Dzieci poniżej 12 lat i mieszkańcy są bezpłatnie, ale i tak muszą być imiennie w rezerwacji. {code} jest płatny jako osobna rezerwacja i <b>nie jest wliczony</b> w karnety wielodniowe — sprawdź status na żywo powyżej, zanim zapłacisz."),
            gt_h=f'<span class="q">Dojazd.</span> Start i meta',
            gt=(f"{name} biegnie od <b>{start}</b> do <b>{end}</b>. To trasa z punktu do punktu, więc nie kończy się tam, gdzie zaparkowałeś — najpierw załatw powrót (dwa auta, zamówiona taksówka lub wędrówka z przewodnikiem i transferami)."
                if linear and start and end else
                f"{name} zaczyna się i kończy w <b>{start or 'punkcie startowym'}</b>, więc wracasz tą samą drogą — nie trzeba organizować powrotu."),
            gt_fact="To długi górski dojazd od wybrzeża, przy większości początków szlaków bez sklepu i pewnego zasięgu. Weź wodę, ciepłe i wodoodporne warstwy oraz latarkę — pogoda w górach zmienia się szybko.",
            cl_h=f'<span class="q">Zamknięta lub pełna?</span> Twoje opcje',
            cl=(f"Jeśli IFCN zamknie {code} (pogoda, osuwisko, prace) lub nie zdobędziesz slotu: <b>przełóż termin</b> przez infolinię SIMplifica przed swoją datą — datę i godzinę zmieniasz dowolnie, a szlak tylko wtedy, gdy twój został oficjalnie zamknięty. "
                f"Otwarte alternatywy znajdziesz na <a class=\"plain\" href=\"{PREFIX[lang]}/trails/\">tablicy na żywo</a>."),
            kn_h="Zanim wyruszysz",
            kn=[
                "<b>Wyłącznie na rezerwację.</b> Wejście na płatny szlak PR bez ważnego biletu SIMplifica to wykroczenie, z grzywnami sięgającymi 250 €.",
                ("<b>Nie wraca pętlą.</b> Kończysz w innym miejscu — załatw powrót przed wyruszeniem."
                 if linear and start and end else
                 "<b>Trasa tam i z powrotem.</b> Zawracaj z zapasem czasu i światła, by wrócić tą samą drogą."),
                "<b>Sprawdź plakietkę na żywo w dniu wyjścia.</b> Górskie szlaki szybko zamyka się z powodu pogody, obrywów lub prac.",
            ],
            footer="Status zestawiany każdego ranka z IFCN (ifcn.madeira.gov.pt) i SIMplifica, z pogodą z IPMA (ipma.pt). Niezależny — niepowiązany z Rządem Regionalnym Madery. Warunki w górach zmieniają się szybko; na szlaku zawsze kieruj się własnym osądem.",
        )
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
.facts{grid-column:2;grid-row:2;align-self:start;margin-top:18px;background:var(--card);
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


def facts_rows(lang, f, linear, typ):
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
    rows.append((LBL["fee"][lang], "€4.50"))
    return "".join(f"    <dt>{k}</dt><dd>{v}</dd>\n" for k, v in rows)


def build(lang, code, name, slug, f, linear, typ):
    start, end = f.get("start"), f.get("end")
    t = T(lang, code, name, f, linear, start, end, typ)
    photo = PHOTOS.get(code)
    if photo:
        hero_rule = (f".hero{{height:210px;background:#20573a url(/img/{photo['file']}) center/cover}}\n"
                     "@media (max-width:640px){.hero{height:150px}}")
        word, resized = PHOTO_CREDIT[lang]
        lic = photo["lic"] + (" (public domain)" if photo["lic"] == "CC0" else "")
        sep = " :" if lang == "fr" else ":"
        footer_extra = (f'\n  <p style="margin-top:6px">{word}{sep} {photo["author"]}, '
                        f'<a href="https://commons.wikimedia.org/" target="_blank" rel="noopener">Wikimedia Commons</a>, {lic}, {resized}.</p>')
    else:
        hero_rule = ".hero{height:130px;background:#20573a}"
        footer_extra = ""
    canon = f"https://madeira.maykef.info{PREFIX[lang]}/{slug}/"
    alts = "\n".join(
        f'<link rel="alternate" hreflang="{hl}" href="https://madeira.maykef.info{PREFIX[hl]}/{slug}/">'
        for hl in ("en", "fr", "de", "pl")
    ) + f'\n<link rel="alternate" hreflang="x-default" href="https://madeira.maykef.info/{slug}/">'
    langnav = "\n".join(
        f'    <a href="{PREFIX[hl]}/{slug}/" hreflang="{hl}"{" aria-current=\"page\"" if hl==lang else ""}>{hl.upper()}</a>'
        for hl in ("en", "fr", "de", "pl")
    )
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": t["h1"],
             "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", t["loading"])[:20] and _faq_open(lang, name, code)}},
            {"@type": "Question", "name": _faq_book_q(lang, name),
             "acceptedAnswer": {"@type": "Answer", "text": _faq_book_a(lang, code)}},
        ],
    }
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

<title>{t['title']}</title>
<meta name="description" content="{t['desc']}">

<link rel="canonical" href="{canon}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{t['h1']}">
<meta property="og:description" content="{t['desc']}">
<meta name="twitter:card" content="summary">

{alts}

<script src="/status.js" defer></script>

<script type="application/ld+json">
{json.dumps(faq, ensure_ascii=False, indent=2)}
</script>

<style>
:root{{
  --paper:#FAFAF7; --ink:#16342A; --ink-soft:#4A5F56;
  --way-yellow:#E8B71A; --way-red:#BE3A2B;
  --open:#1E7A45; --partial:#C07A0A; --closed:#B3372E;
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
  <p class="sub">{t['sub']} {SEE[lang]} <a href="{P}/trails/">{t['allt']}</a> · <a href="{P}/">PR1</a>.</p>
</header>

<div class="status-card" id="statusCard" data-trail="{code}">
  <div class="status-body"><p>{t['loading']}</p></div>
</div>

<aside class="facts">
  <h2>{LBL['facts'][lang]}</h2>
  <dl>
{facts_rows(lang, f, linear, t['typ'])}  </dl>
</aside>

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

<section id="closed">
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


def _faq_open(lang, name, code):
    return {
        "en": f"Today's status is shown live at the top of this page, updated each morning from official IFCN / Visit Madeira information. {name} ({code}) is a paid, booking-only PR trail; access is €4.50 through the SIMplifica portal.",
        "fr": f"Le statut du jour est affiché en direct en haut de cette page, mis à jour chaque matin à partir des informations officielles de l'IFCN / Visit Madeira. La {name} ({code}) est un sentier PR payant, sur réservation ; l'accès coûte 4,50 € via le portail SIMplifica.",
        "de": f"Der heutige Status wird live oben auf dieser Seite angezeigt und jeden Morgen aus offiziellen IFCN- / Visit-Madeira-Informationen aktualisiert. Die {name} ({code}) ist ein kostenpflichtiger PR-Weg nur mit Buchung; der Zugang kostet 4,50 € über das SIMplifica-Portal.",
        "pl": f"Dzisiejszy status jest pokazywany na żywo na górze tej strony, aktualizowany każdego ranka na podstawie oficjalnych informacji IFCN / Visit Madeira. {name} ({code}) to płatny szlak PR wyłącznie na rezerwację; wstęp kosztuje 4,50 € przez portal SIMplifica.",
    }[lang]


def _faq_book_q(lang, name):
    return {
        "en": f"Do you need to book the {name}?",
        "fr": f"Faut-il réserver pour la {name} ?",
        "de": f"Muss man die {name} buchen?",
        "pl": f"Czy trzeba rezerwować {name}?",
    }[lang]


def _faq_book_a(lang, code):
    return {
        "en": f"Yes. {code} requires an advance booking and €4.50 payment through SIMplifica. Under-12s and residents are free but must still be named on the booking.",
        "fr": f"Oui. Le {code} exige une réservation à l'avance et un paiement de 4,50 € via SIMplifica. Les moins de 12 ans et les résidents sont gratuits mais doivent tout de même figurer sur la réservation.",
        "de": f"Ja. Für den {code} sind eine Vorausbuchung und eine Zahlung von 4,50 € über SIMplifica erforderlich. Kinder unter 12 und Einwohner sind frei, müssen aber namentlich in der Buchung stehen.",
        "pl": f"Tak. {code} wymaga wcześniejszej rezerwacji i opłaty 4,50 € przez SIMplifica. Dzieci poniżej 12 lat i mieszkańcy są bezpłatnie, ale muszą być imiennie w rezerwacji.",
    }[lang]


def main():
    urls = trail_urls()
    data = json.load(open(os.path.join(ROOT, "status.json")))
    targets = [t for t in data["trails"] if t["code"] not in HAVE]
    pages_map, sitemap_blocks, summary = {}, [], []
    for t in targets:
        code, name = t["code"], t["name"]
        url = urls.get(code)
        if not url:
            print("  SKIP (no url):", code); continue
        try:
            f = scrape_facts(url)
        except Exception as e:
            print("  scrape failed", code, e); f = {}
        start, end = f.get("start"), f.get("end")
        if f.get("round_trip"):
            kind = "oab"
        elif f.get("circular"):
            kind = "circ"
        elif start and end and slugify(start) != slugify(end):
            kind = "p2p"
        else:
            kind = "oab"
        linear = kind == "p2p"          # "one-way": you don't finish where you started
        slug = slugify(name)
        pages_map[code] = f"/{slug}/"
        for lang in ("en", "fr", "de", "pl"):
            d = os.path.join(ROOT, PREFIX[lang].lstrip("/"), slug) if PREFIX[lang] else os.path.join(ROOT, slug)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(build(lang, code, name, slug, f, linear, TYP[kind][lang]))
        for lang in ("en", "fr", "de", "pl"):
            loc = f"https://madeira.maykef.info{PREFIX[lang]}/{slug}/"
            block = [f"  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>2026-07-08</lastmod>",
                     f"    <changefreq>daily</changefreq>", f"    <priority>0.7</priority>"]
            for hl in ("en", "fr", "de", "pl"):
                block.append(f'    <xhtml:link rel="alternate" hreflang="{hl}" href="https://madeira.maykef.info{PREFIX[hl]}/{slug}/"/>')
            block.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="https://madeira.maykef.info/{slug}/"/>')
            block.append("  </url>")
            sitemap_blocks.append("\n".join(block))
        summary.append((code, kind, f.get("distance", "?"), f.get("duration", "?"), f.get("difficulty", "-")))
    json.dump({"pages": pages_map, "sitemap": sitemap_blocks}, open("/tmp/gen_out.json", "w"))
    print(f"\nGenerated {len(pages_map)} trails × 4 langs = {len(pages_map)*4} pages")
    for row in summary:
        print("  ", row)


if __name__ == "__main__":
    main()
