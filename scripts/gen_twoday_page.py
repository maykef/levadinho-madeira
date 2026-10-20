#!/usr/bin/env python3
"""Writes /two-days-in-madeira/ × 5 languages from the free-walks page shell (owner approved the timed itinerary,
2026-10-20).

Day 1 = the viewpoints taxi loop (the one-day page's plan A, with times); day 2 = Funchal, Monte and the Botanical
Garden on foot and by cable car, with the Carreiros toboggans as the alternative descent. Facts and sources in
seo_research/facts/oneday.md ("Two-day additions"):
  Botanical Garden  €10 over-12s 2026, €3 ages 6-12, under-6 and RAM residents free (Portaria 48/2026, Annex II
                    Part I pt 3.1 + art. 16, PDF read 2026-10-20); 09:00-17:30.
  garden cable car  Monte ↔ Botanical Garden €11 one way / €16 return, child 7-14 €6/€9, under-7 free
                    (telefericojardimbotanico.com); 09:00-17:00. Owner: say plainly that leg is about €21/adult.
  everything else   as on /one-day-in-madeira/ (gen_oneday_page.py docstring).

Re-run after changing the copy: it keeps dateModified, then runs gen_site_nav.py, gen_cta.py, gen_owner.py,
gen_schema.py and gen_chat.py itself (the page is in GUIDES / TAGS and carries the web chat).
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import BASE, LANGS, PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "two-days-in-madeira"
ROOT = gi.ROOT
P591 = "https://joram.madeira.gov.pt/joram/1serie/Ano%20de%202025/ISerie-189-2025-10-27.pdf"
P48 = "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Portarias/Port48ISerie027_2026.pdf"
VM_CG = "https://visitmadeira.com/en/what-to-do/nature-seekers/viewpoints/cabo-girao-viewpoint/"
CABLE = "https://www.madeiracablecar.com/"
GCABLE = "https://www.telefericojardimbotanico.com/en/"
MPAL = "https://montepalacemadeira.com/visita/"
CARR = "https://www.carreirosdomonte.com/v3/en/"
MERC = "https://mercados.funchal.pt/"
OSM = "https://www.openstreetmap.org/"
a, ext = gi.a, gi.ext


def src(lang):
    return ('<p class="src">' + ext(P48, "Portaria 48/2026 (JORAM)") + " · " + ext(P591, "Portaria 591/2025 (JORAM)")
            + " · " + ext(VM_CG, "Visit Madeira") + " · " + ext(CABLE, "Teleférico do Funchal") + " · "
            + ext(GCABLE, "Teleférico do Jardim Botânico") + " · " + ext(MPAL, "Monte Palace") + " · "
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
  title="Two days in Madeira: itinerary with times",
  desc="Two days in Madeira? A timed itinerary: the viewpoints taxi loop on day one; Funchal, Monte and the Botanical Garden on day two. 2026 prices inside.",
  h1="Two days in Madeira: a timed itinerary that fits",
  sub="Day one by taxi to the island's viewpoints, day two on foot and by cable car in Funchal and Monte — the whole top 5, the Botanical Garden, and honest 2026 prices.",
  body=[
   ("What can you do in Madeira in two days?", [
     "Everything the top 5 asks for, without rushing: on day one a taxi loop to the Eira do Serrado viewpoint and Curral das Freiras, the Cabo Girão skywalk and Câmara de Lobos; on day two Funchal on foot — the Mercado and the Old Town — then the cable car to Monte, the Monte Palace garden and the Botanical Garden. It is the two plans of our " + a(L("en", "/one-day-in-madeira/"), "one-day guide") + " done properly, one per day."], True),
   ("Day 1 — Curral das Freiras, Cabo Girão and Câmara de Lobos: what times?", [
     "A taxi loop of about 56 km, roughly 6 hours door to door. Agree the price for this exact round trip when you book (drivers quoted us about €160 for a 6-hour day in October 2026 — indicative, not a tariff): Táxis Madeira +351 291 764 476 (taxismadeira.pt) or AITRAM +351 291 765 760.",
     table(["Time", "Stop"],
           [["09:00", "Taxi pickup in Funchal"],
            ["09:30", "Eira do Serrado viewpoint over the Curral das Freiras valley"],
            ["10:15", "Curral das Freiras town (2.6 km below the viewpoint)"],
            ["11:15", "Drive across to the south coast (about 35 min)"],
            ["12:00", "Cabo Girão skywalk — 20–30 minutes (€5 over-12s, open 08:00–20:00)"],
            ["12:45", "Câmara de Lobos: lunch, then the old town and the pier"],
            ["14:45", "Back to Funchal (about 15 min)"],
            ["15:15", "Mercado dos Lavradores (weekdays to 19:00)"]]),
     "On a Saturday see the Mercado first thing — it closes at 14:00; on a Sunday it is closed, so move it to day two. Road distances from OpenStreetMap; these are mountain roads, so times are without traffic."], True),
   ("Day 2 — Funchal, Monte and the Botanical Garden: what times?", [
     "On foot and by cable car — no taxi needed. The Botanical Garden leg costs about €21 per adult (€11 cable car one way + €10 entry), so skip it if gardens aren't your thing and take the toboggans instead (below).",
     table(["Time", "Stop"],
           [["09:00", "Old Town stroll — and the Mercado, if day one was a weekend"],
            ["10:00", "Cable car up to Monte (08:45–17:45; €16 one way, €22 return)"],
            ["10:30", "Monte church"],
            ["11:00", "Monte Palace garden, about 2 hours (€18, up to 14 free; to 18:00 in winter, 19:00 April–September)"],
            ["13:00", "Light lunch"],
            ["14:00", "Monte–Botanical Garden cable car (09:00–17:00; €11 one way) across the valley"],
            ["14:15", "Botanical Garden (€10 over-12s, €3 ages 6–12, under-6 free; open to 17:30)"],
            ["16:30", "Taxi down to town — they wait at the garden's exits, about €12 to the cable-car station — or the bus"]]),
     "The alternative without the Botanical Garden: after Monte Palace, start the descent on the Carreiros do Monte wicker toboggans (Monday–Saturday 09:00–18:00) and continue by bus or taxi."], True),
   ("How much do two days in Madeira cost?", [
     "Per adult, at 2026 prices: day one is the taxi loop — about €160 for the car for 6 hours (indicative; split it between everyone in the taxi) plus €5 for Cabo Girão. Day two: €16 cable car up to Monte, €18 Monte Palace, then either the Botanical Garden leg — €11 cable + €10 entry, plus about €12 for the taxi down to the cable-car station (they wait at the garden's exits), or €26 with the garden cable there and back or the toboggan ride instead (price on the Carreiros do Monte site). The Mercado, the Old Town, the viewpoints and both towns on day one cost nothing beyond the taxi."], True),
   ("Should I rent a car for two days in Madeira?", [
     "For these two days, no. Parking is limited at most of the day-one stops, and day two is entirely on foot and cable car — the car would sit in a paid Funchal garage all day. Rent a car only if you are adding a third day of your own route."], True),
   ("Can I swap in a levada or a peak?", [
     "Yes — the short mountain taste that fits this plan is the out-and-back from Pico do Areeiro to the Pedra Rija viewpoint on " + a(L("en", "/pr1/"), "PR1") + " (1.2 km each way, €4.50, booked online on SIMplifica — see " + a(L("en", "/simplifica-booking/"), "how to book") + "). Put it at the start of day one and shift the loop an hour later, and check the summit first: " + a(L("en", "/pico-do-areeiro-weather/"), "Pico do Areeiro weather and webcams") + "."], True),
   ("From a cruise ship", [
     "Two port days, or an overnight call, split exactly this way: the taxi loop on the first day, Funchal and Monte on the second. Agree each return time with the driver when you book and keep at least an hour's margin before all-aboard. What's open in town today — events, lidos, last buses — is on " + a(L("en", "/funchal/"), "Funchal today") + "."], False),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="Dois dias na Madeira: roteiro com horários",
  desc="Dois dias na Madeira? Um roteiro com horários: a volta de táxi pelos miradouros no primeiro dia; Funchal, Monte e Jardim Botânico no segundo. Preços 2026.",
  h1="Dois dias na Madeira: um roteiro com horários que cabe",
  sub="O primeiro dia de táxi pelos miradouros da ilha, o segundo a pé e de teleférico no Funchal e no Monte — o top 5 inteiro, o Jardim Botânico e preços honestos de 2026.",
  body=[
   ("O que fazer na Madeira em dois dias?", [
     "Tudo o que o top 5 pede, sem pressa: no primeiro dia uma volta de táxi ao miradouro da Eira do Serrado e ao Curral das Freiras, ao skywalk do Cabo Girão e a Câmara de Lobos; no segundo o Funchal a pé — o Mercado e a Zona Velha — e depois o teleférico até ao Monte, o jardim Monte Palace e o Jardim Botânico. São os dois planos do nosso " + a(L("pt", "/one-day-in-madeira/"), "guia de um dia") + " feitos como deve ser, um por dia."], True),
   ("Dia 1 — Curral das Freiras, Cabo Girão e Câmara de Lobos: a que horas?", [
     "Uma volta de táxi de cerca de 56 km, mais ou menos 6 horas porta a porta. Combine o preço desta volta exata ao reservar (os taxistas indicaram-nos cerca de 160 € por um dia de 6 horas em outubro de 2026 — indicativo, não é tarifa): Táxis Madeira +351 291 764 476 (taxismadeira.pt) ou AITRAM +351 291 765 760.",
     table(["Hora", "Paragem"],
           [["09:00", "O táxi apanha-o no Funchal"],
            ["09:30", "Miradouro da Eira do Serrado sobre o vale do Curral das Freiras"],
            ["10:15", "Vila do Curral das Freiras (2,6 km abaixo do miradouro)"],
            ["11:15", "Travessia para a costa sul (cerca de 35 min)"],
            ["12:00", "Skywalk do Cabo Girão — 20–30 minutos (5 € maiores de 12; aberto 08:00–20:00)"],
            ["12:45", "Câmara de Lobos: almoço, depois a vila e o cais"],
            ["14:45", "Regresso ao Funchal (cerca de 15 min)"],
            ["15:15", "Mercado dos Lavradores (dias úteis até às 19:00)"]]),
     "Ao sábado, veja o Mercado logo de manhã — fecha às 14:00; ao domingo está fechado, passe-o para o segundo dia. Distâncias por estrada do OpenStreetMap; são estradas de montanha, os tempos são sem trânsito."], True),
   ("Dia 2 — Funchal, Monte e Jardim Botânico: a que horas?", [
     "A pé e de teleférico — não precisa de táxi. A parte do Jardim Botânico custa cerca de 21 € por adulto (11 € de teleférico num sentido + 10 € de entrada); se jardins não são o seu género, salte-a e desça nos carros de cesto (abaixo).",
     table(["Hora", "Paragem"],
           [["09:00", "Passeio pela Zona Velha — e o Mercado, se o primeiro dia calhou ao fim de semana"],
            ["10:00", "Teleférico até ao Monte (08:45–17:45; 16 € ida, 22 € ida e volta)"],
            ["10:30", "Igreja do Monte"],
            ["11:00", "Jardim Monte Palace, cerca de 2 horas (18 €, até aos 14 anos grátis; até às 18:00 no inverno, 19:00 de abril a setembro)"],
            ["13:00", "Almoço leve"],
            ["14:00", "Teleférico Monte–Jardim Botânico (09:00–17:00; 11 € num sentido) a atravessar o vale"],
            ["14:15", "Jardim Botânico (10 € maiores de 12, 3 € dos 6 aos 12, menores de 6 grátis; aberto até às 17:30)"],
            ["16:30", "Táxi para a baixa — esperam às saídas do jardim, cerca de 12 € até à estação do teleférico — ou o autocarro"]]),
     "A alternativa sem o Jardim Botânico: depois do Monte Palace, comece a descida nos carros de cesto dos Carreiros do Monte (segunda a sábado, 09:00–18:00) e continue de autocarro ou táxi."], True),
   ("Quanto custam dois dias na Madeira?", [
     "Por adulto, a preços de 2026: o primeiro dia é a volta de táxi — cerca de 160 € pelo carro durante 6 horas (indicativo; divida por todos os ocupantes) mais 5 € do Cabo Girão. O segundo dia: 16 € de teleférico até ao Monte, 18 € do Monte Palace, e depois ou a parte do Jardim Botânico — 11 € de teleférico + 10 € de entrada, mais cerca de 12 € do táxi até à estação do teleférico (esperam às saídas do jardim), ou 26 € com o teleférico do jardim ida e volta ou, em vez disso, os carros de cesto (preço no site dos Carreiros do Monte). O Mercado, a Zona Velha, os miradouros e as duas vilas do primeiro dia não custam nada além do táxi."], True),
   ("Vale a pena alugar carro para dois dias na Madeira?", [
     "Para estes dois dias, não. O estacionamento é limitado na maior parte das paragens do primeiro dia, e o segundo dia é todo a pé e de teleférico — o carro ficaria o dia inteiro numa garagem paga no Funchal. Alugue carro só se juntar um terceiro dia com um roteiro seu."], True),
   ("Posso trocar por uma levada ou um pico?", [
     "Pode — a prova de montanha curta que cabe neste plano é a ida e volta do Pico do Areeiro ao miradouro da Pedra Rija no " + a(L("pt", "/pr1/"), "PR1") + " (1,2 km para cada lado, 4,50 €, com reserva online no SIMplifica — veja " + a(L("pt", "/simplifica-booking/"), "como reservar") + "). Ponha-a no início do primeiro dia e atrase a volta uma hora, e confirme o cume primeiro: " + a(L("pt", "/pico-do-areeiro-weather/"), "tempo e webcams do Pico do Areeiro") + "."], True),
   ("De navio de cruzeiro", [
     "Duas escalas, ou uma escala com pernoita, dividem-se exatamente assim: a volta de táxi no primeiro dia, o Funchal e o Monte no segundo. Combine cada hora de regresso com o motorista ao reservar e guarde pelo menos uma hora de margem antes do all-aboard. O que está aberto hoje na cidade — eventos, lidos, últimos autocarros — está em " + a(L("pt", "/funchal/"), "Funchal hoje") + "."], False),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Madère en deux jours : itinéraire avec horaires",
  desc="Deux jours à Madère ? Un itinéraire minuté : la boucle des belvédères en taxi le premier jour ; Funchal, Monte et le Jardin botanique le second. Prix 2026.",
  h1="Madère en deux jours : un itinéraire minuté qui tient",
  sub="Le premier jour en taxi vers les belvédères de l'île, le second à pied et en téléphérique dans Funchal et Monte — tout le top 5, le Jardin botanique et des prix 2026 honnêtes.",
  body=[
   ("Que faire à Madère en deux jours ?", [
     "Tout ce que demande le top 5, sans courir : le premier jour, une boucle en taxi vers le belvédère d'Eira do Serrado et Curral das Freiras, le skywalk du Cabo Girão et Câmara de Lobos ; le second, Funchal à pied — le Mercado et la vieille ville — puis le téléphérique vers Monte, le jardin Monte Palace et le Jardin botanique. Ce sont les deux plans de notre " + a(L("fr", "/one-day-in-madeira/"), "guide d'un jour") + " faits correctement, un par jour."], True),
   ("Jour 1 — Curral das Freiras, Cabo Girão et Câmara de Lobos : à quelles heures ?", [
     "Une boucle en taxi d'environ 56 km, à peu près 6 heures porte à porte. Convenez du prix de cette boucle exacte à la réservation (des chauffeurs nous ont indiqué environ 160 € pour une journée de 6 heures en octobre 2026 — indicatif, pas un tarif) : Táxis Madeira +351 291 764 476 (taxismadeira.pt) ou AITRAM +351 291 765 760.",
     table(["Heure", "Étape"],
           [["09h00", "Le taxi vous prend à Funchal"],
            ["09h30", "Belvédère d'Eira do Serrado au-dessus de la vallée de Curral das Freiras"],
            ["10h15", "Bourg de Curral das Freiras (2,6 km sous le belvédère)"],
            ["11h15", "Traversée vers la côte sud (environ 35 min)"],
            ["12h00", "Skywalk du Cabo Girão — 20–30 minutes (5 € plus de 12 ans ; ouvert 08h00–20h00)"],
            ["12h45", "Câmara de Lobos : déjeuner, puis la vieille ville et la jetée"],
            ["14h45", "Retour à Funchal (environ 15 min)"],
            ["15h15", "Mercado dos Lavradores (en semaine jusqu'à 19h00)"]]),
     "Le samedi, voyez le Mercado en tout début de journée — il ferme à 14h00 ; le dimanche il est fermé, reportez-le au second jour. Distances routières d'OpenStreetMap ; ce sont des routes de montagne, les temps s'entendent sans circulation."], True),
   ("Jour 2 — Funchal, Monte et le Jardin botanique : à quelles heures ?", [
     "À pied et en téléphérique — pas besoin de taxi. L'étape du Jardin botanique coûte environ 21 € par adulte (11 € de téléphérique dans un sens + 10 € d'entrée) ; si les jardins ne sont pas votre genre, sautez-la et descendez en luge d'osier (ci-dessous).",
     table(["Heure", "Étape"],
           [["09h00", "Flânerie dans la vieille ville — et le Mercado, si le premier jour tombait un week-end"],
            ["10h00", "Téléphérique vers Monte (08h45–17h45 ; 16 € l'aller, 22 € l'aller-retour)"],
            ["10h30", "Église de Monte"],
            ["11h00", "Jardin Monte Palace, environ 2 heures (18 €, gratuit jusqu'à 14 ans ; jusqu'à 18h00 en hiver, 19h00 d'avril à septembre)"],
            ["13h00", "Déjeuner léger"],
            ["14h00", "Téléphérique Monte–Jardin botanique (09h00–17h00 ; 11 € l'aller) au-dessus de la vallée"],
            ["14h15", "Jardin botanique (10 € plus de 12 ans, 3 € de 6 à 12 ans, moins de 6 ans gratuit ; ouvert jusqu'à 17h30)"],
            ["16h30", "Taxi vers le centre — ils attendent aux sorties du jardin, environ 12 € jusqu'à la gare du téléphérique — ou le bus"]]),
     "L'alternative sans le Jardin botanique : après Monte Palace, entamez la descente en luge d'osier des Carreiros do Monte (lundi–samedi 09h00–18h00) et continuez en bus ou en taxi."], True),
   ("Combien coûtent deux jours à Madère ?", [
     "Par adulte, aux prix 2026 : le premier jour, la boucle en taxi — environ 160 € la voiture pour 6 heures (indicatif ; à partager entre les occupants) plus 5 € pour le Cabo Girão. Le second jour : 16 € de téléphérique vers Monte, 18 € pour Monte Palace, puis soit l'étape du Jardin botanique — 11 € de téléphérique + 10 € d'entrée, plus environ 12 € de taxi jusqu'à la gare du téléphérique (ils attendent aux sorties du jardin), soit 26 € avec le téléphérique du jardin aller-retour, soit la luge à la place (prix sur le site des Carreiros do Monte). Le Mercado, la vieille ville, les belvédères et les deux bourgs du premier jour ne coûtent rien au-delà du taxi."], True),
   ("Faut-il louer une voiture pour deux jours à Madère ?", [
     "Pour ces deux jours, non. Le stationnement est limité à la plupart des arrêts du premier jour, et le second jour se fait entièrement à pied et en téléphérique — la voiture resterait toute la journée dans un parking payant de Funchal. Louez une voiture seulement si vous ajoutez un troisième jour avec votre propre route."], True),
   ("Peut-on y glisser une levada ou un pic ?", [
     "Oui — la courte marche de montagne qui tient dans ce plan est l'aller-retour du Pico do Areeiro au belvédère de Pedra Rija sur le " + a(L("fr", "/pr1/"), "PR1") + " (1,2 km par sens, 4,50 €, réservation en ligne sur SIMplifica — voir " + a(L("fr", "/simplifica-booking/"), "comment réserver") + "). Placez-la au début du premier jour et décalez la boucle d'une heure, et vérifiez d'abord le sommet : " + a(L("fr", "/pico-do-areeiro-weather/"), "météo et webcams du Pico do Arieiro") + "."], True),
   ("Depuis un navire de croisière", [
     "Deux escales, ou une escale avec nuit à quai, se partagent exactement ainsi : la boucle en taxi le premier jour, Funchal et Monte le second. Convenez de chaque heure de retour avec le chauffeur à la réservation et gardez au moins une heure de marge avant le rappel à bord. Ce qui est ouvert en ville aujourd'hui — événements, lidos, derniers bus — est sur " + a(L("fr", "/funchal/"), "Funchal aujourd'hui") + "."], False),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Zwei Tage auf Madeira: Route mit Uhrzeiten",
  desc="Zwei Tage auf Madeira? Route mit Uhrzeiten: Taxi-Runde zu den Aussichtspunkten an Tag eins; Funchal, Monte und Botanischer Garten an Tag zwei. Preise 2026.",
  h1="Zwei Tage auf Madeira: eine Route mit Uhrzeiten, die passt",
  sub="Tag eins per Taxi zu den Aussichtspunkten der Insel, Tag zwei zu Fuß und per Seilbahn in Funchal und Monte — die ganzen Top 5, der Botanische Garten und ehrliche Preise 2026.",
  body=[
   ("Was kann man auf Madeira in zwei Tagen machen?", [
     "Alles, was die Top 5 verlangen, ohne Hetze: an Tag eins eine Taxirunde zum Aussichtspunkt Eira do Serrado und nach Curral das Freiras, zum Skywalk am Cabo Girão und nach Câmara de Lobos; an Tag zwei Funchal zu Fuß — der Mercado und die Altstadt — dann die Seilbahn nach Monte, der Garten Monte Palace und der Botanische Garten. Es sind die beiden Pläne unseres " + a(L("de", "/one-day-in-madeira/"), "Ein-Tages-Guides") + ", richtig gemacht: einer pro Tag."], True),
   ("Tag 1 — Curral das Freiras, Cabo Girão und Câmara de Lobos: zu welchen Zeiten?", [
     "Eine Taxirunde von etwa 56 km, rund 6 Stunden Tür zu Tür. Vereinbaren Sie den Preis für genau diese Runde beim Buchen (Fahrer nannten uns im Oktober 2026 etwa 160 € für einen 6-Stunden-Tag — ein Richtwert, kein Tarif): Táxis Madeira +351 291 764 476 (taxismadeira.pt) oder AITRAM +351 291 765 760.",
     table(["Uhrzeit", "Station"],
           [["09:00", "Das Taxi holt Sie in Funchal ab"],
            ["09:30", "Aussichtspunkt Eira do Serrado über dem Tal von Curral das Freiras"],
            ["10:15", "Ort Curral das Freiras (2,6 km unterhalb des Aussichtspunkts)"],
            ["11:15", "Fahrt zur Südküste (etwa 35 min)"],
            ["12:00", "Skywalk am Cabo Girão — 20–30 Minuten (5 € für über 12-Jährige; täglich 08:00–20:00)"],
            ["12:45", "Câmara de Lobos: Mittagessen, dann Altstadt und Mole"],
            ["14:45", "Zurück nach Funchal (etwa 15 min)"],
            ["15:15", "Mercado dos Lavradores (werktags bis 19:00)"]]),
     "Am Samstag den Mercado gleich am Morgen ansehen — er schließt um 14:00; am Sonntag ist er zu, dann auf Tag zwei verschieben. Straßenentfernungen aus OpenStreetMap; es sind Bergstraßen, die Zeiten gelten ohne Verkehr."], True),
   ("Tag 2 — Funchal, Monte und Botanischer Garten: zu welchen Zeiten?", [
     "Zu Fuß und per Seilbahn — kein Taxi nötig. Der Abstecher zum Botanischen Garten kostet etwa 21 € pro Erwachsenem (11 € Seilbahn einfach + 10 € Eintritt); wer kein Gartenfreund ist, lässt ihn aus und nimmt stattdessen die Korbschlitten (unten).",
     table(["Uhrzeit", "Station"],
           [["09:00", "Bummel durch die Altstadt — und der Mercado, falls Tag eins aufs Wochenende fiel"],
            ["10:00", "Seilbahn hinauf nach Monte (08:45–17:45; 16 € einfach, 22 € hin und zurück)"],
            ["10:30", "Kirche von Monte"],
            ["11:00", "Garten Monte Palace, etwa 2 Stunden (18 €, bis 14 Jahre frei; im Winter bis 18:00, April–September bis 19:00)"],
            ["13:00", "Leichtes Mittagessen"],
            ["14:00", "Seilbahn Monte–Botanischer Garten (09:00–17:00; 11 € einfach) über das Tal"],
            ["14:15", "Botanischer Garten (10 € über 12, 3 € von 6 bis 12, unter 6 frei; bis 17:30)"],
            ["16:30", "Taxi hinunter in die Stadt — sie warten an den Ausgängen des Gartens, etwa 12 € bis zur Talstation der Seilbahn — oder der Bus"]]),
     "Die Alternative ohne Botanischen Garten: nach Monte Palace die Abfahrt mit den Korbschlitten der Carreiros do Monte beginnen (Montag–Samstag 09:00–18:00) und mit Bus oder Taxi weiterfahren."], True),
   ("Was kosten zwei Tage auf Madeira?", [
     "Pro Erwachsenem, zu Preisen von 2026: Tag eins ist die Taxirunde — etwa 160 € für den Wagen für 6 Stunden (Richtwert; durch alle Mitfahrer teilen) plus 5 € für den Cabo Girão. Tag zwei: 16 € Seilbahn nach Monte, 18 € Monte Palace, dann entweder der Botanische Garten — 11 € Seilbahn + 10 € Eintritt, plus etwa 12 € fürs Taxi zur Talstation der Seilbahn (sie warten an den Gartenausgängen), oder 26 € mit der Gartenseilbahn hin und zurück oder stattdessen die Schlittenfahrt (Preis auf der Seite der Carreiros do Monte). Der Mercado, die Altstadt, die Aussichtspunkte und die beiden Orte von Tag eins kosten nichts über das Taxi hinaus."], True),
   ("Lohnt sich ein Mietwagen für zwei Tage auf Madeira?", [
     "Für diese zwei Tage: nein. An den meisten Stationen von Tag eins ist das Parken knapp, und Tag zwei läuft ganz zu Fuß und per Seilbahn — der Wagen stünde den Tag über in einem bezahlten Parkhaus in Funchal. Ein Mietwagen lohnt erst mit einem dritten Tag auf eigener Route."], True),
   ("Passt eine Levada oder ein Gipfel hinein?", [
     "Ja — die kurze Bergprobe, die in diesen Plan passt, ist hin und zurück vom Pico do Areeiro zum Aussichtspunkt Pedra Rija auf dem " + a(L("de", "/pr1/"), "PR1") + " (je 1,2 km, 4,50 €, online auf SIMplifica gebucht — siehe " + a(L("de", "/simplifica-booking/"), "wie man bucht") + "). Legen Sie sie an den Anfang von Tag eins und verschieben Sie die Runde um eine Stunde — und prüfen Sie vorher den Gipfel: " + a(L("de", "/pico-do-areeiro-weather/"), "Wetter und Webcams am Pico do Arieiro") + "."], True),
   ("Vom Kreuzfahrtschiff", [
     "Zwei Hafentage, oder ein Aufenthalt über Nacht, teilen sich genau so auf: die Taxirunde am ersten Tag, Funchal und Monte am zweiten. Vereinbaren Sie jede Rückkehrzeit beim Buchen mit dem Fahrer und lassen Sie mindestens eine Stunde Puffer vor dem All-aboard. Was heute in der Stadt offen ist — Veranstaltungen, Lidos, letzte Busse — steht auf " + a(L("de", "/funchal/"), "Funchal heute") + "."], False),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Dwa dni na Maderze: plan z godzinami",
  desc="Dwa dni na Maderze? Plan z godzinami: pętla taksówką po punktach widokowych pierwszego dnia; Funchal, Monte i Ogród Botaniczny drugiego. Ceny 2026.",
  h1="Dwa dni na Maderze: plan z godzinami, który się mieści",
  sub="Pierwszy dzień taksówką po punktach widokowych wyspy, drugi pieszo i kolejką po Funchal i Monte — całe top 5, Ogród Botaniczny i uczciwe ceny 2026.",
  body=[
   ("Co robić na Maderze w dwa dni?", [
     "Wszystko, czego wymaga top 5, bez pośpiechu: pierwszego dnia pętla taksówką na punkt widokowy Eira do Serrado i do Curral das Freiras, na skywalk Cabo Girão i do Câmara de Lobos; drugiego dnia Funchal pieszo — Mercado i starówka — potem kolejka na Monte, ogród Monte Palace i Ogród Botaniczny. To dwa plany z naszego " + a(L("pl", "/one-day-in-madeira/"), "przewodnika na jeden dzień") + " zrobione porządnie, po jednym na dzień."], True),
   ("Dzień 1 — Curral das Freiras, Cabo Girão i Câmara de Lobos: o których godzinach?", [
     "Pętla taksówką około 56 km, mniej więcej 6 godzin od drzwi do drzwi. Umów cenę za dokładnie tę trasę przy rezerwacji (kierowcy podali nam około 160 € za 6-godzinny dzień w październiku 2026 — kwota orientacyjna, nie taryfa): Táxis Madeira +351 291 764 476 (taxismadeira.pt) lub AITRAM +351 291 765 760.",
     table(["Godzina", "Przystanek"],
           [["09:00", "Taksówka odbiera Cię w Funchal"],
            ["09:30", "Punkt widokowy Eira do Serrado nad doliną Curral das Freiras"],
            ["10:15", "Miasteczko Curral das Freiras (2,6 km poniżej punktu widokowego)"],
            ["11:15", "Przejazd na południowe wybrzeże (około 35 min)"],
            ["12:00", "Skywalk Cabo Girão — 20–30 minut (5 € powyżej 12 lat; codziennie 08:00–20:00)"],
            ["12:45", "Câmara de Lobos: obiad, potem starówka i molo"],
            ["14:45", "Powrót do Funchal (około 15 min)"],
            ["15:15", "Mercado dos Lavradores (w dni robocze do 19:00)"]]),
     "W sobotę zobacz Mercado z samego rana — zamyka o 14:00; w niedzielę jest zamknięte, przełóż je na drugi dzień. Odległości drogowe z OpenStreetMap; to drogi górskie, więc czasy są bez ruchu."], True),
   ("Dzień 2 — Funchal, Monte i Ogród Botaniczny: o których godzinach?", [
     "Pieszo i kolejką — taksówka niepotrzebna. Odcinek z Ogrodem Botanicznym kosztuje około 21 € od dorosłego (11 € kolejka w jedną stronę + 10 € wstęp); jeśli ogrody to nie Twoja bajka, pomiń go i zjedź saniami (niżej).",
     table(["Godzina", "Przystanek"],
           [["09:00", "Spacer po starówce — i Mercado, jeśli pierwszy dzień wypadł w weekend"],
            ["10:00", "Kolejka linowa na Monte (08:45–17:45; 16 € w jedną stronę, 22 € w obie)"],
            ["10:30", "Kościół na Monte"],
            ["11:00", "Ogród Monte Palace, około 2 godzin (18 €, do 14 lat za darmo; zimą do 18:00, od kwietnia do września do 19:00)"],
            ["13:00", "Lekki obiad"],
            ["14:00", "Kolejka Monte–Ogród Botaniczny (09:00–17:00; 11 € w jedną stronę) nad doliną"],
            ["14:15", "Ogród Botaniczny (10 € powyżej 12 lat, 3 € od 6 do 12, poniżej 6 za darmo; do 17:30)"],
            ["16:30", "Taksówka do centrum — czekają przy wyjściach z ogrodu, około 12 € do stacji kolejki — albo autobus"]]),
     "Alternatywa bez Ogrodu Botanicznego: po Monte Palace zacznij zjazd wiklinowymi saniami Carreiros do Monte (poniedziałek–sobota 09:00–18:00) i jedź dalej autobusem lub taksówką."], True),
   ("Ile kosztują dwa dni na Maderze?", [
     "Od dorosłego, w cenach 2026: pierwszy dzień to pętla taksówką — około 160 € za auto na 6 godzin (orientacyjnie; podziel między wszystkich pasażerów) plus 5 € za Cabo Girão. Drugi dzień: 16 € kolejka na Monte, 18 € Monte Palace, potem albo odcinek z Ogrodem Botanicznym — 11 € kolejka + 10 € wstęp, plus około 12 € za taksówkę do stacji kolejki (czekają przy wyjściach z ogrodu), albo 26 € z kolejką ogrodową w obie strony, albo zamiast tego zjazd saniami (cena na stronie Carreiros do Monte). Mercado, starówka, punkty widokowe i oba miasteczka pierwszego dnia nie kosztują nic poza taksówką."], True),
   ("Czy warto wynająć auto na dwa dni na Maderze?", [
     "Na te dwa dni — nie. W większości przystanków pierwszego dnia parkowanie jest ograniczone, a drugi dzień jest w całości pieszo i kolejką — auto stałoby cały dzień w płatnym garażu w Funchal. Wynajmij auto dopiero, gdy dodasz trzeci dzień z własną trasą."], True),
   ("Czy da się wcisnąć levadę albo szczyt?", [
     "Tak — krótka górska próbka, która mieści się w tym planie, to tam i z powrotem z Pico do Areeiro do punktu widokowego Pedra Rija na " + a(L("pl", "/pr1/"), "PR1") + " (po 1,2 km, 4,50 €, rezerwacja online w SIMplifica — zobacz " + a(L("pl", "/simplifica-booking/"), "jak zarezerwować") + "). Wstaw ją na początek pierwszego dnia i przesuń pętlę o godzinę, a najpierw sprawdź szczyt: " + a(L("pl", "/pico-do-areeiro-weather/"), "pogoda i kamery na Pico do Arieiro") + "."], True),
   ("Ze statku wycieczkowego", [
     "Dwa dni w porcie, albo postój z noclegiem, dzielą się dokładnie tak: pętla taksówką pierwszego dnia, Funchal i Monte drugiego. Umów każdą godzinę powrotu z kierowcą przy rezerwacji i zostaw co najmniej godzinę zapasu przed all-aboard. Co jest dziś otwarte w mieście — wydarzenia, lida, ostatnie autobusy — znajdziesz na " + a(L("pl", "/funchal/"), "Funchal dzisiaj") + "."], False),
   ("Źródła", [None], False),
  ]),
}


def plain(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())


def main():
    for lang in LANGS:
        c = dict(COPY[lang])
        c["body"] = [(h, [src(lang) if p is None else p for p in parts]) for h, parts, _ in COPY[lang]["body"]]
        out, lt, ld = gi.build(SLUG, lang, c, "WebPage")
        h = open(out, encoding="utf-8").read()
        faq = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(parts[0])}}
            for q, parts, isq in COPY[lang]["body"] if isq]}
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
