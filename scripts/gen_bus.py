#!/usr/bin/env python3
"""Writes the "By bus" section (getting there / getting back) on trail pages, in 5 languages.

Times come from the operators' timetables published on SIGA (siga.madeira.gov.pt/horarios), transcribed
into seo_research/facts/bus/*.json (local, git-ignored) and curated into TRAILS below: only stops printed
on the sheets, no misprinted rows (flagged SUSPECT in the facts files), no guessed stop-to-trailhead walks.
The section sits between <!-- BUS:START --> / <!-- BUS:END --> markers right after the page's
#getting-there (or #getting-back) section; the markers are added on the first run. Idempotent.
Run after gen_spokes.py (it calls this at the end). Balcões, Levada do Furado and the getting-back page
carry hand-written CAM sections instead (section id="bus" / "bus-santana").
"""
import html, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
LANGS = ["en", "pt", "fr", "de", "pl"]
PREFIX = {"en": "", "pt": "pt/", "fr": "fr/", "de": "de/", "pl": "pl/"}

T = {
    "h": {"en": "By bus", "pt": "De autocarro", "fr": "En bus", "de": "Mit dem Bus", "pl": "Autobusem"},
    "there": {"en": "Getting there.", "pt": "Ida.", "fr": "Aller.", "de": "Hin.", "pl": "Dojazd."},
    "back": {"en": "Getting back.", "pt": "Regresso.", "fr": "Retour.", "de": "Zurück.", "pl": "Powrót."},
    "days": {
        "daily": {"en": "Every day", "pt": "Todos os dias", "fr": "Tous les jours", "de": "Täglich", "pl": "Codziennie"},
        "mon_fri": {"en": "Monday to Friday", "pt": "De segunda a sexta", "fr": "Du lundi au vendredi", "de": "Montag bis Freitag", "pl": "Od poniedziałku do piątku"},
        "sat": {"en": "Saturdays", "pt": "Sábados", "fr": "Samedi", "de": "Samstags", "pl": "Soboty"},
        "sun_hol": {"en": "Sundays and holidays", "pt": "Domingos e feriados", "fr": "Dimanches et jours fériés", "de": "Sonn- und Feiertage", "pl": "Niedziele i święta"},
        "sat_sun": {"en": "Saturdays and Sundays", "pt": "Sábados e domingos", "fr": "Samedi et dimanche", "de": "Samstags und sonntags", "pl": "Soboty i niedziele"},
        "sat_sun_hol": {"en": "Saturdays, Sundays and holidays", "pt": "Sábados, domingos e feriados", "fr": "Samedi, dimanche et jours fériés", "de": "Samstags, sonn- und feiertags", "pl": "Soboty, niedziele i święta"},
    },
    "line": {"en": "{op} line {n}", "pt": "linha {n} ({op})", "fr": "ligne {n} ({op})", "de": "Linie {n} ({op})", "pl": "linia {n} ({op})"},
    "new": {"en": " (new no. {x})", "pt": " (novo n.º {x})", "fr": " (nouveau n° {x})", "de": " (neue Nr. {x})", "pl": " (nowy nr {x})"},
    "deps": {"en": "departures from {a}", "pt": "partidas de {a}", "fr": "départs de {a}", "de": "Abfahrten ab {a}", "pl": "odjazdy z {a}"},
    "change": {"en": "* change bus at {p}.", "pt": "* mudança de autocarro em {p}.", "fr": "* changement de bus à {p}.", "de": "* Umsteigen in {p}.", "pl": "* przesiadka w {p}."},
    "PE": {"en": " (school term only)", "pt": " (só em período escolar)", "fr": " (période scolaire seulement)", "de": " (nur in der Schulzeit)", "pl": " (tylko w roku szkolnym)"},
    "PNE": {"en": " (school holidays only)", "pt": " (só fora do período escolar)", "fr": " (vacances scolaires seulement)", "de": " (nur in den Schulferien)", "pl": " (tylko w czasie wakacji szkolnych)"},
    "src": {
        "en": 'Times as printed on the operators\' timetables published on <a href="https://siga.madeira.gov.pt/horarios" rel="noopener">SIGA</a>, the Region\'s public transport site; times at intermediate stops are approximate. No buses on 25 December. Check before you travel.',
        "pt": 'Horários tal como impressos nas tabelas dos operadores publicadas no <a href="https://siga.madeira.gov.pt/horarios" rel="noopener">SIGA</a>, o portal de transportes públicos da Região; as horas nas paragens intermédias são aproximadas. Não há autocarros a 25 de dezembro. Confirme antes de viajar.',
        "fr": 'Horaires tels qu\'imprimés sur les fiches des transporteurs publiées sur <a href="https://siga.madeira.gov.pt/horarios" rel="noopener">SIGA</a>, le site des transports publics de la Région ; les heures aux arrêts intermédiaires sont approximatives. Pas de bus le 25 décembre. Vérifiez avant de partir.',
        "de": 'Zeiten laut den Fahrplänen der Busunternehmen auf <a href="https://siga.madeira.gov.pt/horarios" rel="noopener">SIGA</a>, dem Nahverkehrsportal der Region; Zeiten an Zwischenhalten sind ungefähr. Am 25. Dezember fahren keine Busse. Vor der Fahrt prüfen.',
        "pl": 'Godziny według rozkładów przewoźników opublikowanych w <a href="https://siga.madeira.gov.pt/horarios" rel="noopener">SIGA</a>, regionalnym serwisie transportu publicznego; godziny na przystankach pośrednich są orientacyjne. 25 grudnia autobusy nie kursują. Sprawdź przed podróżą.',
    },
}

# Free-text sentences per trail and language (kept short; facts only from the sheets / official pages).
S = {
    "loop_stop": {"en": "{p}, where the walk starts and ends, is a bus stop.", "pt": "{p}, onde o percurso começa e acaba, é uma paragem de autocarro.",
                  "fr": "{p}, où la balade commence et se termine, est un arrêt de bus.", "de": "{p}, wo die Wanderung beginnt und endet, ist eine Bushaltestelle.",
                  "pl": "{p}, gdzie trasa się zaczyna i kończy, to przystanek autobusowy."},
    "start_stop": {"en": "{p}, where the walk starts, is a bus stop.", "pt": "{p}, onde o percurso começa, é uma paragem de autocarro.",
                   "fr": "{p}, le départ de la balade, est un arrêt de bus.", "de": "{p}, wo die Wanderung beginnt, ist eine Bushaltestelle.",
                   "pl": "{p}, gdzie zaczyna się trasa, to przystanek autobusowy."},
    "end_stop": {"en": "The walk ends at {p}, which has a bus back to Funchal.", "pt": "O percurso termina em {p}, onde há autocarro de regresso ao Funchal.",
                 "fr": "La balade se termine à {p}, d'où un bus repart vers Funchal.", "de": "Die Wanderung endet in {p}, von dort fährt ein Bus zurück nach Funchal.",
                 "pl": "Trasa kończy się w {p}, skąd jest autobus powrotny do Funchal."},
    "no_start": {"en": "We found no bus to {p}, where the walk starts: you need a car, a taxi or a transfer.",
                 "pt": "Não encontrámos autocarro para {p}, onde o percurso começa: precisa de carro, táxi ou transfer.",
                 "fr": "Nous n'avons trouvé aucun bus pour {p}, le départ de la balade : il vous faut une voiture, un taxi ou un transfert.",
                 "de": "Wir haben keinen Bus nach {p} gefunden, wo die Wanderung beginnt: Sie brauchen ein Auto, ein Taxi oder einen Transfer.",
                 "pl": "Nie znaleźliśmy autobusu do {p}, gdzie zaczyna się trasa: potrzebny jest samochód, taksówka lub transfer."},
    "no_end": {"en": "We found no bus from {p}, where the walk ends: book a taxi or arrange a pick-up before you set off.",
               "pt": "Não encontrámos autocarro a partir de {p}, onde o percurso termina: reserve um táxi ou combine a recolha antes de partir.",
               "fr": "Nous n'avons trouvé aucun bus au départ de {p}, où la balade se termine : réservez un taxi ou organisez votre retour avant de partir.",
               "de": "Wir haben keinen Bus ab {p} gefunden, wo die Wanderung endet: Bestellen Sie vorab ein Taxi oder eine Abholung.",
               "pl": "Nie znaleźliśmy autobusu z {p}, gdzie trasa się kończy: zamów wcześniej taksówkę albo odbiór."},
    "from_ruivo": {"en": "The walk starts at the Pico Ruivo shelter, which no bus or road reaches: you get there on foot by PR1 or PR1.2.",
                   "pt": "O percurso começa na Casa de Abrigo do Pico Ruivo, onde não chega autocarro nem estrada: chega-se a pé pelo PR1 ou pelo PR1.2.",
                   "fr": "La balade part du refuge du Pico Ruivo, qu'aucun bus ni aucune route n'atteint : on y monte à pied par le PR1 ou le PR1.2.",
                   "de": "Die Wanderung beginnt an der Schutzhütte am Pico Ruivo, die kein Bus und keine Straße erreicht: Man kommt zu Fuß über PR1 oder PR1.2 hin.",
                   "pl": "Trasa zaczyna się przy schronisku na Pico Ruivo, do którego nie dojeżdża autobus ani nie prowadzi droga: dochodzi się pieszo szlakiem PR1 lub PR1.2."},
    "one_bus": {"en": "It is the only bus of the day from there, so don't miss it.", "pt": "É o único autocarro do dia a partir daí, não o perca.",
                "fr": "C'est le seul bus de la journée depuis cet arrêt : ne le ratez pas.", "de": "Es ist der einzige Bus des Tages ab dort, verpassen Sie ihn nicht.",
                "pl": "To jedyny autobus w ciągu dnia z tego miejsca, nie spóźnij się."},
    "window": {"en": "On weekdays that leaves about {h} hours between arriving at Prazeres and the bus back.",
               "pt": "Nos dias úteis, isso dá cerca de {h} horas entre a chegada aos Prazeres e o autocarro de regresso.",
               "fr": "En semaine, cela laisse environ {h} heures entre l'arrivée à Prazeres et le bus du retour.",
               "de": "An Werktagen bleiben so etwa {h} Stunden zwischen der Ankunft in Prazeres und dem Rückbus.",
               "pl": "W dni robocze daje to ok. {h} godziny między przyjazdem do Prazeres a autobusem powrotnym."},
    "portela": {"en": "Lines 53 and 78 (new no. 825) run via Portela, but their timetables print no time at Portela: ask CAM for the time it passes, or take a taxi.",
                "pt": "As linhas 53 e 78 (novo n.º 825) passam pela Portela, mas as tabelas não indicam a hora na Portela: pergunte à CAM a hora de passagem ou apanhe um táxi.",
                "fr": "Les lignes 53 et 78 (nouveau n° 825) passent par Portela, mais leurs fiches n'indiquent aucune heure à Portela : demandez l'heure de passage à la CAM ou prenez un taxi.",
                "de": "Die Linien 53 und 78 (neue Nr. 825) fahren über Portela, ihre Fahrpläne nennen dort aber keine Zeit: Fragen Sie bei CAM nach der Durchfahrtszeit oder nehmen Sie ein Taxi.",
                "pl": "Linie 53 i 78 (nowy nr 825) jadą przez Portelę, ale ich rozkłady nie podają godziny w Portela: zapytaj CAM o godzinę przejazdu albo weź taksówkę."},
    "plateau": {"en": "No public bus reaches {p}: none of the bus lines on SIGA serves the Paul da Serra plateau or the Fanal. You need a car, a taxi or a tour transfer.",
                "pt": "Nenhum autocarro público chega a {p}: nenhuma das linhas no SIGA serve o planalto do Paul da Serra nem o Fanal. Precisa de carro, táxi ou transfer.",
                "fr": "Aucun bus public ne va à {p} : aucune ligne publiée sur SIGA ne dessert le plateau du Paul da Serra ni le Fanal. Il vous faut une voiture, un taxi ou un transfert.",
                "de": "Kein öffentlicher Bus fährt nach {p}: Keine der Linien auf SIGA bedient die Hochebene Paul da Serra oder den Fanal. Sie brauchen ein Auto, ein Taxi oder einen Transfer.",
                "pl": "Żaden autobus publiczny nie dojeżdża do {p}: żadna z linii w SIGA nie obsługuje płaskowyżu Paul da Serra ani Fanalu. Potrzebny jest samochód, taksówka lub transfer."},
    "rabacal": {"en": "From the Rabaçal car park on the ER110, the Calheta council runs a shuttle down to the Rabaçal house (pay in cash).",
                "pt": "Do parque de estacionamento do Rabaçal, na ER110, a Câmara da Calheta tem um vaivém até à Casa do Rabaçal (pagamento em dinheiro).",
                "fr": "Depuis le parking du Rabaçal sur l'ER110, la mairie de Calheta fait circuler une navette jusqu'à la maison du Rabaçal (paiement en espèces).",
                "de": "Vom Parkplatz Rabaçal an der ER110 fährt ein Shuttle der Gemeinde Calheta hinunter zum Rabaçal-Haus (Barzahlung).",
                "pl": "Z parkingu Rabaçal przy ER110 gmina Calheta prowadzi bus wahadłowy do domu Rabaçal (płatność gotówką)."},
    "queimadas": {"en": "No bus goes up to Queimadas. Take a CAM bus to Santana, then a taxi up to the Queimadas forest park (ask the fare when you book).",
                  "pt": "Nenhum autocarro sobe às Queimadas. Apanhe um autocarro da CAM até Santana e depois um táxi até ao Parque Florestal das Queimadas (pergunte o preço ao reservar).",
                  "fr": "Aucun bus ne monte à Queimadas. Prenez un bus de la CAM jusqu'à Santana, puis un taxi jusqu'au parc forestier de Queimadas (demandez le prix en réservant).",
                  "de": "Kein Bus fährt hinauf nach Queimadas. Nehmen Sie einen CAM-Bus nach Santana und dann ein Taxi zum Waldpark Queimadas (fragen Sie bei der Buchung nach dem Preis).",
                  "pl": "Żaden autobus nie dojeżdża do Queimadas. Jedź autobusem CAM do Santany, a dalej taksówką do parku leśnego Queimadas (zapytaj o cenę przy rezerwacji)."},
}

# Trip lists: (departure, arrival or None, marks) — marks: "T" change bus, "PE"/"PNE" school term / holidays.
L113_THERE = {"mon_fri": [("07:30", "08:50", ""), ("08:30", "09:50", ""), ("09:00", "10:20", ""), ("11:00", "12:30", "T"), ("11:30", "12:50", ""),
                          ("12:15", "13:45", ""), ("14:30", "15:55", ""), ("16:30", "17:45", ""), ("18:15", "19:40", "")],
              "sat": [("07:30", "08:45", ""), ("08:30", "09:45", ""), ("09:00", "10:15", ""), ("10:30", "11:55", ""), ("11:30", "12:40", ""),
                      ("12:15", "13:30", ""), ("14:30", "15:45", ""), ("15:30", "16:45", ""), ("18:15", "19:30", "")],
              "sun_hol": [("07:30", "08:40", ""), ("09:00", "10:15", ""), ("10:30", "12:00", ""), ("11:30", "12:55", ""), ("15:00", "16:15", "T"), ("16:30", "17:55", "T")]}
L113_BACK = {"mon_fri": [("09:20", "10:45", "T"), ("10:30", "12:00", ""), ("11:30", "13:00", ""), ("12:00", "13:15", "T PNE"), ("12:00", "13:45", "T PE"),
                         ("12:55", "14:15", "T"), ("13:55", "15:15", "T"), ("15:00", "16:15", "T"), ("16:00", "17:15", "T"), ("17:00", "18:15", ""),
                         ("18:15", "19:45", ""), ("19:35", "21:05", "")],
             "sat": [("09:20", "10:50", ""), ("10:30", "12:00", ""), ("11:30", "13:00", ""), ("13:00", "14:30", ""), ("14:00", "15:30", ""),
                     ("16:00", "17:30", "T"), ("17:00", "18:30", ""), ("18:15", "19:45", ""), ("19:35", "21:05", "")],
             "sun_hol": [("09:20", "10:50", ""), ("11:55", "13:15", ""), ("14:00", "15:30", ""), ("15:30", "17:00", ""), ("17:00", "18:30", ""), ("18:15", "19:45", "")]}
L142_PRAZERES = {"daily": [("08:05", "11:15", "")]}
L6_ENCUMEADA_BACK = {"daily": [("16:00", "17:05", "")]}
L21_MONTE = {"mon_fri": [(t, None, "") for t in "13:05 13:40 14:15 14:40 15:05 15:35 16:15 17:30 17:45 19:05".split()],
             "sat": [(t, None, "") for t in "15:55 18:05".split()],
             "sun_hol": [(t, None, "") for t in "14:25 14:50 16:00 18:05".split()]}
L181_CURRAL = {"mon_fri": [(t, None, "") for t in "06:55 07:35 08:25 09:00 10:00 11:00".split()],
               "sat": [(t, None, "") for t in "07:40 08:45 10:00 11:30".split()],
               "sun_hol": [(t, None, "") for t in "06:40 09:05 11:40".split()]}
L156_MAROCOS_BACK = {"mon_fri": [("15:30", "16:45", ""), ("17:00", "18:30", ""), ("19:00", "20:15", ""), ("21:10", "22:20", "")],
                     "sat": [("11:30", "13:00", ""), ("12:45", "14:00", ""), ("22:35", "23:45", "")],
                     "sun_hol": [("15:45", "17:00", ""), ("19:40", "20:55", ""), ("22:35", "23:45", "")]}
CAM_SANTANA_THERE = {"mon_fri": [("07:30", "09:00", ""), ("08:10", "10:00", ""), ("09:00", "10:25", ""), ("10:00", "11:25", "")],
                     "sat": [("07:30", "09:13", ""), ("10:00", "11:20", "")], "sun_hol": [("07:30", "09:18", ""), ("10:30", "12:00", "")]}
CAM_SANTANA_BACK = {"mon_fri": [("12:30", "14:25", ""), ("17:25", "19:00", "")], "sat": [("12:00", "13:30", ""), ("13:15", "14:20", ""), ("17:28", "19:20", "")],
                    "sun_hol": [("15:30", "16:50", ""), ("17:28", "19:20", "")]}


def seg(op, n, a, b, trips, new=None, change_at=None, deps_only=False):
    return {"op": op, "n": n, "new": new, "a": a, "b": b, "trips": trips, "change_at": change_at, "deps": deps_only}


def paul_back(stop, t142, t80):
    return [seg("Rodoeste", "142", stop, "Funchal", {"mon_fri": [(t142, "16:55", "")]}),
            seg("Rodoeste", "80", stop, "Funchal", {"sat_sun_hol": [(t80, "18:40", "")]})]


TRAILS = {
    "PR8": {"dir": "sao-lourenco", "there": [("loop_stop", "Baía d'Abra"),
            seg("CAM", "113", "Funchal", "Baía d'Abra", L113_THERE, new="702", change_at="Machico")],
            "back": [seg("CAM", "113", "Baía d'Abra", "Funchal", L113_BACK, new="702", change_at="Machico")]},
    "PR19": {"dir": "caminho-real-do-paul-do-mar", "there": [("start_stop", "Prazeres"), seg("Rodoeste", "142", "Funchal", "Prazeres", L142_PRAZERES)],
             "back": [("end_stop", "Paul do Mar")] + paul_back("Paul do Mar", "14:15", "17:00") + [("window", "3")]},
    "PR20": {"dir": "vereda-do-jardim-do-mar", "there": [("start_stop", "Prazeres"), seg("Rodoeste", "142", "Funchal", "Prazeres", L142_PRAZERES)],
             "back": [("end_stop", "Jardim do Mar")] + paul_back("Jardim do Mar", "14:20", "17:05") + [("window", "3")]},
    "PR3.1": {"dir": "caminho-real-do-monte", "there": [("no_start", "Ribeira das Cales")],
              "back": [("end_stop", "Monte"), seg("Horários do Funchal", "21", "Monte", "Funchal", L21_MONTE, deps_only=True)]},
    "PR1.3": {"dir": "vereda-da-encumeada", "there": [("from_ruivo",)],
              "back": [("end_stop", "Encumeada"), seg("Rodoeste", "6", "Encumeada", "Funchal", L6_ENCUMEADA_BACK), ("one_bus",)]},
    "PR17": {"dir": "caminho-do-pinaculo-e-folhadal", "there": [("no_start", "Lombo do Mouro")],
             "back": [("end_stop", "Encumeada"), seg("Rodoeste", "6", "Encumeada", "Funchal", L6_ENCUMEADA_BACK), ("one_bus",)]},
    "PR2": {"dir": "vereda-do-urzal", "there": [("start_stop", "Curral das Freiras"),
            seg("Horários do Funchal", "81", "Funchal", "Curral das Freiras", L181_CURRAL, new="181", deps_only=True)],
            "back": [("no_end", "Lombo do Urzal")]},
    "PR5": {"dir": "vereda-das-funduras", "there": [("portela",)],
            "back": [("end_stop", "Maroços"), seg("CAM", "156", "Maroços", "Funchal", L156_MAROCOS_BACK, new="704")]},
    "PR9": {"dir": "caldeirao-verde", "there": [("queimadas",), seg("CAM", "Santana", "Funchal", "Santana", CAM_SANTANA_THERE)],
            "back": [seg("CAM", "Santana", "Santana", "Funchal", CAM_SANTANA_BACK)]},
    "PR9.1": {"dir": "levada-do-caldeirao-verde-um-caminho-para-todos", "there": [("queimadas",), seg("CAM", "Santana", "Funchal", "Santana", CAM_SANTANA_THERE)],
              "back": [seg("CAM", "Santana", "Santana", "Funchal", CAM_SANTANA_BACK)]},
}
for code, d, place, rab in [("PR6", "25-fontes", "Rabaçal", True), ("PR6.1", "levada-do-risco", "Rabaçal", True), ("PR6.2", "levada-do-alecrim", "Rabaçal", True),
                            ("PR6.3", "vereda-da-lagoa-do-vento", "Rabaçal", True), ("PR6.4", "levada-velha-do-rabacal", "Rabaçal", True),
                            ("PR6.8", "levada-do-paul-ii-um-caminho-para-todos", "Rabaçal", True), ("PR6.5", "vereda-do-pico-fernandes", "Paul da Serra", False),
                            ("PR6.6", "vereda-do-tunel-do-cavalo", "Paul da Serra", False), ("PR13.1", "vereda-da-palha-carga", "Paul da Serra", False),
                            ("PR27", "glaciar-de-planalto", "Paul da Serra", False), ("PR13", "fanal", "Fanal", False), ("PR28", "levada-da-rocha-vermelha", "Fanal", False)]:
    TRAILS[code] = {"dir": d, "nobus": [("plateau", place)] + ([("rabacal",)] if rab else [])}


def esc(s):
    return html.escape(s, quote=False)


def sentence(item, lang):
    key, *args = item
    t = S[key][lang]
    return t.format(p=esc(args[0]), h=args[0]) if args else t


def render_seg(s, lang):
    if s["n"] == "Santana":
        line = {"en": "CAM's Santana-line buses", "pt": "autocarros da rede Santana da CAM", "fr": "bus du réseau Santana de la CAM",
                "de": "CAM-Busse des Santana-Netzes", "pl": "autobusy sieci Santana firmy CAM"}[lang]
    else:
        line = T["line"][lang].format(op=s["op"], n=s["n"])
        if s["new"]:
            nx = T["new"][lang].format(x=s["new"]).strip()[1:-1]  # "new no. 702"
            line = line[:-1] + f", {nx})" if line.endswith(")") else line + f" ({nx})"
    head = f"{line[0].upper() + line[1:]}, {esc(s['a'])} → {esc(s['b'])}"
    if s["deps"]:
        head += " (" + T["deps"][lang].format(a=esc(s["a"])) + ")"
    parts, star = [], False
    for day, trips in s["trips"].items():
        items = []
        for dep, arr, marks in trips:
            x = dep if arr is None else f"{dep} → {arr}"
            if "T" in marks.split():
                x += "*"; star = True
            if "PE" in marks.split():
                x += T["PE"][lang]
            if "PNE" in marks.split():
                x += T["PNE"][lang]
            items.append(x)
        parts.append(f"{T['days'][day][lang]}{' :' if lang == 'fr' else ':'} {', '.join(items)}.")
    out = f"{head}. " + " ".join(parts)
    if star and s["change_at"]:
        out += " " + T["change"][lang].format(p=esc(s["change_at"]))
    return out


def render_block(items, lang):
    return " ".join(render_seg(i, lang) if isinstance(i, dict) else sentence(i, lang) for i in items)


def section(code, lang):
    t = TRAILS[code]
    body = []
    if "nobus" in t:
        body.append(f"  <p>{render_block(t['nobus'], lang)}</p>")
    else:
        body.append(f"  <p><b>{T['there'][lang]}</b> {render_block(t['there'], lang)}</p>")
        body.append(f"  <p><b>{T['back'][lang]}</b> {render_block(t['back'], lang)}</p>")
        body.append(f'  <p style="font-size:13px;color:var(--ink-soft);margin-top:8px">{T["src"][lang]}</p>')
    return f'<section id="bus">\n  <h2>{T["h"][lang]}</h2>\n' + "\n".join(body) + "\n</section>\n"


def main():
    n = 0
    for code, t in TRAILS.items():
        for lang in LANGS:
            f = ROOT / PREFIX[lang] / t["dir"] / "index.html"
            h = f.read_text(encoding="utf-8")
            assert f'data-trail="{code}"' in h, (f, code)
            block = f"<!-- BUS:START (scripts/gen_bus.py) -->\n{section(code, lang)}<!-- BUS:END -->\n"
            if "<!-- BUS:START" in h:
                new = re.sub(r"<!-- BUS:START[^>]*-->.*?<!-- BUS:END -->\n?", lambda m: block, h, count=1, flags=re.S)
            else:
                m = re.search(r'<section id="getting-(?:there|back)"[^>]*>.*?</section>\n*', h, re.S)
                assert m, (f, "no getting-there section")
                new = h[:m.end()] + block + "\n" + h[m.end():]
            if new != h:
                f.write_text(new, encoding="utf-8"); n += 1
    print(f"bus sections written to {n} page(s)")


if __name__ == "__main__":
    main()
