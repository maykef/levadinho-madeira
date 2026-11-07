#!/usr/bin/env python3
"""Writes /funchal-gardens-trail/ × 5 languages from the free-walks page shell (owner, 2026-11-07).

A port day away from the crowds: taxis up to three gardens in the morning while the cruise crowd is at the cable
car / market / Monte, then a walk down through three more and back to the pier. The owner's idea, route order and
picks ("I would do #2 first, #1 second, jump to 3 and the rest on the way down walking"); the English copy is the
owner's own edit of the draft (Claude Doc, 7 Nov 2026), translated here.

What it says, and where from:
  ship times       APRAM port schedule (510 calls from Oct 2026: arrivals 07-08 h ~69 %, departures mostly 17-19 h)
  orchid garden    visit.funchal.pt: Rua Lombo da Boa Vista, Mon-Sat 09:00-18:00, closed Sun + holidays;
                   entry EUR 5 over 17 (owner, 7 Nov); Garton family since the 1960s, William Cooke (owner)
  Botanical        Portaria 48/2026 (EUR 10 over 12, EUR 3 ages 6-12), 09:00-17:30; owner's own words
  Quinta do Poço   visit.funchal.pt: Estrada dos Marmeleiros 1, Mon-Fri 09:00-17:30, free; 1930s reservoir, gates
  Quinta das Cruzes cultura.madeira.gov.pt/museu-quinta-das-cruzes: Tue-Sat 10:00-17:30; adult EUR 10, 13-25 and
                   65+ EUR 5, family EUR 18 (under-13 not stated: never "free"); house/paintings = owner
  Santa Catarina   visit.funchal.pt: every day 07:00-20:00, to 22:00 from 22 Mar to 22 Sep; chapel 1425
  routes           OpenStreetMap routing (routing.openstreetmap.de, car + foot), checked 7 Nov 2026
  taxis            Rádio Táxis Madeira +351 291 764 476 (IFCN panels); metered tariff, no prices (owner rule)
  plant names      the owner (a botanical collector); Renanthera monachica also on the garden's own label
No ship names, no dates on the page.

Media: img/gardens-trail/ (owner's photos + 12 s clip, 7 Nov 2026; credited in img/CREDITS.txt). The map is a static
image rendered by scripts/gen_gardens_map.py (same pattern as the two-day page).
Re-run after changing the copy: it keeps dateModified, then runs the site chain (the page is in GUIDES / TAGS).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import PREFIX  # noqa: E402
import gen_info_pages as gi  # noqa: E402

SLUG = "funchal-gardens-trail"
P48 = "https://ifcn.madeira.gov.pt/images/Doc_Artigos/Legislacao/Portarias/Port48ISerie027_2026.pdf"
QC = "https://cultura.madeira.gov.pt/museu-quinta-das-cruzes"
VF = "https://visit.funchal.pt/"
APRAM = "https://www.apram.pt/"
OSM = "https://www.openstreetmap.org/"
IMG = "/img/gardens-trail/"
a, ext = gi.a, gi.ext


def L(lang, path):
    return f"{PREFIX[lang]}{path}"


SRC_LABEL = {"en": ("opening hours and entry", "ship times", "routes"),
             "pt": ("horários e entradas", "horários dos navios", "percursos"),
             "fr": ("horaires et entrées", "horaires des navires", "itinéraires"),
             "de": ("Öffnungszeiten und Eintritt", "Schiffszeiten", "Routen"),
             "pl": ("godziny otwarcia i wstęp", "godziny statków", "trasy")}


def src(lang):
    h, s, r = SRC_LABEL[lang]
    return ('<p class="src">' + h.capitalize() + ": " + ext(VF, "visit.funchal.pt") + " · " + ext(QC, "cultura.madeira.gov.pt")
            + " · " + ext(P48, "Portaria 48/2026") + ". " + s.capitalize() + ": " + ext(APRAM, "APRAM")
            + ". " + r.capitalize() + ": " + ext(OSM, "OpenStreetMap") + ".</p>")


def table(head, rows):
    return ('<div class="tbl"><table>\n    <thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead>\n    <tbody>\n"
            + "".join("      <tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>\n" for r in rows) + "    </tbody>\n  </table></div>")


# Gallery CSS: the Balcões field page's (trk-gal), so photos look and behave the same: tap = full-size copy.
GAL_CSS = ("<style>.trk-gal{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:12px 0}"
           ".trk-gal figure{margin:0}.trk-gal img{width:100%;height:auto;aspect-ratio:3/4;object-fit:cover;border-radius:10px;display:block}"
           ".trk-gal a{display:block;cursor:zoom-in}.trk-gal figcaption{font-size:13px;color:var(--ink-soft);margin-top:4px}"
           ".gt-map img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:8px}"
           ".gt-map a{display:block;cursor:zoom-in}.gt-map figcaption{font-size:13px;color:var(--ink-soft);margin-top:6px}"
           "</style>")


def fig(name, alt, cap, w=600, h=800):
    return (f'<figure><a href="{IMG}{name}-full.webp" target="_blank" rel="noopener"><img src="{IMG}{name}.webp" '
            f'alt="{alt}" loading="lazy" width="{w}" height="{h}"></a><figcaption>{cap}</figcaption></figure>')


PAPH = {"en": "A <i>Paphiopedilum</i> hybrid", "pt": "Um híbrido de <i>Paphiopedilum</i>", "fr": "Un hybride de <i>Paphiopedilum</i>",
        "de": "Eine <i>Paphiopedilum</i>-Hybride", "pl": "Hybryda <i>Paphiopedilum</i>"}
GARDEN = {"en": "Quinta da Boa Vista orchid garden", "pt": "jardim de orquídeas da Quinta da Boa Vista",
          "fr": "jardin d'orchidées de la Quinta da Boa Vista", "de": "Orchideengarten der Quinta da Boa Vista",
          "pl": "ogród storczyków Quinta da Boa Vista"}
MUNI = {"en": "Municipal Garden, Funchal", "pt": "Jardim Municipal do Funchal", "fr": "Jardin municipal de Funchal",
        "de": "Stadtgarten Funchal", "pl": "Ogród Miejski w Funchal"}
CREDIT = {"en": "Photos and video: Mayke De Freitas Santos. Tap a photo to open it full size.",
          "pt": "Fotos e vídeo: Mayke De Freitas Santos. Toque numa foto para a ver em tamanho grande.",
          "fr": "Photos et vidéo : Mayke De Freitas Santos. Touchez une photo pour l'ouvrir en grand.",
          "de": "Fotos und Video: Mayke De Freitas Santos. Tippen Sie auf ein Foto, um es groß zu öffnen.",
          "pl": "Zdjęcia i wideo: Mayke De Freitas Santos. Dotknij zdjęcia, aby otworzyć je w pełnym rozmiarze."}
VIDEO_LABEL = {"en": "A short walk among the orchids, Quinta da Boa Vista", "pt": "Um pequeno passeio entre as orquídeas, Quinta da Boa Vista",
               "fr": "Une courte promenade parmi les orchidées, Quinta da Boa Vista", "de": "Ein kurzer Gang zwischen den Orchideen, Quinta da Boa Vista",
               "pl": "Krótki spacer wśród storczyków, Quinta da Boa Vista"}
CEIBA_ALT = {"en": "Ceiba speciosa, a big tree with a swollen bottle-shaped trunk and pink flowers",
             "pt": "Ceiba speciosa, uma grande árvore de tronco em forma de garrafa e flores cor-de-rosa",
             "fr": "Ceiba speciosa, un grand arbre au tronc renflé en bouteille et aux fleurs roses",
             "de": "Ceiba speciosa, ein großer Baum mit flaschenförmig verdicktem Stamm und rosa Blüten",
             "pl": "Ceiba speciosa, duże drzewo o pniu w kształcie butelki i różowych kwiatach"}


def orchid_media(lang):
    g = GARDEN[lang]
    items = [("orchids-5347", "Cattleya Tropical Pointer ‘Cheetah’", "<i>Cattleya</i> Tropical Pointer ‘Cheetah’"),
             ("orchids-5354", "Epicattleya René Marqués", "<i>Epicattleya</i> René Marqués"),
             ("orchids-5364", "Nepenthes Miranda", "<i>Nepenthes</i> Miranda"),
             ("orchids-5370", "Renanthera monachica", "<i>Renanthera monachica</i>"),
             ("orchids-5366", "Nepenthes burkei", "<i>Nepenthes burkei</i>"),
             ("orchids-5381", PAPH[lang].replace("<i>", "").replace("</i>", ""), PAPH[lang])]
    gal = '<div class="trk-gal">' + "".join(fig(n, f"{alt}, {g}", cap) for n, alt, cap in items) + "</div>"
    vid = (f'<video controls muted playsinline preload="none" poster="{IMG}orchids-clip-poster.jpg" aria-label="{VIDEO_LABEL[lang]}" '
           f'style="display:block;width:100%;max-width:260px;margin:10px auto;border-radius:10px">'
           f'<source src="{IMG}orchids-clip.mp4" type="video/mp4"></video>')
    return [gal, vid, f'<p class="src">{CREDIT[lang]}</p>']


def ceiba(lang):
    return ('<div class="trk-gal">' + fig("municipal-1", f"{CEIBA_ALT[lang]}, {MUNI[lang]}", "<i>Ceiba speciosa</i>") + "</div>")


MAP_NAMES = {
 "en": ["Quinta da Boa Vista orchid garden", "Botanical Garden", "Jardins da Quinta do Poço", "Quinta das Cruzes", "Municipal Garden", "Santa Catarina park"],
 "pt": ["Jardim de orquídeas da Quinta da Boa Vista", "Jardim Botânico", "Jardins da Quinta do Poço", "Quinta das Cruzes", "Jardim Municipal", "Parque de Santa Catarina"],
 "fr": ["Jardin d'orchidées de la Quinta da Boa Vista", "Jardin botanique", "Jardins da Quinta do Poço", "Quinta das Cruzes", "Jardin municipal", "Parc de Santa Catarina"],
 "de": ["Orchideengarten der Quinta da Boa Vista", "Botanischer Garten", "Jardins da Quinta do Poço", "Quinta das Cruzes", "Stadtgarten", "Park Santa Catarina"],
 "pl": ["Ogród storczyków Quinta da Boa Vista", "Ogród Botaniczny", "Jardins da Quinta do Poço", "Quinta das Cruzes", "Ogród Miejski", "Park Santa Catarina"],
}
MAP_TXT = {
 "en": ("The trail on the map", "⚓ pier (land end)", "V Pico dos Barcelos viewpoint (optional)",
        "blue dashes: taxi · green: walk · orange: the optional detour", "Open this area in OpenStreetMap"),
 "pt": ("O percurso no mapa", "⚓ cais (lado de terra)", "V miradouro do Pico dos Barcelos (opcional)",
        "tracejado azul: táxi · verde: a pé · laranja: o desvio opcional", "Abrir esta zona no OpenStreetMap"),
 "fr": ("Le parcours sur la carte", "⚓ quai (côté terre)", "V belvédère du Pico dos Barcelos (facultatif)",
        "tirets bleus : taxi · vert : à pied · orange : le détour facultatif", "Ouvrir cette zone dans OpenStreetMap"),
 "de": ("Die Route auf der Karte", "⚓ Pier (landseitiges Ende)", "V Aussichtspunkt Pico dos Barcelos (optional)",
        "blau gestrichelt: Taxi · grün: zu Fuß · orange: der optionale Abstecher", "Diesen Bereich in OpenStreetMap öffnen"),
 "pl": ("Trasa na mapie", "⚓ molo (od strony lądu)", "V punkt widokowy Pico dos Barcelos (opcjonalnie)",
        "niebieska przerywana: taksówka · zielona: pieszo · pomarańczowa: opcjonalny objazd", "Otwórz ten obszar w OpenStreetMap"),
}


def map_html(lang):
    h, pier, bar, lines, osm_t = MAP_TXT[lang]
    legend = " · ".join(f"<b>{i}</b> {n}" for i, n in enumerate(MAP_NAMES[lang], 1)) + f" · {pier} · {bar}"
    alt = (h + ": " + "; ".join(f"{i} {n}" for i, n in enumerate(MAP_NAMES[lang], 1))).replace('"', "")
    osm = "https://www.openstreetmap.org/#map=15/32.6530/-16.9150"
    return ('<figure class="gt-map" style="margin:16px 0"><a href="' + IMG + 'map-full.webp" target="_blank" rel="noopener">'
            '<img src="' + IMG + 'map.webp" alt="' + alt + '" loading="lazy" width="660" height="MAPH"></a>'
            "<figcaption>" + legend + ". " + lines + ". " + ext(osm, osm_t) + ". Map © OpenStreetMap contributors.</figcaption></figure>")


# Sections: (heading, parts, is_question). A question's FAQ answer is its first paragraph, verbatim.
COPY = {
 "en": dict(
  title="Funchal gardens trail: a port day without the crowds",
  desc="A cruise day in Funchal without the crowds: taxi up to three quiet gardens, then walk down through three more to the pier. Timed route, map and costs.",
  h1="Funchal gardens trail: a port day away from the crowds",
  sub="Most cruise passengers head for the cable car, the market and Monte in the morning. This route does the opposite: a taxi up to three quiet gardens while the crowd is in town, then a walk downhill through two more and back to the pier. About 6 hours, 3.5 km on foot, all downhill, Tuesday to Friday.",
  route=("The route", "Times for a weekday, leaving the ship at 09:30 from the land end of the pier (by the fort). From the outer end, add about 3 minutes to the first taxi and 10 minutes to the last walk.",
         ["Time", "Stop", "Then"],
         [["09:30", "Leave the ship", "Taxi 3.1 km, about 6 min"],
          ["09:45–10:35", "1. Quinta da Boa Vista orchid garden", "Taxi 2.0 km, about 4 min"],
          ["10:40–12:10", "2. Botanical Garden", "Taxi 4.2 km, about 6 min"],
          ["12:20–13:00", "3. Jardins da Quinta do Poço", "Walk down 1.5 km, 20 min"],
          ["13:20–14:20", "4. Quinta das Cruzes museum and garden", "Walk 0.6 km, 7 min"],
          ["14:30–14:50", "5. Municipal Garden", "Walk 0.5 km, 7 min"],
          ["15:00–15:25", "6. Santa Catarina park", "Walk 0.9 km, 12 min"],
          ["about 15:40", "Back at the ship", ""]],
         "Driving and walking times are approximate. Allow a few minutes to find each taxi."),
  body=[
   ("When is the centre busiest on a cruise day?", [
     "Most ships arrive between 07:00 and 09:00 and leave between 17:00 and 19:00 (about 7 in 10 calls arrive in that early window). Passengers walk ashore within the hour, so the cable car's base station, the Mercado dos Lavradores and Monte are at their busiest from about 09:00 to 12:00. This trail keeps you out of it: it reaches the centre only after about 14:30. If your departure is at 19:00, you still have plenty of time to head up to " + a(L("en", "/monte/"), "Monte") + " via the cable car and do Monte Palace and the toboggan."], True),
   ("ROUTE", [], False),
   ("The gardens", [
     "<h3>1. Quinta da Boa Vista orchid garden</h3>",
     "The Garton family has run this orchid collection since the 1960s. Rua Lombo da Boa Vista; open Monday to Saturday 09:00–18:00, closed Sundays and public holidays; entry €5 for over-17s. For the curious, the collection in Funchal can be traced back to Sir William Cooke, one of the co-inventors of the electric telegraph. Cooke was an avid collector of orchids and formed the first collection in England, from which many of the Madeiran orchids descend.",
     "ORCHIDS",
     "<h3>2. Botanical Garden</h3>",
     "This tranquil corner of Funchal is not to be missed. It is particularly difficult and rare to find this combination of views, unique plant species and inner contemplation. Open 09:00–17:30; €10 over 12, €3 ages 6–12 (Portaria 48/2026). Taxis wait at the exits. More in " + a(L("en", "/botanical-garden/"), "our Botanical Garden guide") + ".",
     "<h3>3. Jardins da Quinta do Poço</h3>",
     "A quiet municipal garden next to the Imaculado Coração de Maria church, built over the city's 1930s drinking-water reservoir, with a viewpoint over the city and the bay. Its wrought-iron gates once stood in the Municipal Garden. Free; Monday to Friday 09:00–17:30.",
     "<h3>4. Quinta das Cruzes</h3>",
     "A beautiful museum with an impressive garden at Calçada do Pico 1. The house belonged to one of the discoverers of Madeira. It's full of beautiful paintings and furniture. Several paintings depict Funchal and Câmara de Lobos during the early 18th century. Tuesday to Saturday 10:00–17:30; adult €10, 13–25 and 65+ €5, family €18.",
     "<h3>5. Municipal Garden</h3>",
     "The garden in the heart of the city, beside the cathedral. It has an impressive collection of exotic trees. You reach it after the morning crowd has gone back to the ships; if you are short of time, walk from Quinta das Cruzes straight to Santa Catarina instead (1.0 km, 13 min).",
     "CEIBA",
     "<h3>6. Santa Catarina park</h3>",
     "An impressive park that sits above the harbour, with the chapel of Santa Catarina (1425) and a view over the pier where your ship is moored. Open every day 07:00–20:00 (until 22:00 from late March to late September). From here it is 12 minutes on foot to the land end of the pier."], False),
   ("Which days does it work?", [
     table(["Day", "What changes"],
           [["Tuesday to Friday", "The full trail."],
            ["Monday", "Quinta das Cruzes is closed: walk past it from Quinta do Poço to the Municipal Garden."],
            ["Saturday", "Quinta do Poço is closed: take the taxi from the Botanical Garden to Quinta das Cruzes and walk down from there."],
            ["Sunday and public holidays", "Only the Botanical Garden and the two city parks are open: Botanical Garden by taxi, then Santa Catarina and the pier."]])], False),
   ("What does it cost?", [
     "Entry for one adult: orchid garden €5, Botanical Garden €10, Quinta do Poço free, Quinta das Cruzes €10, so €25 in all, plus three short taxi rides. Taxis in Funchal are metered at the official tariff; ask for a quote before you ride."], True),
   ("How do I get the taxis?", [
     "From the pier, take a taxi into town (they are metered). At the Botanical Garden, taxis wait at the exits. At the orchid garden, phone for one before you finish: Rádio Táxis Madeira, +351 291 764 476."], True),
   ("Can I add a viewpoint?", [
     "Yes: Pico dos Barcelos, 337 m above the west of the city, is a 7-minute taxi ride from Quinta do Poço, and 7 minutes on to Quinta das Cruzes. Allow about 30 minutes more in all. If you prefer, you can do Pico dos Barcelos viewpoint."], True),
   ("Is there a quiet alternative to the cable car on a cruise day?", [
     "Yes: do the gardens above the city in the morning by taxi and walk down through the old town in the afternoon, reaching the centre after about 14:30 when most passengers are heading back."], True),
   ("How much walking is the gardens trail?", [
     "3.5 km, about 46 minutes on foot, all downhill or flat, plus three short taxi rides."], True),
   ("Does the gardens trail work on a Sunday?", [
     "Only in part: the orchid garden, Quinta do Poço and Quinta das Cruzes are closed on Sundays. The Botanical Garden and the city parks are open."], True),
   ("Sources", [None], False),
  ]),
 "pt": dict(
  title="Trilho dos jardins do Funchal: dia de cruzeiro sem multidões",
  desc="Um dia de cruzeiro no Funchal sem multidões: táxi até três jardins tranquilos e descida a pé por mais três até ao cais. Horários, mapa e custos.",
  h1="Trilho dos jardins do Funchal: um dia de escala longe das multidões",
  sub="A maioria dos passageiros de cruzeiro vai de manhã para o teleférico, o mercado e o Monte. Este percurso faz o contrário: um táxi até três jardins tranquilos enquanto a multidão está na baixa, depois uma descida a pé por mais dois e de volta ao cais. Cerca de 6 horas, 3,5 km a pé, sempre a descer, de terça a sexta.",
  route=("O percurso", "Horários para um dia útil, saindo do navio às 09:30 pelo lado de terra do cais (junto ao forte). Do lado de fora do cais, conte mais 3 minutos no primeiro táxi e mais 10 minutos na última caminhada.",
         ["Hora", "Paragem", "Depois"],
         [["09:30", "Sair do navio", "Táxi 3,1 km, cerca de 6 min"],
          ["09:45–10:35", "1. Jardim de orquídeas da Quinta da Boa Vista", "Táxi 2,0 km, cerca de 4 min"],
          ["10:40–12:10", "2. Jardim Botânico", "Táxi 4,2 km, cerca de 6 min"],
          ["12:20–13:00", "3. Jardins da Quinta do Poço", "Descida a pé 1,5 km, 20 min"],
          ["13:20–14:20", "4. Museu e jardim da Quinta das Cruzes", "A pé 0,6 km, 7 min"],
          ["14:30–14:50", "5. Jardim Municipal", "A pé 0,5 km, 7 min"],
          ["15:00–15:25", "6. Parque de Santa Catarina", "A pé 0,9 km, 12 min"],
          ["cerca das 15:40", "De volta ao navio", ""]],
         "Os tempos de carro e a pé são aproximados. Conte com alguns minutos para encontrar cada táxi."),
  body=[
   ("Quando é que o centro está mais cheio num dia de cruzeiro?", [
     "A maioria dos navios chega entre as 07:00 e as 09:00 e parte entre as 17:00 e as 19:00 (cerca de 7 em cada 10 escalas chegam nessa janela da manhã). Os passageiros desembarcam dentro de uma hora, por isso a estação de base do teleférico, o Mercado dos Lavradores e o Monte estão mais cheios das 09:00 às 12:00, aproximadamente. Este percurso mantém-no fora disso: só chega ao centro depois das 14:30. Se o seu navio parte às 19:00, ainda tem tempo de sobra para subir ao " + a(L("pt", "/monte/"), "Monte") + " de teleférico e fazer o Monte Palace e os carros de cesto."], True),
   ("ROUTE", [], False),
   ("Os jardins", [
     "<h3>1. Jardim de orquídeas da Quinta da Boa Vista</h3>",
     "A família Garton mantém esta coleção de orquídeas desde a década de 1960. Rua Lombo da Boa Vista; aberto de segunda a sábado, 09:00–18:00, encerrado aos domingos e feriados; entrada 5 € para maiores de 17 anos. Para os curiosos, a coleção do Funchal tem origem em Sir William Cooke, um dos coinventores do telégrafo elétrico. Cooke era um colecionador ávido de orquídeas e formou a primeira coleção em Inglaterra, da qual descendem muitas das orquídeas da Madeira.",
     "ORCHIDS",
     "<h3>2. Jardim Botânico</h3>",
     "Este recanto tranquilo do Funchal é imperdível. É particularmente difícil e raro encontrar esta combinação de vistas, espécies de plantas únicas e contemplação. Aberto das 09:00 às 17:30; 10 € para maiores de 12, 3 € dos 6 aos 12 anos (Portaria 48/2026). Há táxis à espera junto às saídas. Mais no " + a(L("pt", "/botanical-garden/"), "nosso guia do Jardim Botânico") + ".",
     "<h3>3. Jardins da Quinta do Poço</h3>",
     "Um jardim municipal tranquilo junto à igreja do Imaculado Coração de Maria, construído sobre o reservatório de água potável da cidade dos anos 1930, com um miradouro sobre a cidade e a baía. Os portões de ferro forjado estiveram antes no Jardim Municipal. Entrada livre; de segunda a sexta, 09:00–17:30.",
     "<h3>4. Quinta das Cruzes</h3>",
     "Um museu belíssimo com um jardim impressionante, na Calçada do Pico 1. A casa pertenceu a um dos descobridores da Madeira. Está cheia de belas pinturas e mobiliário. Várias pinturas retratam o Funchal e Câmara de Lobos no início do século XVIII. De terça a sábado, 10:00–17:30; adulto 10 €, 13–25 anos e 65+ 5 €, família 18 €.",
     "<h3>5. Jardim Municipal</h3>",
     "O jardim no coração da cidade, junto à Sé. Tem uma coleção impressionante de árvores exóticas. Chega lá depois de a multidão da manhã ter voltado aos navios; se tiver pouco tempo, vá a pé da Quinta das Cruzes diretamente para Santa Catarina (1,0 km, 13 min).",
     "CEIBA",
     "<h3>6. Parque de Santa Catarina</h3>",
     "Um parque impressionante sobre o porto, com a capela de Santa Catarina (1425) e vista sobre o cais onde está o seu navio. Aberto todos os dias, 07:00–20:00 (até às 22:00 de finais de março a finais de setembro). Daqui são 12 minutos a pé até ao lado de terra do cais."], False),
   ("Em que dias funciona?", [
     table(["Dia", "O que muda"],
           [["De terça a sexta", "O percurso completo."],
            ["Segunda-feira", "A Quinta das Cruzes está encerrada: passe ao lado, da Quinta do Poço para o Jardim Municipal."],
            ["Sábado", "A Quinta do Poço está encerrada: apanhe o táxi do Jardim Botânico para a Quinta das Cruzes e desça a pé a partir daí."],
            ["Domingos e feriados", "Só o Jardim Botânico e os dois parques da cidade estão abertos: Jardim Botânico de táxi, depois Santa Catarina e o cais."]])], False),
   ("Quanto custa?", [
     "Entradas para um adulto: jardim de orquídeas 5 €, Jardim Botânico 10 €, Quinta do Poço grátis, Quinta das Cruzes 10 €, ou seja 25 € no total, mais três viagens curtas de táxi. Os táxis no Funchal cobram pelo taxímetro, à tarifa oficial; peça uma estimativa antes de partir."], True),
   ("Como apanho os táxis?", [
     "No cais, apanhe um táxi para a cidade (têm taxímetro). No Jardim Botânico, há táxis à espera junto às saídas. No jardim de orquídeas, ligue a pedir um antes de terminar: Rádio Táxis Madeira, +351 291 764 476."], True),
   ("Posso juntar um miradouro?", [
     "Sim: o Pico dos Barcelos, a 337 m sobre a zona oeste da cidade, fica a 7 minutos de táxi da Quinta do Poço e a mais 7 minutos da Quinta das Cruzes. Conte com cerca de 30 minutos a mais no total. Se preferir, pode fazer o miradouro do Pico dos Barcelos."], True),
   ("Há uma alternativa tranquila ao teleférico num dia de cruzeiro?", [
     "Sim: faça os jardins acima da cidade de manhã, de táxi, e desça a pé pela zona velha à tarde, chegando ao centro depois das 14:30, quando a maioria dos passageiros está a regressar."], True),
   ("Quanto se caminha no trilho dos jardins?", [
     "3,5 km, cerca de 46 minutos a pé, sempre a descer ou plano, mais três viagens curtas de táxi."], True),
   ("O trilho dos jardins funciona ao domingo?", [
     "Só em parte: o jardim de orquídeas, a Quinta do Poço e a Quinta das Cruzes estão encerrados ao domingo. O Jardim Botânico e os parques da cidade estão abertos."], True),
   ("Fontes", [None], False),
  ]),
 "fr": dict(
  title="Parcours des jardins de Funchal : escale sans la foule",
  desc="Une escale à Funchal sans la foule : taxi jusqu'à trois jardins tranquilles, puis descente à pied par trois autres jusqu'au quai. Horaires, carte et coûts.",
  h1="Parcours des jardins de Funchal : une escale loin de la foule",
  sub="La plupart des croisiéristes filent le matin vers le téléphérique, le marché et Monte. Ce parcours fait l'inverse : un taxi jusqu'à trois jardins tranquilles pendant que la foule est en ville, puis une descente à pied par deux autres jusqu'au quai. Environ 6 heures, 3,5 km à pied, toujours en descente, du mardi au vendredi.",
  route=("Le parcours", "Horaires pour un jour de semaine, en quittant le navire à 09:30 côté terre du quai (près du fort). Depuis le bout du quai, ajoutez environ 3 minutes au premier taxi et 10 minutes à la dernière marche.",
         ["Heure", "Étape", "Ensuite"],
         [["09:30", "Quitter le navire", "Taxi 3,1 km, environ 6 min"],
          ["09:45–10:35", "1. Jardin d'orchidées de la Quinta da Boa Vista", "Taxi 2,0 km, environ 4 min"],
          ["10:40–12:10", "2. Jardin botanique", "Taxi 4,2 km, environ 6 min"],
          ["12:20–13:00", "3. Jardins da Quinta do Poço", "Descente à pied 1,5 km, 20 min"],
          ["13:20–14:20", "4. Musée et jardin de la Quinta das Cruzes", "À pied 0,6 km, 7 min"],
          ["14:30–14:50", "5. Jardin municipal", "À pied 0,5 km, 7 min"],
          ["15:00–15:25", "6. Parc de Santa Catarina", "À pied 0,9 km, 12 min"],
          ["vers 15:40", "Retour au navire", ""]],
         "Les temps en voiture et à pied sont approximatifs. Prévoyez quelques minutes pour trouver chaque taxi."),
  body=[
   ("Quand le centre est-il le plus bondé un jour de croisière ?", [
     "La plupart des navires arrivent entre 07:00 et 09:00 et repartent entre 17:00 et 19:00 (environ 7 escales sur 10 arrivent dans ce créneau matinal). Les passagers débarquent dans l'heure, si bien que la gare du téléphérique, le Mercado dos Lavradores et Monte sont le plus bondés d'environ 09:00 à 12:00. Ce parcours vous en tient à l'écart : il n'atteint le centre qu'après 14:30 environ. Si votre départ est à 19:00, vous avez encore largement le temps de monter à " + a(L("fr", "/monte/"), "Monte") + " en téléphérique et de faire Monte Palace et la luge."], True),
   ("ROUTE", [], False),
   ("Les jardins", [
     "<h3>1. Jardin d'orchidées de la Quinta da Boa Vista</h3>",
     "La famille Garton tient cette collection d'orchidées depuis les années 1960. Rua Lombo da Boa Vista ; ouvert du lundi au samedi, 09:00–18:00, fermé le dimanche et les jours fériés ; entrée 5 € au-dessus de 17 ans. Pour les curieux, la collection de Funchal remonte à Sir William Cooke, l'un des co-inventeurs du télégraphe électrique. Cooke était un collectionneur passionné d'orchidées et constitua la première collection d'Angleterre, dont descendent beaucoup des orchidées de Madère.",
     "ORCHIDS",
     "<h3>2. Jardin botanique</h3>",
     "Ce coin paisible de Funchal est à ne pas manquer. Il est particulièrement difficile et rare de trouver une telle combinaison de vues, d'espèces végétales uniques et de contemplation. Ouvert de 09:00 à 17:30 ; 10 € au-dessus de 12 ans, 3 € de 6 à 12 ans (Portaria 48/2026). Des taxis attendent aux sorties. Plus dans " + a(L("fr", "/botanical-garden/"), "notre guide du Jardin botanique") + ".",
     "<h3>3. Jardins da Quinta do Poço</h3>",
     "Un jardin municipal tranquille près de l'église de l'Imaculado Coração de Maria, aménagé sur le réservoir d'eau potable de la ville des années 1930, avec un belvédère sur la ville et la baie. Ses grilles en fer forgé se trouvaient autrefois au Jardin municipal. Gratuit ; du lundi au vendredi, 09:00–17:30.",
     "<h3>4. Quinta das Cruzes</h3>",
     "Un très beau musée avec un jardin impressionnant, Calçada do Pico 1. La maison appartint à l'un des découvreurs de Madère. Elle est remplie de beaux tableaux et de meubles. Plusieurs tableaux représentent Funchal et Câmara de Lobos au début du XVIIIe siècle. Du mardi au samedi, 10:00–17:30 ; adulte 10 €, 13–25 ans et 65 ans et plus 5 €, famille 18 €.",
     "<h3>5. Jardin municipal</h3>",
     "Le jardin au cœur de la ville, à côté de la cathédrale. Il abrite une impressionnante collection d'arbres exotiques. Vous l'atteignez quand la foule du matin est repartie vers les navires ; si vous manquez de temps, allez à pied de la Quinta das Cruzes directement à Santa Catarina (1,0 km, 13 min).",
     "CEIBA",
     "<h3>6. Parc de Santa Catarina</h3>",
     "Un parc impressionnant au-dessus du port, avec la chapelle de Santa Catarina (1425) et une vue sur le quai où votre navire est amarré. Ouvert tous les jours, 07:00–20:00 (jusqu'à 22:00 de fin mars à fin septembre). De là, 12 minutes à pied jusqu'au côté terre du quai."], False),
   ("Quels jours ça marche ?", [
     table(["Jour", "Ce qui change"],
           [["Du mardi au vendredi", "Le parcours complet."],
            ["Lundi", "La Quinta das Cruzes est fermée : passez devant, de la Quinta do Poço au Jardin municipal."],
            ["Samedi", "La Quinta do Poço est fermée : prenez le taxi du Jardin botanique à la Quinta das Cruzes et descendez à pied à partir de là."],
            ["Dimanche et jours fériés", "Seuls le Jardin botanique et les deux parcs de la ville sont ouverts : Jardin botanique en taxi, puis Santa Catarina et le quai."]])], False),
   ("Combien ça coûte ?", [
     "Entrées pour un adulte : jardin d'orchidées 5 €, Jardin botanique 10 €, Quinta do Poço gratuite, Quinta das Cruzes 10 €, soit 25 € en tout, plus trois courtes courses en taxi. À Funchal, les taxis roulent au compteur, au tarif officiel ; demandez une estimation avant de partir."], True),
   ("Comment trouver les taxis ?", [
     "Au quai, prenez un taxi pour la ville (ils ont un compteur). Au Jardin botanique, des taxis attendent aux sorties. Au jardin d'orchidées, appelez-en un avant de terminer : Rádio Táxis Madeira, +351 291 764 476."], True),
   ("Puis-je ajouter un belvédère ?", [
     "Oui : le Pico dos Barcelos, à 337 m au-dessus de l'ouest de la ville, est à 7 minutes de taxi de la Quinta do Poço, puis à 7 minutes de la Quinta das Cruzes. Comptez environ 30 minutes de plus en tout. Si vous préférez, vous pouvez faire le belvédère du Pico dos Barcelos."], True),
   ("Existe-t-il une alternative tranquille au téléphérique un jour de croisière ?", [
     "Oui : faites les jardins au-dessus de la ville le matin en taxi et redescendez à pied par la vieille ville l'après-midi, pour atteindre le centre après 14:30 environ, quand la plupart des passagers rentrent."], True),
   ("Combien marche-t-on sur le parcours des jardins ?", [
     "3,5 km, environ 46 minutes à pied, toujours en descente ou à plat, plus trois courtes courses en taxi."], True),
   ("Le parcours des jardins fonctionne-t-il le dimanche ?", [
     "En partie seulement : le jardin d'orchidées, la Quinta do Poço et la Quinta das Cruzes sont fermés le dimanche. Le Jardin botanique et les parcs de la ville sont ouverts."], True),
   ("Sources", [None], False),
  ]),
 "de": dict(
  title="Gartenroute Funchal: Landgang ohne Menschenmassen",
  desc="Ein Kreuzfahrttag in Funchal ohne Gedränge: mit dem Taxi zu drei ruhigen Gärten, dann zu Fuß durch drei weitere hinab zum Pier. Zeitplan, Karte, Kosten.",
  h1="Gartenroute Funchal: ein Hafentag abseits der Massen",
  sub="Die meisten Kreuzfahrtgäste fahren morgens zur Seilbahn, zum Markt und nach Monte. Diese Route macht es umgekehrt: mit dem Taxi hinauf zu drei ruhigen Gärten, während die Massen in der Stadt sind, dann zu Fuß bergab durch zwei weitere und zurück zum Pier. Etwa 6 Stunden, 3,5 km zu Fuß, nur bergab, Dienstag bis Freitag.",
  route=("Die Route", "Zeiten für einen Wochentag, Abgang vom Schiff um 09:30 am landseitigen Ende des Piers (beim Fort). Vom äußeren Ende rechnen Sie etwa 3 Minuten mehr für das erste Taxi und 10 Minuten mehr für den letzten Fußweg.",
         ["Zeit", "Station", "Dann"],
         [["09:30", "Vom Schiff", "Taxi 3,1 km, etwa 6 Min."],
          ["09:45–10:35", "1. Orchideengarten der Quinta da Boa Vista", "Taxi 2,0 km, etwa 4 Min."],
          ["10:40–12:10", "2. Botanischer Garten", "Taxi 4,2 km, etwa 6 Min."],
          ["12:20–13:00", "3. Jardins da Quinta do Poço", "Zu Fuß bergab 1,5 km, 20 Min."],
          ["13:20–14:20", "4. Museum und Garten Quinta das Cruzes", "Zu Fuß 0,6 km, 7 Min."],
          ["14:30–14:50", "5. Stadtgarten", "Zu Fuß 0,5 km, 7 Min."],
          ["15:00–15:25", "6. Park Santa Catarina", "Zu Fuß 0,9 km, 12 Min."],
          ["gegen 15:40", "Zurück am Schiff", ""]],
         "Fahr- und Gehzeiten sind ungefähr. Rechnen Sie ein paar Minuten ein, um jedes Taxi zu finden."),
  body=[
   ("Wann ist das Zentrum an einem Kreuzfahrttag am vollsten?", [
     "Die meisten Schiffe kommen zwischen 07:00 und 09:00 an und legen zwischen 17:00 und 19:00 ab (etwa 7 von 10 Anläufen kommen in diesem frühen Fenster an). Die Gäste gehen innerhalb einer Stunde an Land, deshalb sind die Talstation der Seilbahn, der Mercado dos Lavradores und Monte etwa von 09:00 bis 12:00 am vollsten. Diese Route hält Sie davon fern: Sie erreicht das Zentrum erst nach etwa 14:30. Legt Ihr Schiff um 19:00 ab, bleibt noch reichlich Zeit, mit der Seilbahn nach " + a(L("de", "/monte/"), "Monte") + " hinaufzufahren und Monte Palace und die Korbschlitten zu machen."], True),
   ("ROUTE", [], False),
   ("Die Gärten", [
     "<h3>1. Orchideengarten der Quinta da Boa Vista</h3>",
     "Die Familie Garton führt diese Orchideensammlung seit den 1960er-Jahren. Rua Lombo da Boa Vista; geöffnet Montag bis Samstag 09:00–18:00, sonntags und an Feiertagen geschlossen; Eintritt 5 € ab 18 Jahren. Für Neugierige: Die Sammlung in Funchal geht auf Sir William Cooke zurück, einen der Miterfinder des elektrischen Telegrafen. Cooke war ein leidenschaftlicher Orchideensammler und legte die erste Sammlung Englands an, von der viele der Orchideen Madeiras abstammen.",
     "ORCHIDS",
     "<h3>2. Botanischer Garten</h3>",
     "Diese ruhige Ecke Funchals sollten Sie nicht verpassen. Diese Verbindung aus Ausblicken, einzigartigen Pflanzenarten und innerer Einkehr findet man nur selten. Geöffnet 09:00–17:30; 10 € ab 12 Jahren, 3 € für 6- bis 12-Jährige (Portaria 48/2026). An den Ausgängen warten Taxis. Mehr in " + a(L("de", "/botanical-garden/"), "unserem Ratgeber zum Botanischen Garten") + ".",
     "<h3>3. Jardins da Quinta do Poço</h3>",
     "Ein ruhiger städtischer Garten neben der Kirche Imaculado Coração de Maria, angelegt über dem Trinkwasserspeicher der Stadt aus den 1930er-Jahren, mit Aussichtspunkt über Stadt und Bucht. Seine schmiedeeisernen Tore standen früher im Stadtgarten. Eintritt frei; Montag bis Freitag 09:00–17:30.",
     "<h3>4. Quinta das Cruzes</h3>",
     "Ein wunderschönes Museum mit eindrucksvollem Garten, Calçada do Pico 1. Das Haus gehörte einem der Entdecker Madeiras. Es ist voller schöner Gemälde und Möbel. Mehrere Gemälde zeigen Funchal und Câmara de Lobos im frühen 18. Jahrhundert. Dienstag bis Samstag 10:00–17:30; Erwachsene 10 €, 13–25 Jahre und ab 65 Jahren 5 €, Familie 18 €.",
     "<h3>5. Stadtgarten</h3>",
     "Der Garten im Herzen der Stadt, neben der Kathedrale. Er hat eine beeindruckende Sammlung exotischer Bäume. Sie erreichen ihn, wenn die Morgenmassen schon zu den Schiffen zurückgekehrt sind; wenn die Zeit knapp ist, gehen Sie von der Quinta das Cruzes direkt nach Santa Catarina (1,0 km, 13 Min.).",
     "CEIBA",
     "<h3>6. Park Santa Catarina</h3>",
     "Ein eindrucksvoller Park über dem Hafen, mit der Kapelle Santa Catarina (1425) und Blick auf den Pier, an dem Ihr Schiff liegt. Täglich geöffnet 07:00–20:00 (Ende März bis Ende September bis 22:00). Von hier sind es 12 Minuten zu Fuß zum landseitigen Ende des Piers."], False),
   ("An welchen Tagen klappt es?", [
     table(["Tag", "Was sich ändert"],
           [["Dienstag bis Freitag", "Die ganze Route."],
            ["Montag", "Die Quinta das Cruzes ist geschlossen: gehen Sie vorbei, von der Quinta do Poço zum Stadtgarten."],
            ["Samstag", "Die Quinta do Poço ist geschlossen: nehmen Sie das Taxi vom Botanischen Garten zur Quinta das Cruzes und gehen Sie von dort zu Fuß hinab."],
            ["Sonn- und Feiertage", "Nur der Botanische Garten und die beiden Stadtparks sind offen: Botanischer Garten mit dem Taxi, dann Santa Catarina und der Pier."]])], False),
   ("Was kostet es?", [
     "Eintritt für einen Erwachsenen: Orchideengarten 5 €, Botanischer Garten 10 €, Quinta do Poço frei, Quinta das Cruzes 10 €, zusammen also 25 €, dazu drei kurze Taxifahrten. Taxis in Funchal fahren mit Taxameter zum amtlichen Tarif; fragen Sie vor der Fahrt nach dem ungefähren Preis."], True),
   ("Wie komme ich an die Taxis?", [
     "Am Pier nehmen Sie ein Taxi in die Stadt (mit Taxameter). Am Botanischen Garten warten Taxis an den Ausgängen. Im Orchideengarten rufen Sie eines, bevor Sie fertig sind: Rádio Táxis Madeira, +351 291 764 476."], True),
   ("Kann ich einen Aussichtspunkt einbauen?", [
     "Ja: der Pico dos Barcelos, 337 m über dem Westen der Stadt, liegt 7 Taximinuten von der Quinta do Poço entfernt und 7 Minuten weiter von der Quinta das Cruzes. Rechnen Sie insgesamt etwa 30 Minuten mehr. Wenn Sie möchten, können Sie den Aussichtspunkt Pico dos Barcelos machen."], True),
   ("Gibt es an einem Kreuzfahrttag eine ruhige Alternative zur Seilbahn?", [
     "Ja: Besuchen Sie morgens mit dem Taxi die Gärten oberhalb der Stadt und gehen Sie nachmittags zu Fuß durch die Altstadt hinab; ins Zentrum kommen Sie nach etwa 14:30, wenn die meisten Gäste auf dem Rückweg sind."], True),
   ("Wie viel geht man auf der Gartenroute?", [
     "3,5 km, etwa 46 Minuten zu Fuß, nur bergab oder eben, dazu drei kurze Taxifahrten."], True),
   ("Klappt die Gartenroute an einem Sonntag?", [
     "Nur teilweise: Orchideengarten, Quinta do Poço und Quinta das Cruzes sind sonntags geschlossen. Der Botanische Garten und die Stadtparks sind offen."], True),
   ("Quellen", [None], False),
  ]),
 "pl": dict(
  title="Szlak ogrodów Funchal: dzień w porcie bez tłumów",
  desc="Dzień z rejsu w Funchal bez tłumów: taksówką do trzech spokojnych ogrodów, potem pieszo w dół przez trzy kolejne do mola. Godziny, mapa i koszty.",
  h1="Szlak ogrodów Funchal: dzień w porcie z dala od tłumów",
  sub="Większość pasażerów statków rusza rano do kolejki linowej, na targ i do Monte. Ta trasa robi odwrotnie: taksówką do trzech spokojnych ogrodów, gdy tłum jest w mieście, potem pieszo w dół przez dwa kolejne i z powrotem do mola. Około 6 godzin, 3,5 km pieszo, cały czas w dół, od wtorku do piątku.",
  route=("Trasa", "Godziny na dzień powszedni, zejście ze statku o 09:30 od strony lądu (przy forcie). Z końca mola doliczcie około 3 minut do pierwszej taksówki i 10 minut do ostatniego odcinka pieszo.",
         ["Godzina", "Przystanek", "Dalej"],
         [["09:30", "Zejście ze statku", "Taksówka 3,1 km, ok. 6 min"],
          ["09:45–10:35", "1. Ogród storczyków Quinta da Boa Vista", "Taksówka 2,0 km, ok. 4 min"],
          ["10:40–12:10", "2. Ogród Botaniczny", "Taksówka 4,2 km, ok. 6 min"],
          ["12:20–13:00", "3. Jardins da Quinta do Poço", "Pieszo w dół 1,5 km, 20 min"],
          ["13:20–14:20", "4. Muzeum i ogród Quinta das Cruzes", "Pieszo 0,6 km, 7 min"],
          ["14:30–14:50", "5. Ogród Miejski", "Pieszo 0,5 km, 7 min"],
          ["15:00–15:25", "6. Park Santa Catarina", "Pieszo 0,9 km, 12 min"],
          ["ok. 15:40", "Z powrotem na statku", ""]],
         "Czasy przejazdu i przejścia są przybliżone. Doliczcie kilka minut na znalezienie każdej taksówki."),
  body=[
   ("Kiedy centrum jest najbardziej zatłoczone w dzień zawinięcia statków?", [
     "Większość statków przypływa między 07:00 a 09:00 i odpływa między 17:00 a 19:00 (około 7 na 10 zawinięć przypada na to poranne okno). Pasażerowie schodzą na ląd w ciągu godziny, więc dolna stacja kolejki, Mercado dos Lavradores i Monte są najbardziej zatłoczone mniej więcej od 09:00 do 12:00. Ta trasa trzyma was z dala od tego: do centrum dociera dopiero po około 14:30. Jeśli statek odpływa o 19:00, macie jeszcze sporo czasu, żeby wjechać kolejką do " + a(L("pl", "/monte/"), "Monte") + " i zobaczyć Monte Palace oraz zjechać saniami."], True),
   ("ROUTE", [], False),
   ("Ogrody", [
     "<h3>1. Ogród storczyków Quinta da Boa Vista</h3>",
     "Rodzina Gartonów prowadzi tę kolekcję storczyków od lat 60. XX wieku. Rua Lombo da Boa Vista; czynne od poniedziałku do soboty 09:00–18:00, zamknięte w niedziele i święta; wstęp 5 € powyżej 17 lat. Dla ciekawskich: kolekcja w Funchal wywodzi się od Sir Williama Cooke'a, jednego ze współwynalazców telegrafu elektrycznego. Cooke był zapalonym kolekcjonerem storczyków i stworzył pierwszą kolekcję w Anglii, od której pochodzi wiele storczyków Madery.",
     "ORCHIDS",
     "<h3>2. Ogród Botaniczny</h3>",
     "Tego spokojnego zakątka Funchal nie można przegapić. Trudno o drugie takie połączenie widoków, wyjątkowych gatunków roślin i wyciszenia. Czynny 09:00–17:30; 10 € powyżej 12 lat, 3 € dla dzieci 6–12 lat (Portaria 48/2026). Przy wyjściach czekają taksówki. Więcej w " + a(L("pl", "/botanical-garden/"), "naszym przewodniku po Ogrodzie Botanicznym") + ".",
     "<h3>3. Jardins da Quinta do Poço</h3>",
     "Spokojny ogród miejski obok kościoła Imaculado Coração de Maria, urządzony nad miejskim zbiornikiem wody pitnej z lat 30. XX wieku, z punktem widokowym na miasto i zatokę. Jego kute bramy stały kiedyś w Ogrodzie Miejskim. Wstęp wolny; od poniedziałku do piątku 09:00–17:30.",
     "<h3>4. Quinta das Cruzes</h3>",
     "Piękne muzeum z imponującym ogrodem, Calçada do Pico 1. Dom należał do jednego z odkrywców Madery. Jest pełen pięknych obrazów i mebli. Kilka obrazów przedstawia Funchal i Câmara de Lobos na początku XVIII wieku. Od wtorku do soboty 10:00–17:30; dorośli 10 €, 13–25 lat i 65+ 5 €, rodzina 18 €.",
     "<h3>5. Ogród Miejski</h3>",
     "Ogród w samym sercu miasta, obok katedry. Ma imponującą kolekcję egzotycznych drzew. Docieracie tu, gdy poranny tłum wrócił już na statki; jeśli brakuje czasu, idźcie z Quinta das Cruzes prosto do Santa Catarina (1,0 km, 13 min).",
     "CEIBA",
     "<h3>6. Park Santa Catarina</h3>",
     "Imponujący park nad portem, z kaplicą Santa Catarina (1425) i widokiem na molo, przy którym stoi wasz statek. Czynny codziennie 07:00–20:00 (do 22:00 od końca marca do końca września). Stąd 12 minut pieszo do mola od strony lądu."], False),
   ("W które dni to działa?", [
     table(["Dzień", "Co się zmienia"],
           [["Od wtorku do piątku", "Cała trasa."],
            ["Poniedziałek", "Quinta das Cruzes jest zamknięta: przejdźcie obok, z Quinta do Poço do Ogrodu Miejskiego."],
            ["Sobota", "Quinta do Poço jest zamknięta: weźcie taksówkę z Ogrodu Botanicznego do Quinta das Cruzes i stamtąd zejdźcie pieszo."],
            ["Niedziele i święta", "Otwarte są tylko Ogród Botaniczny i dwa miejskie parki: Ogród Botaniczny taksówką, potem Santa Catarina i molo."]])], False),
   ("Ile to kosztuje?", [
     "Wstęp dla jednej osoby dorosłej: ogród storczyków 5 €, Ogród Botaniczny 10 €, Quinta do Poço bezpłatnie, Quinta das Cruzes 10 €, razem 25 €, plus trzy krótkie kursy taksówką. Taksówki w Funchal jeżdżą na taksometr według oficjalnej taryfy; zapytajcie o przybliżoną cenę przed kursem."], True),
   ("Jak złapać taksówki?", [
     "Przy molo weźcie taksówkę do miasta (mają taksometr). Przy Ogrodzie Botanicznym taksówki czekają przy wyjściach. W ogrodzie storczyków zadzwońcie po taksówkę, zanim skończycie zwiedzanie: Rádio Táxis Madeira, +351 291 764 476."], True),
   ("Czy mogę dodać punkt widokowy?", [
     "Tak: Pico dos Barcelos, 337 m nad zachodnią częścią miasta, jest 7 minut taksówką od Quinta do Poço i kolejne 7 minut od Quinta das Cruzes. Doliczcie łącznie około 30 minut. Jeśli wolicie, możecie zajrzeć na punkt widokowy Pico dos Barcelos."], True),
   ("Czy jest spokojna alternatywa dla kolejki linowej w dzień zawinięcia statków?", [
     "Tak: rano zwiedźcie taksówką ogrody nad miastem, a po południu zejdźcie pieszo przez stare miasto; do centrum dotrzecie po około 14:30, gdy większość pasażerów wraca na statki."], True),
   ("Ile chodzenia jest na szlaku ogrodów?", [
     "3,5 km, około 46 minut pieszo, cały czas w dół lub po płaskim, plus trzy krótkie kursy taksówką."], True),
   ("Czy szlak ogrodów działa w niedzielę?", [
     "Tylko częściowo: ogród storczyków, Quinta do Poço i Quinta das Cruzes są w niedziele zamknięte. Ogród Botaniczny i parki miejskie są otwarte."], True),
   ("Źródła", [None], False),
  ]),
}


def map_height():
    try:
        from PIL import Image
        return Image.open(os.path.join(gi.ROOT, "img", "gardens-trail", "map.webp")).height
    except Exception:  # noqa: BLE001
        return 660


def prepare(lang, t):
    """Route section (map + table + note), the orchid gallery + clip, the Ceiba photo."""
    h, intro, head, rows, note = COPY[lang]["route"]
    mh = str(map_height())
    out = []
    for heading, parts, isq in t:
        if heading == "ROUTE":
            out.append((h, [intro, GAL_CSS + map_html(lang).replace("MAPH", mh), table(head, rows), note], False))
            continue
        new = []
        for p in parts:
            if p == "ORCHIDS":
                new += orchid_media(lang)
            elif p == "CEIBA":
                new.append(ceiba(lang))
            else:
                new.append(p)
        out.append((heading, new, isq))
    return out


def main():
    gi.build_qa(SLUG, COPY, src, "2026-11-07T21:00+00:00", prepare=prepare,
                og_image="/img/gardens-trail/og.jpg")


if __name__ == "__main__":
    main()
