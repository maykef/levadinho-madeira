"""Hand-curated records for the knowledge store: sources, exact fees, and the few facts that live in no
machine-readable file yet. Every value here is copied from bot/pr1_facts.md / bot/transport_facts.md (which cite
the official sources); change both together. load.py reads this module."""

SOURCES = [
    # id, name, publisher, url, licence, kind
    ("ifcn_warnings", "IFCN trail warnings list (Percursos Pedestres – Avisos)", "IFCN",
     "https://ifcn.madeira.gov.pt/pt/?view=article&id=627:percursos-pedestres-avisos&catid=146:avisos", None, "official"),
    ("ifcn_panels", "IFCN trailhead information panels", "IFCN",
     "https://ifcn.madeira.gov.pt/en/atividades-de-natureza/percursos-pedestres-recomendados/percursos-pedestres-recomendados.html", None, "official"),
    ("ifcn_fees_faq", "IFCN fees FAQ (classified walking routes)", "IFCN",
     "https://ifcn.madeira.gov.pt/en/atividades-de-natureza/percursos-pedestres-recomendados/faq-s-taxas-percursos-pedestres-classificados/frequently-asked-questions-fees-classified-walking-routes.html",
     None, "official"),
    ("portaria_48_2026", "Portaria 48/2026 (republishes Portaria 801/2025)", "Região Autónoma da Madeira",
     "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Portarias/Port48ISerie027_2026.pdf", None, "official"),
    ("dlr_24_2022", "Decreto Legislativo Regional 24/2022/M", "Região Autónoma da Madeira",
     "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Decretos/DLR_14_2022_M_Percursos_Pedestres.pdf", None, "official"),
    ("simplifica", "SIMplifica (trail booking)", "Governo Regional da Madeira",
     "https://simplifica.madeira.gov.pt/services/78-82-259", None, "official"),
    ("visitmadeira", "Visit Madeira hiking pages", "Associação de Promoção da Madeira",
     "https://visitmadeira.com/en/what-to-do/nature-seekers/activities/hiking/", None, "official"),
    ("visitmadeira_taxis", "Visit Madeira: taxis", "Associação de Promoção da Madeira",
     "https://www.visitmadeira.com/pt/meios-de-transporte/taxis/", None, "official"),
    ("ipma", "IPMA weather stations (open data)", "IPMA", "https://api.ipma.pt/", None, "official"),
    ("horarios_funchal_areeiro", "Horários do Funchal: Pico do Areeiro service", "Horários do Funchal",
     "https://www.horariosdofunchal.pt/index.php/viajar/pico-do-areeiro", None, "official"),
    ("siga", "SIGA: operators' bus timetables", "Região Autónoma da Madeira", "https://siga.madeira.gov.pt/horarios", None, "official"),
    ("open_meteo", "Open-Meteo multi-model forecast", "Open-Meteo", "https://open-meteo.com/", "CC BY 4.0", "official"),
    ("levadinho_research", "Levadinho verified research (from the official sources listed with each fact)", "Levadinho",
     "https://levadinho-madeira.com/about/", None, "curated"),
    ("levadinho_site", "levadinho-madeira.com", "Levadinho", "https://levadinho-madeira.com/", None, "site"),
    # Funchal and the island (2026-10-10: every fact the bot uses lives here)
    ("funchal_places", "Opening hours of Funchal's places (each place's own website, listed with it)", "Levadinho",
     "https://levadinho-madeira.com/funchal/", None, "curated"),
    ("frentemar", "Frente MarFunchal (lidos and sea pools)", "Frente MarFunchal", "https://frentemarfunchal.pt/", None, "official"),
    ("horarios_funchal", "Horários do Funchal (city buses, GTFS)", "Horários do Funchal", "https://www.horariosdofunchal.pt/", None, "official"),
    ("apram", "APRAM: ship movements in Funchal port", "APRAM – Portos da Madeira", "https://www.apram.pt/", None, "official"),
    ("funchal_events", "Funchal events (cultura.funchal.pt, eventsmadeira.com)", "Câmara Municipal do Funchal / Events Madeira",
     "https://cultura.funchal.pt/", None, "official"),
    ("netmadeira", "NetMadeira webcams", "NetMadeira", "https://www.netmadeira.com/webcams", None, "official"),
]

L = lambda en, pt, fr, de, pl: {"en": en, "pt": pt, "fr": fr, "de": de, "pl": pl}

FEES = [
    # item, amount, label, applies_to, conditions, source
    ("pr_standard", 4.50, L("Standard PR trail, on your own", "Percurso PR normal, por conta própria", "Sentier PR standard, en individuel",
                            "Normaler PR-Weg, auf eigene Faust", "Standardowy szlak PR, samodzielnie"),
     "every IFCN-fee PR trail except PR1", None, "portaria_48_2026"),
    ("pr_operator", 3.00, L("Standard PR trail, booked by a protocol operator", "Percurso PR normal, reservado por operador com protocolo",
                            "Sentier PR standard, réservé par un opérateur conventionné", "Normaler PR-Weg, über einen Vertragsanbieter gebucht",
                            "Standardowy szlak PR, rezerwacja przez operatora z umową"),
     "every IFCN-fee PR trail except PR1", {"note": "Only the operator can book at this rate."}, "portaria_48_2026"),
    ("pr1_full", 10.50, L("PR1 full route (Areeiro → Pico Ruivo), on your own", "PR1 completo (Areeiro → Pico Ruivo), por conta própria",
                          "PR1 complet (Areeiro → Pico Ruivo), en individuel", "PR1 komplett (Areeiro → Pico Ruivo), auf eigene Faust",
                          "PR1 cały (Areeiro → Pico Ruivo), samodzielnie"),
     "PR1", {"includes": "PR1.1, PR1.2 and PR1.3 at no extra fee"}, "portaria_48_2026"),
    ("pr1_section", 4.50, L("PR1 Areeiro–Pedra Rija only, on your own", "PR1 só Areeiro–Pedra Rija, por conta própria",
                            "PR1 Areeiro–Pedra Rija seulement, en individuel", "PR1 nur Areeiro–Pedra Rija, auf eigene Faust",
                            "PR1 tylko Areeiro–Pedra Rija, samodzielnie"),
     "PR1", None, "portaria_48_2026"),
    ("pr1_operator", 7.00, L("PR1 full route, booked by a protocol operator", "PR1 completo, reservado por operador com protocolo",
                             "PR1 complet, réservé par un opérateur conventionné", "PR1 komplett, über einen Vertragsanbieter gebucht",
                             "PR1 cały, rezerwacja przez operatora z umową"),
     "PR1", {"note": "Only the operator can book at this rate."}, "portaria_48_2026"),
    ("pr1_section_operator", 3.00, L("PR1 Areeiro–Pedra Rija only, booked by a protocol operator",
                                     "PR1 só Areeiro–Pedra Rija, reservado por operador com protocolo",
                                     "PR1 Areeiro–Pedra Rija seulement, réservé par un opérateur conventionné",
                                     "PR1 nur Areeiro–Pedra Rija, über einen Vertragsanbieter gebucht",
                                     "PR1 tylko Areeiro–Pedra Rija, rezerwacja przez operatora z umową"),
     "PR1", {"note": "Only the operator can book at this rate."}, "portaria_48_2026"),
    ("multi_1day", 9.00, L("Two or more trails in one day", "Dois ou mais percursos no mesmo dia", "Deux sentiers ou plus le même jour",
                           "Zwei oder mehr Wege an einem Tag", "Dwa lub więcej szlaków jednego dnia"),
     "every IFCN-fee PR trail except PR1",
     {"note": "Not a pass: every trail still needs its own booking; SIMplifica applies the cheapest combination when they are in one booking. PR1 (even the Pedra Rija ticket) is never included."},
     "portaria_48_2026"),
    ("multi_3day", 22.50, L("Trails over 3 days", "Percursos em 3 dias", "Sentiers sur 3 jours", "Wege an 3 Tagen", "Szlaki przez 3 dni"),
     "every IFCN-fee PR trail except PR1", {"note": "Same rules as the one-day rate; PR1 never included."}, "portaria_48_2026"),
    ("multi_7day", 52.50, L("Trails over 7 days", "Percursos em 7 dias", "Sentiers sur 7 jours", "Wege an 7 Tagen", "Szlaki przez 7 dni"),
     "every IFCN-fee PR trail except PR1", {"note": "Same rules as the one-day rate; PR1 never included."}, "portaria_48_2026"),
    ("exempt", 0.00, L("Free, but must still be on the booking", "Grátis, mas tem de constar da reserva", "Gratuit, mais doit figurer sur la réservation",
                       "Kostenlos, muss aber in der Buchung stehen", "Bezpłatnie, ale trzeba być w rezerwacji"),
     "every IFCN-fee PR trail",
     {"who": ["children 12 and under", "Madeira residents", "people with a certified disability of 60% or more, plus one accompanying guardian"]},
     "portaria_48_2026"),
    ("fine_no_ticket", 250.00, L("Fine for walking an IFCN trail without a valid ticket (individuals)",
                                 "Coima por percorrer um percurso do IFCN sem bilhete válido (pessoas singulares)",
                                 "Amende pour un sentier IFCN sans billet valable (particuliers)",
                                 "Bußgeld für einen IFCN-Weg ohne gültiges Ticket (Privatpersonen)",
                                 "Grzywna za przejście szlaku IFCN bez ważnego biletu (osoby fizyczne)"),
     "every IFCN classified trail",
     {"max_eur": 2500.00, "note": "An administrative offence (Portaria 801/2025 art. 10; DLR 24/2022/M art. 13). Entering a closed trail carries the same range. Never say 'up to €250'."},
     "dlr_24_2022"),
    ("bus_areeiro", 3.00, L("Public bus Funchal ↔ Pico do Areeiro, per trip", "Autocarro Funchal ↔ Pico do Areeiro, por viagem",
                            "Bus Funchal ↔ Pico do Areeiro, par trajet", "Bus Funchal ↔ Pico do Areeiro, pro Fahrt",
                            "Autobus Funchal ↔ Pico do Areeiro, za przejazd"),
     "Horários do Funchal Pico do Areeiro service", {"note": "Paid on board. 31 seats. Seat reservation by phone only, 291 705 555, 7 to 2 working days before."},
     "horarios_funchal_areeiro"),
]

# The PR1 bus (Horários do Funchal, "Pico do Areeiro" service): daily except 25 December. The 19:00 down is 18:00
# in the winter timetable (25 Oct 2026 – 27 Mar 2027).
AREEIRO_BUS = [
    # dep, arr, from, to, leg, valid_from, valid_to
    ("06:00", "06:45", "Funchal (Teleférico-Término 4A)", "Pico do Areeiro (Radar roundabout)", "there", None, None),
    ("13:30", "14:15", "Funchal (Teleférico-Término 4A)", "Pico do Areeiro (Radar roundabout)", "there", None, None),
    ("12:15", None, "Pico do Areeiro (Radar roundabout)", "Funchal", "back", None, None),
    ("19:00", None, "Pico do Areeiro (Radar roundabout)", "Funchal", "back", None, "2026-10-24"),
    ("18:00", None, "Pico do Areeiro (Radar roundabout)", "Funchal", "back", "2026-10-25", "2027-03-27"),
]

ISLAND_TAXIS = [
    # id, kind, town, name, phones, url, source
    ("aitram", "taxi_island", None, "AITRAM", ["+351 291 765 760"], None, "visitmadeira_taxis"),
    ("taxis_madeira", "taxi_island", "Funchal", "Táxis Madeira", ["+351 291 764 476"], "https://taxismadeira.pt", "visitmadeira_taxis"),
]

# General transport facts (from bot/transport_facts.md), English; the bot answers in the visitor's language.
TRANSPORT_FACTS = [
    ("taxi_fares", "taxi", None,
     "Taxis charge by the meter at the official regulated tariff (Convention 1/2019 between the Region's transport authority "
     "IMT-RAM and the taxi associations, amended September 2025, in force from 1 January 2026; nights, weekends and holidays "
     "cost more). There is no fixed price per route and the exact 2026 figures are not confirmed: ask for a quote when "
     "booking and for a receipt. Taxis are paid in cash, so carry enough.", "levadinho_research"),
    ("taxi_no_wait", "taxi", None,
     "At Achada do Teixeira (PR1's finish) taxis usually wait in the daytime, and a shared ride back to Pico do Areeiro "
     "costs about €15–20 per person; if none is there, wait a little. At other trailheads, and for an early, late or "
     "off-season finish, book a set pick-up time before you start. The taxi numbers are as printed on IFCN's "
     "trailhead panels, which are undated.", "ifcn_panels"),
    ("taxi_choice", "taxi", None,
     "Give the rank nearest the pick-up place and, when different, the rank of the town the visitor is going to; they are "
     "alternatives for the same trip. Call both, ask each for a quote, book the better one. EXCEPTION: pick-ups at "
     "Achada do Teixeira are done by the local Santana taxis only (taxi territories are respected; the Funchal rank's "
     "own site says so) — for a pick-up there give Táxis Santana alone, whatever the destination.", "levadinho_research"),
    ("taxi_airport", "taxi", None,
     "Madeira Airport is in Santa Cruz. No airport rank is in our data: use the rank of the town the visitor is going to "
     "plus the island-wide contacts (AITRAM, Táxis Madeira).", "levadinho_research"),
    ("transfer_hotel", "transfer", None,
     "The simplest way to book a transfer is through the hotel reception. Levadinho does not name, recommend or book "
     "transfer companies. Without a hotel (private rental), book a taxi for a set time.", "levadinho_research"),
    ("drive_times", "transfer", None,
     "Never invent driving or taxi times. Sourced times (our one-day page, from the taxi loop): Funchal → Eira do "
     "Serrado/Curral das Freiras about 30 min; Curral → Cabo Girão about 35 min; Cabo Girão → Câmara de Lobos about "
     "10 min; the whole viewpoints loop is a 6-hour day (~56 km; drivers quoted about €160 in October 2026 — "
     "indicative, not a tariff). The western trailheads (Rabaçal, Fanal, Paul da Serra) and the north coast are well "
     "over an hour's drive from Funchal each way. No other road times are in our data: say so rather than guess.",
     "levadinho_research"),
    ("cruise_day", "transfer", None,
     "A cruise passenger with one day ashore: recommend the one-day plan — the viewpoints taxi loop (about 6 hours "
     "door to door from the terminal) or Funchal and Monte on foot and by cable car — not a distant levada. Keep a "
     "margin of at least an hour before all-aboard. Our data on ships in port is context only: never assume which "
     "ship the visitor is on or their hours ashore — ask, or answer in general terms.", "levadinho_research"),
    ("bus_scope", "bus", None,
     "Bus times come only from the operators' printed timetables in our data. If there is no bus in our data from the "
     "visitor's town, say so and give the taxi option. No buses on 25 December.", "siga"),
]

# Which walks SIMplifica actually sells (the free-walks page's rule; owner, 2026-10-22, after the bot told a
# visitor to book PR3 on SIMplifica). Served by fees_and_rules() with the fees_booking topic.
FEE_SCOPE_FACTS = [
    ("booking_scope", "fees_booking", None,
     "SIMplifica sells only the classified PR trails managed by IFCN. Trails managed by another body are NOT on "
     "SIMplifica and have no IFCN fee and nothing to book: PR3 and PR3.1 and PR4 (Funchal council) and PR23 (Caniço "
     "parish). Never tell a visitor to book these on SIMplifica. Non-classified levadas (for example Levada dos "
     "Tornos, Levada do Caniçal, Levada Nova) need no ticket at all.", "ifcn_fees_faq"),
    ("norte_pr17", "fees_booking", "PR17",
     "Levada do Norte is a non-classified levada and needs no ticket where it runs on its own — BUT one stretch is "
     "part of PR17 Caminho do Pináculo e Folhadal, an IFCN trail that needs a €4.50 SIMplifica ticket. Say both "
     "halves when asked whether Levada do Norte is free.", "ifcn_fees_faq"),
]
