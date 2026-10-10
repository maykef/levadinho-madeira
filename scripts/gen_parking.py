#!/usr/bin/env python3
"""Parking block on every trail page (owner OK 2026-10-10, weekly report fix 1), 5 languages.

Search Console shows people asking "levada do rei parking", "pr18 parking", "pico ruivo parkplatz", "pr1.2 parking"
(positions 8-11) while the pages barely mentioned parking. Each trail page gets a short "Where to park for PR18?"
section between <!-- PARKING:START/END --> markers, right after the "getting there" section (Furado: after
"getting back"; otherwise before the bus section).

Facts come from seo_research/facts/parking.json (research 2026-10-10). Only VERIFIED entries are published (an
official source, or two independent reports); fees only where IFCN's price list gives them, or where two reports
agree and the page says so. SINGLE / NONE entries get the honest fallback: no official parking information, see the
trailhead map. Never an unsourced car park, road number or price. Idempotent; gen_spokes.py calls it.
"""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IFCN = "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Servicos/precoseservicos/Servi%C3%A7os.pdf"
DN_RF = "https://www.dnoticias.pt/2025/4/21/445984-estacionamento-no-ribeiro-frio-e-promessa-antiga/"
CALHETA = "https://www.cmcalheta.pt/pt/visitar/percursos-pedestres/transporte-no-rabacal"
CALHETA_PAUL = "https://www.cmcalheta.pt/en/visit/walking-routes/list-of-routes/levada-do-paul-ii"
VM_PR18 = "https://visitmadeira.com/en/what-to-do/nature-seekers/activities/hiking/pr-18-levada-do-rei/"
VM_PICAROUTO = "https://visitmadeira.com/en/where-to-go/madeira/north-coast/santana/picarouto-viewpoint/"

HEAD = {"en": "Where to park for {c}?", "pt": "Onde estacionar para o {c}?", "fr": "Où se garer pour le {c} ?",
        "de": "Wo parken für den {c}?", "pl": "Gdzie zaparkować przy {c}?"}
SRC = {"en": "Sources", "pt": "Fontes", "fr": "Sources", "de": "Quellen", "pl": "Źródła"}
NAMES = {IFCN: {"en": "IFCN price list", "pt": "tabela de preços do IFCN", "fr": "tarifs de l'IFCN",
                "de": "IFCN-Preisliste", "pl": "cennik IFCN"},
         DN_RF: {l: "DN, 2025" for l in HEAD}, CALHETA: {l: "CM Calheta" for l in HEAD},
         CALHETA_PAUL: {l: "CM Calheta" for l in HEAD}, VM_PR18: {l: "Visit Madeira" for l in HEAD},
         VM_PICAROUTO: {l: "Visit Madeira" for l in HEAD}}

AREEIRO = {
    "en": "Park at Pico do Areeiro. The upper car park by the viewpoint costs €4 an hour, up to €20 a day; the lower car park on the access road costs €2 an hour, up to €5 a day. The first 30 minutes are free and residents pay too. Both fill up before sunrise.",
    "pt": "Estacione no Pico do Areeiro. O parque de cima, junto ao miradouro, custa 4 € por hora, até 20 € por dia; o parque inferior, na estrada de acesso, custa 2 € por hora, até 5 € por dia. Os primeiros 30 minutos são grátis e os residentes também pagam. Ambos enchem antes do nascer do sol.",
    "fr": "Garez-vous au Pico do Areeiro. Le parking du haut, près du belvédère, coûte 4 € de l'heure, jusqu'à 20 € par jour ; celui du bas, sur la route d'accès, 2 € de l'heure, jusqu'à 5 € par jour. Les 30 premières minutes sont gratuites et les résidents paient aussi. Les deux sont pleins avant le lever du soleil.",
    "de": "Parken Sie am Pico do Areeiro. Der obere Parkplatz am Aussichtspunkt kostet 4 € pro Stunde, höchstens 20 € am Tag; der untere an der Zufahrtsstraße 2 € pro Stunde, höchstens 5 € am Tag. Die ersten 30 Minuten sind frei, auch Einheimische zahlen. Beide sind vor Sonnenaufgang voll.",
    "pl": "Zaparkuj na Pico do Areeiro. Górny parking przy punkcie widokowym kosztuje 4 € za godzinę, maksymalnie 20 € dziennie; dolny, przy drodze dojazdowej, 2 € za godzinę, maksymalnie 5 € dziennie. Pierwsze 30 minut jest gratis, mieszkańcy też płacą. Oba zapełniają się przed wschodem słońca.",
}
QUEIMADAS = {
    "en": "Park at the IFCN car park in the Queimadas Forest Park, above Santana: €2 an hour, up to €10 a day, first 30 minutes free.",
    "pt": "Estacione no parque do IFCN no Parque Florestal das Queimadas, acima de Santana: 2 € por hora, até 10 € por dia, primeiros 30 minutos grátis.",
    "fr": "Garez-vous au parking de l'IFCN du parc forestier des Queimadas, au-dessus de Santana : 2 € de l'heure, jusqu'à 10 € par jour, 30 premières minutes gratuites.",
    "de": "Parken Sie auf dem IFCN-Parkplatz im Waldpark Queimadas oberhalb von Santana: 2 € pro Stunde, höchstens 10 € am Tag, die ersten 30 Minuten frei.",
    "pl": "Zaparkuj na parkingu IFCN w parku leśnym Queimadas nad Santaną: 2 € za godzinę, maksymalnie 10 € dziennie, pierwsze 30 minut gratis.",
}
RABACAL = {
    "en": "Park at the car park on the ER105 above Rabaçal: free, according to 2026 visitor reports (there is no official statement). Private cars can't drive the 2 km road down to the Rabaçal house: walk it, or take the Calheta council shuttle (€5 one way, €8 return, daily 10:00–18:00).",
    "pt": "Estacione no parque da ER105, acima do Rabaçal: gratuito, segundo relatos de visitantes de 2026 (não há informação oficial). Os carros particulares não podem descer os 2 km de estrada até à Casa do Rabaçal: desça a pé ou apanhe o vaivém da Câmara da Calheta (5 € ida, 8 € ida e volta, todos os dias 10:00–18:00).",
    "fr": "Garez-vous au parking de l'ER105, au-dessus de Rabaçal : gratuit d'après des visiteurs en 2026 (aucune information officielle). Les voitures particulières ne peuvent pas descendre les 2 km de route jusqu'à la maison de Rabaçal : à pied, ou avec la navette de la mairie de Calheta (5 € l'aller, 8 € l'aller-retour, tous les jours 10:00–18:00).",
    "de": "Parken Sie auf dem Parkplatz an der ER105 oberhalb von Rabaçal: laut Besucherberichten von 2026 kostenlos (keine offizielle Angabe). Privatautos dürfen die 2 km Straße hinunter zum Rabaçal-Haus nicht fahren: zu Fuß oder mit dem Shuttle der Gemeinde Calheta (5 € einfach, 8 € hin und zurück, täglich 10:00–18:00).",
    "pl": "Zaparkuj na parkingu przy ER105 nad Rabaçal: według relacji odwiedzających z 2026 r. bezpłatnie (brak informacji oficjalnej). Samochody prywatne nie mogą zjechać 2 km drogą do domu Rabaçal: zejdź pieszo albo jedź busem gminy Calheta (5 € w jedną stronę, 8 € w obie, codziennie 10:00–18:00).",
}
ALECRIM_EXTRA = {
    "en": " The Levada do Alecrim starts from the road at the top, so you don't need to go down.",
    "pt": " A Levada do Alecrim começa na estrada, em cima, por isso não precisa de descer.",
    "fr": " La Levada do Alecrim part de la route, en haut : inutile de descendre.",
    "de": " Die Levada do Alecrim beginnt oben an der Straße, Sie müssen also nicht hinunter.",
    "pl": " Levada do Alecrim zaczyna się przy drodze na górze, więc nie trzeba schodzić.",
}
RIBEIRO_FRIO = {
    "en": "Ribeiro Frio has no car park: there are about 30 to 40 roadside spaces along the ER103, and at busy times police direct the traffic. Arrive early.",
    "pt": "O Ribeiro Frio não tem parque de estacionamento: há cerca de 30 a 40 lugares na berma da ER103 e, nas horas de maior movimento, a polícia controla o trânsito. Chegue cedo.",
    "fr": "Ribeiro Frio n'a pas de parking : environ 30 à 40 places le long de l'ER103, et aux heures de pointe la police règle la circulation. Arrivez tôt.",
    "de": "Ribeiro Frio hat keinen Parkplatz: Es gibt etwa 30 bis 40 Plätze am Rand der ER103, zu Stoßzeiten regelt die Polizei den Verkehr. Kommen Sie früh.",
    "pl": "W Ribeiro Frio nie ma parkingu: jest około 30–40 miejsc na poboczu ER103, a w godzinach szczytu ruch kieruje policja. Przyjedź wcześnie.",
}
FURADO_EXTRA = {
    "en": " The trail ends at Portela, so plan how you get back to the car.",
    "pt": " O percurso termina na Portela, por isso planeie como volta ao carro.",
    "fr": " Le sentier se termine à Portela : prévoyez le retour à la voiture.",
    "de": " Der Weg endet in Portela, planen Sie also den Rückweg zum Auto.",
    "pl": " Szlak kończy się w Portela, więc zaplanuj powrót do auta.",
}
PARK = {
    "PR3": ({l: AREEIRO[l] + {"en": " PR3 ends far below, at Ribeira das Cales, so plan how you get back to the car.",
                              "pt": " O PR3 termina muito abaixo, na Ribeira das Cales, por isso planeie como volta ao carro.",
                              "fr": " Le PR3 se termine bien plus bas, à Ribeira das Cales : prévoyez le retour à la voiture.",
                              "de": " Der PR3 endet weit unten in Ribeira das Cales, planen Sie also den Rückweg zum Auto.",
                              "pl": " PR3 kończy się daleko niżej, w Ribeira das Cales, więc zaplanuj powrót do auta."}[l] for l in HEAD}, [IFCN]),
    "PR9": (QUEIMADAS, [IFCN]),
    "PR9.1": (QUEIMADAS, [IFCN]),
    "PR6": (RABACAL, [CALHETA]),
    "PR6.1": (RABACAL, [CALHETA]),
    "PR6.2": ({l: RABACAL[l] + ALECRIM_EXTRA[l] for l in HEAD}, [CALHETA]),
    "PR6.3": (RABACAL, [CALHETA]),
    "PR6.8": ({
        "en": "Calheta council says there is a parking area just north of the water reservoir at Rabaçal, on the ER105. We found no fee information.",
        "pt": "A Câmara da Calheta indica uma zona de estacionamento logo a norte do reservatório de água do Rabaçal, na ER105. Não encontrámos informação sobre preços.",
        "fr": "La mairie de Calheta indique une zone de stationnement juste au nord du réservoir d'eau de Rabaçal, sur l'ER105. Nous n'avons trouvé aucune information de tarif.",
        "de": "Laut der Gemeinde Calheta gibt es einen Parkbereich direkt nördlich des Wasserreservoirs von Rabaçal an der ER105. Angaben zu Gebühren haben wir nicht gefunden.",
        "pl": "Według gminy Calheta tuż na północ od zbiornika wody w Rabaçal, przy ER105, jest miejsce do parkowania. Nie znaleźliśmy informacji o opłatach.",
    }, [CALHETA_PAUL]),
    "PR11": (RIBEIRO_FRIO, [DN_RF]),
    "PR10": ({l: RIBEIRO_FRIO[l] + FURADO_EXTRA[l] for l in HEAD}, [DN_RF]),
    "PR1.2": ({
        "en": "Park at the car park at Achada do Teixeira, at the end of the ER218 from Santana (PR1 finishes here too). It fills on busy mornings, when cars park along the road. Visit Madeira gives the road's opening hours as 07:00–21:00. We found no official fee.",
        "pt": "Estacione no parque da Achada do Teixeira, no fim da ER218 que sobe de Santana (o PR1 também termina aqui). Enche nas manhãs de maior movimento e os carros ficam na berma. Segundo o Visit Madeira, a estrada está aberta das 07:00 às 21:00. Não encontrámos preço oficial.",
        "fr": "Garez-vous au parking d'Achada do Teixeira, au bout de l'ER218 depuis Santana (le PR1 s'y termine aussi). Il est plein les matins chargés ; les voitures se garent alors le long de la route. D'après Visit Madeira, la route est ouverte de 07:00 à 21:00. Aucun tarif officiel trouvé.",
        "de": "Parken Sie auf dem Parkplatz in Achada do Teixeira am Ende der ER218 von Santana (hier endet auch der PR1). An vollen Vormittagen parken die Autos an der Straße. Laut Visit Madeira ist die Straße von 07:00 bis 21:00 geöffnet. Eine offizielle Gebühr haben wir nicht gefunden.",
        "pl": "Zaparkuj na parkingu w Achada do Teixeira, na końcu drogi ER218 z Santany (tu kończy się też PR1). W ruchliwe poranki jest pełny i auta stoją przy drodze. Według Visit Madeira droga jest otwarta w godz. 07:00–21:00. Nie znaleźliśmy oficjalnej opłaty.",
    }, [VM_PICAROUTO]),
    "PR8": ({
        "en": "Park at the small car park at Baía d'Abra, at the end of the road through Caniçal: free, according to 2026 visitor reports. It fills early in the season and cars then park along the approach road, so arrive early.",
        "pt": "Estacione no pequeno parque da Baía d'Abra, no fim da estrada que passa pelo Caniçal: gratuito, segundo relatos de visitantes de 2026. Enche cedo na época alta e os carros ficam então na berma da estrada de acesso, por isso chegue cedo.",
        "fr": "Garez-vous au petit parking de la Baía d'Abra, au bout de la route qui traverse Caniçal : gratuit d'après des visiteurs en 2026. Il est plein tôt en saison, les voitures se garent alors le long de la route d'accès : arrivez tôt.",
        "de": "Parken Sie auf dem kleinen Parkplatz an der Baía d'Abra am Ende der Straße durch Caniçal: laut Besucherberichten von 2026 kostenlos. In der Saison ist er früh voll, dann parken die Autos an der Zufahrtsstraße. Kommen Sie früh.",
        "pl": "Zaparkuj na małym parkingu przy Baía d'Abra, na końcu drogi przez Caniçal: według relacji odwiedzających z 2026 r. bezpłatnie. W sezonie szybko się zapełnia i auta stoją wtedy przy drodze dojazdowej, więc przyjedź wcześnie.",
    }, []),
    "PR13": ({
        "en": "Park at the Fanal car park on the ER209, by the forestry post, which has public toilets; when it's full, cars park along the ER209. Free, according to visitor reports. There is no bus to Fanal.",
        "pt": "Estacione no parque do Fanal, na ER209, junto ao posto florestal, que tem casas de banho públicas; quando está cheio, os carros ficam na berma da ER209. Gratuito, segundo relatos de visitantes. Não há autocarro para o Fanal.",
        "fr": "Garez-vous au parking du Fanal sur l'ER209, près du poste forestier, qui a des toilettes publiques ; quand il est plein, les voitures se garent le long de l'ER209. Gratuit d'après des visiteurs. Pas de bus pour le Fanal.",
        "de": "Parken Sie auf dem Fanal-Parkplatz an der ER209 beim Forsthaus, das öffentliche Toiletten hat; ist er voll, parken die Autos an der ER209. Laut Besucherberichten kostenlos. Zum Fanal fährt kein Bus.",
        "pl": "Zaparkuj na parkingu Fanal przy ER209, obok posterunku leśnego z publicznymi toaletami; gdy jest pełny, auta stoją przy ER209. Według relacji odwiedzających bezpłatnie. Do Fanal nie dojeżdża autobus.",
    }, []),
    "PR14": ({
        "en": "There is small roadside parking at the Fanal end, on the ER209, and a small lot at Curral Falso, also on the ER209, where the trail ends.",
        "pt": "Há pequenos lugares na berma no lado do Fanal, na ER209, e um pequeno parque no Curral Falso, também na ER209, onde o percurso termina.",
        "fr": "Il y a quelques places en bord de route côté Fanal, sur l'ER209, et un petit parking à Curral Falso, aussi sur l'ER209, où se termine le sentier.",
        "de": "Am Fanal-Ende gibt es wenige Plätze am Rand der ER209 und einen kleinen Parkplatz in Curral Falso, ebenfalls an der ER209, wo der Weg endet.",
        "pl": "Po stronie Fanal jest kilka miejsc na poboczu ER209, a w Curral Falso, gdzie kończy się szlak, mały parking, również przy ER209.",
    }, []),
    "PR18": ({
        "en": "There is no dedicated car park. The road above São Jorge ends at the ETAR water-treatment plant by the Quinta Levada do Rei, with a small space at the end and roadside parking along the road. No source mentions a fee.",
        "pt": "Não há parque de estacionamento próprio. A estrada acima de São Jorge termina na ETAR, junto à Quinta Levada do Rei, com um pequeno espaço no fim e lugares na berma ao longo da estrada. Nenhuma fonte refere um preço.",
        "fr": "Il n'y a pas de parking dédié. La route au-dessus de São Jorge se termine à la station d'épuration (ETAR), près de la Quinta Levada do Rei, avec un petit espace au bout et des places le long de la route. Aucune source ne mentionne de tarif.",
        "de": "Einen eigenen Parkplatz gibt es nicht. Die Straße oberhalb von São Jorge endet an der Kläranlage (ETAR) bei der Quinta Levada do Rei, mit wenig Platz am Ende und Parkmöglichkeiten am Straßenrand. Keine Quelle nennt eine Gebühr.",
        "pl": "Nie ma osobnego parkingu. Droga nad São Jorge kończy się przy oczyszczalni ścieków (ETAR) obok Quinta Levada do Rei; na końcu jest trochę miejsca, a dalej miejsca na poboczu. Żadne źródło nie wspomina o opłacie.",
    }, [VM_PR18]),
    "PR1.3": ({
        "en": "There is no road at the start, by Pico Ruivo: park at Achada do Teixeira and walk up PR1.2, or at Encumeada, where the trail ends. We found no official parking information for either end.",
        "pt": "Não há estrada no início, junto ao Pico Ruivo: estacione na Achada do Teixeira e suba pelo PR1.2, ou na Encumeada, onde o percurso termina. Não encontrámos informação oficial de estacionamento para nenhum dos lados.",
        "fr": "Pas de route au départ, près du Pico Ruivo : garez-vous à Achada do Teixeira et montez par le PR1.2, ou à Encumeada, où se termine le sentier. Aucune information officielle de stationnement trouvée pour l'un ou l'autre.",
        "de": "Am Start beim Pico Ruivo gibt es keine Straße: Parken Sie in Achada do Teixeira und gehen Sie den PR1.2 hinauf, oder in Encumeada, wo der Weg endet. Offizielle Parkangaben haben wir für keines der Enden gefunden.",
        "pl": "Na starcie przy Pico Ruivo nie ma drogi: zaparkuj w Achada do Teixeira i wejdź szlakiem PR1.2 albo w Encumeada, gdzie szlak się kończy. Nie znaleźliśmy oficjalnych informacji o parkingu na żadnym końcu.",
    }, []),
}
FALLBACK = {
    "en": "We found no official parking information for this trailhead. Check the trailhead map on this page before you drive, and never block the road.",
    "pt": "Não encontrámos informação oficial de estacionamento para este ponto de partida. Veja o mapa do ponto de partida nesta página antes de ir de carro e nunca bloqueie a estrada.",
    "fr": "Nous n'avons trouvé aucune information officielle de stationnement pour ce départ. Consultez la carte du point de départ sur cette page avant de prendre la voiture, et ne bloquez jamais la route.",
    "de": "Offizielle Parkangaben für diesen Ausgangspunkt haben wir nicht gefunden. Sehen Sie vor der Fahrt die Karte zum Ausgangspunkt auf dieser Seite an und blockieren Sie nie die Straße.",
    "pl": "Nie znaleźliśmy oficjalnych informacji o parkingu na początku tego szlaku. Przed wyjazdem sprawdź mapę początku szlaku na tej stronie i nigdy nie blokuj drogi.",
}


def block(code, lang):
    text, srcs = PARK.get(code, (FALLBACK, []))
    src = ""
    if srcs:
        links = " · ".join(f'<a class="plain" href="{u}" target="_blank" rel="noopener">{NAMES[u][lang]}</a>' for u in srcs)
        src = f'\n  <p class="src" style="font-size:13px;color:var(--ink-soft)">{SRC[lang]}: {links}</p>'
    return (f'<!-- PARKING:START (scripts/gen_parking.py) -->\n<section id="parking">\n  <h2>{HEAD[lang].format(c=code)}</h2>\n'
            f'  <p>{text[lang]}</p>{src}\n</section>\n<!-- PARKING:END -->\n')


def place(h, blk):
    if blk in h:
        return h
    h = re.sub(r"\n*<!-- PARKING:START.*?<!-- PARKING:END -->\n*", "\n\n", h, flags=re.S)
    for sec in ("getting-there", "getting-back"):
        m = re.search(rf'<section id="{sec}">.*?</section>\n', h, re.S)
        if m:
            return h[:m.end()] + "\n" + blk + h[m.end():]
    i = h.find("<!-- BUS:START")
    if i < 0:
        i = h.find('<section id="bus">')
    if i < 0:
        return None
    return h[:i] + blk + "\n" + h[i:]


def main():
    os.chdir(ROOT)
    n = 0
    for f in sorted(glob.glob("**/index.html", recursive=True)):
        if f.split(os.sep)[0] in ("bot", "seo_research", "reports", "google_search_console", ".claude", "trails"):
            continue
        h = open(f, encoding="utf-8").read()
        m = re.search(r'id="statusCard"[^>]*data-trail="([^"]+)"', h)
        if not m or '<aside class="facts">' not in h:
            continue
        lang = re.search(r'<html lang="([a-z]{2})', h).group(1)
        new = place(h, block(m.group(1), lang))
        if new is None:
            print("no place for parking block:", f)
            continue
        if new != h:
            open(f, "w", encoding="utf-8").write(new); n += 1
    print(f"parking blocks written to {n} page(s)")


if __name__ == "__main__":
    main()
