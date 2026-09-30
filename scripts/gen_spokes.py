#!/usr/bin/env python3
"""One-off generator for the long-tail trail spoke pages.

Builds a lightweight, live-status-first spoke page (en/pt/fr/de/pl) for every PR
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


def T(lang, code, name, f, linear, start, end, typ):
    """Return a dict of every localised text slot for one language."""
    allt = {"en": "all Madeira trails", "pt": "todos os percursos da Madeira", "fr": "tous les sentiers de Madère",
            "de": "alle Wanderwege Madeiras", "pl": "wszystkie szlaki Madery"}[lang]
    route = f"{start} → {end}" if (linear and start and end) else (start or "—")
    d = {}
    if lang == "en":
        d.update(
            title=f"Is the {name} open today? {name} ({code}) status &amp; booking",
            desc=f"Live status for the {name} ({code}) — is it open today? How to book the €4.50 SIMplifica slot, the trail facts, and open alternatives if it's closed.",
            h1=f"Is the {name} open today?",
            sub=f"{name} ({code}) — a paid, booking-only PR trail. Status from the official IFCN warnings list, with IFCN's own “updated” date.",
            loading="Trail status comes from the official IFCN warnings list, which IFCN updates when conditions change and dates itself (\"updated\"). It is shown here as a live badge (it needs JavaScript). If it doesn't appear, check the official sources linked below.",
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
                f"For open alternatives, <a class=\"plain\" href=\"{PREFIX[lang]}/\">check the live board</a>."),
            kn_h="Before you go",
            kn=[
                "<b>Booking-only.</b> Walking an IFCN classified trail without a valid SIMplifica ticket is an administrative offence (Portaria 801/2025 art. 10; DLR 24/2022/M art. 13); the law sets fines for individuals of €250–€2,500.",
                ("<b>It doesn't loop back.</b> You finish somewhere else — fix your return before you set off."
                 if linear and start and end else
                 "<b>It's out-and-back.</b> Turn around with enough time and daylight to walk out the way you came."),
                "<b>Check the live badge the morning you go.</b> Mountain trails close fast for weather, rockfall or works.",
            ],
            footer="Status compiled from <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">IFCN</a> and <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, with weather from <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. Independent — not affiliated with the Madeira Regional Government. Conditions change fast in the mountains; always use your own judgement on the trail.",
        )
    elif lang == "pt":
        A, a, da, o = pt_g(name)
        d.update(
            title=f"{A} {name} está abert{o} hoje? {name} ({code}): estado e reserva",
            desc=f"Estado em direto {da} {name} ({code}) — está abert{o} hoje? Como reservar a vaga de 4,50 € no SIMplifica, os dados do percurso e alternativas abertas se estiver fechad{o}.",
            h1=f"{A} {name} está abert{o} hoje?",
            sub=f"{name} ({code}) — um percurso PR pago e só com reserva. Estado segundo a lista oficial de avisos do IFCN, com a data de «atualizado» do próprio IFCN.",
            loading="O estado do percurso vem da lista oficial de avisos do IFCN, que o IFCN atualiza quando as condições mudam e data (\"atualizado\"). É mostrado aqui em direto (requer JavaScript). Se não aparecer, consulte as fontes oficiais indicadas abaixo.",
            book_h=f'<span class="q">Reserve.</span> O {code} no SIMplifica',
            book=(f"Assim que aparecer como aberto, reserve com antecedência a sua <a class=\"plain\" href=\"https://simplifica.madeira.gov.pt/services/78-82-259\" target=\"_blank\" rel=\"noopener\">vaga de 4,50 € no SIMplifica</a>. "
                  f"Menores de 12 anos e residentes não pagam, mas têm de constar nominalmente da reserva. O {code} paga-se numa reserva própria e <b>não está incluído</b> nos passes de vários dias — confirme o estado em direto acima antes de pagar."),
            gt_h=f'<span class="q">Como chegar.</span> Início e fim',
            gt=(f"{A} {name} vai de <b>{start}</b> até <b>{end}</b>. É um percurso linear, por isso não termina onde estacionou — trate primeiro do regresso (dois carros, um táxi reservado ou uma caminhada guiada com transporte incluído)."
                if linear and start and end else
                f"{A} {name} começa e termina " + (f"em <b>{start}</b>" if start else "no mesmo ponto de partida") + ", por isso regressa pelo mesmo caminho — não há transporte de regresso a organizar."),
            gt_fact="É uma longa viagem de montanha a partir da costa, sem loja nem rede fiável na maioria dos pontos de partida. Leve água, roupa quente e impermeável e uma lanterna — o tempo muda depressa em altitude.",
            cl_h=f'<span class="q">Fechado ou esgotado?</span> As suas opções',
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
            footer="Estado compilado a partir do <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">IFCN</a> e do <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, com meteorologia do <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. Independente — sem ligação ao Governo Regional da Madeira. As condições mudam depressa na montanha; use sempre o seu próprio discernimento no percurso.",
        )
    elif lang == "fr":
        d.update(
            title=f"La {name} est-elle ouverte aujourd'hui ? {name} ({code}) : statut et réservation",
            desc=f"Statut en direct de la {name} ({code}) — est-elle ouverte aujourd'hui ? Comment réserver le créneau SIMplifica à 4,50 €, les infos du sentier et les alternatives ouvertes.",
            h1=f"La {name} est-elle ouverte aujourd'hui ?",
            sub=f"{name} ({code}) — un sentier PR payant, sur réservation. Statut issu de la liste officielle des avis de l'IFCN, avec sa propre date de « mise à jour ».",
            loading="L'état du sentier provient de la liste officielle des avis de l'IFCN, que l'IFCN met à jour quand les conditions changent et qu'il date lui-même (« mise à jour »). Il s'affiche ici en direct (JavaScript requis). S'il n'apparaît pas, consultez les sources officielles indiquées ci-dessous.",
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
                f"Pour des alternatives ouvertes, <a class=\"plain\" href=\"{PREFIX[lang]}/\">consultez le tableau en direct</a>."),
            kn_h="Avant de partir",
            kn=[
                "<b>Sur réservation uniquement.</b> Parcourir un sentier classé par l'IFCN sans billet SIMplifica valide est une infraction administrative (Portaria 801/2025 art. 10 ; DLR 24/2022/M art. 13) ; la loi prévoit pour les particuliers des amendes de 250 € à 2 500 €.",
                ("<b>Elle ne boucle pas.</b> Vous finissez ailleurs — réglez votre retour avant de partir."
                 if linear and start and end else
                 "<b>C'est un aller-retour.</b> Faites demi-tour avec assez de temps et de lumière pour revenir par le même chemin."),
                "<b>Vérifiez le badge en direct le matin même.</b> Les sentiers de montagne ferment vite pour météo, chutes de pierres ou travaux.",
            ],
            footer="Statut compilé à partir de l'<a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">IFCN</a> et de <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, avec la météo de l'<a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. Indépendant — non affilié au Gouvernement régional de Madère. Les conditions changent vite en montagne ; fiez-vous toujours à votre propre jugement sur le sentier.",
        )
    elif lang == "de":
        d.update(
            title=f"Ist die {name} heute geöffnet? {name} ({code}): Status &amp; Buchung",
            desc=f"Live-Status der {name} ({code}) — heute geöffnet? Wie man den 4,50-€-Slot auf SIMplifica bucht, die Weg-Fakten und offene Alternativen.",
            h1=f"Ist die {name} heute geöffnet?",
            sub=f"{name} ({code}) — ein kostenpflichtiger PR-Weg, nur mit Buchung. Status aus der offiziellen Hinweisliste des IFCN, mit dessen eigenem „aktualisiert“-Datum.",
            loading="Der Wegestatus stammt aus der offiziellen Hinweisliste des IFCN, die das IFCN bei Änderungen aktualisiert und selbst datiert („aktualisiert“). Er wird hier live angezeigt (dafür ist JavaScript nötig). Falls er nicht erscheint, prüfen Sie die unten verlinkten offiziellen Quellen.",
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
                f"Offene Alternativen finden Sie auf der <a class=\"plain\" href=\"{PREFIX[lang]}/\">Live-Tafel</a>."),
            kn_h="Vor dem Start",
            kn=[
                "<b>Nur mit Buchung.</b> Einen vom IFCN klassifizierten Weg ohne gültiges SIMplifica-Ticket zu gehen ist eine Ordnungswidrigkeit (Portaria 801/2025 Art. 10; DLR 24/2022/M Art. 13); das Gesetz sieht für Privatpersonen Bußgelder von 250 € bis 2.500 € vor.",
                ("<b>Sie führt nicht im Kreis zurück.</b> Sie enden woanders — regeln Sie den Rückweg vor dem Start."
                 if linear and start and end else
                 "<b>Hin und zurück.</b> Drehen Sie mit genug Zeit und Tageslicht um, um denselben Weg zurückzugehen."),
                "<b>Prüfen Sie das Live-Abzeichen am Morgen Ihrer Tour.</b> Bergwege werden schnell wegen Wetter, Steinschlag oder Arbeiten gesperrt.",
            ],
            footer="Status aus <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">IFCN</a> und <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a> zusammengestellt, mit Wetter von <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. Unabhängig — nicht mit der Regionalregierung von Madeira verbunden. Die Bedingungen ändern sich in den Bergen schnell; verlassen Sie sich auf dem Weg immer auf Ihr eigenes Urteil.",
        )
    else:  # pl
        d.update(
            title=f"Czy {name} jest dziś otwarta? {name} ({code}): status i rezerwacja",
            desc=f"Status na żywo {name} ({code}) — czy jest dziś otwarta? Jak zarezerwować slot za 4,50 € w SIMplifica, fakty o szlaku i otwarte alternatywy.",
            h1=f"Czy {name} jest dziś otwarta?",
            sub=f"{name} ({code}) — płatny szlak PR, wyłącznie na rezerwację. Status z oficjalnej listy komunikatów IFCN, z datą „aktualizacji” podaną przez IFCN.",
            loading="Stan szlaku pochodzi z oficjalnej listy komunikatów IFCN, którą IFCN aktualizuje, gdy zmieniają się warunki, i sam datuje („aktualizacja”). Jest pokazywany tutaj na żywo (wymaga JavaScriptu). Jeśli się nie pojawi, sprawdź oficjalne źródła podane poniżej.",
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
                f"Otwarte alternatywy znajdziesz na <a class=\"plain\" href=\"{PREFIX[lang]}/\">tablicy na żywo</a>."),
            kn_h="Zanim wyruszysz",
            kn=[
                "<b>Wyłącznie na rezerwację.</b> Przejście szlaku sklasyfikowanego przez IFCN bez ważnego biletu SIMplifica to wykroczenie administracyjne (Portaria 801/2025 art. 10; DLR 24/2022/M art. 13); przepisy przewidują dla osób fizycznych grzywny od 250 € do 2500 €.",
                ("<b>Nie wraca pętlą.</b> Kończysz w innym miejscu — załatw powrót przed wyruszeniem."
                 if linear and start and end else
                 "<b>Trasa tam i z powrotem.</b> Zawracaj z zapasem czasu i światła, by wrócić tą samą drogą."),
                "<b>Sprawdź plakietkę na żywo w dniu wyjścia.</b> Górskie szlaki szybko zamyka się z powodu pogody, obrywów lub prac.",
            ],
            footer="Status zestawiany z <a href=\"https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos\" rel=\"noopener\">IFCN</a> i <a href=\"https://simplifica.madeira.gov.pt/\" rel=\"noopener\">SIMplifica</a>, z pogodą z <a href=\"https://www.ipma.pt/\" rel=\"noopener\">IPMA</a>. Niezależny — niepowiązany z Rządem Regionalnym Madery. Warunki w górach zmieniają się szybko; na szlaku zawsze kieruj się własnym osądem.",
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
    rows.append((LBL["fee"][lang], "4,50 €" if lang == "pt" else "€4.50"))
    return "".join(f"    <dt>{k}</dt><dd>{v}</dd>\n" for k, v in rows)


def build(lang, code, name, slug, f, linear, typ):
    start, end = f.get("start"), f.get("end")
    t = T(lang, code, name, f, linear, start, end, typ)
    photo = PHOTOS.get(code)
    if photo:
        hero_rule = (f".hero{{height:210px;background:#20573a url(/img/{photo['file']}) center/cover}}\n"
                     "@media (max-width:640px){.hero{height:150px}}")
        word, resized = PHOTO_CREDIT[lang]
        lic = photo["lic"] + ((" (domínio público)" if lang == "pt" else " (public domain)") if photo["lic"] == "CC0" else "")
        sep = " :" if lang == "fr" else ":"
        footer_extra = (f'\n  <p style="margin-top:6px">{word}{sep} {photo["author"]}, '
                        f'<a href="https://commons.wikimedia.org/wiki/Main_Page" target="_blank" rel="noopener">Wikimedia Commons</a>, {lic}, {resized}.</p>')
    else:
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
  <p class="sub">{t['sub']} {SEE[lang]} <a href="{P}/">{t['allt']}</a> · <a href="{P}/pr1/">PR1</a>.</p>
</header>

<div class="status-card" id="statusCard" data-trail="{code}">
  <div class="status-body"><p class="static-status"><!-- STATIC-STATUS:{code}:START --><!-- STATIC-STATUS:{code}:END --></p><p>{t['loading']}</p></div>
</div>

<aside class="facts">
  <h2>{LBL['facts'][lang]}</h2>
  <dl>
{facts_rows(lang, f, linear, t['typ'])}  </dl>
{gen_trail_extras.facts_block(code, lang, EXTRAS)}</aside>

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
        "pt": "O estado de hoje aparece em direto no topo desta página, com base na lista oficial de avisos do IFCN, com a data de «atualizado» do próprio IFCN. {} {} ({}) é um percurso PR pago e só com reserva; o acesso custa 4,50 € através do portal SIMplifica.".format(pt_g(name)[0], name, code),
        "en": f"Today's status is shown live at the top of this page, taken from the official IFCN warnings list, which carries IFCN's own “updated” date. {name} ({code}) is a paid, booking-only PR trail; access is €4.50 through the SIMplifica portal.",
        "fr": f"Le statut du jour est affiché en direct en haut de cette page, issu de la liste officielle des avis de l'IFCN, avec sa propre date de « mise à jour ». La {name} ({code}) est un sentier PR payant, sur réservation ; l'accès coûte 4,50 € via le portail SIMplifica.",
        "de": f"Der heutige Status wird live oben auf dieser Seite angezeigt und stammt aus der offiziellen Hinweisliste des IFCN, mit dessen eigenem „aktualisiert“-Datum. Die {name} ({code}) ist ein kostenpflichtiger PR-Weg nur mit Buchung; der Zugang kostet 4,50 € über das SIMplifica-Portal.",
        "pl": f"Dzisiejszy status jest pokazywany na żywo na górze tej strony, pochodzi z oficjalnej listy komunikatów IFCN i ma datę „aktualizacji” podaną przez IFCN. {name} ({code}) to płatny szlak PR wyłącznie na rezerwację; wstęp kosztuje 4,50 € przez portal SIMplifica.",
    }[lang]


def _faq_book_q(lang, name):
    return {
        "en": f"Do you need to book the {name}?",
        "pt": f"É preciso reservar {pt_g(name)[1]} {name}?",
        "fr": f"Faut-il réserver pour la {name} ?",
        "de": f"Muss man die {name} buchen?",
        "pl": f"Czy trzeba rezerwować {name}?",
    }[lang]


def _faq_book_a(lang, code):
    return {
        "pt": f"Sim. O {code} exige reserva antecipada e pagamento de 4,50 € através do SIMplifica. Menores de 12 anos e residentes não pagam, mas têm de constar nominalmente da reserva.",
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
        for lang in LANGS:
            d = os.path.join(ROOT, PREFIX[lang].lstrip("/"), slug) if PREFIX[lang] else os.path.join(ROOT, slug)
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(build(lang, code, name, slug, f, linear, TYP[kind][lang]))
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


if __name__ == "__main__":
    main()
