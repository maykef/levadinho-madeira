#!/usr/bin/env python3
"""Writes /botanical-garden/ × 5 languages from the free-walks page shell (owner, 2026-10-21).

What it says, and where from:
  verdict        the owner, first-hand, 2026-10-21 (an avid botanical collector): a resounding yes — beautiful
                 specimens, the succulents and cacti sections, bromeliads and orchids in a glasshouse, amazing
                 views, peace away from the crowds, a small café (coffee + pastel de nata). One criticism: the
                 Madeira endemics section is too small. Day order with the toboggans: up early, garden FIRST,
                 cable back to Monte, Monte Palace, then the toboggans (they only run downhill from Monte).
  entry          Portaria 48/2026 Annex II pt 3.1 (PDF read 2026-10-20): €10 over-12s (2027-29: 12.50/15/17.50),
                 €3 ages 6-12, under-6 free; art. 16: RAM residents exempt. Hours 09:00-17:30 (PLACES).
  combo          telefericojardimbotanico.com/en/prices.html (read 2026-10-21): cable car + garden entry in one
                 ticket, adult €19 one way / €24 round trip, child 7-14 €9/€12; cable 09:00-17:00; the operator's
                 own guidance: the visit takes about 1h30-2 hours. Watched daily by scripts/check_prices.py.
  taxi ~€12      owner first-hand (2026-10-20): taxis wait at the garden's exits; ~€12 down to the Funchal
                 cable-car station. INDICATIVE. Walk-down alternative: bus stop CAM Meio Papagaios D (310A),
                 fine with time to spare (owner).
  Monte Palace   €18, under-15s free (montepalacemadeira.com) — for the comparison section.

Re-run after changing the copy: it keeps dateModified, then runs gen_site_nav.py, gen_cta.py, gen_owner.py and
gen_schema.py itself (the page is in GUIDES / TAGS).
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import LANGS, PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "botanical-garden"
ROOT = gi.ROOT
P48 = "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Portarias/Port48ISerie027_2026.pdf"
TJ = "https://telefericojardimbotanico.com/en/prices.html"
MP = "https://montepalacemadeira.com/visita/"
a, ext = gi.a, gi.ext


def src(lang):
    return ('<p class="src">' + ext(P48, "Portaria 48/2026") + " · " + ext(TJ, "Teleférico Jardim Botânico")
            + " · " + ext(MP, "Monte Palace Madeira") + "</p>")


def table(head, rows):
    return ('<div class="tbl"><table>\n    <thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead>\n    <tbody>\n"
            + "".join("      <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n" for r in rows) + "    </tbody>\n  </table></div>")


def L(lang, path):
    return f"{PREFIX[lang]}{path}"


# Owner's own photos, October 2026 (img/CREDITS.txt). webp shown, jpg kept for og:image.
def fig(name, alt, cap):
    return (f'<figure style="margin:1.2em 0"><img src="/img/botanical/{name}.webp" alt="{html.escape(alt)}" '
            f'loading="lazy" width="900" height="1200" style="width:100%;max-width:560px;height:auto;border-radius:8px;display:block">'
            f'<figcaption style="font-size:.85em;opacity:.8;margin-top:.4em">{cap}</figcaption></figure>')


FIGS = {
 "en": {"trees": fig("garden-trees", "Tall araucaria and fan palms in the Madeira Botanical Garden",
                     "The garden's big specimens against the sky. Photo: Mayke De Freitas Santos."),
        "endemic": fig("endemic-argyranthemum", "Argyranthemum pinnatifidum, a labelled Madeira endemic, in the Botanical Garden",
                       "Argyranthemum pinnatifidum ssp. pinnatifidum — one of the labelled Madeira endemics. Photo: Mayke De Freitas Santos."),
        "cable": fig("cable-car-view", "View from the garden cable car over the João Gomes valley towards Funchal and the bay",
                     "The ride in: the garden cable car crosses the João Gomes valley with Funchal and the port below. Photo: Mayke De Freitas Santos.")},
 "pt": {"trees": fig("garden-trees", "Araucária alta e palmeiras no Jardim Botânico da Madeira",
                     "Os grandes espécimes do jardim contra o céu. Foto: Mayke De Freitas Santos."),
        "endemic": fig("endemic-argyranthemum", "Argyranthemum pinnatifidum, endemismo da Madeira identificado, no Jardim Botânico",
                       "Argyranthemum pinnatifidum ssp. pinnatifidum — um dos endemismos da Madeira identificados. Foto: Mayke De Freitas Santos."),
        "cable": fig("cable-car-view", "Vista do teleférico do jardim sobre o vale de João Gomes, com o Funchal e a baía",
                     "A chegada: o teleférico do jardim atravessa o vale de João Gomes com o Funchal e o porto lá em baixo. Foto: Mayke De Freitas Santos.")},
 "fr": {"trees": fig("garden-trees", "Grand araucaria et palmiers au Jardin botanique de Madère",
                     "Les grands spécimens du jardin contre le ciel. Photo : Mayke De Freitas Santos."),
        "endemic": fig("endemic-argyranthemum", "Argyranthemum pinnatifidum, endémique de Madère étiquetée, au Jardin botanique",
                       "Argyranthemum pinnatifidum ssp. pinnatifidum — l'une des endémiques de Madère étiquetées. Photo : Mayke De Freitas Santos."),
        "cable": fig("cable-car-view", "Vue du téléphérique du jardin sur la vallée de João Gomes, vers Funchal et la baie",
                     "L'arrivée : le téléphérique du jardin traverse la vallée de João Gomes, Funchal et le port en contrebas. Photo : Mayke De Freitas Santos.")},
 "de": {"trees": fig("garden-trees", "Hohe Araukarie und Fächerpalmen im Botanischen Garten Madeiras",
                     "Die großen Exemplare des Gartens vor dem Himmel. Foto: Mayke De Freitas Santos."),
        "endemic": fig("endemic-argyranthemum", "Argyranthemum pinnatifidum, ein beschriftetes Madeira-Endemit, im Botanischen Garten",
                       "Argyranthemum pinnatifidum ssp. pinnatifidum — eines der beschrifteten Madeira-Endemiten. Foto: Mayke De Freitas Santos."),
        "cable": fig("cable-car-view", "Blick aus der Gartenseilbahn über das João-Gomes-Tal auf Funchal und die Bucht",
                     "Die Anfahrt: die Gartenseilbahn quert das João-Gomes-Tal, unten Funchal und der Hafen. Foto: Mayke De Freitas Santos.")},
 "pl": {"trees": fig("garden-trees", "Wysoka araukaria i palmy w Ogrodzie Botanicznym Madery",
                     "Wielkie okazy ogrodu na tle nieba. Fot.: Mayke De Freitas Santos."),
        "endemic": fig("endemic-argyranthemum", "Argyranthemum pinnatifidum, opisany endemit Madery, w Ogrodzie Botanicznym",
                       "Argyranthemum pinnatifidum ssp. pinnatifidum — jeden z opisanych endemitów Madery. Fot.: Mayke De Freitas Santos."),
        "cable": fig("cable-car-view", "Widok z kolejki ogrodowej na dolinę João Gomes, Funchal i zatokę",
                     "Dojazd: kolejka ogrodowa przecina dolinę João Gomes, w dole Funchal i port. Fot.: Mayke De Freitas Santos.")},
}


# Sections: (heading, parts, is_question). A question's FAQ answer is its first paragraph, verbatim.
COPY = {
 "en": dict(
  title="Madeira Botanical Garden: worth it, prices, how to go",
  desc="Is Madeira's Botanical Garden worth it? A resounding yes: €10 entry or the €19 cable-car combo, a plant collector's verdict and the right day order.",
  h1="The Botanical Garden: worth it, and how to do it right",
  sub="Written from a visit with a botanical collector's eye: what's genuinely good, the one weak spot, the honest prices and the order that lets you fit Monte and the toboggans into the same day.",
  body=[
   ("Is the Botanical Garden worth it?", [
     "A resounding yes. There are beautiful specimens throughout, and the strongest sections are the succulents and cacti terraces and the glasshouse with bromeliads and orchids; around them you get amazing views over Funchal and the bay, and — rare for Madeira's big sights — peace and tranquility away from the crowds. The operator's own guidance says the visit takes about 1h30–2 hours, which matches our experience. There is a small café for a good coffee and a traditional pastel de nata halfway through.",
     "Why hunt out the endemics at all? Madeira belongs to Macaronesia, and its laurel forest is a UNESCO World Heritage site: the laurels, the ferns, the wild blueberries and the wild olive trees grow here and almost nowhere else on Earth — there is a wild olive in the garden itself, right by the endemics section. Which brings our one honest criticism, from an avid botanical collector's eye: that section is small — too small, in our view, for the island that owns this flora. Go for the collection and the setting, not for an endemics masterclass.",
     "A drawback to know before you go: the garden sits on the island's dry southern side. Even high above Funchal it is much drier and hotter than the Serra do Faial — the central massif of Pico do Areeiro and Pico Ruivo — so what thrives here is the sun-loving collection, not the cloud forest. For the living laurel forest, walk a levada: " + a(L("en", "/best-levada-walks/"), "the best levada walks") + ".",
     ], True),
   ("How much does the Botanical Garden cost?", [
     "Entry is €10 for visitors over 12, €3 for ages 6–12 and free under 6; Madeira residents enter free (Portaria 48/2026). The garden is open 09:00–17:30. The better buy for most visitors is the combo ticket of the garden cable car, which includes the entry: €19 one way or €24 round trip (children 7–14: €9/€12).",
     table(["Ticket", "Adult", "Child"],
           [["Garden entry alone", "€10", "€3 (6–12), under-6 free"],
            ["Cable car + entry, one way", "€19", "€9 (7–14)"],
            ["Cable car + entry, round trip", "€24", "€12 (7–14)"]])], True),
   ("How do I get to the Botanical Garden?", [
     "The scenic way is the garden cable car from Babosas, a short walk from Monte's centre (09:00–17:00, nine minutes across the valley) — with the entry included in its ticket. Leaving, you don't have to ride back: taxis wait at the garden's exits, and the trip down to the Funchal cable-car station is about €12 (indicative — confirm with the driver). With time to spare you can instead walk down from the lower gate to the CAM Meio Papagaios D bus stop (line 310A) and take the bus; not worth the hassle if you're on the clock.",
     "The full Funchal day around it is " + a(L("en", "/two-days-in-madeira/"), "day two of our two-day plan") + "."], True),
   ("Can I do the garden, Monte Palace and the toboggans in one day?", [
     "Yes — but only in this order: go up early, see the Botanical Garden first, ride the cable car back to Monte, do Monte Palace, and finish with the wicker toboggans. The order matters because the toboggans only run downhill from Monte (Monday–Saturday, 09:00–18:00): leave the garden last and you come back to Monte too late, or not at all. Early start, garden before lunch, Monte Palace after, toboggans as the grand exit.",
     "And if you do end up at the Botanical Garden late, or keep it as the final attraction, there is no trap: simply exit and take a taxi from there — they usually wait outside, about €12 all the way down to the Funchal cable-car station (indicative). If you'd rather experience vertigo on a bus, walk a little further down to the Meio Papagaios stop (line 310A) — it's marked on the day-two map.",
     "Everything in Monte, timed and priced: " + a(L("en", "/monte/"), "Monte: what to see") + "."], True),
   ("Botanical Garden or Monte Palace?", [
     "Different gardens for different people. Monte Palace (€18, under-15s free) is the designed spectacle — koi lakes, tile panels, drama — and the obvious family pick since the children enter free. The Botanical Garden is the plant collection proper: cheaper, quieter, better labelled, with the cacti terraces and the orchid glasshouse, and views Monte Palace doesn't have. A plant lover should not skip the Botanical Garden; with two days in Madeira, do both — they are one cable-car ride apart."], True),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="Jardim Botânico da Madeira: vale a pena? Preços e acesso",
  desc="O Jardim Botânico vale a pena? Um sim rotundo: 10 € de entrada ou 19 € combinado com o teleférico, o olhar de um coletor e a ordem certa do dia.",
  h1="O Jardim Botânico: vale a pena, e como fazer bem",
  sub="Escrito a partir de uma visita com olho de coletor botânico: o que é mesmo bom, o ponto fraco, os preços honestos e a ordem que permite juntar o Monte e os carros de cesto no mesmo dia.",
  body=[
   ("O Jardim Botânico vale a pena?", [
     "Um sim rotundo. Há espécimes bonitos por todo o lado, e as secções mais fortes são os socalcos de suculentas e catos e a estufa com bromélias e orquídeas; à volta, vistas fantásticas sobre o Funchal e a baía e — coisa rara nos grandes pontos da Madeira — paz e tranquilidade longe das multidões. A indicação do próprio operador é que a visita leva cerca de 1h30–2 horas, o que bate certo com a nossa experiência. Há um pequeno café para um bom café e um pastel de nata tradicional a meio.",
     "E porquê procurar os endemismos? A Madeira pertence à Macaronésia, e a sua Laurissilva é Património Mundial da UNESCO: os loureiros, os fetos, as uveiras bravas e os zambujeiros crescem aqui e em quase mais lado nenhum do planeta — há um zambujeiro no próprio jardim, mesmo junto à secção dos endemismos. E é daí que vem a nossa crítica honesta, com olho de coletor botânico ávido: essa secção é pequena — pequena de mais, na nossa opinião, para a ilha dona desta flora. Vá pela coleção e pelo lugar, não por uma aula de endemismos.",
     "Um senão que convém saber: o jardim fica no lado seco e soalheiro do sul da ilha. Mesmo bem acima do Funchal, é muito mais seco e quente do que a Serra do Faial — o maciço central do Pico do Areeiro e do Pico Ruivo — por isso o que ali prospera é a coleção amante de sol, não a floresta das nuvens. Para a Laurissilva viva, caminhe numa levada: " + a(L("pt", "/best-levada-walks/"), "as melhores levadas") + ".",
     ], True),
   ("Quanto custa o Jardim Botânico?", [
     "A entrada custa 10 € para maiores de 12 anos, 3 € dos 6 aos 12 e é grátis até aos 6; os residentes na Madeira entram grátis (Portaria 48/2026). O jardim abre das 09:00 às 17:30. Para a maioria dos visitantes compensa mais o bilhete combinado do teleférico do jardim, que inclui a entrada: 19 € num sentido ou 24 € ida e volta (crianças 7–14 anos: 9 €/12 €).",
     table(["Bilhete", "Adulto", "Criança"],
           [["Só a entrada no jardim", "10 €", "3 € (6–12), grátis até aos 6"],
            ["Teleférico + entrada, num sentido", "19 €", "9 € (7–14)"],
            ["Teleférico + entrada, ida e volta", "24 €", "12 € (7–14)"]])], True),
   ("Como se chega ao Jardim Botânico?", [
     "O caminho bonito é o teleférico do jardim a partir das Babosas, a uma curta caminhada do centro do Monte (09:00–17:00, nove minutos a atravessar o vale) — com a entrada incluída no bilhete. À saída não precisa de voltar pelo ar: há táxis à espera junto às saídas do jardim, e a descida até à estação do teleférico do Funchal custa cerca de 12 € (indicativo — confirme com o motorista). Com tempo de sobra pode, em alternativa, descer a pé da saída de baixo até à paragem CAM Meio Papagaios D (carreira 310A) e apanhar o autocarro; não vale a pena se anda contra o relógio.",
     "O dia completo no Funchal à volta disto é o " + a(L("pt", "/two-days-in-madeira/"), "segundo dia do nosso plano de dois dias") + "."], True),
   ("Dá para fazer o jardim, o Monte Palace e os carros de cesto num dia?", [
     "Dá — mas só por esta ordem: suba cedo, veja primeiro o Jardim Botânico, volte de teleférico ao Monte, faça o Monte Palace e termine nos carros de cesto. A ordem importa porque os carros de cesto só descem a partir do Monte (segunda a sábado, 09:00–18:00): deixe o jardim para o fim e regressa ao Monte tarde de mais, ou já sem descidas. Começo cedo, jardim antes do almoço, Monte Palace a seguir, carros de cesto como saída em grande.",
     "E se acabar por fazer o Jardim Botânico tarde, ou o deixar como última atração, não há armadilha: basta sair e apanhar um táxi ali mesmo — costumam esperar à porta, cerca de 12 € até à estação do teleférico do Funchal (indicativo). Se preferir experimentar vertigens de autocarro, desça mais um pouco até à paragem Meio Papagaios (carreira 310A) — está marcada no mapa do segundo dia.",
     "Tudo o que há no Monte, com tempos e preços: " + a(L("pt", "/monte/"), "Monte: o que ver") + "."], True),
   ("Jardim Botânico ou Monte Palace?", [
     "Jardins diferentes para pessoas diferentes. O Monte Palace (18 €, menores de 15 grátis) é o espetáculo desenhado — lagos de carpas, azulejos, dramatismo — e a escolha óbvia em família, porque as crianças entram grátis. O Jardim Botânico é a coleção de plantas propriamente dita: mais barato, mais calmo, melhor identificado, com os socalcos de catos e a estufa das orquídeas, e vistas que o Monte Palace não tem. Quem gosta de plantas não deve saltar o Jardim Botânico; com dois dias na Madeira, faça os dois — estão à distância de um teleférico."], True),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Jardin botanique de Madère : ça vaut le coup ? Prix, accès",
  desc="Le Jardin botanique vaut-il le coup ? Un oui franc : entrée 10 € ou combiné téléphérique à 19 €, l'avis d'un collectionneur et le bon ordre du jour.",
  h1="Le Jardin botanique : ça vaut le coup, et comment bien faire",
  sub="Écrit après une visite avec un œil de collectionneur botanique : ce qui est vraiment bien, le point faible, les prix honnêtes et l'ordre qui permet de caser Monte et les luges le même jour.",
  body=[
   ("Le Jardin botanique vaut-il le coup ?", [
     "Un oui franc. De beaux spécimens partout, avec en point fort les terrasses de succulentes et de cactus et la serre aux broméliacées et aux orchidées ; autour, des vues superbes sur Funchal et la baie et — chose rare parmi les grands sites de Madère — du calme et de la tranquillité, loin des foules. L'opérateur lui-même indique qu'il faut environ 1 h 30 à 2 h de visite, ce qui correspond à notre expérience. Un petit café permet de faire une pause avec un bon café et un pastel de nata traditionnel.",
     "Pourquoi chercher les endémiques ? Madère appartient à la Macaronésie, et sa forêt de lauriers est classée au patrimoine mondial de l'UNESCO : les lauriers, les fougères, les myrtilles sauvages et les oliviers sauvages poussent ici et presque nulle part ailleurs sur Terre — il y a un olivier sauvage dans le jardin même, juste à côté de la section des endémiques. D'où notre critique honnête, avec un œil de collectionneur botanique passionné : cette section est petite — trop petite, à notre avis, pour l'île à qui appartient cette flore. Venez pour la collection et le cadre, pas pour une leçon d'endémisme.",
     "Un défaut à connaître avant d'y aller : le jardin se trouve sur le versant sud, le côté sec de l'île. Même haut au-dessus de Funchal, il y fait bien plus sec et plus chaud que dans la Serra do Faial — le massif central du Pico do Areeiro et du Pico Ruivo — si bien que c'est la collection de plein soleil qui y prospère, pas la forêt de nuages. Pour la forêt de lauriers vivante, marchez le long d'une levada : " + a(L("fr", "/best-levada-walks/"), "les plus belles levadas") + ".",
     ], True),
   ("Combien coûte le Jardin botanique ?", [
     "L'entrée coûte 10 € au-dessus de 12 ans, 3 € de 6 à 12 ans, gratuite avant 6 ans ; les résidents de Madère entrent gratuitement (Portaria 48/2026). Le jardin est ouvert de 09:00 à 17:30. Pour la plupart des visiteurs, la meilleure affaire est le billet combiné du téléphérique du jardin, entrée comprise : 19 € l'aller ou 24 € l'aller-retour (enfants 7–14 ans : 9 €/12 €).",
     table(["Billet", "Adulte", "Enfant"],
           [["Entrée seule", "10 €", "3 € (6–12), gratuit avant 6 ans"],
            ["Téléphérique + entrée, aller", "19 €", "9 € (7–14)"],
            ["Téléphérique + entrée, aller-retour", "24 €", "12 € (7–14)"]])], True),
   ("Comment aller au Jardin botanique ?", [
     "Le chemin panoramique est le téléphérique du jardin depuis Babosas, à quelques minutes à pied du centre de Monte (09:00–17:00, neuf minutes au-dessus de la vallée) — entrée comprise dans le billet. À la sortie, pas besoin de reprendre les airs : des taxis attendent aux sorties du jardin, et la descente jusqu'à la gare du téléphérique de Funchal coûte environ 12 € (indicatif — à confirmer avec le chauffeur). Avec du temps devant soi, on peut aussi descendre à pied de la sortie basse jusqu'à l'arrêt CAM Meio Papagaios D (ligne 310A) et prendre le bus ; pas la peine si l'on est à l'heure près.",
     "La journée complète à Funchal autour : " + a(L("fr", "/two-days-in-madeira/"), "le deuxième jour de notre plan de deux jours") + "."], True),
   ("Peut-on faire le jardin, Monte Palace et les luges le même jour ?", [
     "Oui — mais seulement dans cet ordre : montez tôt, voyez d'abord le Jardin botanique, revenez à Monte par le téléphérique, faites Monte Palace, et terminez par les luges d'osier. L'ordre compte parce que les luges ne descendent que depuis Monte (du lundi au samedi, 09:00–18:00) : gardez le jardin pour la fin et vous revenez à Monte trop tard, ou plus du tout. Départ matinal, jardin avant midi, Monte Palace ensuite, luges en apothéose.",
     "Et si vous finissez quand même le Jardin botanique tard, ou le gardez pour la fin : aucun piège — sortez et prenez un taxi sur place, ils attendent généralement dehors, environ 12 € jusqu'à la gare du téléphérique de Funchal (indicatif). Pour goûter au vertige en bus, descendez un peu plus bas jusqu'à l'arrêt Meio Papagaios (ligne 310A) — il figure sur la carte du deuxième jour.",
     "Tout Monte, minuté et chiffré : " + a(L("fr", "/monte/"), "Monte : que voir") + "."], True),
   ("Jardin botanique ou Monte Palace ?", [
     "Deux jardins pour deux publics. Monte Palace (18 €, moins de 15 ans gratuits) est le spectacle dessiné — bassins de carpes, azulejos, mise en scène — et le choix familial évident puisque les enfants entrent gratuitement. Le Jardin botanique est la collection de plantes à proprement parler : moins cher, plus calme, mieux étiqueté, avec les terrasses de cactus et la serre aux orchidées, et des vues que Monte Palace n'a pas. Un amoureux des plantes ne doit pas le manquer ; avec deux jours à Madère, faites les deux — ils sont à un téléphérique l'un de l'autre."], True),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Botanischer Garten Madeira: lohnt er sich? Preise, Anfahrt",
  desc="Lohnt sich der Botanische Garten? Ein klares Ja: 10 € Eintritt oder 19 € Kombiticket mit Seilbahn, das Urteil eines Sammlers und die kluge Reihenfolge.",
  h1="Der Botanische Garten: er lohnt sich — so machen Sie es richtig",
  sub="Geschrieben nach einem Besuch mit dem Blick eines Pflanzensammlers: was wirklich gut ist, die eine Schwäche, die ehrlichen Preise und die Reihenfolge, mit der Monte und die Korbschlitten in denselben Tag passen.",
  body=[
   ("Lohnt sich der Botanische Garten?", [
     "Ein klares Ja. Überall schöne Exemplare; am stärksten sind die Terrassen mit Sukkulenten und Kakteen und das Gewächshaus mit Bromelien und Orchideen. Dazu großartige Ausblicke auf Funchal und die Bucht und — selten bei Madeiras großen Zielen — Ruhe und Frieden abseits der Menschenmassen. Der Betreiber selbst veranschlagt etwa 1,5–2 Stunden für den Besuch, was unserer Erfahrung entspricht. Ein kleines Café lädt zwischendurch zu einem guten Kaffee und einem traditionellen Pastel de Nata ein.",
     "Warum überhaupt den Endemiten nachspüren? Madeira gehört zu Makaronesien, und sein Lorbeerwald ist UNESCO-Weltnaturerbe: die Lorbeerbäume, die Farne, die wilden Heidelbeeren und die wilden Ölbäume wachsen hier und fast nirgendwo sonst auf der Erde — ein wilder Ölbaum steht im Garten selbst, direkt am Endemiten-Bereich. Und genau daher unsere ehrliche Kritik, mit dem Blick eines passionierten Pflanzensammlers: dieser Bereich ist klein — zu klein, finden wir, für die Insel, der diese Flora gehört. Kommen Sie für die Sammlung und die Lage, nicht für eine Endemiten-Lehrstunde.",
     "Ein Nachteil, den man vorher kennen sollte: Der Garten liegt auf der trockenen Südseite der Insel. Selbst hoch über Funchal ist es hier deutlich trockener und heißer als in der Serra do Faial — dem zentralen Massiv von Pico do Areeiro und Pico Ruivo — hier gedeiht also die sonnenliebende Sammlung, nicht der Nebelwald. Für den lebenden Lorbeerwald wandern Sie eine Levada: " + a(L("de", "/best-levada-walks/"), "die schönsten Levadas") + ".",
     ], True),
   ("Was kostet der Botanische Garten?", [
     "Der Eintritt kostet 10 € ab 12 Jahren, 3 € für 6- bis 12-Jährige, unter 6 frei; Einwohner Madeiras zahlen nichts (Portaria 48/2026). Geöffnet 09:00–17:30. Für die meisten Besucher ist das Kombiticket der Gartenseilbahn der bessere Kauf, der Eintritt ist darin enthalten: 19 € einfach oder 24 € hin und zurück (Kinder 7–14: 9 €/12 €).",
     table(["Ticket", "Erwachsene", "Kinder"],
           [["Nur der Eintritt", "10 €", "3 € (6–12), unter 6 frei"],
            ["Seilbahn + Eintritt, einfach", "19 €", "9 € (7–14)"],
            ["Seilbahn + Eintritt, hin und zurück", "24 €", "12 € (7–14)"]])], True),
   ("Wie komme ich zum Botanischen Garten?", [
     "Der schöne Weg ist die Gartenseilbahn ab Babosas, einen kurzen Fußweg vom Zentrum Montes (09:00–17:00, neun Minuten über das Tal) — der Eintritt steckt im Ticket. Zurück müssen Sie nicht schweben: An den Ausgängen des Gartens warten Taxis, die Fahrt hinunter zur Talstation der Funchal-Seilbahn kostet etwa 12 € (Richtwert — mit dem Fahrer bestätigen). Mit Zeit im Gepäck können Sie stattdessen vom unteren Tor zur Bushaltestelle CAM Meio Papagaios D (Linie 310A) hinuntergehen und den Bus nehmen; unter Zeitdruck lohnt das nicht.",
     "Der ganze Funchal-Tag darum herum: " + a(L("de", "/two-days-in-madeira/"), "Tag zwei unseres Zwei-Tage-Plans") + "."], True),
   ("Schaffe ich Garten, Monte Palace und Korbschlitten an einem Tag?", [
     "Ja — aber nur in dieser Reihenfolge: früh hinauf, zuerst den Botanischen Garten, mit der Seilbahn zurück nach Monte, dann Monte Palace, zum Schluss die Korbschlitten. Die Reihenfolge zählt, weil die Schlitten nur von Monte aus bergab fahren (Montag–Samstag, 09:00–18:00): Wer den Garten ans Ende legt, kommt zu spät nach Monte zurück — oder gar nicht mehr. Früher Start, Garten vor dem Mittag, danach Monte Palace, die Schlitten als großes Finale.",
     "Und wer den Botanischen Garten doch spät macht oder als letzten Punkt aufhebt: keine Falle — einfach hinausgehen und dort ein Taxi nehmen, sie warten meist vor den Ausgängen, etwa 12 € bis zur Talstation der Funchal-Seilbahn (Richtwert). Wer den Schwindel lieber im Bus erlebt, geht ein Stück weiter hinunter zur Haltestelle Meio Papagaios (Linie 310A) — sie ist auf der Karte von Tag zwei eingezeichnet.",
     "Alles in Monte, getaktet und mit Preisen: " + a(L("de", "/monte/"), "Monte: was sehen") + "."], True),
   ("Botanischer Garten oder Monte Palace?", [
     "Zwei Gärten für zwei Publikum. Monte Palace (18 €, unter 15 frei) ist das inszenierte Spektakel — Koi-Teiche, Fliesenbilder, Dramatik — und mit freiem Kindereintritt die naheliegende Familienwahl. Der Botanische Garten ist die eigentliche Pflanzensammlung: günstiger, ruhiger, besser beschriftet, mit den Kakteenterrassen und dem Orchideen-Gewächshaus, und mit Ausblicken, die Monte Palace nicht hat. Wer Pflanzen liebt, lässt ihn nicht aus; mit zwei Tagen auf Madeira machen Sie beide — sie liegen eine Seilbahnfahrt auseinander."], True),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Ogród Botaniczny na Maderze: czy warto? Ceny i dojazd",
  desc="Czy Ogród Botaniczny jest wart wizyty? Zdecydowanie tak: wstęp 10 € albo 19 € z kolejką w cenie, ocena kolekcjonera roślin i dobra kolejność dnia.",
  h1="Ogród Botaniczny: warto — i jak to zrobić dobrze",
  sub="Napisane po wizycie okiem kolekcjonera roślin: co jest naprawdę dobre, jedna słabość, uczciwe ceny i kolejność, dzięki której Monte i sanie zmieszczą się w tym samym dniu.",
  body=[
   ("Czy Ogród Botaniczny jest wart wizyty?", [
     "Zdecydowanie tak. Piękne okazy na każdym kroku, a najmocniejsze punkty to tarasy sukulentów i kaktusów oraz szklarnia z bromeliami i storczykami; wokół wspaniałe widoki na Funchal i zatokę oraz — rzadkość wśród wielkich atrakcji Madery — spokój i cisza z dala od tłumów. Sam operator podaje, że zwiedzanie zajmuje około 1,5–2 godzin, co zgadza się z naszym doświadczeniem. Po drodze jest mała kawiarnia na dobrą kawę i tradycyjne pastel de nata.",
     "Po co w ogóle szukać endemitów? Madera należy do Makaronezji, a jej wawrzynowy las jest na liście światowego dziedzictwa UNESCO: wawrzyny, paprocie, dzikie borówki i dzikie drzewa oliwne rosną tu i prawie nigdzie indziej na Ziemi — dzika oliwka rośnie w samym ogrodzie, tuż przy części z endemitami. I stąd nasza szczera uwaga, okiem zapalonego kolekcjonera roślin: ta część jest mała — naszym zdaniem za mała jak na wyspę, do której ta flora należy. Jedź dla kolekcji i miejsca, nie po lekcję endemitów.",
     "Wada, którą warto znać przed wizytą: ogród leży po suchej, południowej stronie wyspy. Nawet wysoko nad Funchal jest tu znacznie suszej i goręcej niż w Serra do Faial — centralnym masywie Pico do Areeiro i Pico Ruivo — więc kwitnie tu kolekcja słońcolubna, nie las mgielny. Po żywy las wawrzynowy idź wzdłuż lewady: " + a(L("pl", "/best-levada-walks/"), "najlepsze lewady") + ".",
     ], True),
   ("Ile kosztuje Ogród Botaniczny?", [
     "Wstęp kosztuje 10 € powyżej 12 lat, 3 € dla dzieci 6–12 lat, do 6 lat za darmo; mieszkańcy Madery wchodzą bezpłatnie (Portaria 48/2026). Ogród jest otwarty 09:00–17:30. Dla większości odwiedzających lepszym zakupem jest bilet łączony kolejki ogrodowej, który zawiera wstęp: 19 € w jedną stronę albo 24 € w obie (dzieci 7–14 lat: 9 €/12 €).",
     table(["Bilet", "Dorosły", "Dziecko"],
           [["Sam wstęp do ogrodu", "10 €", "3 € (6–12), do 6 lat gratis"],
            ["Kolejka + wstęp, w jedną stronę", "19 €", "9 € (7–14)"],
            ["Kolejka + wstęp, w obie strony", "24 €", "12 € (7–14)"]])], True),
   ("Jak dojechać do Ogrodu Botanicznego?", [
     "Widokowa droga to kolejka ogrodowa z Babosas, krótki spacer od centrum Monte (09:00–17:00, dziewięć minut nad doliną) — wstęp jest w cenie biletu. Przy wyjściu nie musisz wracać górą: przy wyjściach z ogrodu czekają taksówki, a zjazd do dolnej stacji kolejki w Funchal kosztuje około 12 € (orientacyjnie — potwierdź z kierowcą). Mając zapas czasu, możesz zamiast tego zejść od dolnej bramy do przystanku CAM Meio Papagaios D (linia 310A) i pojechać autobusem; w pośpiechu nie warto.",
     "Cały dzień w Funchal wokół tego: " + a(L("pl", "/two-days-in-madeira/"), "drugi dzień naszego planu na dwa dni") + "."], True),
   ("Czy da się zrobić ogród, Monte Palace i sanie w jeden dzień?", [
     "Da się — ale tylko w tej kolejności: wjedź wcześnie, najpierw Ogród Botaniczny, kolejką z powrotem do Monte, potem Monte Palace, a na koniec sanie z wikliny. Kolejność ma znaczenie, bo sanie zjeżdżają tylko z Monte (poniedziałek–sobota, 09:00–18:00): zostaw ogród na koniec, a wrócisz do Monte za późno — albo wcale. Wczesny start, ogród przed południem, potem Monte Palace, sanie jako wielki finał.",
     "A jeśli jednak zrobisz Ogród Botaniczny późno albo zostawisz go na koniec: żadnej pułapki — po prostu wyjdź i weź taksówkę na miejscu, zwykle czekają przed wyjściami, około 12 € do dolnej stacji kolejki w Funchal (orientacyjnie). Jeśli wolisz przeżyć zawrót głowy w autobusie, zejdź kawałek niżej do przystanku Meio Papagaios (linia 310A) — jest zaznaczony na mapie drugiego dnia.",
     "Całe Monte, z czasami i cenami: " + a(L("pl", "/monte/"), "Monte: co zobaczyć") + "."], True),
   ("Ogród Botaniczny czy Monte Palace?", [
     "Dwa ogrody dla dwóch rodzajów gości. Monte Palace (18 €, do 15 lat za darmo) to zaprojektowany spektakl — stawy z karpiami koi, azulejos, rozmach — i oczywisty wybór rodzinny, bo dzieci wchodzą bezpłatnie. Ogród Botaniczny to właściwa kolekcja roślin: tańszy, spokojniejszy, lepiej opisany, z tarasami kaktusów i szklarnią storczyków oraz widokami, których Monte Palace nie ma. Miłośnik roślin nie powinien go pominąć; mając dwa dni na Maderze, zrób oba — dzieli je jedna przejażdżka kolejką."], True),
   ("Źródła", [None], False),
  ]),
}


def plain(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", s)).split())


def main():
    for lang in LANGS:
        c = dict(COPY[lang])
        body = [(h, [src(lang) if p is None else p for p in parts]) for h, parts, _ in COPY[lang]["body"]]
        F = FIGS[lang]
        # photos: the specimens after the verdict's first paragraph, the endemic after the critique,
        # the cable-car view in the getting-there section
        body[0] = (body[0][0], [body[0][1][0], F["trees"], body[0][1][1], F["endemic"], body[0][1][2]])
        body[2] = (body[2][0], [body[2][1][0], F["cable"], *body[2][1][1:]])
        c["body"] = body
        out, lt, ld = gi.build(SLUG, lang, c, "WebPage")
        h = open(out, encoding="utf-8").read()
        faq = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(parts[0])}}
            for q, parts, isq in COPY[lang]["body"] if isq]}
        block = '<script type="application/ld+json">\n' + json.dumps(faq, ensure_ascii=False, indent=1) + "\n</script>\n"
        h = re.sub(r'<script type="application/ld\+json">\n\{\n "@context": "https://schema.org",\n "@type": "FAQPage".*?</script>\n', "", h, flags=re.S)
        i = h.index("</head>")
        h = h[:i] + block + h[i:]
        h = h.replace('"dateModified": "2026-10-07T12:00+01:00"', '"dateModified": "2026-10-21T12:00+01:00"')
        h = h.replace("/img/og-default.jpg", "/img/botanical/garden-trees.jpg")
        open(out, "w", encoding="utf-8").write(h)
        flag = "" if lt <= 60 and 120 <= ld <= 155 else "  <-- title/description length"
        print(f"{os.path.relpath(out, ROOT)}: title {lt}, description {ld}{flag}")
    import subprocess
    for script in ("gen_site_nav.py", "gen_cta.py", "gen_owner.py", "gen_schema.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
