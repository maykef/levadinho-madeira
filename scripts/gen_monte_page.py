#!/usr/bin/env python3
"""Writes /monte/ × 5 languages from the free-walks page shell (owner, 2026-10-21).

What it says, and where from (seo_research/facts/oneday.md, operators' sites read 2026-10-20/21):
  cable car      madeiracablecar.com: €16 one way / €22 return, 0-6 free, 7-14 half price; 08:45-17:45 daily,
                 closed 25 Dec.
  Monte Palace   montepalacemadeira.com/visita/: €18 adult, up to 14 free with an accompanying adult; garden
                 09:00-19:00 Apr-Sep / 09:00-18:00 Oct-Mar; museum 09:00-17:30; closed 25 Dec.
  toboggans      carreirosdomonte.com/v3/en/prices.php (read 2026-10-21): per sled €30 (1 person) / €40 (2) /
                 €60 (3); Mon-Sat 09:00-18:00, closed Sundays. Rules, closed days and the Livramento finish
                 (Caminho do Monte 82/84, ~2 km, ~10 min): prices.php + locations.php, read 2026-11-02.
  way back      bus 019 from 'Antes CZ CAM Monte' (~54 m from the finish) to Palácio S Lourenço, 15-18 min;
                weekday gaps 25-45 min, Saturday 30-60 (Horários do Funchal GTFS, Nov 2026). Walks: OSM foot
                routing (routing.openstreetmap.de, 2026-11-02): Livramento -> Sé 2.05 km / 27 min, -> cruise
                terminal 4.0 km / 54 min. Fare: municipal €2.05 on board / €1.45 pre-paid on GIRO (card €0.50),
                Portaria 128/2026 via tiim.pt (owner pasted, 2026-11-02; seo_research/facts/bus_fares.md).
  garden cable   telefericojardimbotanico.com/en/prices.html (read 2026-10-21): COMBO with Botanical Garden entry
                 included, adult €19 one way / €24 round trip, child 7-14 €9/€12; 09:00-17:00.
  taxi ~€12      owner first-hand (2026-10-20): taxis wait at the Botanical Garden's exits; ~€12 down to the
                 Funchal cable-car station. INDICATIVE.
  Monte rule     owner: cable car up from the Old Town; the bus only as the way down. No rental car.

Re-run after changing the copy: it keeps dateModified, then runs gen_site_nav.py, gen_cta.py, gen_owner.py and
gen_schema.py itself (the page is in GUIDES / TAGS). Prices on this page are watched daily by
scripts/check_prices.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "monte"
ROOT = gi.ROOT
CC = "https://madeiracablecar.com/en/"
MP = "https://montepalacemadeira.com/visita/"
CM = "https://www.carreirosdomonte.com/v3/en/prices.php"
TJ = "https://telefericojardimbotanico.com/en/prices.html"
TIIM = "https://tiim.pt/index.php/tarifarios/bilhetes"  # bus fares, Portaria 128/2026 (seo_research/facts/bus_fares.md)
a, ext = gi.a, gi.ext


def src(lang):
    return ('<p class="src">' + ext(CC, "Madeira Cable Car") + " · " + ext(MP, "Monte Palace Madeira") + " · "
            + ext(CM, "Carreiros do Monte") + " · " + ext(TJ, "Teleférico Jardim Botânico") + " · " + ext(TIIM, "TIIM") + "</p>")


def table(head, rows):
    return ('<div class="tbl"><table>\n    <thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead>\n    <tbody>\n"
            + "".join("      <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n" for r in rows) + "    </tbody>\n  </table></div>")


def L(lang, path):
    return f"{PREFIX[lang]}{path}"


# Sections: (heading, parts, is_question). A question's FAQ answer is its first paragraph, verbatim.
COPY = {
 "en": dict(
  title="Monte Madeira: what to see, cable car and toboggans",
  desc="What to see in Monte: the church, Monte Palace (€18), the wicker toboggans (€30–60 a sled) and the cable cars — 2026 prices and the smart way down.",
  h1="Monte: what to see and how to do it right",
  sub="Funchal's hill village: the island's most famous church, a palace garden, the wicker toboggans — cable car up, and better ways down than the way you came.",
  body=[
   ("What is there to see in Monte?", [
     "Four things, honestly timed. The church of Nossa Senhora do Monte, whose staircase is the postcard — a short visit. Monte Palace Madeira, the main event: a steep tropical garden with koi lakes, tile panels and a mineral museum (€18, under-15s free with an accompanying adult; garden 09:00–19:00 April–September, 09:00–18:00 October–March; museum 09:00–17:30; closed 25 December) — allow 1.5–2 hours and expect stairs. The Carreiros do Monte wicker toboggans, below the church. And Largo da Fonte under the plane trees, where the village catches its breath."], True),
   ("How do I get up to Monte?", [
     "Take the cable car from Funchal's Old Town: €16 one way, €22 return, children 0–6 free and 7–14 half price; it runs 08:45–17:45 every day except 25 December. Don't drive up — there is nothing worth parking for, and the fun of Monte is arriving over the valley. The bus is the budget way down, not the way up.",
     "Monte is day two of our " + a(L("en", "/two-days-in-madeira/"), "two-day itinerary") + " — the timed version of this page."], True),
   ("How much is the Monte toboggan ride?", [
     "The price is per sled, not per person: €30 for one person, €40 for two, €60 for three. They run Monday to Saturday, 09:00–18:00 — no rides on Sundays. Two runners in straw hats steer you down the asphalt on wicker and wood; the ride is about 2 km and 10 minutes, and it ends at Livramento (Caminho do Monte 82/84), not in Funchal.",
     table(["Sled", "Price"], [["1 person", "€30"], ["2 people", "€40"], ["3 people", "€60"]]),
     'Tickets are sold at the start, below the church, for the same day only: no online booking, no reservations. The desk at the top closes at 17:45 and may close earlier when the queue is long or the weather is bad. In rain or on a wet road there are no three-person sleds, so a group of three rides in two (€30 + €40). Besides Sundays they are closed on Good Friday, Easter Sunday, 14–15 August, 25 December and 1 January.'], True),
   ('How do I get back from the toboggan at Livramento?', [
     'Bus 19 (Horários do Funchal) stops about 50 m from the finish and runs down to the city centre, by the Palácio de São Lourenço on the seafront, in 15–20 minutes. The fare is €2.05 bought on board, or €1.45 pre-paid on a GIRO card (the card costs €0.50). On weekdays it leaves every 25–45 minutes, on Saturdays every 30–60 minutes. On foot it is about 2 km downhill to the cathedral, roughly half an hour; a taxi is a short metered ride.',
     'Back to a cruise ship: Livramento is about 4 km from the cruise terminal, just under an hour on foot, and once you count the wait the bus barely saves time. Leave the toboggan at least 1.5 hours before all-aboard. More on the ' + a(L('en', "/madeira-cruise-port/"), 'Madeira cruise port') + ' page.'], True),
   ("Should I buy the cable car return?", [
     "Usually no. The €22 return only pays off if you plan to come back to Monte, and the best of Monte is leaving it downhill: the toboggans (Mon–Sat), the garden cable car to the Botanical Garden, or the public bus. Buy €16 one way up, then decide at the top."], True),
   ("How do I continue to the Botanical Garden?", [
     "Take the garden cable car from Babosas, a short walk from Monte's centre. The combo ticket includes the Botanical Garden entry: €19 one way, €24 if you ride back to Monte (children 7–14 €9/€12; 09:00–17:00). From the garden's exits taxis wait, and the trip down to the Funchal cable-car station is about €12 — indicative, confirm with the driver. That one-way-plus-taxi combination is how our two-day plan does it."], True),
   ("Is Monte Palace worth the €18?", [
     "It is the most content-rich stop in Monte, and under-15s go free, which makes it the obvious family pick: for two adults and two children the €36 covers everyone. It is also the island's steepest single entry fee, and the garden itself is steep on the legs. If you only have one day in Madeira and the viewpoints matter more to you, our " + a(L("en", "/one-day-in-madeira/"), "one-day plan") + " skips it without regret; with two days it earns its place."], True),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="Monte, Madeira: o que ver, teleférico e carros de cesto",
  desc="O que ver no Monte: a igreja, o Monte Palace (18 €), os carros de cesto (30–60 € por carro) e os teleféricos — preços 2026 e a descida inteligente.",
  h1="Monte: o que ver e como fazer bem",
  sub="A vila nas alturas do Funchal: a igreja mais famosa da ilha, um jardim-palácio, os carros de cesto — teleférico para subir, e descidas melhores do que o caminho de volta.",
  body=[
   ("O que há para ver no Monte?", [
     "Quatro coisas, com tempos honestos. A igreja de Nossa Senhora do Monte, cuja escadaria é o postal — visita curta. O Monte Palace Madeira, o prato principal: um jardim tropical íngreme com lagos de carpas, painéis de azulejo e um museu de minerais (18 €, menores de 15 anos grátis com um adulto acompanhante; jardim 09:00–19:00 de abril a setembro, 09:00–18:00 de outubro a março; museu 09:00–17:30; fecha a 25 de dezembro) — conte com 1,5–2 horas e muitas escadas. Os carros de cesto dos Carreiros do Monte, abaixo da igreja. E o Largo da Fonte, à sombra dos plátanos, onde a vila respira."], True),
   ("Como subo até ao Monte?", [
     "De teleférico a partir da Zona Velha do Funchal: 16 € num sentido, 22 € ida e volta, crianças dos 0 aos 6 grátis e dos 7 aos 14 a metade; funciona das 08:45 às 17:45 todos os dias exceto 25 de dezembro. Não suba de carro — não há nada que justifique estacionar, e a graça do Monte é chegar por cima do vale. O autocarro é a descida económica, não a subida.",
     "O Monte é o segundo dia do nosso " + a(L("pt", "/two-days-in-madeira/"), "roteiro de dois dias") + " — a versão com horários desta página."], True),
   ("Quanto custa o carro de cesto do Monte?", [
     "O preço é por carro, não por pessoa: 30 € para uma pessoa, 40 € para duas, 60 € para três. Funcionam de segunda a sábado, das 09:00 às 18:00 — ao domingo não há descidas. Dois carreiros de chapéu de palha guiam-no pelo asfalto em verga e madeira; a descida tem cerca de 2 km e 10 minutos e termina no Livramento (Caminho do Monte 82/84), não no Funchal.",
     table(["Carro", "Preço"], [["1 pessoa", "30 €"], ["2 pessoas", "40 €"], ["3 pessoas", "60 €"]]),
     'Os bilhetes vendem-se na partida, abaixo da igreja, só para o próprio dia: sem reservas nem venda online. A bilheteira de cima fecha às 17:45 e pode fechar mais cedo se a fila for grande ou o tempo estiver mau. Com chuva ou piso molhado não há carros para três pessoas; um grupo de três desce em dois carros (30 € + 40 €). Além dos domingos, fecham na Sexta-feira Santa, no Domingo de Páscoa, a 14 e 15 de agosto, a 25 de dezembro e a 1 de janeiro.'], True),
   ('Como regresso do Livramento, no fim do carro de cesto?', [
     'O autocarro 19 (Horários do Funchal) para a cerca de 50 m da chegada e desce até ao centro, junto ao Palácio de São Lourenço, na frente-mar, em 15–20 minutos. O bilhete custa 2,05 € a bordo, ou 1,45 € pré-comprado no cartão GIRO (o cartão custa 0,50 €). Nos dias úteis passa a cada 25–45 minutos, ao sábado a cada 30–60 minutos. A pé são cerca de 2 km a descer até à Sé, mais ou menos meia hora; de táxi é uma viagem curta, ao taxímetro.',
     'Para voltar a um navio de cruzeiro: o Livramento fica a cerca de 4 km do terminal, pouco menos de uma hora a pé, e contando a espera o autocarro quase não poupa tempo. Saia do carro de cesto pelo menos 1h30 antes da hora de embarque. Mais na página do ' + a(L('pt', "/madeira-cruise-port/"), 'porto de cruzeiros da Madeira') + '.'], True),
   ("Vale a pena comprar o teleférico de ida e volta?", [
     "Normalmente não. Os 22 € de ida e volta só compensam se tencionar voltar ao Monte, e o melhor do Monte é sair dele a descer: os carros de cesto (segunda a sábado), o teleférico do jardim até ao Jardim Botânico, ou o autocarro. Compre 16 € só de subida e decida lá em cima."], True),
   ("Como continuo até ao Jardim Botânico?", [
     "Apanhe o teleférico do jardim nas Babosas, a uma curta caminhada do centro do Monte. O bilhete combinado inclui a entrada no Jardim Botânico: 19 € num sentido, 24 € se regressar ao Monte (crianças 7–14 anos 9 €/12 €; 09:00–17:00). Às saídas do jardim esperam táxis, e a descida até à estação do teleférico do Funchal custa cerca de 12 € — indicativo, confirme com o motorista. Essa combinação de ida simples mais táxi é a que o nosso plano de dois dias usa."], True),
   ("O Monte Palace vale os 18 €?", [
     "É a paragem com mais conteúdo do Monte, e os menores de 15 anos entram grátis, o que o torna a escolha óbvia em família: para dois adultos e duas crianças, os 36 € cobrem toda a gente. É também a entrada individual mais cara da ilha, e o jardim é puxado para as pernas. Se só tem um dia na Madeira e os miradouros lhe importam mais, o nosso " + a(L("pt", "/one-day-in-madeira/"), "plano de um dia") + " passa-lhe ao lado sem remorsos; com dois dias, merece o lugar."], True),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Monte, Madère : que voir, téléphérique et luges d'osier",
  desc="Que voir à Monte : l'église, Monte Palace (18 €), les luges d'osier (30–60 € la luge) et les téléphériques — prix 2026 et la descente futée.",
  h1="Monte : que voir et comment bien faire",
  sub="Le village perché de Funchal : l'église la plus célèbre de l'île, un jardin-palais, les luges d'osier — téléphérique pour monter, et de meilleures descentes que le chemin de l'aller.",
  body=[
   ("Que voir à Monte ?", [
     "Quatre choses, aux durées honnêtes. L'église de Nossa Senhora do Monte, dont l'escalier est la carte postale — visite courte. Monte Palace Madeira, le plat principal : un jardin tropical escarpé avec bassins de carpes, panneaux d'azulejos et un musée des minéraux (18 €, moins de 15 ans gratuits avec un adulte accompagnant ; jardin 09:00–19:00 d'avril à septembre, 09:00–18:00 d'octobre à mars ; musée 09:00–17:30 ; fermé le 25 décembre) — comptez 1 h 30–2 h et beaucoup de marches. Les luges d'osier des Carreiros do Monte, sous l'église. Et le Largo da Fonte, sous les platanes, où le village souffle."], True),
   ("Comment monter à Monte ?", [
     "Par le téléphérique depuis la vieille ville de Funchal : 16 € l'aller, 22 € l'aller-retour, enfants de 0 à 6 ans gratuits et de 7 à 14 ans à moitié prix ; il fonctionne de 08:45 à 17:45 tous les jours sauf le 25 décembre. Ne montez pas en voiture — rien n'y justifie de se garer, et le plaisir de Monte est d'arriver au-dessus de la vallée. Le bus est la descente économique, pas la montée.",
     "Monte est le deuxième jour de notre " + a(L("fr", "/two-days-in-madeira/"), "itinéraire de deux jours") + " — la version minutée de cette page."], True),
   ("Combien coûte la luge de Monte ?", [
     "Le prix est par luge, pas par personne : 30 € pour une personne, 40 € pour deux, 60 € pour trois. Elles circulent du lundi au samedi, de 09:00 à 18:00 — pas de descentes le dimanche. Deux carreiros en chapeau de paille vous guident sur l'asphalte, en osier et en bois ; la descente fait environ 2 km et 10 minutes, et s'arrête au Livramento (Caminho do Monte 82/84), pas à Funchal.",
     table(["Luge", "Prix"], [["1 personne", "30 €"], ["2 personnes", "40 €"], ["3 personnes", "60 €"]]),
     "Les billets se vendent au départ, sous l'église, pour le jour même seulement : ni réservation ni vente en ligne. Le guichet du haut ferme à 17:45 et peut fermer plus tôt si la file est longue ou si le temps est mauvais. Sous la pluie ou sur route mouillée, pas de luge à trois : un groupe de trois descend en deux luges (30 € + 40 €). En plus des dimanches, fermé le Vendredi saint, le dimanche de Pâques, les 14 et 15 août, le 25 décembre et le 1er janvier."], True),
   ("Comment revenir du Livramento, à l'arrivée de la luge ?", [
     "Le bus 19 (Horários do Funchal) s'arrête à environ 50 m de l'arrivée et descend au centre-ville, près du Palácio de São Lourenço sur le front de mer, en 15 à 20 minutes. Le billet coûte 2,05 € à bord, ou 1,45 € prépayé sur la carte GIRO (la carte coûte 0,50 €). En semaine il passe toutes les 25 à 45 minutes, le samedi toutes les 30 à 60 minutes. À pied, c'est environ 2 km en descente jusqu'à la cathédrale, une demi-heure environ ; en taxi, un court trajet au compteur.",
     "Pour rejoindre un navire de croisière : le Livramento est à environ 4 km du terminal, un peu moins d'une heure à pied, et une fois l'attente comptée le bus ne fait guère gagner de temps. Quittez la luge au moins 1 h 30 avant l'heure de retour à bord. Plus de détails sur la page " + a(L('fr', "/madeira-cruise-port/"), 'port de croisière de Madère') + '.'], True),
   ("Faut-il acheter l'aller-retour du téléphérique ?", [
     "En général non. Les 22 € aller-retour ne valent le coup que si vous comptez revenir à Monte, et le meilleur de Monte, c'est d'en repartir en descendant : les luges (du lundi au samedi), le téléphérique du jardin vers le Jardin botanique, ou le bus. Prenez 16 € l'aller simple et décidez là-haut."], True),
   ("Comment continuer vers le Jardin botanique ?", [
     "Prenez le téléphérique du jardin à Babosas, à quelques minutes à pied du centre de Monte. Le billet combiné inclut l'entrée au Jardin botanique : 19 € l'aller, 24 € si vous revenez à Monte (enfants 7–14 ans 9 €/12 € ; 09:00–17:00). Aux sorties du jardin, des taxis attendent, et la descente jusqu'à la gare du téléphérique de Funchal coûte environ 12 € — indicatif, à confirmer avec le chauffeur. C'est cette combinaison aller simple plus taxi que suit notre plan de deux jours."], True),
   ("Monte Palace vaut-il les 18 € ?", [
     "C'est l'étape la plus riche de Monte, et les moins de 15 ans entrent gratuitement, ce qui en fait le choix familial évident : pour deux adultes et deux enfants, les 36 € couvrent tout le monde. C'est aussi l'entrée individuelle la plus chère de l'île, et le jardin est raide pour les jambes. Si vous n'avez qu'un jour à Madère et que les belvédères comptent plus pour vous, notre " + a(L("fr", "/one-day-in-madeira/"), "plan d'une journée") + " s'en passe sans regret ; sur deux jours, il mérite sa place."], True),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Monte auf Madeira: was sehen, Seilbahn und Korbschlitten",
  desc="Was in Monte sehen: die Kirche, Monte Palace (18 €), die Korbschlitten (30–60 € pro Schlitten) und die Seilbahnen — Preise 2026 und der kluge Weg hinunter.",
  h1="Monte: was sehen und wie man es richtig macht",
  sub="Funchals Bergdorf: die berühmteste Kirche der Insel, ein Palastgarten, die Korbschlitten — mit der Seilbahn hinauf, und bessere Wege hinunter als der Rückweg.",
  body=[
   ("Was gibt es in Monte zu sehen?", [
     "Vier Dinge, ehrlich getaktet. Die Kirche Nossa Senhora do Monte, deren Treppe das Postkartenmotiv ist — ein kurzer Besuch. Monte Palace Madeira, der Hauptgang: ein steiler tropischer Garten mit Koi-Teichen, Fliesenbildern und einem Mineralienmuseum (18 €, unter 15 frei mit begleitendem Erwachsenen; Garten 09:00–19:00 April–September, 09:00–18:00 Oktober–März; Museum 09:00–17:30; am 25. Dezember geschlossen) — rechnen Sie mit 1,5–2 Stunden und vielen Stufen. Die Korbschlitten der Carreiros do Monte, unterhalb der Kirche. Und der Largo da Fonte unter den Platanen, wo das Dorf durchatmet."], True),
   ("Wie komme ich nach Monte hinauf?", [
     "Mit der Seilbahn aus Funchals Altstadt: 16 € einfach, 22 € hin und zurück, Kinder von 0–6 frei, 7–14 zum halben Preis; sie fährt täglich 08:45–17:45, außer am 25. Dezember. Fahren Sie nicht mit dem Auto hinauf — es gibt nichts, wofür sich das Parken lohnt, und der Reiz von Monte ist die Ankunft über dem Tal. Der Bus ist der günstige Weg hinunter, nicht hinauf.",
     "Monte ist Tag zwei unserer " + a(L("de", "/two-days-in-madeira/"), "Zwei-Tage-Route") + " — die getaktete Fassung dieser Seite."], True),
   ("Was kostet die Korbschlittenfahrt in Monte?", [
     "Der Preis gilt pro Schlitten, nicht pro Person: 30 € für eine Person, 40 € für zwei, 60 € für drei. Gefahren wird Montag bis Samstag, 09:00–18:00 — sonntags keine Fahrten. Zwei Carreiros mit Strohhüten steuern Sie auf Weide und Holz über den Asphalt; die Fahrt ist etwa 2 km lang, dauert rund 10 Minuten und endet in Livramento (Caminho do Monte 82/84), nicht in Funchal.",
     table(["Schlitten", "Preis"], [["1 Person", "30 €"], ["2 Personen", "40 €"], ["3 Personen", "60 €"]]),
     'Tickets gibt es am Start unterhalb der Kirche, nur für denselben Tag: keine Reservierung, kein Online-Verkauf. Der Schalter oben schließt um 17:45 und kann früher schließen, wenn die Schlange lang oder das Wetter schlecht ist. Bei Regen oder nasser Straße fahren keine Dreierschlitten; eine Dreiergruppe fährt dann in zwei Schlitten (30 € + 40 €). Außer sonntags geschlossen an Karfreitag, Ostersonntag, am 14. und 15. August, am 25. Dezember und am 1. Januar.'], True),
   ('Wie komme ich von Livramento, dem Ziel der Korbschlitten, zurück?', [
     'Bus 19 (Horários do Funchal) hält etwa 50 m vom Ziel und fährt in 15–20 Minuten ins Zentrum, zum Palácio de São Lourenço an der Uferpromenade. Die Fahrt kostet 2,05 € beim Fahrer oder 1,45 € vorab auf der GIRO-Karte (die Karte kostet 0,50 €). Werktags fährt er alle 25–45 Minuten, samstags alle 30–60 Minuten. Zu Fuß sind es etwa 2 km bergab bis zur Kathedrale, rund eine halbe Stunde; mit dem Taxi ist es eine kurze Fahrt mit Taxameter.',
     'Zurück zum Kreuzfahrtschiff: Livramento liegt etwa 4 km vom Terminal, knapp eine Stunde zu Fuß, und mit der Wartezeit spart der Bus kaum Zeit. Verlassen Sie den Schlitten mindestens 1,5 Stunden vor All-aboard. Mehr auf der Seite ' + a(L('de', "/madeira-cruise-port/"), 'Kreuzfahrthafen Madeira') + '.'], True),
   ("Lohnt sich das Hin-und-zurück-Ticket der Seilbahn?", [
     "Meist nicht. Die 22 € hin und zurück lohnen sich nur, wenn Sie nach Monte zurückkehren wollen — und das Beste an Monte ist, es bergab zu verlassen: mit den Korbschlitten (Mo–Sa), mit der Gartenseilbahn zum Botanischen Garten oder mit dem Bus. Kaufen Sie 16 € einfach und entscheiden Sie oben."], True),
   ("Wie komme ich weiter zum Botanischen Garten?", [
     "Nehmen Sie die Gartenseilbahn ab Babosas, einen kurzen Fußweg vom Zentrum Montes. Das Kombiticket enthält den Eintritt in den Botanischen Garten: 19 € einfach, 24 € mit Rückfahrt nach Monte (Kinder 7–14 Jahre 9 €/12 €; 09:00–17:00). An den Ausgängen des Gartens warten Taxis, die Fahrt hinunter zur Talstation der Funchal-Seilbahn kostet etwa 12 € — Richtwert, mit dem Fahrer bestätigen. Genau diese Kombination aus einfacher Fahrt plus Taxi nutzt unser Zwei-Tage-Plan."], True),
   ("Ist Monte Palace die 18 € wert?", [
     "Es ist der gehaltvollste Halt in Monte, und unter 15 ist der Eintritt frei — für Familien die naheliegende Wahl: Bei zwei Erwachsenen mit zwei Kindern decken 36 € alle ab. Es ist zugleich der teuerste Einzeleintritt der Insel, und der Garten geht in die Beine. Wer nur einen Tag auf Madeira hat und wem die Aussichtspunkte wichtiger sind: Unser " + a(L("de", "/one-day-in-madeira/"), "Ein-Tages-Plan") + " lässt ihn ohne Reue aus; mit zwei Tagen verdient er seinen Platz."], True),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Monte na Maderze: co zobaczyć, kolejka i sanie z wikliny",
  desc="Co zobaczyć w Monte: kościół, Monte Palace (18 €), sanie z wikliny (30–60 € za sanie) i kolejki linowe — ceny 2026 i sprytny zjazd w dół.",
  h1="Monte: co zobaczyć i jak to zrobić dobrze",
  sub="Górska dzielnica Funchal: najsłynniejszy kościół wyspy, pałacowy ogród, sanie z wikliny — kolejką w górę, a w dół lepszymi drogami niż ta sama trasa.",
  body=[
   ("Co można zobaczyć w Monte?", [
     "Cztery rzeczy, uczciwie wyliczone w czasie. Kościół Nossa Senhora do Monte, którego schody są pocztówką — krótka wizyta. Monte Palace Madeira, danie główne: stromy tropikalny ogród ze stawami karpi koi, panelami azulejos i muzeum minerałów (18 €, do 15 lat wstęp wolny z dorosłym opiekunem; ogród 09:00–19:00 od kwietnia do września, 09:00–18:00 od października do marca; muzeum 09:00–17:30; nieczynne 25 grudnia) — licz 1,5–2 godziny i sporo schodów. Sanie z wikliny Carreiros do Monte, poniżej kościoła. I Largo da Fonte pod platanami, gdzie wioska łapie oddech."], True),
   ("Jak dostać się do Monte?", [
     "Kolejką linową ze Starego Miasta w Funchal: 16 € w jedną stronę, 22 € w obie, dzieci 0–6 lat za darmo, 7–14 za pół ceny; kursuje 08:45–17:45 codziennie oprócz 25 grudnia. Nie wjeżdżaj autem — nie ma tam nic wartego parkowania, a urok Monte to przylot nad doliną. Autobus to tani zjazd, nie wjazd.",
     "Monte to drugi dzień naszego " + a(L("pl", "/two-days-in-madeira/"), "planu na dwa dni") + " — wersji tej strony z godzinami."], True),
   ("Ile kosztują sanie w Monte?", [
     "Cena jest za sanie, nie od osoby: 30 € za jedną osobę, 40 € za dwie, 60 € za trzy. Jeżdżą od poniedziałku do soboty, 09:00–18:00 — w niedziele zjazdów nie ma. Dwóch carreiros w słomkowych kapeluszach prowadzi sanie z wikliny i drewna po asfalcie; zjazd ma około 2 km, trwa około 10 minut i kończy się w Livramento (Caminho do Monte 82/84), nie w Funchal.",
     table(["Sanie", "Cena"], [["1 osoba", "30 €"], ["2 osoby", "40 €"], ["3 osoby", "60 €"]]),
     'Bilety sprzedaje się na starcie, poniżej kościoła, tylko na ten sam dzień: bez rezerwacji i sprzedaży online. Kasa na górze zamyka się o 17:45 i może zamknąć się wcześniej przy długiej kolejce lub złej pogodzie. W deszczu lub na mokrej drodze nie ma sań dla trzech osób; trzyosobowa grupa zjeżdża wtedy dwoma saniami (30 € + 40 €). Poza niedzielami nieczynne w Wielki Piątek, w Niedzielę Wielkanocną, 14 i 15 sierpnia, 25 grudnia i 1 stycznia.'], True),
   ('Jak wrócić z Livramento, gdzie kończy się zjazd saniami?', [
     'Autobus 19 (Horários do Funchal) zatrzymuje się około 50 m od mety i w 15–20 minut zjeżdża do centrum, pod Palácio de São Lourenço na nabrzeżu. Bilet kosztuje 2,05 € u kierowcy albo 1,45 € w przedpłacie na karcie GIRO (karta kosztuje 0,50 €). W dni robocze kursuje co 25–45 minut, w soboty co 30–60 minut. Pieszo to około 2 km w dół do katedry, mniej więcej pół godziny; taksówką krótki kurs na taksometr.',
     'Powrót na statek wycieczkowy: Livramento jest około 4 km od terminalu, niecała godzina pieszo, a po doliczeniu czekania autobus prawie nie oszczędza czasu. Zjedź saniami najpóźniej 1,5 godziny przed godziną powrotu na pokład. Więcej na stronie ' + a(L('pl', "/madeira-cruise-port/"), 'port wycieczkowy na Maderze') + '.'], True),
   ("Czy opłaca się bilet na kolejkę w obie strony?", [
     "Zwykle nie. 22 € w obie strony zwraca się tylko wtedy, gdy planujesz wrócić do Monte, a najlepsze w Monte jest opuszczenie go w dół: saniami (pon–sob), kolejką ogrodową do Ogrodu Botanicznego albo autobusem. Kup bilet za 16 € w jedną stronę i zdecyduj na górze."], True),
   ("Jak dostać się dalej do Ogrodu Botanicznego?", [
     "Kolejką ogrodową z Babosas, krótki spacer od centrum Monte. Bilet łączony zawiera wstęp do Ogrodu Botanicznego: 19 € w jedną stronę, 24 € z powrotem do Monte (dzieci 7–14 lat 9 €/12 €; 09:00–17:00). Przy wyjściach z ogrodu czekają taksówki, a zjazd do dolnej stacji kolejki w Funchal kosztuje około 12 € — orientacyjnie, potwierdź z kierowcą. Właśnie tę kombinację biletu w jedną stronę i taksówki stosuje nasz plan na dwa dni."], True),
   ("Czy Monte Palace jest wart 18 €?", [
     "To najbogatszy w treść przystanek w Monte, a dzieci do 15 lat wchodzą za darmo, więc dla rodzin wybór jest oczywisty: dla dwojga dorosłych z dwójką dzieci 36 € pokrywa wszystkich. To zarazem najdroższy pojedynczy wstęp na wyspie, a ogród daje w nogi. Jeśli masz na Maderze tylko jeden dzień i bardziej zależy Ci na punktach widokowych, nasz " + a(L("pl", "/one-day-in-madeira/"), "plan na jeden dzień") + " pomija go bez żalu; przy dwóch dniach zasługuje na swoje miejsce."], True),
   ("Źródła", [None], False),
  ]),
}


def main():
    gi.build_qa(SLUG, COPY, src, "2026-10-21T12:00+01:00")


if __name__ == "__main__":
    main()
