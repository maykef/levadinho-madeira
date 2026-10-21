#!/usr/bin/env python3
"""Writes /one-day-in-madeira/ × 5 languages from the free-walks page shell (owner, 2026-10-20).

The cruise-passenger page: the owner's top 5 (first-hand, 17-18 Oct 2026 visit + taxi-driver talks) — Cabo Girão
skywalk, Curral das Freiras, Câmara de Lobos, Monte, Mercado dos Lavradores — and two honest one-day plans, because
all five do not fit in one day. Facts and sources in seo_research/facts/oneday.md:
  Cabo Girão    €5 over-12s from 1 Jan 2026, children ≤12 and Madeira residents free (Portaria 591/2025, JORAM I-189,
                read in the PDF 2026-10-20); daily 08:00-20:00, 580 m, glass skywalk (Visit Madeira).
  Monte         cable car €16 / €22 return, 0-6 free, 7-14 half, 08:45-17:45 (madeiracablecar.com); Monte Palace €18,
                ≤14 free, garden 09:00-19:00 Apr-Sep / 09:00-18:00 Oct-Mar (montepalacemadeira.com); Carreiros
                Mon-Sat 09:00-18:00 (carreirosdomonte.com, price not stated: link only).
  Mercado       Mon-Fri 07:00-19:00, Sat 07:00-14:00, closed Sunday (mercados.funchal.pt).
  taxi day      ~€160 for 6 hours, INDICATIVE (owner's taxi-driver talks, Oct 2026): the page says to call a rank and
                get a quote for the specific round trip (Táxis Madeira +351 291 764 476 / AITRAM +351 291 765 760,
                bot/transport_facts.md). No companies ever.
  distances     OSRM/OpenStreetMap 2026-10-20, presented as "about".
  rental cars   owner's advice: don't, parking is limited at most of these places.

Re-run after changing the copy: it keeps dateModified, then runs gen_site_nav.py, gen_cta.py, gen_owner.py,
gen_schema.py and gen_chat.py itself (the page is in GUIDES / TAGS and carries the web chat).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "one-day-in-madeira"
ROOT = gi.ROOT
P591 = "https://joram.madeira.gov.pt/joram/1serie/Ano%20de%202025/ISerie-189-2025-10-27.pdf"
VM_CG = "https://visitmadeira.com/en/what-to-do/nature-seekers/viewpoints/cabo-girao-viewpoint/"
CABLE = "https://www.madeiracablecar.com/"
MPAL = "https://montepalacemadeira.com/visita/"
CARR = "https://www.carreirosdomonte.com/v3/en/"
MERC = "https://mercados.funchal.pt/"
OSM = "https://www.openstreetmap.org/"
a, ext = gi.a, gi.ext


def src(lang):
    return ('<p class="src">' + ext(P591, "Portaria 591/2025 (JORAM)") + " · " + ext(VM_CG, "Visit Madeira") + " · "
            + ext(CABLE, "Teleférico do Funchal") + " · " + ext(MPAL, "Monte Palace") + " · "
            + ext(CARR, "Carreiros do Monte") + " · " + ext(MERC, "Mercado dos Lavradores") + " · "
            + ext(OSM, "OpenStreetMap") + "</p>")


def table(head, rows):
    return ('<div class="tbl"><table>\n    <thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead>\n    <tbody>\n"
            + "".join("      <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n" for r in rows) + "    </tbody>\n  </table></div>")


def L(lang, path):
    return f"{PREFIX[lang]}{path}"


# Sections: (heading, parts, is_question). A question's FAQ answer is its first paragraph, verbatim.
COPY = {
 "en": dict(
  title="One day in Madeira: top 5 and a realistic plan",
  desc="In Madeira for one day? The top 5 — Cabo Girão, Curral das Freiras, Câmara de Lobos, Monte, the Mercado — with 2026 prices and two realistic plans.",
  h1="One day in Madeira: the top 5, and what really fits",
  sub="A cruise call or a short stop: the five places taxi drivers and locals name first, real distances, 2026 prices — and why you must pick a plan, not do it all.",
  body=[
   ("What are the top 5 things to do in Madeira in one day?", [
     "The five places taxi drivers and locals name first: the Cabo Girão skywalk, the Curral das Freiras valley, the old town of Câmara de Lobos, Monte above Funchal, and the Mercado dos Lavradores market. They do not all fit in one day — Cabo Girão and Curral das Freiras lie in different directions and Monte takes half a day — so pick one of the two plans below.",
     "<ul>"
     "<li><b>Cabo Girão skywalk</b> — the glass platform on a 580 m sea cliff, which Visit Madeira calls the highest promontory in Europe. It is a viewpoint, nothing more: 20–30 minutes is enough. €5 for over-12s (2026 rate; children up to 12 and Madeira residents free), open daily 08:00–20:00.</li>"
     "<li><b>Curral das Freiras</b> — the valley in the island's heart. The Eira do Serrado viewpoint above it is the impressive part; the town itself comes 2.6 km further down.</li>"
     "<li><b>Câmara de Lobos</b> — a stroll through the old fishing town and along the pier. The natural lunch stop of the day.</li>"
     "<li><b>Monte</b> — the cable car up from Funchal's Old Town (€16 one way, €22 return), the church, and the Monte Palace garden (€18, up to 14 free).</li>"
     "<li><b>Mercado dos Lavradores</b> — Funchal's market hall: Monday–Friday 07:00–19:00, Saturday to 14:00, closed on Sunday.</li>"
     "</ul>"], True),
   ("How do I see Curral das Freiras, Cabo Girão and Câmara de Lobos in one day?", [
     "By taxi, in one loop of about 56 km (Plan A): Funchal up to the Eira do Serrado viewpoint and down into Curral das Freiras in the morning, across to the Cabo Girão skywalk (20–30 minutes there), then down to Câmara de Lobos for lunch and a stroll through the old town and the pier, and back to Funchal early in the afternoon. With the stops it is about a 6-hour day.",
     table(["Leg", "Road", "Taxi time"],
           [["Funchal → Eira do Serrado → Curral das Freiras", "about 18 km", "about 30 min"],
            ["Curral das Freiras → Cabo Girão", "about 22 km", "about 35 min"],
            ["Cabo Girão → Câmara de Lobos", "about 6 km", "about 10 min"],
            ["Câmara de Lobos → Funchal", "about 10 km", "about 15 min"]]),
     "Road distances from OpenStreetMap; these are mountain roads, so the times are without traffic. Back in Funchal, the Mercado dos Lavradores is open to 19:00 on weekdays and 14:00 on Saturdays (closed Sunday)."], True),
   ("How much does a taxi for a day in Madeira cost?", [
     "Taxi drivers quoted us about €160 for a 6-hour day out in October 2026 — an indicative figure, not a tariff. Cabo Girão, Curral das Freiras and the Funchal sights lie in different directions, so the price depends on the exact round trip you want: call a rank, describe your loop, and get a quote before you set off. Official contacts: Táxis Madeira +351 291 764 476 (online at taxismadeira.pt) and AITRAM +351 291 765 760."], True),
   ("What can I do in Funchal and Monte in one day?", [
     "Plan B stays on foot and on the cable car. Morning at the Mercado dos Lavradores (closed Sunday) and the Old Town; then the cable car up to Monte (daily 08:45–17:45, €16 one way, €22 return; ages 0–6 free, 7–14 half price), the church, and the Monte Palace garden (€18, up to 14 free; 09:00–19:00 April–September, to 18:00 in winter). Come down by cable car — or start the descent with the Carreiros do Monte wicker toboggans (Monday–Saturday 09:00–18:00) and continue by bus or taxi.",
     "The Botanical Garden honestly needs the second day: with the market, Monte and Monte Palace, the day is full. Plans A and B together are a two-day itinerary, not one — it is worked out, with times, in " + a(L("en", "/two-days-in-madeira/"), "two days in Madeira") + "."], True),
   ("Should I rent a car for one day in Madeira?", [
     "We advise against it for this day. Parking is limited at most of these places — and in central Funchal you would pay for a garage while seeing the town on foot. The taxi loop plus the cable car covers the same ground without the parking hunt. If you are set on driving, go early and have a plan B for parking."], True),
   ("Can I fit a levada or a peak into one day?", [
     "One short mountain walk fits a port day: the out-and-back from Pico do Areeiro to the Pedra Rija viewpoint on " + a(L("en", "/pr1/"), "PR1") + " — 1.2 km each way on the famous stairway ridge, €4.50, booked online on SIMplifica (see " + a(L("en", "/simplifica-booking/"), "how to book") + "). Check the summit first: " + a(L("en", "/pico-do-areeiro-weather/"), "Pico do Areeiro weather and webcams") + "."], True),
   ("From a cruise ship", [
     "Plan A is sized for a port call: about 6 hours door to door from the terminal. Agree the return time with the driver when you book, and keep a margin of at least an hour before all-aboard. What's open in town today — events, lidos, last buses — is on " + a(L("en", "/funchal/"), "Funchal today") + "."], False),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="Um dia na Madeira: top 5 e um plano realista",
  desc="Um dia na Madeira? O top 5 — Cabo Girão, Curral das Freiras, Câmara de Lobos, Monte e Mercado — com preços de 2026 e dois planos realistas. Escolha o seu.",
  h1="Um dia na Madeira: o top 5 e o que cabe mesmo",
  sub="Escala de cruzeiro ou visita curta: os cinco lugares que os taxistas e os madeirenses dizem primeiro, distâncias reais, preços de 2026 — e porque tem de escolher um plano, não fazer tudo.",
  body=[
   ("O que fazer na Madeira num dia: quais são os top 5?", [
     "Os cinco lugares que os taxistas e os madeirenses dizem primeiro: o skywalk do Cabo Girão, o vale do Curral das Freiras, a vila de Câmara de Lobos, o Monte sobre o Funchal e o Mercado dos Lavradores. Não cabem todos num dia — o Cabo Girão e o Curral das Freiras ficam em direções diferentes e o Monte leva meio dia — por isso escolha um dos dois planos abaixo.",
     "<ul>"
     "<li><b>Skywalk do Cabo Girão</b> — a plataforma de vidro numa falésia de 580 m, que o Visit Madeira descreve como o promontório mais alto da Europa. É um miradouro e nada mais: 20–30 minutos chegam. 5 € para maiores de 12 anos (tarifa de 2026; crianças até aos 12 e residentes na Madeira grátis), aberto todos os dias das 08:00 às 20:00.</li>"
     "<li><b>Curral das Freiras</b> — o vale no coração da ilha. O miradouro da Eira do Serrado, por cima, é a parte impressionante; a vila fica 2,6 km mais abaixo.</li>"
     "<li><b>Câmara de Lobos</b> — um passeio pela vila piscatória antiga e pelo cais. A paragem natural para o almoço.</li>"
     "<li><b>Monte</b> — o teleférico a subir da Zona Velha do Funchal (16 € ida, 22 € ida e volta), a igreja e o jardim Monte Palace (18 €, até aos 14 anos grátis).</li>"
     "<li><b>Mercado dos Lavradores</b> — o mercado do Funchal: segunda a sexta das 07:00 às 19:00, sábado até às 14:00, fechado ao domingo.</li>"
     "</ul>"], True),
   ("Como ver o Curral das Freiras, o Cabo Girão e Câmara de Lobos num dia?", [
     "De táxi, numa volta de cerca de 56 km (plano A): do Funchal ao miradouro da Eira do Serrado e ao Curral das Freiras de manhã, depois até ao skywalk do Cabo Girão (20–30 minutos lá), descida a Câmara de Lobos para almoçar e passear pela vila e pelo cais, e regresso ao Funchal no início da tarde. Com as paragens é um dia de cerca de 6 horas.",
     table(["Troço", "Estrada", "Tempo de táxi"],
           [["Funchal → Eira do Serrado → Curral das Freiras", "cerca de 18 km", "cerca de 30 min"],
            ["Curral das Freiras → Cabo Girão", "cerca de 22 km", "cerca de 35 min"],
            ["Cabo Girão → Câmara de Lobos", "cerca de 6 km", "cerca de 10 min"],
            ["Câmara de Lobos → Funchal", "cerca de 10 km", "cerca de 15 min"]]),
     "Distâncias por estrada do OpenStreetMap; são estradas de montanha, por isso os tempos são sem trânsito. De volta ao Funchal, o Mercado dos Lavradores está aberto até às 19:00 nos dias úteis e até às 14:00 ao sábado (fechado ao domingo)."], True),
   ("Quanto custa um táxi para um dia na Madeira?", [
     "Os taxistas indicaram-nos cerca de 160 € por um dia de 6 horas, em outubro de 2026 — um valor indicativo, não uma tarifa. O Cabo Girão, o Curral das Freiras e o Funchal ficam em direções diferentes, por isso o preço depende da volta exata que quer fazer: ligue para uma praça, descreva o percurso e peça uma cotação antes de partir. Contactos oficiais: Táxis Madeira +351 291 764 476 (online em taxismadeira.pt) e AITRAM +351 291 765 760."], True),
   ("O que fazer no Funchal e no Monte num dia?", [
     "O plano B é a pé e de teleférico. De manhã, o Mercado dos Lavradores (fechado ao domingo) e a Zona Velha; depois o teleférico até ao Monte (todos os dias das 08:45 às 17:45, 16 € ida, 22 € ida e volta; dos 0 aos 6 anos grátis, dos 7 aos 14 metade), a igreja e o jardim Monte Palace (18 €, até aos 14 anos grátis; das 09:00 às 19:00 de abril a setembro, até às 18:00 no inverno). Desça de teleférico — ou comece a descida nos carros de cesto dos Carreiros do Monte (segunda a sábado, 09:00–18:00) e continue de autocarro ou táxi.",
     "O Jardim Botânico precisa, honestamente, do segundo dia: com o mercado, o Monte e o Monte Palace, o dia fica cheio. Os planos A e B juntos são um roteiro de dois dias, não de um — está feito, com horários, em " + a(L("pt", "/two-days-in-madeira/"), "dois dias na Madeira") + "."], True),
   ("Vale a pena alugar carro para um dia na Madeira?", [
     "Para este dia, não aconselhamos. O estacionamento é limitado na maior parte destes lugares — e no centro do Funchal pagaria uma garagem para ver a cidade a pé. A volta de táxi mais o teleférico cobrem o mesmo sem a caça ao lugar. Se fizer questão de conduzir, vá cedo e tenha um plano B para estacionar."], True),
   ("Cabe uma levada ou um pico num dia?", [
     "Há uma caminhada curta de montanha que cabe num dia de escala: a ida e volta do Pico do Areeiro ao miradouro da Pedra Rija no " + a(L("pt", "/pr1/"), "PR1") + " — 1,2 km para cada lado na famosa crista das escadas, 4,50 €, com reserva online no SIMplifica (veja " + a(L("pt", "/simplifica-booking/"), "como reservar") + "). Confirme o cume primeiro: " + a(L("pt", "/pico-do-areeiro-weather/"), "tempo e webcams do Pico do Areeiro") + "."], True),
   ("De navio de cruzeiro", [
     "O plano A está à medida de uma escala: cerca de 6 horas porta a porta desde o terminal. Combine a hora de regresso com o motorista ao reservar e guarde uma margem de pelo menos uma hora antes do all-aboard. O que está aberto hoje na cidade — eventos, lidos, últimos autocarros — está em " + a(L("pt", "/funchal/"), "Funchal hoje") + "."], False),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Madère en un jour : top 5 et un plan réaliste",
  desc="Un jour à Madère ? Le top 5 — Cabo Girão, Curral das Freiras, Câmara de Lobos, Monte, le Mercado — avec les prix 2026 et deux plans réalistes. À lire ici.",
  h1="Madère en un jour : le top 5, et ce qui tient vraiment",
  sub="Escale de croisière ou visite courte : les cinq lieux que citent d'abord les chauffeurs de taxi et les Madériens, les vraies distances, les prix 2026 — et pourquoi il faut choisir un plan, pas tout faire.",
  body=[
   ("Quelles sont les 5 choses à faire à Madère en un jour ?", [
     "Les cinq lieux que citent d'abord les chauffeurs de taxi et les Madériens : le skywalk du Cabo Girão, la vallée de Curral das Freiras, la vieille ville de Câmara de Lobos, Monte au-dessus de Funchal, et le marché Mercado dos Lavradores. Tout ne tient pas en un jour — Cabo Girão et Curral das Freiras sont dans des directions différentes et Monte prend une demi-journée — choisissez donc l'un des deux plans ci-dessous.",
     "<ul>"
     "<li><b>Skywalk du Cabo Girão</b> — la plateforme de verre sur une falaise de 580 m, que Visit Madeira présente comme le plus haut promontoire d'Europe. C'est un belvédère, rien de plus : 20 à 30 minutes suffisent. 5 € pour les plus de 12 ans (tarif 2026 ; enfants jusqu'à 12 ans et résidents de Madère gratuits), ouvert tous les jours de 08h00 à 20h00.</li>"
     "<li><b>Curral das Freiras</b> — la vallée au cœur de l'île. Le belvédère d'Eira do Serrado, au-dessus, est la partie impressionnante ; le bourg est 2,6 km plus bas.</li>"
     "<li><b>Câmara de Lobos</b> — une flânerie dans le vieux village de pêcheurs et sur la jetée. L'arrêt déjeuner naturel de la journée.</li>"
     "<li><b>Monte</b> — le téléphérique depuis la vieille ville de Funchal (16 € l'aller, 22 € l'aller-retour), l'église et le jardin Monte Palace (18 €, gratuit jusqu'à 14 ans).</li>"
     "<li><b>Mercado dos Lavradores</b> — les halles de Funchal : lundi–vendredi 07h00–19h00, samedi jusqu'à 14h00, fermé le dimanche.</li>"
     "</ul>"], True),
   ("Comment voir Curral das Freiras, Cabo Girão et Câmara de Lobos en un jour ?", [
     "En taxi, en une boucle d'environ 56 km (plan A) : de Funchal au belvédère d'Eira do Serrado puis à Curral das Freiras le matin, route vers le skywalk du Cabo Girão (20–30 minutes sur place), descente à Câmara de Lobos pour déjeuner et flâner dans la vieille ville et sur la jetée, et retour à Funchal en début d'après-midi. Avec les arrêts, comptez environ 6 heures.",
     table(["Trajet", "Route", "Temps en taxi"],
           [["Funchal → Eira do Serrado → Curral das Freiras", "environ 18 km", "environ 30 min"],
            ["Curral das Freiras → Cabo Girão", "environ 22 km", "environ 35 min"],
            ["Cabo Girão → Câmara de Lobos", "environ 6 km", "environ 10 min"],
            ["Câmara de Lobos → Funchal", "environ 10 km", "environ 15 min"]]),
     "Distances routières d'OpenStreetMap ; ce sont des routes de montagne, les temps s'entendent sans circulation. De retour à Funchal, le Mercado dos Lavradores est ouvert jusqu'à 19h00 en semaine et 14h00 le samedi (fermé le dimanche)."], True),
   ("Combien coûte un taxi à la journée à Madère ?", [
     "Des chauffeurs nous ont indiqué environ 160 € pour une sortie de 6 heures, en octobre 2026 — un chiffre indicatif, pas un tarif. Cabo Girão, Curral das Freiras et Funchal sont dans des directions différentes : le prix dépend de la boucle exacte que vous voulez. Appelez une station, décrivez votre parcours et demandez un devis avant de partir. Contacts officiels : Táxis Madeira +351 291 764 476 (en ligne sur taxismadeira.pt) et AITRAM +351 291 765 760."], True),
   ("Que faire à Funchal et à Monte en un jour ?", [
     "Le plan B se fait à pied et en téléphérique. Le matin, le Mercado dos Lavradores (fermé le dimanche) et la vieille ville ; puis le téléphérique vers Monte (tous les jours 08h45–17h45, 16 € l'aller, 22 € l'aller-retour ; 0–6 ans gratuit, 7–14 ans demi-tarif), l'église et le jardin Monte Palace (18 €, gratuit jusqu'à 14 ans ; 09h00–19h00 d'avril à septembre, jusqu'à 18h00 en hiver). Redescendez en téléphérique — ou entamez la descente en luge d'osier des Carreiros do Monte (lundi–samedi 09h00–18h00) et continuez en bus ou en taxi.",
     "Le Jardin botanique demande honnêtement un deuxième jour : avec le marché, Monte et Monte Palace, la journée est pleine. Les plans A et B réunis font un itinéraire de deux jours, pas d'un — il est détaillé, avec horaires, dans " + a(L("fr", "/two-days-in-madeira/"), "Madère en deux jours") + "."], True),
   ("Faut-il louer une voiture pour un jour à Madère ?", [
     "Pour cette journée, nous le déconseillons. Le stationnement est limité dans la plupart de ces lieux — et dans le centre de Funchal vous paieriez un parking pour visiter à pied. La boucle en taxi plus le téléphérique couvrent la même journée sans chasse à la place. Si vous tenez à conduire, partez tôt et prévoyez un plan B pour vous garer."], True),
   ("Peut-on caser une levada ou un pic dans la journée ?", [
     "Une marche courte de montagne tient dans une journée d'escale : l'aller-retour du Pico do Areeiro au belvédère de Pedra Rija sur le " + a(L("fr", "/pr1/"), "PR1") + " — 1,2 km par sens sur la fameuse crête aux escaliers, 4,50 €, réservation en ligne sur SIMplifica (voir " + a(L("fr", "/simplifica-booking/"), "comment réserver") + "). Vérifiez d'abord le sommet : " + a(L("fr", "/pico-do-areeiro-weather/"), "météo et webcams du Pico do Arieiro") + "."], True),
   ("Depuis un navire de croisière", [
     "Le plan A est taillé pour une escale : environ 6 heures porte à porte depuis le terminal. Convenez de l'heure de retour avec le chauffeur à la réservation et gardez une marge d'au moins une heure avant le rappel à bord. Ce qui est ouvert en ville aujourd'hui — événements, lidos, derniers bus — est sur " + a(L("fr", "/funchal/"), "Funchal aujourd'hui") + "."], False),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Ein Tag auf Madeira: Top 5 und ein realistischer Plan",
  desc="Ein Tag auf Madeira? Die Top 5 — Cabo Girão, Curral das Freiras, Câmara de Lobos, Monte, Mercado — mit Preisen 2026 und zwei realistischen Plänen zur Wahl.",
  h1="Ein Tag auf Madeira: die Top 5 — und was wirklich passt",
  sub="Kreuzfahrt-Stopp oder Kurzbesuch: die fünf Orte, die Taxifahrer und Einheimische zuerst nennen, echte Entfernungen, Preise 2026 — und warum man einen Plan wählen muss, statt alles zu machen.",
  body=[
   ("Was sind die Top 5 an einem Tag auf Madeira?", [
     "Die fünf Orte, die Taxifahrer und Einheimische zuerst nennen: der Skywalk am Cabo Girão, das Tal Curral das Freiras, die Altstadt von Câmara de Lobos, Monte über Funchal und die Markthalle Mercado dos Lavradores. Alle fünf passen nicht in einen Tag — Cabo Girão und Curral das Freiras liegen in verschiedenen Richtungen, und Monte braucht einen halben Tag — wählen Sie also einen der beiden Pläne unten.",
     "<ul>"
     "<li><b>Skywalk am Cabo Girão</b> — die Glasplattform auf einer 580-m-Klippe, laut Visit Madeira das höchste Kliff Europas. Es ist ein Aussichtspunkt, mehr nicht: 20–30 Minuten genügen. 5 € für über 12-Jährige (Tarif 2026; Kinder bis 12 und Madeira-Bewohner frei), täglich 08:00–20:00.</li>"
     "<li><b>Curral das Freiras</b> — das Tal im Herzen der Insel. Der Aussichtspunkt Eira do Serrado darüber ist der beeindruckende Teil; der Ort selbst liegt 2,6 km weiter unten.</li>"
     "<li><b>Câmara de Lobos</b> — ein Bummel durch das alte Fischerstädtchen und über die Mole. Der natürliche Mittagsstopp des Tages.</li>"
     "<li><b>Monte</b> — die Seilbahn hinauf aus Funchals Altstadt (16 € einfach, 22 € hin und zurück), die Kirche und der Garten Monte Palace (18 €, bis 14 Jahre frei).</li>"
     "<li><b>Mercado dos Lavradores</b> — Funchals Markthalle: Montag–Freitag 07:00–19:00, Samstag bis 14:00, sonntags geschlossen.</li>"
     "</ul>"], True),
   ("Wie sieht man Curral das Freiras, Cabo Girão und Câmara de Lobos an einem Tag?", [
     "Mit dem Taxi, in einer Runde von etwa 56 km (Plan A): von Funchal morgens zum Aussichtspunkt Eira do Serrado und hinunter nach Curral das Freiras, weiter zum Skywalk am Cabo Girão (20–30 Minuten dort), dann hinab nach Câmara de Lobos zum Mittagessen und für einen Bummel durch Altstadt und Mole, und am frühen Nachmittag zurück nach Funchal. Mit den Stopps ist das ein Tag von rund 6 Stunden.",
     table(["Abschnitt", "Straße", "Taxizeit"],
           [["Funchal → Eira do Serrado → Curral das Freiras", "etwa 18 km", "etwa 30 min"],
            ["Curral das Freiras → Cabo Girão", "etwa 22 km", "etwa 35 min"],
            ["Cabo Girão → Câmara de Lobos", "etwa 6 km", "etwa 10 min"],
            ["Câmara de Lobos → Funchal", "etwa 10 km", "etwa 15 min"]]),
     "Straßenentfernungen aus OpenStreetMap; es sind Bergstraßen, die Zeiten gelten ohne Verkehr. Zurück in Funchal hat der Mercado dos Lavradores werktags bis 19:00 und samstags bis 14:00 geöffnet (sonntags geschlossen)."], True),
   ("Was kostet ein Taxi für einen Tag auf Madeira?", [
     "Taxifahrer nannten uns im Oktober 2026 etwa 160 € für einen 6-Stunden-Ausflug — ein Richtwert, kein Tarif. Cabo Girão, Curral das Freiras und Funchal liegen in verschiedenen Richtungen, der Preis hängt also von Ihrer genauen Runde ab: Rufen Sie einen Taxistand an, beschreiben Sie die Route und holen Sie ein Angebot ein, bevor Sie losfahren. Offizielle Kontakte: Táxis Madeira +351 291 764 476 (online auf taxismadeira.pt) und AITRAM +351 291 765 760."], True),
   ("Was macht man in Funchal und Monte an einem Tag?", [
     "Plan B geht zu Fuß und mit der Seilbahn. Morgens der Mercado dos Lavradores (sonntags geschlossen) und die Altstadt; dann die Seilbahn nach Monte (täglich 08:45–17:45, 16 € einfach, 22 € hin und zurück; 0–6 Jahre frei, 7–14 halber Preis), die Kirche und der Garten Monte Palace (18 €, bis 14 frei; 09:00–19:00 April–September, im Winter bis 18:00). Hinunter mit der Seilbahn — oder das erste Stück mit den Korbschlitten der Carreiros do Monte (Montag–Samstag 09:00–18:00), dann weiter mit Bus oder Taxi.",
     "Der Botanische Garten braucht ehrlicherweise den zweiten Tag: Mit Markt, Monte und Monte Palace ist der Tag voll. Plan A und B zusammen sind eine Zwei-Tage-Route, keine für einen Tag — ausgearbeitet, mit Uhrzeiten, in " + a(L("de", "/two-days-in-madeira/"), "Zwei Tage auf Madeira") + "."], True),
   ("Lohnt sich ein Mietwagen für einen Tag auf Madeira?", [
     "Für diesen Tag raten wir ab. An den meisten dieser Orte ist das Parken knapp — und im Zentrum von Funchal zahlt man fürs Parkhaus, während man die Stadt zu Fuß ansieht. Die Taxirunde plus Seilbahn deckt denselben Tag ohne Parkplatzsuche ab. Wer unbedingt fahren will: früh los, und einen Plan B fürs Parken haben."], True),
   ("Passt eine Levada oder ein Gipfel in einen Tag?", [
     "Eine kurze Bergwanderung passt in einen Hafentag: hin und zurück vom Pico do Areeiro zum Aussichtspunkt Pedra Rija auf dem " + a(L("de", "/pr1/"), "PR1") + " — je 1,2 km auf dem berühmten Treppengrat, 4,50 €, online auf SIMplifica gebucht (siehe " + a(L("de", "/simplifica-booking/"), "wie man bucht") + "). Vorher den Gipfel prüfen: " + a(L("de", "/pico-do-areeiro-weather/"), "Wetter und Webcams am Pico do Arieiro") + "."], True),
   ("Vom Kreuzfahrtschiff", [
     "Plan A ist auf einen Landgang zugeschnitten: etwa 6 Stunden Tür zu Tür ab Terminal. Vereinbaren Sie die Rückkehrzeit beim Buchen mit dem Fahrer und lassen Sie mindestens eine Stunde Puffer vor dem All-aboard. Was heute in der Stadt offen ist — Veranstaltungen, Lidos, letzte Busse — steht auf " + a(L("de", "/funchal/"), "Funchal heute") + "."], False),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Jeden dzień na Maderze: top 5 i realny plan",
  desc="Jeden dzień na Maderze? Top 5 — Cabo Girão, Curral das Freiras, Câmara de Lobos, Monte i Mercado — z cenami 2026 i dwoma realnymi planami. Sprawdź tutaj.",
  h1="Jeden dzień na Maderze: top 5 i co naprawdę się mieści",
  sub="Postój statku czy krótka wizyta: pięć miejsc, które taksówkarze i mieszkańcy wymieniają pierwsze, prawdziwe odległości, ceny 2026 — i dlaczego trzeba wybrać plan, a nie robić wszystko.",
  body=[
   ("Co robić na Maderze w jeden dzień: jakie jest top 5?", [
     "Pięć miejsc, które taksówkarze i mieszkańcy wymieniają pierwsze: skywalk na Cabo Girão, dolina Curral das Freiras, stare miasto Câmara de Lobos, Monte nad Funchal i hala targowa Mercado dos Lavradores. Wszystkie pięć nie mieści się w jednym dniu — Cabo Girão i Curral das Freiras leżą w różnych kierunkach, a Monte zajmuje pół dnia — wybierz więc jeden z dwóch planów poniżej.",
     "<ul>"
     "<li><b>Skywalk na Cabo Girão</b> — szklana platforma na 580-metrowym klifie, według Visit Madeira najwyższym cyplu Europy. To punkt widokowy i nic więcej: 20–30 minut wystarczy. 5 € dla osób powyżej 12 lat (taryfa 2026; dzieci do 12 lat i mieszkańcy Madery za darmo), codziennie 08:00–20:00.</li>"
     "<li><b>Curral das Freiras</b> — dolina w sercu wyspy. Punkt widokowy Eira do Serrado nad nią to ta imponująca część; samo miasteczko leży 2,6 km niżej.</li>"
     "<li><b>Câmara de Lobos</b> — spacer po starej rybackiej miejscowości i po molo. Naturalny przystanek na obiad.</li>"
     "<li><b>Monte</b> — kolejka linowa ze starówki Funchal (16 € w jedną stronę, 22 € w obie), kościół i ogród Monte Palace (18 €, do 14 lat za darmo).</li>"
     "<li><b>Mercado dos Lavradores</b> — hala targowa Funchal: poniedziałek–piątek 07:00–19:00, sobota do 14:00, w niedzielę zamknięte.</li>"
     "</ul>"], True),
   ("Jak zobaczyć Curral das Freiras, Cabo Girão i Câmara de Lobos w jeden dzień?", [
     "Taksówką, w jednej pętli około 56 km (plan A): rano z Funchal na punkt widokowy Eira do Serrado i w dół do Curral das Freiras, potem do skywalku na Cabo Girão (20–30 minut na miejscu), zjazd do Câmara de Lobos na obiad i spacer po starówce i molo, i powrót do Funchal wczesnym popołudniem. Z przystankami to dzień około 6 godzin.",
     table(["Odcinek", "Droga", "Czas taksówką"],
           [["Funchal → Eira do Serrado → Curral das Freiras", "około 18 km", "około 30 min"],
            ["Curral das Freiras → Cabo Girão", "około 22 km", "około 35 min"],
            ["Cabo Girão → Câmara de Lobos", "około 6 km", "około 10 min"],
            ["Câmara de Lobos → Funchal", "około 10 km", "około 15 min"]]),
     "Odległości drogowe z OpenStreetMap; to drogi górskie, więc czasy są bez ruchu. Po powrocie do Funchal Mercado dos Lavradores jest otwarte do 19:00 w dni robocze i do 14:00 w soboty (w niedzielę zamknięte)."], True),
   ("Ile kosztuje taksówka na cały dzień na Maderze?", [
     "Taksówkarze podali nam około 160 € za 6-godzinny dzień, w październiku 2026 — kwota orientacyjna, nie taryfa. Cabo Girão, Curral das Freiras i Funchal leżą w różnych kierunkach, więc cena zależy od dokładnej pętli, którą chcesz zrobić: zadzwoń na postój, opisz trasę i poproś o wycenę, zanim ruszysz. Oficjalne kontakty: Táxis Madeira +351 291 764 476 (online na taxismadeira.pt) i AITRAM +351 291 765 760."], True),
   ("Co robić w Funchal i na Monte w jeden dzień?", [
     "Plan B jest pieszo i kolejką. Rano Mercado dos Lavradores (w niedzielę zamknięte) i starówka; potem kolejka linowa na Monte (codziennie 08:45–17:45, 16 € w jedną stronę, 22 € w obie; 0–6 lat za darmo, 7–14 pół ceny), kościół i ogród Monte Palace (18 €, do 14 lat za darmo; 09:00–19:00 od kwietnia do września, zimą do 18:00). W dół kolejką — albo zacznij zjazd wiklinowymi saniami Carreiros do Monte (poniedziałek–sobota 09:00–18:00) i dalej autobusem lub taksówką.",
     "Ogród Botaniczny szczerze mówiąc potrzebuje drugiego dnia: z targiem, Monte i Monte Palace dzień jest pełny. Plany A i B razem to trasa na dwa dni, nie na jeden — rozpisana, z godzinami, w " + a(L("pl", "/two-days-in-madeira/"), "dwa dni na Maderze") + "."], True),
   ("Czy warto wynająć auto na jeden dzień na Maderze?", [
     "Na ten dzień odradzamy. W większości tych miejsc parkowanie jest ograniczone — a w centrum Funchal płaciłbyś za parking, zwiedzając miasto pieszo. Pętla taksówką plus kolejka pokrywają ten sam dzień bez szukania miejsca. Jeśli koniecznie chcesz jechać autem, wyjedź wcześnie i miej plan B na parkowanie."], True),
   ("Czy w jeden dzień zmieści się levada albo szczyt?", [
     "Jedna krótka górska trasa mieści się w dniu postoju: tam i z powrotem z Pico do Areeiro do punktu widokowego Pedra Rija na " + a(L("pl", "/pr1/"), "PR1") + " — po 1,2 km słynną granią ze schodami, 4,50 €, rezerwacja online w SIMplifica (zobacz " + a(L("pl", "/simplifica-booking/"), "jak zarezerwować") + "). Najpierw sprawdź szczyt: " + a(L("pl", "/pico-do-areeiro-weather/"), "pogoda i kamery na Pico do Arieiro") + "."], True),
   ("Ze statku wycieczkowego", [
     "Plan A jest skrojony pod postój w porcie: około 6 godzin od terminalu do terminalu. Umów godzinę powrotu z kierowcą przy rezerwacji i zostaw co najmniej godzinę zapasu przed all-aboard. Co jest dziś otwarte w mieście — wydarzenia, lida, ostatnie autobusy — znajdziesz na " + a(L("pl", "/funchal/"), "Funchal dzisiaj") + "."], False),
   ("Źródła", [None], False),
  ]),
}


# "is one day enough in madeira" is a top autocomplete query (checked 2026-10-20); answered verbatim.
ENOUGH = {
    "en": ("Is one day in Madeira enough?",
           "For one of the two plans above, yes; for the whole top 5, no. One day covers either the viewpoints taxi loop or Funchal and Monte — not both, and not the Botanical Garden. If your ship calls for a single day, pick the plan that fits your hours ashore; with two days you do both — see "),
    "pt": ("Um dia na Madeira chega?",
           "Para um dos dois planos acima, sim; para o top 5 inteiro, não. Um dia dá para a volta de táxi pelos miradouros ou para o Funchal e o Monte — não para ambos, nem para o Jardim Botânico. Se o navio fica só um dia, escolha o plano que cabe nas suas horas em terra; com dois dias faz os dois — veja "),
    "fr": ("Un jour à Madère, est-ce suffisant ?",
           "Pour l'un des deux plans ci-dessus, oui ; pour tout le top 5, non. Une journée couvre soit la boucle des belvédères en taxi, soit Funchal et Monte — pas les deux, ni le Jardin botanique. Si votre navire ne fait escale qu'un jour, choisissez le plan qui tient dans vos heures à terre ; avec deux jours, vous faites les deux — voir "),
    "de": ("Reicht ein Tag auf Madeira?",
           "Für einen der beiden Pläne oben: ja; für die ganzen Top 5: nein. Ein Tag reicht entweder für die Taxirunde zu den Aussichtspunkten oder für Funchal und Monte — nicht für beides, und nicht für den Botanischen Garten. Liegt Ihr Schiff nur einen Tag im Hafen, wählen Sie den Plan, der in Ihre Stunden an Land passt; mit zwei Tagen machen Sie beide — siehe "),
    "pl": ("Czy jeden dzień na Maderze wystarczy?",
           "Na jeden z dwóch planów powyżej — tak; na całe top 5 — nie. Jeden dzień wystarczy albo na pętlę taksówką po punktach widokowych, albo na Funchal i Monte — nie na oba, ani na Ogród Botaniczny. Jeśli statek stoi tylko jeden dzień, wybierz plan, który mieści się w Twoich godzinach na lądzie; w dwa dni zrobisz oba — zobacz "),
}
TWODAY_NAME = {"en": "two days in Madeira", "pt": "dois dias na Madeira", "fr": "Madère en deux jours",
               "de": "Zwei Tage auf Madeira", "pl": "dwa dni na Maderze"}


def prepare(lang, t):
    eq, etext = ENOUGH[lang]
    t.insert(4, (eq, [etext + a(L(lang, "/two-days-in-madeira/"), TWODAY_NAME[lang]) + "."], True))
    return t


def main():
    gi.build_qa(SLUG, COPY, src, "2026-10-20T12:00+01:00", prepare=prepare,
                chain=("gen_site_nav.py", "gen_cta.py", "gen_owner.py", "gen_schema.py", "gen_chat.py"))


if __name__ == "__main__":
    main()
