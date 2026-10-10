"""Pre-populated answers (owner, 2026-10-10): the questions people actually send, answered by code from our stored
facts, in 5 languages, with no model. They go out instantly (even while the model sleeps) and can't drift.

Real chats (4-8 Oct) were all "how do I get to / back from PR1", twice from cruise passengers. So:
  - cruise():    someone on a cruise ship: the ship's real time in port (APRAM schedule, if we can match it),
                 what fits, taxis from the port, getting back from Achada do Teixeira; never "hotel reception".
  - pr1_trip():  PR1 status (with what PARTLY OPEN means), one-way rule, ticket, getting there (bus as printed,
                 taxis), getting back from Achada do Teixeira, and a pick-up window from their entrance time.
  - trail_trip(): any other trail: status, getting there and back (bus as printed, the taxi ranks on its IFCN panel).
  - status_line(): the status sentence the guard puts in front of any model answer that names a trail.
Every fact comes from status.json, backend/kbtools (the knowledge store) or the APRAM cruise calls; nothing is
written from memory. quick() decides; None = let the model answer (guard.py still checks it).
"""
import datetime, json, os, re, sys, unicodedata, zoneinfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
import kbtools  # noqa: E402

TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRUISE_CALLS = os.path.join(ROOT, "seo_research/funchal/mobility/data/cruise_calls.json")
SITE = "https://levadinho-madeira.com"
LP = {"en": "", "pt": "/pt", "fr": "/fr", "de": "/de", "pl": "/pl"}


STOP = {
    "pt": "e o a os as de do da dos das para com um uma que nao meu minha gostaria estou como onde quero esta obrigado obrigada amanha hoje trilha percurso navio",
    "en": "the and to for is are we i you how what where can do my have from with would our please tomorrow today",
    "fr": "le la les et pour avec je nous est une un des du comment ou vous mon ma demain aujourd hui bonjour merci",
    "de": "der die das und ich wir ist mit fur wie wo nicht ein eine zum zur mein morgen heute bitte danke hallo",
    "pl": "i w na z do jak gdzie czy jest sie nie to mam chce moj jutro dzisiaj prosze dziekuje",
}
STOP = {k: set(v.split()) for k, v in STOP.items()}


def detect_lang(text, fallback="en"):
    """Language of a message by common words (accents folded); unclear -> fallback (the visitor's chosen language)."""
    words = re.findall(r"[a-z]+", fold(text))
    scores = sorted(((sum(w in STOP[l] for w in words), l) for l in STOP), reverse=True)
    (best, lang), (second, _) = scores[0], scores[1]
    return lang if best >= 2 and best > second else fallback


def fold(t):
    return "".join(c for c in unicodedata.normalize("NFKD", (t or "").lower()) if not unicodedata.combining(c))


CRUISE_RE = re.compile(r"\b(navio|cruzeiro|cruise|cruiseship|ship|msc|aida|kreuzfahrt\w*|schiff|croisiere|paquebot|"
                       r"statek|statku|rejs\w*|wycieczkow\w*|porto do funchal|cruise port|terminal de cruzeiros)\b")
TRANSPORT_RE = re.compile(r"transfer|taxi|bus\b|autocarro|shuttle|navette|pick ?up|pickup|recolha|boleia|lift\b|"
                          r"get (there|back|to)|getting (there|back|to)|how (do i|to|can i|can we|do we) get|go back|return|"
                          r"voltar|volto|voltamos|regress|chegar|como ir|ir para|comment (aller|y aller|rejoindre)|wie komme|komme ich|"
                          r"anreise|hinfahren|jak dojechac|jak dostac|"
                          r"retour|aller|rentrer|zuruck|hinkommen|abhol|dojazd|dojechac|dojsc|wrocic|powrot|transport")
STATUS_RE = re.compile(r"\b(open|opened|closed|aberto|aberta|fechad\w*|encerrad\w*|ouvert\w*|ferme\w*|geoffnet|offen|"
                       r"gesperrt|geschlossen|otwart\w*|zamkniet\w*)\b")
TIME_RE = re.compile(r"\b([01]?\d|2[0-3])[:h.]([0-5]\d)\b|\b([01]?\d|2[0-3])\s?(h|am|pm|uhr)\b", re.I)

ST = {"OPEN": {"en": "OPEN", "pt": "ABERTO", "fr": "OUVERT", "de": "GEÖFFNET", "pl": "OTWARTY"},
      "PARTIAL": {"en": "PARTLY OPEN", "pt": "PARCIALMENTE ABERTO", "fr": "PARTIELLEMENT OUVERT",
                  "de": "TEILWEISE GEÖFFNET", "pl": "CZĘŚCIOWO OTWARTY"},
      "CLOSED": {"en": "CLOSED", "pt": "ENCERRADO", "fr": "FERMÉ", "de": "GESCHLOSSEN", "pl": "ZAMKNIĘTY"}}

T = {
 "status": {"en": "*{name} ({code})* is *{st}* on IFCN's official warnings list.",
            "pt": "*{name} ({code})*: *{st}* na lista oficial de avisos do IFCN.",
            "fr": "*{name} ({code})* : *{st}* sur la liste officielle des avis de l'IFCN.",
            "de": "*{name} ({code})*: *{st}* laut offizieller Hinweisliste des IFCN.",
            "pl": "*{name} ({code})*: *{st}* według oficjalnej listy komunikatów IFCN."},
 "pr1_partial": {"en": "*Vereda do Areeiro (PR1)*, on IFCN's official warnings list:\n• Pico do Areeiro ↔ Pedra Rija viewpoint: *both ways*.\n• Full trail to Pico Ruivo: *one way only*, ending at Achada do Teixeira.",
                 "pt": "*Vereda do Areeiro (PR1)*, na lista oficial de avisos do IFCN:\n• Pico do Areeiro ↔ Miradouro da Pedra Rija: *nos dois sentidos*.\n• Percurso completo até ao Pico Ruivo: *só num sentido*, a terminar na Achada do Teixeira.",
                 "fr": "*Vereda do Areeiro (PR1)*, sur la liste officielle des avis de l'IFCN :\n• Pico do Areeiro ↔ belvédère de Pedra Rija : *dans les deux sens*.\n• Parcours complet jusqu'au Pico Ruivo : *sens unique*, arrivée à Achada do Teixeira.",
                 "de": "*Vereda do Areeiro (PR1)*, laut offizieller Hinweisliste des IFCN:\n• Pico do Areeiro ↔ Aussichtspunkt Pedra Rija: *in beide Richtungen*.\n• Ganze Strecke bis zum Pico Ruivo: *nur in eine Richtung*, Ende in Achada do Teixeira.",
                 "pl": "*Vereda do Areeiro (PR1)*, według oficjalnej listy komunikatów IFCN:\n• Pico do Areeiro ↔ punkt widokowy Pedra Rija: *w obie strony*.\n• Cała trasa na Pico Ruivo: *tylko w jedną stronę*, z końcem w Achada do Teixeira."},
 "partial": {"en": "*{name} ({code})*, on IFCN's official warnings list: {n}", "pt": "*{name} ({code})*, na lista oficial de avisos do IFCN: {n}",
             "fr": "*{name} ({code})*, sur la liste officielle des avis de l'IFCN : {n}", "de": "*{name} ({code})*, laut offizieller Hinweisliste des IFCN: {n}",
             "pl": "*{name} ({code})*, według oficjalnej listy komunikatów IFCN: {n}"},
 "note": {"en": "IFCN's note: {n}", "pt": "Nota do IFCN: {n}", "fr": "Note de l'IFCN : {n}", "de": "Hinweis des IFCN: {n}", "pl": "Uwaga IFCN: {n}"},
 "closed_alt": {"en": "Don't walk it while it is closed.", "pt": "Não o faça enquanto estiver encerrado.", "fr": "Ne le parcourez pas tant qu'il est fermé.",
                "de": "Gehen Sie ihn nicht, solange er gesperrt ist.", "pl": "Nie wchodź na szlak, dopóki jest zamknięty."},
 "ticket_pr1": {"en": "Ticket: SIMplifica, online only, €10.50 per person for the full walk (€4.50 for Areeiro ↔ Pedra Rija and back), for a timed slot.",
                "pt": "Bilhete: SIMplifica, só online, 10,50 € por pessoa no percurso completo (4,50 € para Areeiro ↔ Pedra Rija e volta), com hora marcada.",
                "fr": "Billet : SIMplifica, en ligne uniquement, 10,50 € par personne pour le parcours complet (4,50 € pour Areeiro ↔ Pedra Rija aller-retour), avec un créneau horaire.",
                "de": "Ticket: SIMplifica, nur online, 10,50 € pro Person für die ganze Strecke (4,50 € für Areeiro ↔ Pedra Rija hin und zurück), mit Zeitfenster.",
                "pl": "Bilet: SIMplifica, tylko online, 10,50 € od osoby za całą trasę (4,50 € za Areeiro ↔ Pedra Rija i z powrotem), na konkretną godzinę."},
 "ticket": {"en": "Ticket: SIMplifica, online only, €4.50 per person, for a timed slot.",
            "pt": "Bilhete: SIMplifica, só online, 4,50 € por pessoa, com hora marcada.",
            "fr": "Billet : SIMplifica, en ligne uniquement, 4,50 € par personne, avec un créneau horaire.",
            "de": "Ticket: SIMplifica, nur online, 4,50 € pro Person, mit Zeitfenster.",
            "pl": "Bilet: SIMplifica, tylko online, 4,50 € od osoby, na konkretną godzinę."},
 "no_fee": {"en": "No IFCN ticket is needed (it is run by another body).", "pt": "Não precisa de bilhete do IFCN (é gerido por outra entidade).",
            "fr": "Pas de billet IFCN (il est géré par un autre organisme).", "de": "Kein IFCN-Ticket nötig (ein anderer Träger betreibt ihn).",
            "pl": "Bilet IFCN nie jest potrzebny (szlakiem zarządza inny podmiot)."},
 "pr1_walk": {"en": "The full walk is about 3 h from Pico do Areeiro to Pico Ruivo, then about 45–60 min down PR1.2 to *Achada do Teixeira*, where it ends. No bus goes there.",
              "pt": "O percurso completo leva cerca de 3 h do Pico do Areeiro ao Pico Ruivo e depois cerca de 45–60 min a descer pelo PR1.2 até à *Achada do Teixeira*, onde termina. Não há autocarro lá.",
              "fr": "Le parcours complet prend environ 3 h du Pico do Areeiro au Pico Ruivo, puis environ 45–60 min de descente par le PR1.2 jusqu'à *Achada do Teixeira*, où il se termine. Aucun bus n'y va.",
              "de": "Die ganze Strecke dauert etwa 3 Std. vom Pico do Areeiro zum Pico Ruivo, dann etwa 45–60 Min. über den PR1.2 hinunter nach *Achada do Teixeira*, wo sie endet. Dort fährt kein Bus.",
              "pl": "Cała trasa to około 3 godz. z Pico do Areeiro na Pico Ruivo, potem około 45–60 min zejścia szlakiem PR1.2 do *Achada do Teixeira*, gdzie się kończy. Nie dojeżdża tam żaden autobus."},
 "window": {"en": "With a {slot} entrance you reach Achada do Teixeira at about *{a}–{b}* on walking time alone; add your breaks and book the pick-up for then, not hours later.",
            "pt": "Com entrada às {slot}, chega à Achada do Teixeira por volta das *{a}–{b}* só a andar; some as pausas e marque a recolha para essa hora, não horas depois.",
            "fr": "Avec une entrée à {slot}, vous arrivez à Achada do Teixeira vers *{a}–{b}* en temps de marche seul ; ajoutez vos pauses et réservez la prise en charge pour ce moment-là, pas des heures plus tard.",
            "de": "Mit Einlass um {slot} sind Sie reine Gehzeit gegen *{a}–{b}* in Achada do Teixeira; rechnen Sie Pausen dazu und bestellen Sie die Abholung für dann, nicht Stunden später.",
            "pl": "Z wejściem o {slot} dojdziesz do Achada do Teixeira około *{a}–{b}* (sam czas marszu); dolicz przerwy i zamów odbiór na tę porę, a nie kilka godzin później."},
 "there_bus": {"en": "Getting there by bus (as printed): {tt}", "pt": "Ir de autocarro (horário impresso): {tt}", "fr": "Y aller en bus (horaires imprimés) : {tt}",
               "de": "Hin mit dem Bus (laut Fahrplan): {tt}", "pl": "Dojazd autobusem (według rozkładu): {tt}"},
 "back_bus": {"en": "Back by bus (as printed): {tt}", "pt": "Voltar de autocarro (horário impresso): {tt}", "fr": "Retour en bus (horaires imprimés) : {tt}",
              "de": "Zurück mit dem Bus (laut Fahrplan): {tt}", "pl": "Powrót autobusem (według rozkładu): {tt}"},
 "taxis": {"en": "Taxis (official ranks): {t}. Call two, ask each for a quote and take the better one; fares are metered at the official tariff.",
           "pt": "Táxis (praças oficiais): {t}. Ligue para dois, peça orçamento a cada um e escolha o melhor; o preço é pelo taxímetro, à tarifa oficial.",
           "fr": "Taxis (stations officielles) : {t}. Appelez-en deux, demandez un devis à chacun et prenez le meilleur ; les courses sont au compteur, au tarif officiel.",
           "de": "Taxis (offizielle Standplätze): {t}. Rufen Sie zwei an, lassen Sie sich je einen Preis nennen und nehmen Sie den besseren; abgerechnet wird nach Taxameter zum offiziellen Tarif.",
           "pl": "Taksówki (oficjalne postoje): {t}. Zadzwoń do dwóch, zapytaj każdą o cenę i wybierz lepszą; opłata według taksometru, po oficjalnej taryfie."},
 "back_pr1": {"en": "Getting back from Achada do Teixeira: book a taxi for your finish time, e.g. {t}.",
              "pt": "Regresso da Achada do Teixeira: marque um táxi para a hora a que acaba, por exemplo {t}.",
              "fr": "Retour depuis Achada do Teixeira : réservez un taxi pour votre heure d'arrivée, par exemple {t}.",
              "de": "Zurück von Achada do Teixeira: Bestellen Sie ein Taxi für Ihre Ankunftszeit, z. B. {t}.",
              "pl": "Powrót z Achada do Teixeira: zamów taksówkę na godzinę zakończenia, np. {t}."},
 "ship_found": {"en": "Your ship *{ship}* is in Funchal from *{a}* to *{d}* (port schedule, APRAM). All-aboard is earlier than departure: check your ship's programme.",
                "pt": "O seu navio *{ship}* está no Funchal das *{a}* às *{d}* (horário do porto, APRAM). A hora de embarque é antes da partida: confirme no programa do navio.",
                "fr": "Votre navire *{ship}* est à Funchal de *{a}* à *{d}* (horaires du port, APRAM). L'heure de retour à bord est avant le départ : vérifiez le programme du navire.",
                "de": "Ihr Schiff *{ship}* liegt von *{a}* bis *{d}* in Funchal (Hafenplan, APRAM). Alle an Bord ist früher als die Abfahrt: prüfen Sie das Bordprogramm.",
                "pl": "Twój statek *{ship}* stoi w Funchal od *{a}* do *{d}* (rozkład portu, APRAM). Powrót na pokład jest wcześniej niż wypłynięcie: sprawdź program statku."},
 "ship_ask": {"en": "What time must you be back on board? I'll fit the walk to it.",
              "pt": "A que horas tem de estar de volta a bordo? Ajusto o percurso a isso.",
              "fr": "À quelle heure devez-vous être de retour à bord ? J'adapte la randonnée.",
              "de": "Wann müssen Sie wieder an Bord sein? Ich passe die Wanderung daran an.",
              "pl": "O której musisz wrócić na pokład? Dopasuję do tego trasę."},
 "ship_nobus": {"en": "The only morning bus to Pico do Areeiro leaves Funchal at 06:00, before ships are in, so from the port it's a taxi there and a taxi back.",
                "pt": "O único autocarro da manhã para o Pico do Areeiro sai do Funchal às 06:00, antes de os navios chegarem, por isso do porto é táxi para lá e táxi para cá.",
                "fr": "Le seul bus du matin pour le Pico do Areeiro part de Funchal à 06:00, avant l'arrivée des navires : depuis le port, c'est taxi à l'aller et au retour.",
                "de": "Der einzige Morgenbus zum Pico do Areeiro fährt um 06:00 in Funchal ab, bevor die Schiffe da sind: vom Hafen also Taxi hin und Taxi zurück.",
                "pl": "Jedyny poranny autobus na Pico do Areeiro odjeżdża z Funchal o 06:00, zanim przypłyną statki, więc z portu jedziesz taksówką tam i z powrotem."},
 "ship_short": {"en": "Short on time? The Areeiro ↔ Pedra Rija section (1.2 km each way, €4.50) starts and ends at the same car park, so your taxi can wait or come back.",
                "pt": "Pouco tempo? O troço Areeiro ↔ Pedra Rija (1,2 km para cada lado, 4,50 €) começa e acaba no mesmo parque, por isso o táxi pode esperar ou voltar.",
                "fr": "Peu de temps ? La section Areeiro ↔ Pedra Rija (1,2 km dans chaque sens, 4,50 €) part et revient au même parking : le taxi peut attendre ou revenir.",
                "de": "Wenig Zeit? Der Abschnitt Areeiro ↔ Pedra Rija (je 1,2 km, 4,50 €) beginnt und endet am selben Parkplatz, das Taxi kann warten oder wiederkommen.",
                "pl": "Mało czasu? Odcinek Areeiro ↔ Pedra Rija (1,2 km w każdą stronę, 4,50 €) zaczyna się i kończy na tym samym parkingu, więc taksówka może poczekać albo wrócić."},
 "ship_generic": {"en": "Tell me which walk you have in mind and I'll fit it to your time in port.",
                  "pt": "Diga-me que percurso tem em mente e ajusto-o ao seu tempo em terra.",
                  "fr": "Dites-moi quelle randonnée vous intéresse et je l'adapte à votre escale.",
                  "de": "Sagen Sie mir, welche Wanderung Sie vorhaben, und ich passe sie an Ihre Liegezeit an.",
                  "pl": "Napisz, o którą trasę chodzi, a dopasuję ją do czasu postoju w porcie."},
 "generic_taxi": {"en": "Taxis from {b} (official ranks): {t}. Call two, ask each for a quote and take the better one; fares are metered at the official tariff. Tell me which walk you're going to and I'll add the bus and the way back.",
                  "pt": "Táxis a partir de {b} (praças oficiais): {t}. Ligue para dois, peça orçamento a cada um e escolha o melhor; o preço é pelo taxímetro, à tarifa oficial. Diga-me para que percurso vai e junto o autocarro e o regresso.",
                  "fr": "Taxis depuis {b} (stations officielles) : {t}. Appelez-en deux, demandez un devis à chacun et prenez le meilleur ; les courses sont au compteur, au tarif officiel. Dites-moi quelle randonnée vous visez et j'ajoute le bus et le retour.",
                  "de": "Taxis ab {b} (offizielle Standplätze): {t}. Rufen Sie zwei an, lassen Sie sich je einen Preis nennen und nehmen Sie den besseren; abgerechnet wird nach Taxameter. Sagen Sie mir, zu welcher Wanderung Sie wollen, dann ergänze ich Bus und Rückweg.",
                  "pl": "Taksówki z {b} (oficjalne postoje): {t}. Zadzwoń do dwóch, zapytaj każdą o cenę i wybierz lepszą; opłata według taksometru. Napisz, na który szlak jedziesz, a dodam autobus i powrót."},
 "airport_taxi": {"en": "From the airport (Santa Cruz) to {b}: there is no airport taxi rank in our official data, so call the rank of {b} or an island-wide service: {t}. Ask each for a quote; fares are metered at the official tariff.",
                  "pt": "Do aeroporto (Santa Cruz) para {b}: não há praça de táxis do aeroporto nos nossos dados oficiais, por isso ligue para a praça de {b} ou um serviço de toda a ilha: {t}. Peça orçamento a cada um; o preço é pelo taxímetro, à tarifa oficial.",
                  "fr": "De l'aéroport (Santa Cruz) à {b} : pas de station de taxis de l'aéroport dans nos données officielles ; appelez la station de {b} ou un service de toute l'île : {t}. Demandez un devis à chacun ; course au compteur, tarif officiel.",
                  "de": "Vom Flughafen (Santa Cruz) nach {b}: In unseren offiziellen Daten gibt es keinen Flughafen-Taxistand; rufen Sie den Stand von {b} oder einen inselweiten Dienst an: {t}. Lassen Sie sich je einen Preis nennen; Taxameter zum offiziellen Tarif.",
                  "pl": "Z lotniska (Santa Cruz) do {b}: w naszych oficjalnych danych nie ma postoju taksówek na lotnisku, więc zadzwoń na postój w {b} albo do serwisu na całą wyspę: {t}. Zapytaj każdego o cenę; opłata według taksometru."},
 "from_place": {"en": "From {p} to {b}: {t}. Book it for your finish time and ask for a quote; fares are metered at the official tariff.",
                "pt": "De {p} para {b}: {t}. Marque-o para a hora a que acaba e peça orçamento; o preço é pelo taxímetro, à tarifa oficial.",
                "fr": "De {p} à {b} : {t}. Réservez-le pour votre heure d'arrivée et demandez un devis ; course au compteur, tarif officiel.",
                "de": "Von {p} nach {b}: {t}. Bestellen Sie es für Ihre Ankunftszeit und fragen Sie nach dem Preis; Taxameter zum offiziellen Tarif.",
                "pl": "Z {p} do {b}: {t}. Zamów ją na godzinę zakończenia i zapytaj o cenę; opłata według taksometru."},
 "page": {"en": "Live status and details: {u}", "pt": "Estado e detalhes: {u}", "fr": "Statut et détails : {u}", "de": "Status und Details: {u}", "pl": "Status i szczegóły: {u}"},
}


def _status_data():
    import brain  # live status.json, cached (same source as the site)
    return brain.live_status()


def _trail(code):
    return next((t for t in _status_data().get("trails", []) if t["code"] == code), None)


def status_line(code, lang):
    t = _trail(code)
    if not t:
        return ""
    note = t.get("note") or {}
    text = note.get(lang) or note.get("en") or "" if isinstance(note, dict) else note
    # Owner, 2026-10-10: never "PARTLY OPEN" (confusing); OPEN / CLOSED, or the full description of what is open.
    if t["status"] == "PARTIAL":
        if code == "PR1" and re.search(r"sentido [uú]nico|one-way", json.dumps(note, ensure_ascii=False), re.I):
            return T["pr1_partial"][lang]
        return T["partial"][lang].format(name=t["name"], code=code, n=text or ST["PARTIAL"][lang])
    out = [T["status"][lang].format(name=t["name"], code=code, st=ST[t["status"]][lang])]
    if t["status"] != "OPEN" and text:
        out.append(T["note"][lang].format(n=text))
    if t["status"] == "CLOSED":
        out.append(T["closed_alt"][lang])
    return " ".join(out)


def _taxis(trail=None, pickup=None, destination=None, n=3):
    r = kbtools.transport(trail=trail, pickup=pickup, destination=destination)
    seen, out = set(), []
    for x in r.get("taxis", []):
        key = tuple(x.get("phone") or [x["name"]])   # same number under two names (Táxis Funchal / Táxis Madeira)
        if key in seen:
            continue
        seen.add(key)
        out.append(f"*{x['name']}* {', '.join(x.get('phone') or [])}".strip())
    return ", ".join(out[:n])


def _bus(trail, leg):
    b = kbtools.bus(trail=trail)
    lines = [l for l in b.get("timetable", []) if l.startswith(leg + " ·")]
    return " | ".join(l.split(" · ", 1)[1] for l in lines)


def _page(code, lang):
    t = _trail(code)
    return f"{SITE}{LP[lang]}{t['page']}" if t and t.get("page") else ""


def _hhmm(text):
    m = TIME_RE.search(text or "")
    if not m:
        return None
    if m.group(1):
        h, mi = int(m.group(1)), int(m.group(2))
    else:
        h, mi = int(m.group(3)), 0
        if m.group(4).lower() == "pm" and h < 12:
            h += 12
    return h, mi


ENTRANCE_RE = re.compile(r"(entrance|entry|slot|booked|ticket|entrada|bilhete|reserv\w*|marcad\w*|creneau|entree|"
                         r"einlass|eintritt|gebucht|zeitfenster|wejscie|wejsciem|bilet\w*|godzin\w*)\D{0,30}?"
                         r"(\d{1,2}[:h.]\d{2}|\d{1,2}\s?(?:h|am|pm|uhr))", re.I)


def entrance_time(text):
    """The SIMplifica entrance time the visitor gave ("PR1 entrance booked for 10:30"), never an arrival or pick-up time."""
    m = ENTRANCE_RE.search(fold(text))
    return _hhmm(m.group(2)) if m else None


def _plus(hm, minutes):
    d = datetime.datetime(2000, 1, 1, hm[0], hm[1]) + datetime.timedelta(minutes=minutes)
    return d.strftime("%H:%M")


def pr1_trip(lang, text="", ship=None):
    parts = [status_line("PR1", lang), T["ticket_pr1"][lang], T["pr1_walk"][lang]]
    slot = entrance_time(text)
    if slot and 5 <= slot[0] <= 16:
        parts.append(T["window"][lang].format(slot=f"{slot[0]:02d}:{slot[1]:02d}", a=_plus(slot, 225), b=_plus(slot, 240)))
    if ship:
        parts.append(T["ship_nobus"][lang])
        parts.append(T["taxis"][lang].format(t=_taxis(pickup="Funchal")))
    else:
        tt = _bus("PR1", "there")
        if tt:
            parts.append(T["there_bus"][lang].format(tt=tt))
    parts.append(T["back_pr1"][lang].format(t=_taxis(pickup="Achada do Teixeira", destination="Funchal", n=2)))
    if ship:
        parts.append(T["ship_short"][lang])
    u = _page("PR1", lang)
    if u:
        parts.append(T["page"][lang].format(u=u))
    return "\n\n".join(p for p in parts if p)


def trail_trip(code, lang):
    t = _trail(code)
    if not t:
        return None
    parts = [status_line(code, lang), T["ticket"][lang] if t.get("fee") else T["no_fee"][lang]]
    there, back = _bus(code, "there"), _bus(code, "back")
    if there:
        parts.append(T["there_bus"][lang].format(tt=there))
    if back:
        parts.append(T["back_bus"][lang].format(tt=back))
    taxis = _taxis(trail=code)
    if taxis:
        parts.append(T["taxis"][lang].format(t=taxis))
    u = _page(code, lang)
    if u:
        parts.append(T["page"][lang].format(u=u))
    return "\n\n".join(p for p in parts if p)


def find_ship(text, today=None):
    """Match a ship in Funchal today or tomorrow from the APRAM schedule: by name in the text, or the only MSC/AIDA…
    call if the brand alone is given. Returns {"ship", "arrival", "departure"} or None."""
    try:
        calls = json.load(open(CRUISE_CALLS, encoding="utf-8"))["calls"]
    except Exception:
        return None
    today = today or datetime.datetime.now(TZ).date()
    days = {today.isoformat(), (today + datetime.timedelta(days=1)).isoformat()}
    if re.search(r"amanh|tomorrow|demain|morgen|jutro", fold(text)):
        days = {(today + datetime.timedelta(days=1)).isoformat()}
    near = [c for c in calls if c.get("port") == "Funchal" and c.get("arrival", "")[:10] in days]
    f = fold(text)
    named = [c for c in near if fold(c["ship"]) in f]
    if not named:
        brand = re.search(r"\b(msc|aida|tui|costa|norwegian|celebrity|princess|marella|p&o|royal caribbean|mein schiff)\b", f)
        if brand:
            named = [c for c in near if fold(c["ship"]).startswith(brand.group(1))]
    if len(named) == 1:
        c = named[0]
        name = " ".join(w if len(w) <= 3 else w.title() for w in c["ship"].split())   # MSC Virtuosa, AIDAnova stays readable
        return {"ship": name, "arrival": c["arrival"], "departure": c["departure"]}
    return None


def cruise(lang, text, trails):
    parts = []
    s = find_ship(text)
    if s:
        a, d = s["arrival"][11:16], s["departure"][11:16]
        parts.append(T["ship_found"][lang].format(ship=s["ship"], a=a, d=d))
    else:
        parts.append(T["ship_ask"][lang])
    if "PR1" in trails or "PR1.2" in trails or re.search(r"areeiro|arieiro|ruivo|pr ?1\b", fold(text)):
        parts.append(pr1_trip(lang, text, ship=True))
    elif trails:
        tt = trail_trip(trails[0], lang)
        if tt:
            parts.append(tt)
    else:
        parts.append(T["ship_generic"][lang])
    return "\n\n".join(parts)


PLACES = {"achada do teixeira": "Achada do Teixeira", "rabacal": "Rabaçal", "queimadas": "Queimadas",
          "ribeiro frio": "Ribeiro Frio", "encumeada": "Encumeada", "portela": "Portela", "fanal": "Fanal",
          "pico do areeiro": "Pico do Areeiro", "pico do arieiro": "Pico do Areeiro", "baia d'abra": "Baía d'Abra",
          "baia dabra": "Baía d'Abra", "curral das freiras": "Curral das Freiras", "boca da corrida": "Boca da Corrida"}
PLACES_RE = re.compile(r"\b(?:from|de|do|da|desde|depuis|von|vom|ab|z|ze)\s+(" + "|".join(re.escape(k) for k in PLACES) + r")\b")


def quick(text, lang, trails, context=""):
    """The pre-populated answer for this message, or None. context = what the visitor told us before (where they
    stay, the original question)."""
    f, full = fold(text), fold(text + " " + context)
    lang = lang if lang in LP else "en"
    if CRUISE_RE.search(full) and (TRANSPORT_RE.search(full) or trails or re.search(r"areeiro|ruivo|levada|trail|trilha|percurso|wander|randon|szlak", full)):
        return cruise(lang, text + " " + context, trails)
    pr1 = "PR1" in trails or re.search(r"areeiro|arieiro|pico ruivo|pr ?1\b", full)
    if TRANSPORT_RE.search(full) and pr1:
        return pr1_trip(lang, text + " " + context)
    if TRANSPORT_RE.search(full) and len(trails) == 1:
        return trail_trip(trails[0], lang)
    base = re.search(r"\(staying in: ([^)]+)\)", context, re.I) or re.search(r"^staying in: (.+)$", context, re.I)
    pick = PLACES_RE.search(f)
    if TRANSPORT_RE.search(full) and pick:
        place, dest = PLACES[pick.group(1)], base.group(1).strip() if base else "Funchal"
        taxis = _taxis(pickup=place, destination=dest)
        if taxis:
            return T["from_place"][lang].format(p=place, b=dest, t=taxis)
    if TRANSPORT_RE.search(full) and not trails and base:
        place = base.group(1).strip()
        if re.search(r"airport|aeroporto|aeroport|flughafen|lotnisk", full):
            taxis = _taxis(pickup="Madeira Airport", destination=place)
            if taxis:
                return T["airport_taxi"][lang].format(b=place, t=taxis)
        taxis = _taxis(pickup=place)
        if taxis:
            return T["generic_taxi"][lang].format(b=place, t=taxis)
    if STATUS_RE.search(f) and trails and len(f) < 120:
        return "\n\n".join([status_line(c, lang) for c in trails[:3]] + [T["page"][lang].format(u=_page(trails[0], lang))])
    return None
