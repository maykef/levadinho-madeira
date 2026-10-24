#!/usr/bin/env python3
"""Writes /areeiro-pedra-rija/ × 5 languages from the free-walks page shell (owner, 2026-10-21).

What it says, and where from:
  ticket         SIMplifica's own product text ("PR 1 … bidirecional entre o Pico do Areeiro e o Miradouro da Pedra
                 Rija, ao km 1,2. Não permite aceder ao Pico Ruivo", €4.50; operator €3; exemptions) and FAQ 5.7/5.8
                 (no upgrade, no refund); Portaria 801/2025 for the rates; seo_research/facts/simplifica_howto.md,
                 permit_fees.md.
  two-way rule   IFCN warnings list (one-way between the Pedra Rija viewpoint and Pico Ruivo); Sep 2026 works closed
                 only Pedra Rija → Ruivo while Areeiro ↔ Pedra Rija stayed open (bot/pr1_facts.md, IFCN AVISOS).
  bus            Horários do Funchal "Pico do Areeiro" page: up 06:00/13:30 (summit 06:45/14:15), down 12:15 and
                 18:00 (winter timetable to 27 Mar 2027; 19:00 in summer), €3 on board, 31 seats, phone reservation 291 705 555
                 (seo_research/facts/pr1_transport.md, scraped 2026-09-30).
  parking        Portaria 48/2026 Annex II point 6 (upper €4/h max €20/day) — the full page is /pico-do-areeiro-parking/.
  taxi fares     owner first-hand, 2026-10-21, INDICATIVE: ~€80 Funchal round trip with waiting; ~€35-40 one way down.
                 Agree the price / call for a quote. No companies named (taxi ranks only, as site-wide).
  no duration    the walking time for the 1.2 km is deliberately not stated (no source yet); Ninho da Manta is not
                 named (unconfirmed whether it sits before or after the km 1.2 gate).

Re-run after changing the copy: it keeps dateModified, then runs gen_site_nav.py, gen_cta.py, gen_owner.py and
gen_schema.py itself (the page is in GUIDES / TAGS). The STATIC-STATUS:PR1 span is prefilled and refreshed daily
by the updater.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "areeiro-pedra-rija"
ROOT = gi.ROOT
SIMP = "https://simplifica.madeira.gov.pt/services/78-82-259"
IFCN_FAQ = "https://ifcn.madeira.gov.pt/en/atividades-de-natureza/percursos-pedestres-recomendados/faq-s-taxas-percursos-pedestres-classificados/frequently-asked-questions-fees-classified-walking-routes.html"
IFCN_AVISOS = "https://ifcn.madeira.gov.pt/pt/?view=article&id=627:percursos-pedestres-avisos&catid=146:avisos"
P801 = "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Portarias/ISerie-218-Portaria-Taxas.pdf"
P48 = "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Portarias/Port48ISerie027_2026.pdf"
HF = "https://www.horariosdofunchal.pt/index.php/viajar/pico-do-areeiro"
a, ext = gi.a, gi.ext

# the updater's own PR1 line per language (refreshed daily between the markers)
STATUS = {
 "en": "Official IFCN list: Pico do Areeiro ↔ Pedra Rija viewpoint: both ways. Full trail to Pico Ruivo: one way only, ending at Achada do Teixeira.",
 "pt": "Lista oficial do IFCN: Pico do Areeiro ↔ Miradouro da Pedra Rija: nos dois sentidos. Percurso completo até ao Pico Ruivo: só num sentido, a terminar na Achada do Teixeira.",
 "fr": "Liste officielle de l'IFCN : Pico do Areeiro ↔ belvédère de Pedra Rija : dans les deux sens. Parcours complet jusqu'au Pico Ruivo : sens unique, arrivée à Achada do Teixeira.",
 "de": "Offizielle IFCN-Liste: Pico do Areeiro ↔ Aussichtspunkt Pedra Rija: in beide Richtungen. Ganze Strecke bis zum Pico Ruivo: nur in eine Richtung, Ende in Achada do Teixeira.",
 "pl": "Oficjalna lista IFCN: Pico do Areeiro ↔ punkt widokowy Pedra Rija: w obie strony. Cała trasa na Pico Ruivo: tylko w jedną stronę, z końcem w Achada do Teixeira.",
}


def status_span(lang):
    return ('<span class="static-status"><!-- STATIC-STATUS:PR1:START -->' + STATUS[lang]
            + "<!-- STATIC-STATUS:PR1:END --></span>")


def src(lang):
    return ('<p class="src">' + ext(SIMP, "SIMplifica") + " · " + ext(IFCN_FAQ, "IFCN FAQ 5.7–5.8") + " · "
            + ext(IFCN_AVISOS, "IFCN avisos") + " · " + ext(P801, "Portaria 801/2025") + " · "
            + ext(P48, "Portaria 48/2026") + " · " + ext(HF, "Horários do Funchal") + "</p>")


def table(head, rows):
    return ('<div class="tbl"><table>\n    <thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead>\n    <tbody>\n"
            + "".join("      <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n" for r in rows) + "    </tbody>\n  </table></div>")


def L(lang, path):
    return f"{PREFIX[lang]}{path}"


# Sections: (heading, parts, is_question). A question's FAQ answer is its first paragraph, verbatim.
COPY = {
 "en": dict(
  title="Short walk at Pico do Areeiro: PR1 to Pedra Rija, €4.50",
  desc="Walk PR1 from Pico do Areeiro to the Pedra Rija viewpoint and back: €4.50 ticket, 1.2 km each way, the only two-way part of PR1. Book it right.",
  h1="The short PR1 walk: Pico do Areeiro to Pedra Rija",
  sub="You don't need the full PR1 to stand above the clouds: the first 1.2 km to the Miradouro da Pedra Rija has its own €4.50 ticket — and it's two-way.",
  body=[
   ("Can I walk part of PR1 without booking the whole trail?", [
     "Yes. SIMplifica sells a separate ticket for the first stretch of PR1: Pico do Areeiro to the Miradouro da Pedra Rija at km 1.2, and back the same way, for €4.50 (€3 through a licensed operator). Under-12s, Madeira residents and people with a 60%+ disability are exempt, but must still be on the booking. It is the only part of PR1 you may walk in both directions.",
     status_span("en"),
     "How to book it, step by step: " + a(L("en", "/simplifica-booking/"), "SIMplifica booking guide") + "."], True),
   ("How far is the walk to Pedra Rija?", [
     "1.2 km each way on the stepped crest path from the Areeiro summit — about 2.4 km in total. You walk the open ridge with the central peaks on both sides and turn around at the Pedra Rija viewpoint. It is high mountain at around 1,800 m: cold wind, sudden cloud and strong sun at any time of year, so bring a warm layer whatever the forecast in Funchal says.",
     "Is the summit clear right now? " + a(L("en", "/pico-do-areeiro-weather/"), "Pico do Areeiro now: webcams and weather") + "."], True),
   ("Can I continue to Pico Ruivo on the €4.50 ticket?", [
     "No. The €4.50 ticket ends at the Pedra Rija viewpoint, and SIMplifica's FAQ is explicit: there is no upgrade on the trail and no refund. To walk the full PR1 to Pico Ruivo you need the €10.50 full-route ticket, and the full route must be started at Pico do Areeiro. The two products sit side by side on SIMplifica, and buying the wrong one is the most common PR1 booking mistake."], True),
   ("Why can I walk back, when the rest of PR1 is one-way?", [
     "Because the one-way rule begins at Pedra Rija. From there to Pico Ruivo the trail runs one way only, and walkers finish at Achada do Teixeira, far from Areeiro. The first stretch is kept two-way precisely so the short ticket works: you return to your car, taxi or bus at the summit. When IFCN closed the Pedra Rija → Pico Ruivo section for works in September 2026, this stretch stayed open both ways.",
     "The full one-way story: " + a(L("en", "/pr1-one-way/"), "is PR1 one-way?") + "."], True),
   ("How do I get to Pico do Areeiro without renting a car?", [
     "Please don't drive up: parking at the summit is very limited (€4 an hour in the upper car park, and it fills early), and circling for a space can eat your morning. A taxi from Funchal costs around €80 for the whole round trip with the driver waiting while you walk — the price is indicative, so agree it or call for a quote before you get in.",
     "The cheap way is Horários do Funchal's \"Pico do Areeiro\" bus: every day except 25 December, €3 a trip, paid on board (31 seats; seat reservation by phone, +351 291 705 555, from 7 to 2 working days ahead). Morning run: up at 06:00 from the Teleférico terminus, at the summit 06:45 — before sunrise all year; back down at 12:15. Afternoon run, the natural fit for this walk: up at 13:30, at the summit 14:15; last bus down at 18:00. <b>If you miss the last bus there is no other</b> — only a taxi called to the summit. On a tight day, take the taxi.",
     "On a tight budget? Go up on the bus and book a taxi to pick you up: €35–40 to come down to Funchal (indicative). The maths for two people:",
     table(["For two people", "Bus up + taxi down", "Taxi round trip"],
           [["Trail tickets (2 × €4.50)", "€9", "€9"], ["Bus up (2 × €3)", "€6", "—"],
            ["Taxi", "€35–40 (the car, one way)", "~€80 (waiting included)"],
            ["<b>Total for two</b>", "<b>€50–55 (≈€25–28 each)</b>", "<b>~€89 (≈€45 each)</b>"]]),
     "Parking rates and the morning rush: " + a(L("en", "/pico-do-areeiro-parking/"), "Pico do Areeiro parking") + ". All summit transport: " + a(L("en", "/pr1-sunrise-transport/"), "getting to Areeiro") + "."], True),
   ("How much does it cost for four people?", [
     "About €24.50 each, door to door. A taxi costs the same with one person or four, so the biggest saving on this trip is simply filling the cab: pair up with another couple — your table neighbours from the ship, people at your hotel — and the ~€80 round trip becomes about €20 each, plus the €4.50 ticket. For cruise passengers this is the realistic way to touch PR1 and be back aboard within half a day, on your own schedule, with no last-bus anxiety.",
     table(["For four people", "Per person"],
           [["Taxi round trip, waiting included (~€80 ÷ 4)", "~€20"], ["Trail ticket", "€4.50"],
            ["<b>Total</b>", "<b>~€24.50</b>"]]),
     "Only a day on the island? " + a(L("en", "/one-day-in-madeira/"), "one day in Madeira") + " · " + a(L("en", "/madeira-cruise-port/"), "from the cruise port") + "."], True),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="PR1 curto: Pico do Areeiro até à Pedra Rija, 4,50 €",
  desc="PR1 do Pico do Areeiro ao Miradouro da Pedra Rija e volta: bilhete de 4,50 €, 1,2 km por sentido, o único troço nos dois sentidos. Como reservar bem.",
  h1="O PR1 curto: do Pico do Areeiro à Pedra Rija",
  sub="Não precisa do PR1 completo para ficar acima das nuvens: os primeiros 1,2 km até ao Miradouro da Pedra Rija têm bilhete próprio de 4,50 € — e são nos dois sentidos.",
  body=[
   ("Posso fazer parte do PR1 sem reservar o percurso completo?", [
     "Sim. O SIMplifica vende um bilhete separado para o primeiro troço do PR1: do Pico do Areeiro ao Miradouro da Pedra Rija, ao km 1,2, e volta pelo mesmo caminho, por 4,50 € (3 € através de operador licenciado). Menores de 12 anos, residentes na Madeira e pessoas com incapacidade igual ou superior a 60% estão isentos, mas têm de constar da reserva. É o único troço do PR1 que pode percorrer nos dois sentidos.",
     status_span("pt"),
     "Como reservar, passo a passo: " + a(L("pt", "/simplifica-booking/"), "guia de reserva no SIMplifica") + "."], True),
   ("Qual é a distância até à Pedra Rija?", [
     "1,2 km por sentido, pelo caminho em escadaria na crista a partir do cume do Areeiro — cerca de 2,4 km no total. Caminha pela cumeada aberta, com os picos centrais dos dois lados, e dá a volta no Miradouro da Pedra Rija. É alta montanha, a cerca de 1.800 m: vento frio, nuvens repentinas e sol forte em qualquer altura do ano, por isso leve um agasalho diga o que disser a previsão no Funchal.",
     "O cume está limpo agora? " + a(L("pt", "/pico-do-areeiro-weather/"), "Pico do Areeiro agora: webcams e tempo") + "."], True),
   ("Posso continuar até ao Pico Ruivo com o bilhete de 4,50 €?", [
     "Não. O bilhete de 4,50 € termina no Miradouro da Pedra Rija, e as FAQ do SIMplifica são explícitas: não há upgrade no percurso nem reembolso. Para fazer o PR1 completo até ao Pico Ruivo precisa do bilhete de 10,50 € do percurso completo, que tem de ser iniciado no Pico do Areeiro. Os dois produtos aparecem lado a lado no SIMplifica, e comprar o errado é o engano mais comum nas reservas do PR1."], True),
   ("Porque posso voltar para trás, se o resto do PR1 é em sentido único?", [
     "Porque a regra do sentido único começa na Pedra Rija. Daí até ao Pico Ruivo o percurso é só num sentido, e termina-se na Achada do Teixeira, longe do Areeiro. O primeiro troço mantém-se nos dois sentidos precisamente para o bilhete curto funcionar: regressa ao carro, ao táxi ou ao autocarro no cume. Quando o IFCN fechou o troço Pedra Rija → Pico Ruivo para obras, em setembro de 2026, este troço manteve-se aberto nos dois sentidos.",
     "A história completa do sentido único: " + a(L("pt", "/pr1-one-way/"), "o PR1 é em sentido único?") + "."], True),
   ("Como chego ao Pico do Areeiro sem alugar carro?", [
     "Por favor, não suba de carro: o estacionamento no cume é muito limitado (4 € por hora no parque de cima, que enche cedo) e andar às voltas à procura de lugar pode consumir a manhã. Um táxi do Funchal custa cerca de 80 € pela viagem completa de ida e volta, com o motorista à espera enquanto caminha — o preço é indicativo: combine-o ou peça orçamento antes de entrar.",
     "A opção barata é o autocarro \"Pico do Areeiro\" dos Horários do Funchal: todos os dias exceto 25 de dezembro, 3 € por viagem, pagos a bordo (31 lugares; reserva por telefone, +351 291 705 555, de 7 a 2 dias úteis antes). De manhã: sobe às 06:00 do terminal do Teleférico, chega ao cume às 06:45 — antes do nascer do sol todo o ano; desce às 12:15. De tarde, o encaixe natural para este passeio: sobe às 13:30, chega às 14:15; último autocarro para baixo às 18:00. <b>Se perder o último autocarro, não há outro</b> — só um táxi chamado ao cume. Num dia apertado, vá de táxi.",
     "Orçamento curto? Suba de autocarro e marque um táxi para o vir buscar: 35–40 € para descer até ao Funchal (indicativo). As contas para duas pessoas:",
     table(["Para duas pessoas", "Autocarro + táxi na descida", "Táxi ida e volta"],
           [["Bilhetes do percurso (2 × 4,50 €)", "9 €", "9 €"], ["Autocarro na subida (2 × 3 €)", "6 €", "—"],
            ["Táxi", "35–40 € (o carro, só descida)", "~80 € (espera incluída)"],
            ["<b>Total para dois</b>", "<b>50–55 € (≈25–28 € cada)</b>", "<b>~89 € (≈45 € cada)</b>"]]),
     "Preços do estacionamento e a confusão da manhã: " + a(L("pt", "/pico-do-areeiro-parking/"), "estacionamento no Pico do Areeiro") + ". Todo o transporte para o cume: " + a(L("pt", "/pr1-sunrise-transport/"), "chegar ao Areeiro") + "."], True),
   ("Quanto custa para quatro pessoas?", [
     "Cerca de 24,50 € por pessoa, porta a porta. O táxi custa o mesmo com uma pessoa ou com quatro, por isso a maior poupança desta viagem é simplesmente encher o carro: junte-se a outro casal — os vizinhos de mesa do navio, pessoas do hotel — e os ~80 € de ida e volta passam a cerca de 20 € por cabeça, mais o bilhete de 4,50 €. Para passageiros de cruzeiro é a forma realista de tocar no PR1 e estar de volta a bordo em meio dia, ao seu ritmo e sem a ansiedade do último autocarro.",
     table(["Para quatro pessoas", "Por pessoa"],
           [["Táxi ida e volta, espera incluída (~80 € ÷ 4)", "~20 €"], ["Bilhete do percurso", "4,50 €"],
            ["<b>Total</b>", "<b>~24,50 €</b>"]]),
     "Só um dia na ilha? " + a(L("pt", "/one-day-in-madeira/"), "um dia na Madeira") + " · " + a(L("pt", "/madeira-cruise-port/"), "a partir do porto de cruzeiros") + "."], True),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Balade courte au Pico do Arieiro : PR1 à Pedra Rija, 4,50 €",
  desc="Le PR1 du Pico do Arieiro au belvédère de Pedra Rija et retour : billet à 4,50 €, 1,2 km par sens, seul tronçon à double sens. Réservez le bon billet.",
  h1="Le PR1 court : du Pico do Arieiro à Pedra Rija",
  sub="Pas besoin du PR1 entier pour être au-dessus des nuages : les premiers 1,2 km jusqu'au belvédère de Pedra Rija ont leur propre billet à 4,50 € — et le tronçon est à double sens.",
  body=[
   ("Peut-on faire une partie du PR1 sans réserver tout le sentier ?", [
     "Oui. SIMplifica vend un billet séparé pour le premier tronçon du PR1 : du Pico do Arieiro au belvédère de Pedra Rija, au km 1,2, et retour par le même chemin, pour 4,50 € (3 € via un opérateur agréé). Les moins de 12 ans, les résidents de Madère et les personnes avec un handicap d'au moins 60 % sont exonérés, mais doivent figurer sur la réservation. C'est le seul tronçon du PR1 praticable dans les deux sens.",
     status_span("fr"),
     "Comment réserver, pas à pas : " + a(L("fr", "/simplifica-booking/"), "guide de réservation SIMplifica") + "."], True),
   ("Quelle distance jusqu'à Pedra Rija ?", [
     "1,2 km par sens, sur le sentier en escaliers de la crête depuis le sommet de l'Arieiro — environ 2,4 km en tout. Vous marchez sur la crête ouverte, les pics centraux des deux côtés, et faites demi-tour au belvédère de Pedra Rija. C'est de la haute montagne, vers 1 800 m : vent froid, nuages soudains et soleil fort en toute saison, alors prenez une couche chaude quoi que dise la météo à Funchal.",
     "Le sommet est-il dégagé en ce moment ? " + a(L("fr", "/pico-do-areeiro-weather/"), "Pico do Arieiro maintenant : webcams et météo") + "."], True),
   ("Peut-on continuer jusqu'au Pico Ruivo avec le billet à 4,50 € ?", [
     "Non. Le billet à 4,50 € s'arrête au belvédère de Pedra Rija, et la FAQ de SIMplifica est explicite : pas de surclassement sur le sentier, pas de remboursement. Pour faire le PR1 entier jusqu'au Pico Ruivo, il faut le billet à 10,50 € du parcours complet, qui doit être commencé au Pico do Arieiro. Les deux produits sont côte à côte sur SIMplifica, et acheter le mauvais est l'erreur de réservation la plus courante du PR1."], True),
   ("Pourquoi peut-on revenir sur ses pas, alors que le reste du PR1 est à sens unique ?", [
     "Parce que la règle du sens unique commence à Pedra Rija. De là au Pico Ruivo, le sentier est à sens unique, et on termine à Achada do Teixeira, loin de l'Arieiro. Le premier tronçon reste à double sens précisément pour que le billet court fonctionne : vous retrouvez votre voiture, votre taxi ou votre bus au sommet. Quand l'IFCN a fermé le tronçon Pedra Rija → Pico Ruivo pour travaux, en septembre 2026, ce tronçon est resté ouvert dans les deux sens.",
     "Toute l'histoire du sens unique : " + a(L("fr", "/pr1-one-way/"), "le PR1 est-il à sens unique ?") + "."], True),
   ("Comment aller au Pico do Arieiro sans louer de voiture ?", [
     "Ne montez pas en voiture : le parking au sommet est très limité (4 € de l'heure au parking du haut, qui se remplit tôt), et tourner pour trouver une place peut manger la matinée. Un taxi depuis Funchal coûte environ 80 € pour l'aller-retour complet, chauffeur en attente pendant la balade — prix indicatif : convenez-en ou demandez un devis avant de monter.",
     "L'option économique est le bus « Pico do Areeiro » des Horários do Funchal : tous les jours sauf le 25 décembre, 3 € le trajet, payés à bord (31 places ; réservation par téléphone, +351 291 705 555, de 7 à 2 jours ouvrés avant). Le matin : départ 06:00 du terminus du Teleférico, au sommet à 06:45 — avant le lever du soleil toute l'année ; descente à 12:15. L'après-midi, le créneau naturel pour cette balade : montée à 13:30, au sommet à 14:15 ; dernier bus de descente à 18:00. <b>Si vous ratez le dernier bus, il n'y en a pas d'autre</b> — seulement un taxi appelé au sommet. Journée serrée : prenez le taxi.",
     "Petit budget ? Montez en bus et réservez un taxi pour venir vous chercher : 35–40 € pour redescendre à Funchal (indicatif). Le calcul pour deux :",
     table(["Pour deux personnes", "Bus + taxi à la descente", "Taxi aller-retour"],
           [["Billets du sentier (2 × 4,50 €)", "9 €", "9 €"], ["Bus à la montée (2 × 3 €)", "6 €", "—"],
            ["Taxi", "35–40 € (la voiture, descente seule)", "~80 € (attente comprise)"],
            ["<b>Total pour deux</b>", "<b>50–55 € (≈25–28 € chacun)</b>", "<b>~89 € (≈45 € chacun)</b>"]]),
     "Tarifs du parking et cohue du matin : " + a(L("fr", "/pico-do-areeiro-parking/"), "parking du Pico do Arieiro") + ". Tous les transports vers le sommet : " + a(L("fr", "/pr1-sunrise-transport/"), "aller à l'Arieiro") + "."], True),
   ("Combien ça coûte pour quatre personnes ?", [
     "Environ 24,50 € par personne, porte à porte. Un taxi coûte le même prix avec une personne ou quatre, donc la plus grosse économie de cette sortie est simplement de remplir la voiture : associez-vous à un autre couple — vos voisins de table du navire, des gens de l'hôtel — et les ~80 € d'aller-retour deviennent environ 20 € chacun, plus le billet à 4,50 €. Pour les croisiéristes, c'est la façon réaliste de goûter au PR1 et d'être de retour à bord en une demi-journée, à votre rythme, sans l'angoisse du dernier bus.",
     table(["Pour quatre personnes", "Par personne"],
           [["Taxi aller-retour, attente comprise (~80 € ÷ 4)", "~20 €"], ["Billet du sentier", "4,50 €"],
            ["<b>Total</b>", "<b>~24,50 €</b>"]]),
     "Une seule journée sur l'île ? " + a(L("fr", "/one-day-in-madeira/"), "Madère en un jour") + " · " + a(L("fr", "/madeira-cruise-port/"), "depuis le port de croisière") + "."], True),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Kurzer PR1 am Pico do Arieiro: bis Pedra Rija, 4,50 €",
  desc="PR1 vom Pico do Arieiro zum Aussichtspunkt Pedra Rija und zurück: Ticket 4,50 €, 1,2 km je Richtung, das einzige Stück in beide Richtungen. Richtig buchen.",
  h1="Der kurze PR1: vom Pico do Arieiro nach Pedra Rija",
  sub="Sie brauchen nicht den ganzen PR1, um über den Wolken zu stehen: die ersten 1,2 km zum Aussichtspunkt Pedra Rija haben ein eigenes Ticket für 4,50 € — und sind in beide Richtungen begehbar.",
  body=[
   ("Kann ich ein Stück des PR1 gehen, ohne den ganzen Weg zu buchen?", [
     "Ja. SIMplifica verkauft ein eigenes Ticket für das erste Stück des PR1: vom Pico do Arieiro zum Aussichtspunkt Pedra Rija bei km 1,2 und auf demselben Weg zurück, für 4,50 € (3 € über einen lizenzierten Anbieter). Kinder unter 12, Einwohner Madeiras und Menschen mit einer Behinderung ab 60 % sind befreit, müssen aber auf der Buchung stehen. Es ist das einzige Stück des PR1, das Sie in beide Richtungen gehen dürfen.",
     status_span("de"),
     "So buchen Sie es, Schritt für Schritt: " + a(L("de", "/simplifica-booking/"), "SIMplifica-Buchungsratgeber") + "."], True),
   ("Wie weit ist die Wanderung nach Pedra Rija?", [
     "1,2 km je Richtung auf dem Stufenweg über den Grat vom Areeiro-Gipfel — insgesamt etwa 2,4 km. Sie gehen über den offenen Grat, die zentralen Gipfel zu beiden Seiten, und kehren am Aussichtspunkt Pedra Rija um. Es ist Hochgebirge auf rund 1.800 m: kalter Wind, plötzliche Wolken und starke Sonne zu jeder Jahreszeit — nehmen Sie eine warme Schicht mit, egal was die Vorhersage für Funchal sagt.",
     "Ist der Gipfel gerade klar? " + a(L("de", "/pico-do-areeiro-weather/"), "Pico do Arieiro jetzt: Webcams und Wetter") + "."], True),
   ("Kann ich mit dem 4,50-€-Ticket bis zum Pico Ruivo weitergehen?", [
     "Nein. Das 4,50-€-Ticket endet am Aussichtspunkt Pedra Rija, und die FAQ von SIMplifica sind eindeutig: kein Upgrade auf dem Weg, keine Erstattung. Für den ganzen PR1 bis zum Pico Ruivo brauchen Sie das 10,50-€-Ticket der Gesamtstrecke, und die Gesamtstrecke muss am Pico do Arieiro begonnen werden. Die beiden Produkte stehen auf SIMplifica direkt nebeneinander — das falsche zu kaufen ist der häufigste Buchungsfehler beim PR1."], True),
   ("Warum darf ich zurückgehen, wenn der Rest des PR1 nur in eine Richtung geht?", [
     "Weil die Einbahnregel erst an der Pedra Rija beginnt. Von dort bis zum Pico Ruivo führt der Weg nur in eine Richtung, und man kommt in Achada do Teixeira an, weit vom Areeiro. Das erste Stück bleibt in beide Richtungen offen, genau damit das kurze Ticket funktioniert: Sie kehren zu Ihrem Auto, Taxi oder Bus am Gipfel zurück. Als das IFCN im September 2026 den Abschnitt Pedra Rija → Pico Ruivo für Arbeiten sperrte, blieb dieses Stück in beide Richtungen offen.",
     "Die ganze Einbahn-Geschichte: " + a(L("de", "/pr1-one-way/"), "ist der PR1 nur in eine Richtung begehbar?") + "."], True),
   ("Wie komme ich ohne Mietwagen zum Pico do Arieiro?", [
     "Bitte fahren Sie nicht selbst hinauf: Die Parkplätze am Gipfel sind sehr begrenzt (4 € pro Stunde oben, und es ist früh voll), und die Suche nach einer Lücke kann den Vormittag kosten. Ein Taxi ab Funchal kostet etwa 80 € für die ganze Hin- und Rückfahrt, mit wartendem Fahrer während der Wanderung — der Preis ist ein Richtwert: vereinbaren Sie ihn oder holen Sie vor dem Einsteigen ein Angebot ein.",
     "Die günstige Variante ist der Bus \"Pico do Areeiro\" von Horários do Funchal: täglich außer am 25. Dezember, 3 € pro Fahrt, zahlbar im Bus (31 Plätze; Platzreservierung telefonisch, +351 291 705 555, 7 bis 2 Werktage vorher). Morgens: Abfahrt 06:00 am Teleférico-Terminal, am Gipfel 06:45 — das ganze Jahr vor Sonnenaufgang; hinunter um 12:15. Nachmittags, die natürliche Wahl für diese Wanderung: hinauf 13:30, am Gipfel 14:15; letzter Bus hinunter um 18:00. <b>Wer den letzten Bus verpasst, hat keinen weiteren</b> — nur ein zum Gipfel gerufenes Taxi. An einem knappen Tag: nehmen Sie das Taxi.",
     "Kleines Budget? Mit dem Bus hinauf und ein Taxi zum Abholen bestellen: 35–40 € für die Fahrt hinunter nach Funchal (Richtwert). Die Rechnung für zwei:",
     table(["Für zwei Personen", "Bus hinauf + Taxi hinunter", "Taxi hin und zurück"],
           [["Wegtickets (2 × 4,50 €)", "9 €", "9 €"], ["Bus hinauf (2 × 3 €)", "6 €", "—"],
            ["Taxi", "35–40 € (das Auto, nur hinunter)", "~80 € (Warten inbegriffen)"],
            ["<b>Summe für zwei</b>", "<b>50–55 € (≈25–28 € pro Kopf)</b>", "<b>~89 € (≈45 € pro Kopf)</b>"]]),
     "Parkgebühren und der Andrang am Morgen: " + a(L("de", "/pico-do-areeiro-parking/"), "Parken am Pico do Arieiro") + ". Alle Wege zum Gipfel: " + a(L("de", "/pr1-sunrise-transport/"), "Anfahrt zum Areeiro") + "."], True),
   ("Was kostet es für vier Personen?", [
     "Etwa 24,50 € pro Person, von Tür zu Tür. Ein Taxi kostet mit einer Person dasselbe wie mit vier — die größte Ersparnis dieser Tour ist also schlicht, das Auto zu füllen: Tun Sie sich mit einem anderen Paar zusammen — den Tischnachbarn vom Schiff, Leuten aus dem Hotel — und aus den ~80 € Hin- und Rückfahrt werden etwa 20 € pro Kopf, plus das 4,50-€-Ticket. Für Kreuzfahrtgäste ist das der realistische Weg, den PR1 zu erleben und in einem halben Tag wieder an Bord zu sein — nach eigenem Zeitplan, ohne Angst um den letzten Bus.",
     table(["Für vier Personen", "Pro Person"],
           [["Taxi hin und zurück, Warten inbegriffen (~80 € ÷ 4)", "~20 €"], ["Wegticket", "4,50 €"],
            ["<b>Summe</b>", "<b>~24,50 €</b>"]]),
     "Nur ein Tag auf der Insel? " + a(L("de", "/one-day-in-madeira/"), "ein Tag auf Madeira") + " · " + a(L("de", "/madeira-cruise-port/"), "vom Kreuzfahrthafen") + "."], True),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Krótki spacer na Pico do Arieiro: PR1 do Pedra Rija, 4,50 €",
  desc="PR1 z Pico do Arieiro do punktu Pedra Rija i z powrotem: bilet 4,50 €, 1,2 km w jedną stronę, jedyny dwukierunkowy odcinek. Jak dobrze zarezerwować.",
  h1="Krótki PR1: z Pico do Arieiro do Pedra Rija",
  sub="Nie potrzebujesz całego PR1, żeby stanąć ponad chmurami: pierwsze 1,2 km do punktu widokowego Pedra Rija ma własny bilet za 4,50 € — i jest dwukierunkowe.",
  body=[
   ("Czy można przejść część PR1 bez rezerwowania całego szlaku?", [
     "Tak. SIMplifica sprzedaje osobny bilet na pierwszy odcinek PR1: z Pico do Arieiro do punktu widokowego Pedra Rija na km 1,2 i z powrotem tą samą drogą, za 4,50 € (3 € przez licencjonowanego operatora). Dzieci do 12 lat, mieszkańcy Madery i osoby z niepełnosprawnością od 60% są zwolnieni z opłaty, ale muszą być w rezerwacji. To jedyny odcinek PR1, którym wolno iść w obu kierunkach.",
     status_span("pl"),
     "Jak zarezerwować, krok po kroku: " + a(L("pl", "/simplifica-booking/"), "przewodnik rezerwacji SIMplifica") + "."], True),
   ("Jak daleko jest do Pedra Rija?", [
     "1,2 km w jedną stronę, schodkową ścieżką granią od szczytu Areeiro — łącznie około 2,4 km. Idziesz otwartą granią, z centralnymi szczytami po obu stronach, i zawracasz przy punkcie widokowym Pedra Rija. To wysokie góry, około 1 800 m: zimny wiatr, nagłe chmury i ostre słońce o każdej porze roku — weź ciepłą warstwę niezależnie od prognozy dla Funchal.",
     "Czy szczyt jest teraz odsłonięty? " + a(L("pl", "/pico-do-areeiro-weather/"), "Pico do Arieiro teraz: kamery i pogoda") + "."], True),
   ("Czy z biletem za 4,50 € można iść dalej na Pico Ruivo?", [
     "Nie. Bilet za 4,50 € kończy się przy punkcie widokowym Pedra Rija, a FAQ SIMplifica mówi wprost: nie ma dopłaty na szlaku ani zwrotu. Na cały PR1 do Pico Ruivo potrzebny jest bilet za 10,50 € na pełną trasę, a pełną trasę trzeba zacząć na Pico do Arieiro. Oba produkty stoją na SIMplifica obok siebie i kupno złego to najczęstszy błąd przy rezerwacji PR1."], True),
   ("Dlaczego mogę wrócić, skoro reszta PR1 jest jednokierunkowa?", [
     "Bo zasada jednego kierunku zaczyna się przy Pedra Rija. Stamtąd do Pico Ruivo szlak prowadzi tylko w jedną stronę i kończy się w Achada do Teixeira, daleko od Areeiro. Pierwszy odcinek pozostaje dwukierunkowy właśnie po to, żeby krótki bilet działał: wracasz do auta, taksówki albo autobusu na szczycie. Gdy IFCN zamknął odcinek Pedra Rija → Pico Ruivo na prace we wrześniu 2026, ten odcinek pozostał otwarty w obu kierunkach.",
     "Cała historia jednego kierunku: " + a(L("pl", "/pr1-one-way/"), "czy PR1 jest jednokierunkowy?") + "."], True),
   ("Jak dostać się na Pico do Arieiro bez wynajmowania auta?", [
     "Nie wjeżdżaj własnym autem: parking na szczycie jest bardzo ograniczony (4 € za godzinę na górnym parkingu, który szybko się zapełnia), a krążenie w poszukiwaniu miejsca potrafi pochłonąć pół poranka. Taksówka z Funchal kosztuje około 80 € za cały kurs tam i z powrotem, z kierowcą czekającym podczas spaceru — cena orientacyjna: ustal ją albo poproś o wycenę przed wejściem do auta.",
     "Tania opcja to autobus \"Pico do Areeiro\" Horários do Funchal: codziennie oprócz 25 grudnia, 3 € za kurs, płatne w autobusie (31 miejsc; rezerwacja miejsc telefonicznie, +351 291 705 555, od 7 do 2 dni roboczych wcześniej). Rano: odjazd 06:00 z pętli przy Teleférico, na szczycie 06:45 — przed wschodem słońca przez cały rok; zjazd o 12:15. Po południu — naturalny wybór na ten spacer: wjazd 13:30, na szczycie 14:15; ostatni autobus w dół o 18:00. <b>Jeśli przegapisz ostatni autobus, następnego nie ma</b> — tylko taksówka wezwana na szczyt. W napięty dzień jedź taksówką.",
     "Mały budżet? Wjedź autobusem i zamów taksówkę na powrót: 35–40 € za zjazd do Funchal (orientacyjnie). Rachunek dla dwóch osób:",
     table(["Dla dwóch osób", "Autobus w górę + taksówka w dół", "Taksówka tam i z powrotem"],
           [["Bilety na szlak (2 × 4,50 €)", "9 €", "9 €"], ["Autobus w górę (2 × 3 €)", "6 €", "—"],
            ["Taksówka", "35–40 € (auto, tylko zjazd)", "~80 € (z czekaniem)"],
            ["<b>Razem dla dwojga</b>", "<b>50–55 € (≈25–28 € od osoby)</b>", "<b>~89 € (≈45 € od osoby)</b>"]]),
     "Ceny parkingu i poranny tłok: " + a(L("pl", "/pico-do-areeiro-parking/"), "parking na Pico do Arieiro") + ". Cały transport na szczyt: " + a(L("pl", "/pr1-sunrise-transport/"), "dojazd na Areeiro") + "."], True),
   ("Ile to kosztuje dla czterech osób?", [
     "Około 24,50 € od osoby, od drzwi do drzwi. Taksówka kosztuje tyle samo z jedną osobą co z czterema, więc największa oszczędność tej wycieczki to po prostu zapełnienie auta: dobierzcie się z drugą parą — sąsiadami ze stolika na statku, ludźmi z hotelu — a ~80 € za kurs tam i z powrotem zamienia się w około 20 € od osoby, plus bilet za 4,50 €. Dla pasażerów wycieczkowców to realny sposób, żeby dotknąć PR1 i wrócić na pokład w pół dnia, we własnym tempie i bez strachu o ostatni autobus.",
     table(["Dla czterech osób", "Od osoby"],
           [["Taksówka tam i z powrotem, z czekaniem (~80 € ÷ 4)", "~20 €"], ["Bilet na szlak", "4,50 €"],
            ["<b>Razem</b>", "<b>~24,50 €</b>"]]),
     "Tylko jeden dzień na wyspie? " + a(L("pl", "/one-day-in-madeira/"), "jeden dzień na Maderze") + " · " + a(L("pl", "/madeira-cruise-port/"), "z portu wycieczkowego") + "."], True),
   ("Źródła", [None], False),
  ]),
}


def main():
    gi.build_qa(SLUG, COPY, src, "2026-10-21T12:00+01:00")


if __name__ == "__main__":
    main()
