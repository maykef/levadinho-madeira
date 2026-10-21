#!/usr/bin/env python3
"""Writes /pico-do-areeiro-parking/ × 5 languages from the free-walks page shell (owner, 2026-10-14).

What it says, and where from:
  rates          Portaria 48/2026, Annex II, Part I, point 6 (6.2 Miradouro do Pico do Areeiro, 6.3 Outros), notes (e)/(f);
                 the parking rows carry no residents' note (a), and art. 16 exempts residents only from points 2, 3.1,
                 3.2 and 4. Art. 17: point 6 is not index-linked, its 2027-2029 rates are in the table.
  in force       DN 28 Oct 2024: charging started that day, meters at the upper and the peripheral car park, pay per
                 fraction or for the whole day, residents pay too.
  shuttle        Horários do Funchal Pico do Areeiro page + map PDF: stops CAM Florestal / Parque Pico do Areeiro (the P
                 below the summit) / Radar roundabout, every 15 min 06:40-12:15 and 14:10-19:00, last trip 18:00 from
                 25 Oct 2026 (winter timetable), €1.20 on board, leaves with at least 4 passengers.
  radar road     DN 29 Sep 2022 (about 15 spaces for tour buses, vans and taxis on the road to the radar station,
                 yellow lines on the bends, towing warning). Whether that signage is unchanged in 2026 is not confirmed.
  morning crush  DN 27 Jun 2024 (emergency vehicles blocked).
  announced      DN 28 Oct 2024 (Casa das Sorveiras car park, ~300 spaces, tender early 2025; rental-car restriction
                 under consideration); JM 2024 (electronic panels to control car access). No later report found.
  Achada         no official parking fee found there (seo_research/facts/parking.json, PR1.2).
Not used: social posts (owner's rule), card-only/cash claims (sources disagree), space counts (unsourced).

Re-run after changing the copy: it keeps dateModified, then runs gen_site_nav.py, gen_cta.py, gen_owner.py and
gen_schema.py itself (the page is in GUIDES / TAGS).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "pico-do-areeiro-parking"
ROOT = gi.ROOT
P48 = "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Portarias/Port48ISerie027_2026.pdf"
HF = "https://www.horariosdofunchal.pt/index.php/viajar/pico-do-areeiro"
DN_2024 = "https://www.dnoticias.pt/2024/10/28/424972-estacionamento-junto-a-casa-das-sorveiras-so-avanca-no-inicio-do-proximo-ano/"
DN_RAC = "https://www.dnoticias.pt/2024/10/28/424985-proibicao-de-rent-a-cars-no-areeiro-ainda-esta-a-ser-equacionada/"
DN_2022 = "https://www.dnoticias.pt/2022/9/29/329985-quintuplicaram-os-lugares-de-estacionamento-no-areeiro/"
DN_CHAOS = "https://www.dnoticias.pt/2024/6/27/410927-caos-no-pico-do-areeiro-ja-impediu-a-passagem-de-viaturas-de-emergencia/"
JM = "https://www.jm-madeira.pt/regiao/acesso-de-carro-ao-pico-do-areeiro-sera-controlado-por-paineis-eletronicos-e-estacionamentos-pagos-KF16469939"
a, ext = gi.a, gi.ext


def src(lang):
    return ('<p class="src">' + ext(P48, "Portaria 48/2026") + " · " + ext(HF, "Horários do Funchal") + " · "
            + ext(DN_2024, "DN 28.10.2024") + " · " + ext(DN_RAC, "DN 28.10.2024 (rent-a-car)") + " · "
            + ext(DN_2022, "DN 29.09.2022") + " · " + ext(DN_CHAOS, "DN 27.06.2024") + " · " + ext(JM, "JM") + "</p>")


def table(head, rows):
    return ('<div class="tbl"><table>\n    <thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead>\n    <tbody>\n"
            + "".join("      <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n" for r in rows) + "    </tbody>\n  </table></div>")


def L(lang, path):
    return f"{PREFIX[lang]}{path}"


# Sections: (heading, parts, is_question). A question's FAQ answer is its first paragraph, verbatim.
COPY = {
 "en": dict(
  title="Pico do Areeiro parking 2026: prices and which car park",
  desc="Pico do Areeiro parking: €4/h up to €20 a day at the top, €2/h up to €5 below. Walking the full PR1? Which car park to use and how to save. Read on.",
  h1="Pico do Areeiro parking: prices, which car park for PR1, and the morning rush",
  sub="IFCN's two car parks at the summit, the official 2026 rates, and what they mean when your car stays there all day.",
  body=[
   ("How much does parking at Pico do Areeiro cost?", [
     "There are two IFCN car parks, both with meters. The upper car park by the viewpoint, café and shop costs €4 an hour, up to €20 a day. The lower car park, on the access road below the summit, costs €2 an hour, up to €5 a day. At both the first 30 minutes are free, and you can pay by the hour or for the whole day.",
     table(["Car park", "Per hour", "First 30 minutes", "Daily maximum"],
           [["Upper (Miradouro do Pico do Areeiro)", "€4.00", "free", "€20"], ["Lower (on the access road)", "€2.00", "free", "€5"]]),
     "The rates are set in Portaria 48/2026 (Annex II, point 6), which already fixes the next years: the upper car park goes to €4.25 an hour in 2027, €4.50 in 2028 and €5.00 in 2029; the lower one to €2.25, €2.35 and €2.50."], True),
   ("Do residents pay for parking at Pico do Areeiro?", [
     "Yes. The residents' exemption in Portaria 48/2026 covers the trail fees and four IFCN visits (the Casa das Tradições Madeirenses, the Botanical Garden, the Quinta do Santo da Serra and the Ribeiro Frio fish farm), not the car parks. Parking is charged to visitors and Madeirans alike."], True),
   ("Which car park should I use for the full PR1?", [
     "The lower one, or none at all. PR1 is one-way: you finish at Achada do Teixeira, far from your car, and fetch it hours later. A full day costs €20 in the upper car park and €5 in the lower one, so €15 less per car. The upper car park reaches its €20 cap after about five and a half hours, the lower one its €5 cap after about three.",
     "<ul><li><b>Full PR1 (Areeiro → Pico Ruivo → Achada):</b> the lower car park, or leave the car at Achada do Teixeira (below).</li>"
     "<li><b>Sunrise only, or the out-and-back to Pedra Rija:</b> you are back within a couple of hours, so the upper car park costs only a few euros more and saves the walk.</li></ul>"], True),
   ("How do I get from the lower car park to the top?", [
     "Walk up the access road, or take Horários do Funchal's summit shuttle. Its Parque Pico do Areeiro stop is at the lower car park, and it runs to the roundabout by the radar at the top every 15 minutes, 06:40–12:15 and 14:10–19:00 (last trip 18:00 from 25 October, with the winter timetable). It costs €1.20 a trip, paid on board, and only leaves with at least 4 passengers.",
     "The first trip is at 06:40, which is too tight for sunrise in June and July. The " + a(L("en", "/pr1-sunrise-transport/"), "sunrise transport guide") + " has the times."], True),
   ("Can I avoid paying for a whole day at Areeiro?", [
     "Yes: park where you finish. Leave the car at Achada do Teixeira, where PR1 ends (we found no official parking fee there), and take a taxi to Pico do Areeiro for your slot: Táxis Santana, +351 291 572 540, is the nearest rank. When you come down, your car is waiting. Without a car, the Horários do Funchal bus reaches the top at 06:45 and 14:15 for €3.",
     "All the ways back from Achada are in " + a(L("en", "/getting-back.html"), "getting back from PR1") + "."], True),
   ("Why is parking at Pico do Areeiro so hard in the morning?", [
     "Both car parks fill before sunrise. Cars then park along the access road, and in past years tour buses and even emergency vehicles were blocked on the bends. Don't park on the yellow lines on the bends, where cars can be towed, or on the road to the radar station: in 2022 about 15 spaces there were reserved for tour buses, vans and taxis. Arrive at least an hour before sunrise, or come mid-morning, after the sunrise crowd has gone.",
     "Is the summit clear right now? " + a(L("en", "/pico-do-areeiro-weather/"), "Pico do Areeiro now: webcams and weather") + "."], True),
   ("Announced, not confirmed", [
     "<ul><li><b>A new car park of about 300 spaces</b> near the Casa das Sorveiras, between Poiso and the summit: its tender was due in early 2025. We found no report that it has been built.</li>"
     "<li><b>Electronic panels to control car access</b> to the summit were announced in 2024. We found no report of them working.</li>"
     "<li><b>Keeping rental cars away from the top</b> was being considered in October 2024. We found no decision.</li></ul>"], False),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="Estacionamento no Pico do Areeiro 2026: preços e parques",
  desc="Estacionamento no Pico do Areeiro: 4 €/h até 20 €/dia em cima, 2 €/h até 5 € em baixo. Vai fazer o PR1 completo? Que parque usar e como poupar.",
  h1="Estacionamento no Pico do Areeiro: preços, que parque para o PR1 e a confusão da manhã",
  sub="Os dois parques do IFCN no cume, os preços oficiais de 2026 e o que significam quando o carro fica lá o dia todo.",
  body=[
   ("Quanto custa estacionar no Pico do Areeiro?", [
     "Há dois parques do IFCN, ambos com parquímetro. O parque de cima, junto ao miradouro, ao café e à loja, custa 4 € por hora, até 20 € por dia. O parque de baixo, na estrada de acesso abaixo do cume, custa 2 € por hora, até 5 € por dia. Em ambos os primeiros 30 minutos são grátis e pode pagar à hora ou o dia inteiro.",
     table(["Parque", "Por hora", "Primeiros 30 minutos", "Máximo diário"],
           [["De cima (Miradouro do Pico do Areeiro)", "4,00 €", "grátis", "20 €"], ["De baixo (na estrada de acesso)", "2,00 €", "grátis", "5 €"]]),
     "Os preços constam da Portaria 48/2026 (Anexo II, ponto 6), que já fixa os anos seguintes: o parque de cima passa a 4,25 € por hora em 2027, 4,50 € em 2028 e 5,00 € em 2029; o de baixo a 2,25 €, 2,35 € e 2,50 €."], True),
   ("Os residentes pagam estacionamento no Pico do Areeiro?", [
     "Sim. A isenção dos residentes na Portaria 48/2026 abrange as taxas dos percursos e quatro visitas do IFCN (a Casa das Tradições Madeirenses, o Jardim Botânico, a Quinta do Santo da Serra e o Centro Aquícola do Ribeiro Frio), não os parques. O estacionamento é pago por visitantes e madeirenses."], True),
   ("Que parque devo usar para o PR1 completo?", [
     "O de baixo, ou nenhum. O PR1 é em sentido único: termina na Achada do Teixeira, longe do carro, e vai buscá-lo horas depois. Um dia inteiro custa 20 € no parque de cima e 5 € no de baixo, ou seja, menos 15 € por carro. O parque de cima chega ao máximo de 20 € ao fim de cerca de cinco horas e meia, o de baixo aos 5 € ao fim de cerca de três.",
     "<ul><li><b>PR1 completo (Areeiro → Pico Ruivo → Achada):</b> o parque de baixo, ou deixe o carro na Achada do Teixeira (ver abaixo).</li>"
     "<li><b>Só o nascer do sol, ou ida e volta à Pedra Rija:</b> volta ao fim de poucas horas, por isso o parque de cima custa só mais alguns euros e poupa a subida.</li></ul>"], True),
   ("Como se vai do parque de baixo até ao cume?", [
     "A pé pela estrada de acesso, ou no vaivém dos Horários do Funchal. A paragem Parque Pico do Areeiro fica no parque de baixo, e o vaivém sobe até à rotunda junto ao Radar a cada 15 minutos, das 06:40 às 12:15 e das 14:10 às 19:00 (última viagem às 18:00 a partir de 25 de outubro, com o horário de inverno). Custa 1,20 € por viagem, pago a bordo, e só parte com pelo menos 4 passageiros.",
     "A primeira viagem é às 06:40, o que é apertado para o nascer do sol em junho e julho. O " + a(L("pt", "/pr1-sunrise-transport/"), "guia de transporte para o nascer do sol") + " tem os horários."], True),
   ("Posso evitar pagar um dia inteiro no Areeiro?", [
     "Sim: estacione onde termina. Deixe o carro na Achada do Teixeira, onde acaba o PR1 (não encontrámos preço oficial de estacionamento lá), e apanhe um táxi até ao Pico do Areeiro para o seu horário: a praça mais próxima é a dos Táxis Santana, +351 291 572 540. Quando descer, o carro está à sua espera. Sem carro, o autocarro dos Horários do Funchal chega ao cume às 06:45 e às 14:15, por 3 €.",
     "Todas as formas de regressar da Achada estão em " + a(L("pt", "/getting-back.html"), "regressar do PR1") + "."], True),
   ("Porque é tão difícil estacionar no Pico do Areeiro de manhã?", [
     "Os dois parques enchem antes do nascer do sol. Os carros ficam então ao longo da estrada de acesso, e em anos anteriores autocarros de turismo e até viaturas de emergência ficaram bloqueados nas curvas. Não estacione nas linhas amarelas das curvas, onde os carros podem ser rebocados, nem na estrada da Estação Radar: em 2022 cerca de 15 lugares ali ficaram reservados a autocarros, carrinhas de turismo e táxis. Chegue pelo menos uma hora antes do nascer do sol, ou a meio da manhã, quando a multidão do nascer do sol já saiu.",
     "O cume está limpo agora? " + a(L("pt", "/pico-do-areeiro-weather/"), "Pico do Areeiro agora: webcams e tempo") + "."], True),
   ("Anunciado, não confirmado", [
     "<ul><li><b>Um novo parque de cerca de 300 lugares</b> junto à Casa das Sorveiras, entre o Poiso e o cume: o concurso estava previsto para o início de 2025. Não encontrámos notícia de que tenha sido construído.</li>"
     "<li><b>Painéis eletrónicos para controlar o acesso de carro</b> ao cume foram anunciados em 2024. Não encontrámos notícia de que estejam a funcionar.</li>"
     "<li><b>Afastar os rent-a-car do cume</b> estava a ser ponderado em outubro de 2024. Não encontrámos decisão.</li></ul>"], False),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Parking du Pico do Arieiro 2026 : tarifs et quel parking",
  desc="Parking du Pico do Arieiro : 4 €/h jusqu'à 20 € par jour en haut, 2 €/h jusqu'à 5 € en bas. PR1 en entier ? Quel parking choisir et comment économiser.",
  h1="Parking du Pico do Arieiro : tarifs, quel parking pour le PR1, et la cohue du matin",
  sub="Les deux parkings de l'IFCN au sommet, les tarifs officiels 2026, et ce qu'ils signifient quand la voiture y reste toute la journée.",
  body=[
   ("Combien coûte le parking au Pico do Arieiro ?", [
     "Il y a deux parkings de l'IFCN, tous deux à horodateur. Le parking du haut, près du belvédère, du café et de la boutique, coûte 4 € de l'heure, jusqu'à 20 € par jour. Le parking du bas, sur la route d'accès sous le sommet, coûte 2 € de l'heure, jusqu'à 5 € par jour. Dans les deux, les 30 premières minutes sont gratuites, et vous pouvez payer à l'heure ou pour la journée.",
     table(["Parking", "Par heure", "30 premières minutes", "Maximum par jour"],
           [["Haut (Miradouro do Pico do Areeiro)", "4,00 €", "gratuites", "20 €"], ["Bas (sur la route d'accès)", "2,00 €", "gratuites", "5 €"]]),
     "Les tarifs sont fixés par la Portaria 48/2026 (annexe II, point 6), qui prévoit déjà les années suivantes : le parking du haut passe à 4,25 € de l'heure en 2027, 4,50 € en 2028 et 5,00 € en 2029 ; celui du bas à 2,25 €, 2,35 € et 2,50 €."], True),
   ("Les résidents paient-ils le parking au Pico do Arieiro ?", [
     "Oui. L'exonération des résidents dans la Portaria 48/2026 couvre les taxes des sentiers et quatre visites de l'IFCN (la Casa das Tradições Madeirenses, le Jardin botanique, la Quinta do Santo da Serra et le centre aquacole de Ribeiro Frio), pas les parkings. Visiteurs et Madériens paient le parking."], True),
   ("Quel parking choisir pour le PR1 en entier ?", [
     "Celui du bas, ou aucun. Le PR1 est à sens unique : vous terminez à Achada do Teixeira, loin de la voiture, et la récupérez des heures plus tard. Une journée coûte 20 € dans le parking du haut et 5 € dans celui du bas, soit 15 € de moins par voiture. Le parking du haut atteint son plafond de 20 € au bout d'environ cinq heures et demie, celui du bas son plafond de 5 € au bout d'environ trois heures.",
     "<ul><li><b>PR1 en entier (Areeiro → Pico Ruivo → Achada) :</b> le parking du bas, ou laissez la voiture à Achada do Teixeira (voir plus bas).</li>"
     "<li><b>Lever du soleil seul, ou aller-retour jusqu'à Pedra Rija :</b> vous revenez en quelques heures, donc le parking du haut ne coûte que quelques euros de plus et évite la montée.</li></ul>"], True),
   ("Comment aller du parking du bas au sommet ?", [
     "À pied par la route d'accès, ou avec la navette des Horários do Funchal. Son arrêt Parque Pico do Areeiro est au parking du bas, et elle monte au rond-point du radar toutes les 15 minutes, de 06:40 à 12:15 et de 14:10 à 19:00 (dernier départ à 18:00 à partir du 25 octobre, avec l'horaire d'hiver). Elle coûte 1,20 € le trajet, payé à bord, et ne part qu'avec au moins 4 passagers.",
     "Le premier départ est à 06:40, trop juste pour le lever du soleil en juin et juillet. Le " + a(L("fr", "/pr1-sunrise-transport/"), "guide des transports pour le lever du soleil") + " donne les horaires."], True),
   ("Peut-on éviter de payer une journée entière à l'Areeiro ?", [
     "Oui : garez-vous là où vous terminez. Laissez la voiture à Achada do Teixeira, où finit le PR1 (nous n'y avons trouvé aucun tarif officiel de stationnement), et prenez un taxi jusqu'au Pico do Arieiro pour votre créneau : Táxis Santana, +351 291 572 540, est la station la plus proche. En redescendant, la voiture vous attend. Sans voiture, le bus des Horários do Funchal arrive au sommet à 06:45 et 14:15, pour 3 €.",
     "Toutes les façons de revenir d'Achada sont dans " + a(L("fr", "/getting-back.html"), "revenir du PR1") + "."], True),
   ("Pourquoi est-il si difficile de se garer au Pico do Arieiro le matin ?", [
     "Les deux parkings sont pleins avant le lever du soleil. Les voitures se garent alors le long de la route d'accès, et les années passées des autocars et même des véhicules de secours ont été bloqués dans les virages. Ne vous garez pas sur les lignes jaunes des virages, où les voitures peuvent être remorquées, ni sur la route de la station radar : en 2022, une quinzaine de places y ont été réservées aux autocars, minibus de tourisme et taxis. Arrivez au moins une heure avant le lever du soleil, ou en milieu de matinée, une fois la foule du lever du soleil partie.",
     "Le sommet est-il dégagé en ce moment ? " + a(L("fr", "/pico-do-areeiro-weather/"), "Pico do Arieiro maintenant : webcams et météo") + "."], True),
   ("Annoncé, non confirmé", [
     "<ul><li><b>Un nouveau parking d'environ 300 places</b> près de la Casa das Sorveiras, entre Poiso et le sommet : l'appel d'offres était prévu début 2025. Nous n'avons trouvé aucun article indiquant qu'il a été construit.</li>"
     "<li><b>Des panneaux électroniques pour contrôler l'accès en voiture</b> au sommet ont été annoncés en 2024. Nous n'avons trouvé aucun article indiquant qu'ils fonctionnent.</li>"
     "<li><b>Écarter les voitures de location du sommet</b> était à l'étude en octobre 2024. Nous n'avons trouvé aucune décision.</li></ul>"], False),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Pico do Arieiro Parken 2026: Preise und welcher Parkplatz",
  desc="Parken am Pico do Arieiro: oben 4 €/h, höchstens 20 € am Tag, unten 2 €/h, höchstens 5 €. Ganzer PR1? Welcher Parkplatz passt und wie Sie sparen.",
  h1="Parken am Pico do Arieiro: Preise, welcher Parkplatz für den PR1 und der Andrang am Morgen",
  sub="Die beiden IFCN-Parkplätze am Gipfel, die offiziellen Preise 2026 und was sie bedeuten, wenn das Auto den ganzen Tag dort steht.",
  body=[
   ("Was kostet das Parken am Pico do Arieiro?", [
     "Es gibt zwei IFCN-Parkplätze, beide mit Parkautomat. Der obere Parkplatz am Aussichtspunkt, beim Café und Laden, kostet 4 € pro Stunde, höchstens 20 € am Tag. Der untere Parkplatz an der Zufahrtsstraße unterhalb des Gipfels kostet 2 € pro Stunde, höchstens 5 € am Tag. Auf beiden sind die ersten 30 Minuten frei, und Sie können stundenweise oder für den ganzen Tag zahlen.",
     table(["Parkplatz", "Pro Stunde", "Erste 30 Minuten", "Tageshöchstbetrag"],
           [["Oben (Miradouro do Pico do Areeiro)", "4,00 €", "frei", "20 €"], ["Unten (an der Zufahrtsstraße)", "2,00 €", "frei", "5 €"]]),
     "Die Preise stehen in der Portaria 48/2026 (Anhang II, Punkt 6), die schon die nächsten Jahre festlegt: oben 4,25 € pro Stunde 2027, 4,50 € 2028 und 5,00 € 2029; unten 2,25 €, 2,35 € und 2,50 €."], True),
   ("Zahlen Einheimische für das Parken am Pico do Arieiro?", [
     "Ja. Die Befreiung für Einwohner in der Portaria 48/2026 gilt für die Weggebühren und vier IFCN-Besuche (Casa das Tradições Madeirenses, Botanischer Garten, Quinta do Santo da Serra und die Fischzucht in Ribeiro Frio), nicht für die Parkplätze. Besucher und Madeirer zahlen gleichermaßen."], True),
   ("Welchen Parkplatz nehme ich für den ganzen PR1?", [
     "Den unteren, oder gar keinen. Der PR1 geht nur in eine Richtung: Sie kommen in Achada do Teixeira an, weit vom Auto, und holen es Stunden später. Ein ganzer Tag kostet oben 20 € und unten 5 €, also 15 € weniger pro Auto. Oben ist der Höchstbetrag von 20 € nach etwa fünfeinhalb Stunden erreicht, unten der von 5 € nach etwa drei.",
     "<ul><li><b>Ganzer PR1 (Areeiro → Pico Ruivo → Achada):</b> der untere Parkplatz, oder lassen Sie das Auto in Achada do Teixeira (siehe unten).</li>"
     "<li><b>Nur Sonnenaufgang, oder hin und zurück bis Pedra Rija:</b> Sie sind nach ein paar Stunden zurück, oben kostet es also nur ein paar Euro mehr und erspart den Aufstieg.</li></ul>"], True),
   ("Wie komme ich vom unteren Parkplatz zum Gipfel?", [
     "Zu Fuß über die Zufahrtsstraße, oder mit dem Shuttle von Horários do Funchal. Seine Haltestelle Parque Pico do Areeiro liegt am unteren Parkplatz, und er fährt alle 15 Minuten zum Kreisverkehr am Radar oben, 06:40–12:15 und 14:10–19:00 (letzte Fahrt 18:00 ab 25. Oktober, mit dem Winterfahrplan). Die Fahrt kostet 1,20 €, zahlbar im Bus, und er fährt erst ab 4 Fahrgästen.",
     "Die erste Fahrt ist um 06:40, zu knapp für den Sonnenaufgang im Juni und Juli. Die Zeiten stehen im " + a(L("de", "/pr1-sunrise-transport/"), "Ratgeber zur Anreise zum Sonnenaufgang") + "."], True),
   ("Kann ich vermeiden, am Areeiro einen ganzen Tag zu zahlen?", [
     "Ja: Parken Sie dort, wo Sie ankommen. Lassen Sie das Auto in Achada do Teixeira, wo der PR1 endet (eine offizielle Parkgebühr haben wir dort nicht gefunden), und fahren Sie mit dem Taxi zum Pico do Arieiro zu Ihrem Slot: Táxis Santana, +351 291 572 540, ist der nächste Taxistand. Wenn Sie herunterkommen, wartet das Auto. Ohne Auto erreicht der Bus von Horários do Funchal den Gipfel um 06:45 und 14:15, für 3 €.",
     "Alle Wege zurück aus Achada stehen unter " + a(L("de", "/getting-back.html"), "Rückweg vom PR1") + "."], True),
   ("Warum ist Parken am Pico do Arieiro morgens so schwierig?", [
     "Beide Parkplätze sind vor Sonnenaufgang voll. Dann parken Autos entlang der Zufahrtsstraße, und in den vergangenen Jahren blieben Reisebusse und sogar Rettungsfahrzeuge in den Kurven stecken. Parken Sie nicht auf den gelben Linien in den Kurven, wo abgeschleppt werden kann, und nicht an der Straße zur Radarstation: Dort wurden 2022 etwa 15 Plätze für Reisebusse, Kleinbusse und Taxis reserviert. Kommen Sie mindestens eine Stunde vor Sonnenaufgang, oder am Vormittag, wenn die Sonnenaufgangsbesucher weg sind.",
     "Ist der Gipfel gerade klar? " + a(L("de", "/pico-do-areeiro-weather/"), "Pico do Arieiro jetzt: Webcams und Wetter") + "."], True),
   ("Angekündigt, nicht bestätigt", [
     "<ul><li><b>Ein neuer Parkplatz mit etwa 300 Plätzen</b> bei der Casa das Sorveiras, zwischen Poiso und Gipfel: Die Ausschreibung war für Anfang 2025 geplant. Einen Bericht, dass er gebaut wurde, haben wir nicht gefunden.</li>"
     "<li><b>Elektronische Anzeigen zur Steuerung der Zufahrt</b> zum Gipfel wurden 2024 angekündigt. Einen Bericht, dass sie in Betrieb sind, haben wir nicht gefunden.</li>"
     "<li><b>Mietwagen vom Gipfel fernzuhalten</b> wurde im Oktober 2024 erwogen. Eine Entscheidung haben wir nicht gefunden.</li></ul>"], False),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Parking na Pico do Arieiro 2026: ceny i który parking",
  desc="Parking na Pico do Arieiro: na górze 4 €/godz., do 20 € dziennie, na dole 2 €/godz., do 5 €. Cały PR1? Który parking wybrać i jak zaoszczędzić.",
  h1="Parking na Pico do Arieiro: ceny, który parking na PR1 i poranny tłok",
  sub="Dwa parkingi IFCN na szczycie, oficjalne ceny na 2026 i co oznaczają, gdy auto stoi tam cały dzień.",
  body=[
   ("Ile kosztuje parking na Pico do Arieiro?", [
     "Są dwa parkingi IFCN, oba z parkomatami. Górny parking przy punkcie widokowym, kawiarni i sklepie kosztuje 4 € za godzinę, maksymalnie 20 € dziennie. Dolny parking, przy drodze dojazdowej poniżej szczytu, kosztuje 2 € za godzinę, maksymalnie 5 € dziennie. Na obu pierwsze 30 minut jest gratis, a zapłacić można za godzinę lub za cały dzień.",
     table(["Parking", "Za godzinę", "Pierwsze 30 minut", "Maksymalnie dziennie"],
           [["Górny (Miradouro do Pico do Areeiro)", "4,00 €", "gratis", "20 €"], ["Dolny (przy drodze dojazdowej)", "2,00 €", "gratis", "5 €"]]),
     "Ceny ustala Portaria 48/2026 (załącznik II, punkt 6), która określa już kolejne lata: górny parking 4,25 € za godzinę w 2027, 4,50 € w 2028 i 5,00 € w 2029; dolny 2,25 €, 2,35 € i 2,50 €."], True),
   ("Czy mieszkańcy płacą za parking na Pico do Arieiro?", [
     "Tak. Zwolnienie mieszkańców w Portaria 48/2026 obejmuje opłaty za szlaki i cztery wizyty IFCN (Casa das Tradições Madeirenses, ogród botaniczny, Quinta do Santo da Serra i hodowlę ryb w Ribeiro Frio), a nie parkingi. Za parking płacą i turyści, i Maderczycy."], True),
   ("Który parking wybrać na cały PR1?", [
     "Dolny albo żaden. PR1 jest jednokierunkowy: kończysz w Achada do Teixeira, daleko od auta, i wracasz po nie po wielu godzinach. Cały dzień kosztuje 20 € na górnym parkingu i 5 € na dolnym, czyli 15 € mniej za auto. Górny parking osiąga limit 20 € po około pięciu i pół godzinach, dolny limit 5 € po około trzech.",
     "<ul><li><b>Cały PR1 (Areeiro → Pico Ruivo → Achada):</b> dolny parking albo zostaw auto w Achada do Teixeira (niżej).</li>"
     "<li><b>Tylko wschód słońca albo tam i z powrotem do Pedra Rija:</b> wracasz po kilku godzinach, więc górny parking kosztuje tylko kilka euro więcej i oszczędza podejście.</li></ul>"], True),
   ("Jak dostać się z dolnego parkingu na szczyt?", [
     "Pieszo drogą dojazdową albo busem wahadłowym Horários do Funchal. Jego przystanek Parque Pico do Areeiro jest przy dolnym parkingu, a bus jeździ na rondo przy radarze na szczycie co 15 minut, 06:40–12:15 i 14:10–19:00 (ostatni kurs o 18:00 od 25 października, w rozkładzie zimowym). Kosztuje 1,20 € za kurs, płatne w busie, i rusza dopiero z co najmniej 4 pasażerami.",
     "Pierwszy kurs jest o 06:40, za późno na wschód słońca w czerwcu i lipcu. Godziny są w " + a(L("pl", "/pr1-sunrise-transport/"), "przewodniku dojazdu na wschód słońca") + "."], True),
   ("Czy da się nie płacić za cały dzień na Areeiro?", [
     "Tak: zaparkuj tam, gdzie kończysz. Zostaw auto w Achada do Teixeira, gdzie kończy się PR1 (nie znaleźliśmy tam oficjalnej opłaty za parking), i podjedź taksówką na Pico do Arieiro na swój slot: najbliższy postój to Táxis Santana, +351 291 572 540. Gdy zejdziesz, auto na Ciebie czeka. Bez auta autobus Horários do Funchal dojeżdża na szczyt o 06:45 i 14:15, za 3 €.",
     "Wszystkie sposoby powrotu z Achada są w " + a(L("pl", "/getting-back.html"), "powrocie z PR1") + "."], True),
   ("Dlaczego rano tak trudno zaparkować na Pico do Arieiro?", [
     "Oba parkingi zapełniają się przed wschodem słońca. Auta stają wtedy wzdłuż drogi dojazdowej, a w poprzednich latach autokary, a nawet pojazdy ratunkowe utykały na zakrętach. Nie parkuj na żółtych liniach na zakrętach, gdzie auta mogą zostać odholowane, ani na drodze do stacji radarowej: w 2022 około 15 miejsc zarezerwowano tam dla autokarów, busów turystycznych i taksówek. Przyjedź co najmniej godzinę przed wschodem słońca albo w połowie poranka, gdy tłum od wschodu słońca już odjedzie.",
     "Czy szczyt jest teraz odsłonięty? " + a(L("pl", "/pico-do-areeiro-weather/"), "Pico do Arieiro teraz: kamery i pogoda") + "."], True),
   ("Zapowiedziane, niepotwierdzone", [
     "<ul><li><b>Nowy parking na około 300 miejsc</b> przy Casa das Sorveiras, między Poiso a szczytem: przetarg miał ruszyć na początku 2025. Nie znaleźliśmy informacji, że go zbudowano.</li>"
     "<li><b>Elektroniczne tablice do kontroli wjazdu</b> na szczyt zapowiedziano w 2024. Nie znaleźliśmy informacji, że działają.</li>"
     "<li><b>Ograniczenie wjazdu aut z wypożyczalni na szczyt</b> rozważano w październiku 2024. Nie znaleźliśmy decyzji.</li></ul>"], False),
   ("Źródła", [None], False),
  ]),
}


def main():
    gi.build_qa(SLUG, COPY, src, "2026-10-14T12:00+01:00")


if __name__ == "__main__":
    main()
