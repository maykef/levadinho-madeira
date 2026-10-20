#!/usr/bin/env python3
"""Writes /madeira-cruise-port/ × 5 languages from the free-walks page shell (owner, 2026-10-20: "build pages that
answer the google queries to the letter"). Each heading is one of the real autocomplete queries around "madeira
cruise port": things to do, to town centre, to the cable car, map, webcam, plus the levada question.

Facts and sources:
  terminal      Gare Marítima Internacional on the Pontinha pier (OpenStreetMap/Nominatim, 2026-10-20).
  distances     road/seafront distances from OpenStreetMap (OSRM, 2026-10-20): terminal → Praça do Povo ≈ 2.4 km,
                → cable car base ≈ 2.4 km, → Mercado ≈ 2.6 km, → cathedral/Avenida Arriaga ≈ 3 km. Flat; the page
                says 30–40 minutes on foot and notes the berth changes it.
  cable car     €16 / €22 return, 0-6 free, 7-14 half, 08:45-17:45 (madeiracablecar.com, read 2026-10-20).
  webcam        REMOVED (owner, 2026-10-20: "we don't need the webcam of the port").
  map           img/cruise-port/port-map(.{,-full})webp, rendered by scripts/gen_port_map.py (keep MAP_PTS in step).
  taxis         never "taxis wait at the terminal" (unsourced); metered at the official tariff, quotes, the
                one-day guide's taxi question for day loops. No companies.

Re-run after changing the copy: it keeps dateModified, then runs gen_site_nav.py, gen_cta.py, gen_owner.py,
gen_schema.py and gen_chat.py itself (the page is in GUIDES / TAGS and carries the web chat).
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import BASE, LANGS, PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "madeira-cruise-port"
ROOT = gi.ROOT
CABLE = "https://www.madeiracablecar.com/"
MERC = "https://mercados.funchal.pt/"
OSM = "https://www.openstreetmap.org/"
a, ext = gi.a, gi.ext


def src(lang):
    return ('<p class="src">' + ext(OSM, "OpenStreetMap") + " · " + ext(CABLE, "Teleférico do Funchal") + " · "
            + ext(MERC, "Mercado dos Lavradores") + "</p>")


def L(lang, path):
    return f"{PREFIX[lang]}{path}"


MAP_PTS = [  # keep in step with scripts/gen_port_map.py
    {"en": "Cruise terminal (Gare Marítima, Pontinha pier)", "pt": "Terminal de cruzeiros (Gare Marítima, molhe da Pontinha)",
     "fr": "Terminal de croisière (Gare Marítima, jetée de Pontinha)", "de": "Kreuzfahrtterminal (Gare Marítima, Pontinha-Pier)",
     "pl": "Terminal wycieczkowy (Gare Marítima, molo Pontinha)"},
    {"en": "Praça do Povo", "pt": "Praça do Povo", "fr": "Praça do Povo", "de": "Praça do Povo", "pl": "Praça do Povo"},
    {"en": "Town centre: Avenida Arriaga and the cathedral", "pt": "Centro: Avenida Arriaga e a Sé",
     "fr": "Centre-ville : Avenida Arriaga et la cathédrale", "de": "Zentrum: Avenida Arriaga und die Kathedrale",
     "pl": "Centrum: Avenida Arriaga i katedra"},
    {"en": "Mercado dos Lavradores", "pt": "Mercado dos Lavradores", "fr": "Mercado dos Lavradores",
     "de": "Mercado dos Lavradores", "pl": "Mercado dos Lavradores"},
    {"en": "Cable car base station", "pt": "Estação de baixo do teleférico", "fr": "Gare basse du téléphérique",
     "de": "Talstation der Seilbahn", "pl": "Dolna stacja kolejki"},
    {"en": "Old Town (Zona Velha)", "pt": "Zona Velha", "fr": "Vieille ville (Zona Velha)", "de": "Altstadt (Zona Velha)",
     "pl": "Starówka (Zona Velha)"},
]
MAP_H = {"en": "Is there a map of the Madeira cruise port?", "pt": "Há um mapa do porto de cruzeiros da Madeira?",
         "fr": "Y a-t-il une carte du port de croisière de Madère ?", "de": "Gibt es eine Karte des Kreuzfahrthafens von Madeira?",
         "pl": "Czy jest mapa portu wycieczkowego na Maderze?"}
MAP_LEAD = {
    "en": "Yes — this one: the Pontinha pier, where the ships dock, and the flat seafront walk past Praça do Povo into the centre, with the Mercado, the cable car base station and the Old Town marked.",
    "pt": "Sim — este: o molhe da Pontinha, onde os navios atracam, e o passeio plano pela frente-mar, pela Praça do Povo até ao centro, com o Mercado, a estação do teleférico e a Zona Velha marcados.",
    "fr": "Oui — celle-ci : la jetée de Pontinha, où accostent les navires, et la promenade plate du front de mer par la Praça do Povo vers le centre, avec le Mercado, la gare du téléphérique et la vieille ville.",
    "de": "Ja — diese: der Pontinha-Pier, an dem die Schiffe anlegen, und der flache Uferweg über die Praça do Povo ins Zentrum, mit Mercado, Talstation der Seilbahn und Altstadt markiert.",
    "pl": "Tak — ta: molo Pontinha, przy którym cumują statki, i płaski spacer nabrzeżem przez Praça do Povo do centrum, z zaznaczonym Mercado, dolną stacją kolejki i starówką.",
}
MAP_OSM = {"en": "Open this area in OpenStreetMap", "pt": "Abrir esta zona no OpenStreetMap",
           "fr": "Ouvrir cette zone dans OpenStreetMap", "de": "Diesen Bereich in OpenStreetMap öffnen",
           "pl": "Otwórz ten obszar w OpenStreetMap"}


def map_html(lang):
    alt = html.escape(MAP_H[lang] + " " + "; ".join(f"{i + 1} {n[lang]}" for i, n in enumerate(MAP_PTS)), quote=True)
    legend = " · ".join(f"<b>{i + 1}</b> {n[lang]}" for i, n in enumerate(MAP_PTS))
    osm = "https://www.openstreetmap.org/#map=15/32.6460/-16.9060"
    return ('<figure style="margin:16px 0"><a href="/img/cruise-port/port-map-full.webp" target="_blank" rel="noopener">'
            '<img src="/img/cruise-port/port-map.webp" alt="' + alt + '" loading="lazy" width="660" height="535" '
            'style="display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:8px"></a>'
            '<figcaption style="font-size:13px;color:var(--muted);margin-top:6px">' + legend
            + ". " + ext(osm, MAP_OSM[lang]) + ". Map © OpenStreetMap contributors.</figcaption></figure>")



# Sections: (heading, parts, is_question). A question's FAQ answer is its first paragraph, verbatim.
COPY = {
 "en": dict(
  title="Madeira cruise port: to town, cable car and map",
  desc="Docked in Funchal? From the Madeira cruise port to the town centre and cable car on foot, the port map, and what fits in a day. Plan it all here.",
  h1="Madeira cruise port: into town, the cable car, the map",
  sub="Where the ships dock, the flat walk into Funchal, real distances from OpenStreetMap, and what actually fits in your hours ashore.",
  body=[
   ("What is there to do at the Madeira cruise port for a day?", [
     "The port is in Funchal itself, so a day ashore is a Funchal day: the Mercado dos Lavradores (closed Sunday), the Old Town, the cable car up to Monte — or a taxi loop to the island's viewpoints. The honest version of both, with times and 2026 prices, is in " + a(L("en", "/one-day-in-madeira/"), "one day in Madeira") + "; with a second day aboard, " + a(L("en", "/two-days-in-madeira/"), "two days in Madeira") + " covers the lot."], True),
   ("How do I get from the Madeira cruise port to the town centre?", [
     "On foot, along the sea. Ships dock on the Pontinha pier; from the cruise terminal it is a flat walk along the pier and the seafront promenade — about 2.4 km to Praça do Povo and about 3 km to the centre around the cathedral and Avenida Arriaga. Allow 30–40 minutes, a little more or less depending on your berth. Taxis are metered at the official tariff; ask for a quote before you ride.",
     "Road distances from OpenStreetMap. The Mercado dos Lavradores is about 2.6 km from the terminal, just past the cable car station."], True),
   ("How do I get from the cruise port to the cable car?", [
     "The cable car's base station is on the seafront by the Old Town, about 2.4 km from the cruise terminal — the same flat walk, 30–35 minutes, or a short taxi ride. It runs daily 08:45–17:45 (closed 25 December); €16 one way, €22 return, ages 0–6 free, 7–14 half price. Up at Monte you have the church, the Monte Palace garden and the toboggans — the full plan is in " + a(L("en", "/one-day-in-madeira/"), "one day in Madeira") + "."], True),
   (None, [  # map section: heading from MAP_H
     None], True),
   ("Can I do a levada walk from the cruise port?", [
     "The walk that fits a port call is not a levada but the mountain taste: the out-and-back from Pico do Areeiro to the Pedra Rija viewpoint on " + a(L("en", "/pr1/"), "PR1") + " — 1.2 km each way, €4.50, booked online on SIMplifica (" + a(L("en", "/simplifica-booking/"), "how to book") + "), reached by taxi with an agreed return. A real levada is a half-day or more before the ride there and back; if that is why you came, check " + a(L("en", "/best-levada-walks/"), "the best levada walks") + " and today's status first: " + a(L("en", "/"), "all Madeira trails — open or closed today") + "."], True),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="Porto de cruzeiros da Madeira: cidade, teleférico, mapa",
  desc="Atracado no Funchal? Do porto de cruzeiros da Madeira ao centro e ao teleférico a pé, o mapa do porto e o que cabe num dia. Planeie aqui.",
  h1="Porto de cruzeiros da Madeira: até à cidade, o teleférico, o mapa",
  sub="Onde atracam os navios, a caminhada plana até ao Funchal, distâncias reais do OpenStreetMap, e o que cabe mesmo nas suas horas em terra.",
  body=[
   ("O que fazer no porto de cruzeiros da Madeira num dia?", [
     "O porto é no próprio Funchal, por isso um dia em terra é um dia de Funchal: o Mercado dos Lavradores (fechado ao domingo), a Zona Velha, o teleférico até ao Monte — ou uma volta de táxi pelos miradouros da ilha. A versão honesta de ambos, com horários e preços de 2026, está em " + a(L("pt", "/one-day-in-madeira/"), "um dia na Madeira") + "; com um segundo dia a bordo, " + a(L("pt", "/two-days-in-madeira/"), "dois dias na Madeira") + " cobre tudo."], True),
   ("Como ir do porto de cruzeiros da Madeira ao centro da cidade?", [
     "A pé, ao longo do mar. Os navios atracam no molhe da Pontinha; do terminal de cruzeiros é uma caminhada plana pelo molhe e pela frente-mar — cerca de 2,4 km até à Praça do Povo e cerca de 3 km até ao centro, junto à Sé e à Avenida Arriaga. Conte 30–40 minutos, um pouco mais ou menos conforme o cais. Os táxis são ao taxímetro, à tarifa oficial; peça uma cotação antes de seguir.",
     "Distâncias por estrada do OpenStreetMap. O Mercado dos Lavradores fica a cerca de 2,6 km do terminal, logo a seguir à estação do teleférico."], True),
   ("Como ir do porto de cruzeiros ao teleférico?", [
     "A estação de baixo do teleférico fica na frente-mar, junto à Zona Velha, a cerca de 2,4 km do terminal — a mesma caminhada plana, 30–35 minutos, ou um táxi curto. Funciona todos os dias das 08:45 às 17:45 (fecha a 25 de dezembro); 16 € ida, 22 € ida e volta, dos 0 aos 6 anos grátis, dos 7 aos 14 metade. Lá em cima, no Monte, tem a igreja, o jardim Monte Palace e os carros de cesto — o plano completo está em " + a(L("pt", "/one-day-in-madeira/"), "um dia na Madeira") + "."], True),
   (None, [None], True),
   ("Posso fazer uma levada a partir do porto de cruzeiros?", [
     "A caminhada que cabe numa escala não é uma levada, é a prova de montanha: a ida e volta do Pico do Areeiro ao miradouro da Pedra Rija no " + a(L("pt", "/pr1/"), "PR1") + " — 1,2 km para cada lado, 4,50 €, com reserva online no SIMplifica (" + a(L("pt", "/simplifica-booking/"), "como reservar") + "), de táxi com regresso combinado. Uma levada a sério é meio dia ou mais, antes de contar a viagem; se foi por isso que veio, veja " + a(L("pt", "/best-levada-walks/"), "as melhores levadas") + " e o estado de hoje primeiro: " + a(L("pt", "/"), "todos os percursos da Madeira — abertos ou fechados hoje") + "."], True),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Port de croisière de Madère : ville, téléphérique, carte",
  desc="À quai à Funchal ? Du port de croisière de Madère au centre-ville et au téléphérique à pied, la carte du port, et ce qui tient en un jour.",
  h1="Port de croisière de Madère : vers la ville, le téléphérique, la carte",
  sub="Où accostent les navires, la marche plate vers Funchal, les vraies distances d'OpenStreetMap, et ce qui tient vraiment dans vos heures à terre.",
  body=[
   ("Que faire au port de croisière de Madère en une journée ?", [
     "Le port est dans Funchal même : une journée à terre est une journée à Funchal — le Mercado dos Lavradores (fermé le dimanche), la vieille ville, le téléphérique vers Monte — ou une boucle en taxi vers les belvédères de l'île. La version honnête des deux, avec horaires et prix 2026, est dans " + a(L("fr", "/one-day-in-madeira/"), "Madère en un jour") + " ; avec un second jour à bord, " + a(L("fr", "/two-days-in-madeira/"), "Madère en deux jours") + " couvre le tout."], True),
   ("Comment aller du port de croisière de Madère au centre-ville ?", [
     "À pied, le long de la mer. Les navires accostent à la jetée de Pontinha ; depuis le terminal, c'est une marche plate le long de la jetée puis du front de mer — environ 2,4 km jusqu'à la Praça do Povo et environ 3 km jusqu'au centre, vers la cathédrale et l'Avenida Arriaga. Comptez 30 à 40 minutes, un peu plus ou moins selon le quai. Les taxis sont au compteur, au tarif officiel ; demandez un devis avant de monter.",
     "Distances routières d'OpenStreetMap. Le Mercado dos Lavradores est à environ 2,6 km du terminal, juste après la gare du téléphérique."], True),
   ("Comment aller du port de croisière au téléphérique ?", [
     "La gare basse du téléphérique est sur le front de mer, près de la vieille ville, à environ 2,4 km du terminal — la même marche plate, 30 à 35 minutes, ou un court trajet en taxi. Il fonctionne tous les jours de 08h45 à 17h45 (fermé le 25 décembre) ; 16 € l'aller, 22 € l'aller-retour, 0–6 ans gratuit, 7–14 ans demi-tarif. En haut, à Monte : l'église, le jardin Monte Palace et les luges — le plan complet est dans " + a(L("fr", "/one-day-in-madeira/"), "Madère en un jour") + "."], True),
   (None, [None], True),
   ("Peut-on faire une levada depuis le port de croisière ?", [
     "La marche qui tient dans une escale n'est pas une levada mais l'avant-goût de montagne : l'aller-retour du Pico do Areeiro au belvédère de Pedra Rija sur le " + a(L("fr", "/pr1/"), "PR1") + " — 1,2 km par sens, 4,50 €, réservation en ligne sur SIMplifica (" + a(L("fr", "/simplifica-booking/"), "comment réserver") + "), en taxi avec retour convenu. Une vraie levada prend une demi-journée ou plus, trajet non compris ; si c'est pour cela que vous venez, voyez " + a(L("fr", "/best-levada-walks/"), "les meilleures levadas") + " et l'état du jour d'abord : " + a(L("fr", "/"), "tous les sentiers de Madère — ouverts ou fermés aujourd'hui") + "."], True),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Kreuzfahrthafen Madeira: Stadt, Seilbahn und Karte",
  desc="In Funchal angelegt? Vom Kreuzfahrthafen Madeiras zu Fuß ins Zentrum und zur Seilbahn, die Hafenkarte, und was in einen Tag passt. Hier planen.",
  h1="Kreuzfahrthafen Madeira: in die Stadt, zur Seilbahn, die Karte",
  sub="Wo die Schiffe anlegen, der flache Weg nach Funchal, echte Entfernungen aus OpenStreetMap, und was in Ihre Stunden an Land wirklich passt.",
  body=[
   ("Was kann man am Kreuzfahrthafen Madeiras an einem Tag machen?", [
     "Der Hafen liegt in Funchal selbst, ein Tag an Land ist also ein Funchal-Tag: der Mercado dos Lavradores (sonntags geschlossen), die Altstadt, die Seilbahn nach Monte — oder eine Taxirunde zu den Aussichtspunkten der Insel. Die ehrliche Fassung von beidem, mit Uhrzeiten und Preisen 2026, steht in " + a(L("de", "/one-day-in-madeira/"), "Ein Tag auf Madeira") + "; mit einem zweiten Tag an Bord deckt " + a(L("de", "/two-days-in-madeira/"), "Zwei Tage auf Madeira") + " alles ab."], True),
   ("Wie komme ich vom Kreuzfahrthafen Madeiras ins Stadtzentrum?", [
     "Zu Fuß, am Meer entlang. Die Schiffe legen am Pontinha-Pier an; vom Kreuzfahrtterminal ist es ein flacher Weg über den Pier und die Uferpromenade — etwa 2,4 km bis zur Praça do Povo und etwa 3 km bis ins Zentrum an der Kathedrale und der Avenida Arriaga. Rechnen Sie 30–40 Minuten, je nach Liegeplatz etwas mehr oder weniger. Taxis fahren mit Taxameter zum offiziellen Tarif; fragen Sie vor der Fahrt nach einem Preis.",
     "Straßenentfernungen aus OpenStreetMap. Der Mercado dos Lavradores liegt etwa 2,6 km vom Terminal, kurz hinter der Talstation der Seilbahn."], True),
   ("Wie komme ich vom Kreuzfahrthafen zur Seilbahn?", [
     "Die Talstation der Seilbahn liegt an der Uferpromenade bei der Altstadt, etwa 2,4 km vom Terminal — derselbe flache Weg, 30–35 Minuten, oder eine kurze Taxifahrt. Sie fährt täglich 08:45–17:45 (am 25. Dezember geschlossen); 16 € einfach, 22 € hin und zurück, 0–6 Jahre frei, 7–14 halber Preis. Oben in Monte warten die Kirche, der Garten Monte Palace und die Korbschlitten — der ganze Plan steht in " + a(L("de", "/one-day-in-madeira/"), "Ein Tag auf Madeira") + "."], True),
   (None, [None], True),
   ("Kann ich vom Kreuzfahrthafen aus eine Levada gehen?", [
     "Die Wanderung, die in einen Hafentag passt, ist keine Levada, sondern die Bergprobe: hin und zurück vom Pico do Areeiro zum Aussichtspunkt Pedra Rija auf dem " + a(L("de", "/pr1/"), "PR1") + " — je 1,2 km, 4,50 €, online auf SIMplifica gebucht (" + a(L("de", "/simplifica-booking/"), "wie man bucht") + "), per Taxi mit vereinbarter Rückfahrt. Eine richtige Levada braucht einen halben Tag oder mehr, die Anfahrt nicht gerechnet; wenn Sie dafür kommen, sehen Sie " + a(L("de", "/best-levada-walks/"), "die schönsten Levadas") + " und zuerst den heutigen Status: " + a(L("de", "/"), "alle Wanderwege Madeiras — heute offen oder gesperrt") + "."], True),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Port wycieczkowy na Maderze: miasto, kolejka, mapa",
  desc="Zacumowani w Funchal? Z portu wycieczkowego na Maderze pieszo do centrum i do kolejki, mapa portu i co mieści się w jeden dzień. Zaplanuj tutaj.",
  h1="Port wycieczkowy na Maderze: do miasta, do kolejki, mapa",
  sub="Gdzie cumują statki, płaski spacer do Funchal, prawdziwe odległości z OpenStreetMap, i co naprawdę mieści się w godzinach na lądzie.",
  body=[
   ("Co robić w porcie wycieczkowym na Maderze przez jeden dzień?", [
     "Port leży w samym Funchal, więc dzień na lądzie to dzień w Funchal: Mercado dos Lavradores (w niedzielę zamknięte), starówka, kolejka na Monte — albo pętla taksówką po punktach widokowych wyspy. Uczciwa wersja obu planów, z godzinami i cenami 2026, jest w " + a(L("pl", "/one-day-in-madeira/"), "jednym dniu na Maderze") + "; z drugim dniem na pokładzie " + a(L("pl", "/two-days-in-madeira/"), "dwa dni na Maderze") + " obejmują wszystko."], True),
   ("Jak dojść z portu wycieczkowego na Maderze do centrum miasta?", [
     "Pieszo, wzdłuż morza. Statki cumują przy molo Pontinha; od terminalu to płaski spacer po molo i nadmorskiej promenadzie — około 2,4 km do Praça do Povo i około 3 km do centrum przy katedrze i Avenida Arriaga. Licz 30–40 minut, trochę mniej lub więcej zależnie od nabrzeża. Taksówki jeżdżą na taksometr według oficjalnej taryfy; poproś o wycenę przed kursem.",
     "Odległości drogowe z OpenStreetMap. Mercado dos Lavradores jest około 2,6 km od terminalu, tuż za stacją kolejki."], True),
   ("Jak dojść z portu wycieczkowego do kolejki linowej?", [
     "Dolna stacja kolejki stoi przy nadmorskiej promenadzie obok starówki, około 2,4 km od terminalu — ten sam płaski spacer, 30–35 minut, albo krótka taksówka. Kolejka jeździ codziennie 08:45–17:45 (nieczynna 25 grudnia); 16 € w jedną stronę, 22 € w obie, 0–6 lat za darmo, 7–14 pół ceny. Na górze, na Monte: kościół, ogród Monte Palace i sanie — cały plan jest w " + a(L("pl", "/one-day-in-madeira/"), "jednym dniu na Maderze") + "."], True),
   (None, [None], True),
   ("Czy z portu wycieczkowego da się zrobić levadę?", [
     "Trasa, która mieści się w dniu postoju, to nie levada, lecz górska próbka: tam i z powrotem z Pico do Areeiro do punktu widokowego Pedra Rija na " + a(L("pl", "/pr1/"), "PR1") + " — po 1,2 km, 4,50 €, rezerwacja online w SIMplifica (" + a(L("pl", "/simplifica-booking/"), "jak zarezerwować") + "), taksówką z umówionym powrotem. Prawdziwa levada to pół dnia lub więcej, nie licząc dojazdu; jeśli po to przypłynąłeś, zobacz " + a(L("pl", "/best-levada-walks/"), "najlepsze lewady") + " i najpierw dzisiejszy status: " + a(L("pl", "/"), "wszystkie szlaki Madery — otwarte czy zamknięte dziś") + "."], True),
   ("Źródła", [None], False),
  ]),
}


def plain(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())


def main():
    for lang in LANGS:
        c = dict(COPY[lang])
        body = []
        faq_src = []
        for h, parts, isq in COPY[lang]["body"]:
            if h is None:                                   # the map section
                h, parts = MAP_H[lang], [MAP_LEAD[lang], map_html(lang)]
            parts = [src(lang) if p is None else p for p in parts]
            body.append((h, parts))
            faq_src.append((h, parts, isq))
        c["body"] = body
        out, lt, ld = gi.build(SLUG, lang, c, "WebPage")
        h = open(out, encoding="utf-8").read()
        faq = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(parts[0])}}
            for q, parts, isq in faq_src if isq]}
        block = '<script type="application/ld+json">\n' + json.dumps(faq, ensure_ascii=False, indent=1) + "\n</script>\n"
        h = re.sub(r'<script type="application/ld\+json">\n\{\n "@context": "https://schema.org",\n "@type": "FAQPage".*?</script>\n', "", h, flags=re.S)
        i = h.index("</head>")
        h = h[:i] + block + h[i:]
        h = h.replace('"dateModified": "2026-10-07T12:00+01:00"', '"dateModified": "2026-10-20T12:00+01:00"')
        open(out, "w", encoding="utf-8").write(h)
        flag = "" if lt <= 60 and 120 <= ld <= 155 else "  <-- title/description length"
        print(f"{os.path.relpath(out, ROOT)}: title {lt}, description {ld}{flag}")
    import subprocess
    for script in ("gen_site_nav.py", "gen_cta.py", "gen_owner.py", "gen_schema.py", "gen_chat.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
