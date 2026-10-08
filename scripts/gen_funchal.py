#!/usr/bin/env python3
"""Writes /funchal/ in 5 languages: "Funchal today: what's on, what's open" (owner, 2026-10-08: the page where
tourists find what's on in the city while they are in it; not an arrivals monitor).

Two layers (the dynamic-page design agreed 2026-10-07):
  * a fixed core that ranks: title, H1, the sections below and the FAQ (JSON-LD verbatim with the visible text);
  * a "now" layer at the top: the Levadinho panel (#now), which /funchal.js fills from /funchal.json by Madeira
    time, the landing page (data-page) and a QR scan (/qr.js). Same for everyone at the same moment.

Opening hours come from scripts/update_funchal.py (PLACES, PARKING: one source of truth for the page, the panel
and funchal.json). The event list and the last-bus table are filled by the updater (STATIC-FX-* markers), so
crawlers read them. The shell (head CSS, header, footer, analytics) is copied from free-walks/ in each language,
as gen_info_pages.py does. Re-run after changing the copy: it keeps the updater-written markers and dateModified,
then re-runs gen_site_nav.py, gen_cta.py, gen_owner.py, gen_qr.py and update_funchal.py's page fill.
"""
import html
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import BASE, LANGS, PREFIX, wa_link  # noqa: E402
from update_funchal import PARKING, PLACES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLUG = "funchal"
GREET = {"en": "Hello Levadinho! 👋", "pt": "Olá Levadinho! 👋", "fr": "Bonjour Levadinho ! 👋", "de": "Hallo Levadinho! 👋",
         "pl": "Cześć Levadinho! 👋"}


def ext(href, text):
    return f'<a class="plain" href="{href}" target="_blank" rel="noopener">{text}</a>'


# --------------------------------------------------------------------------- hours as text
DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DN = {"en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "pt": ["seg.", "ter.", "qua.", "qui.", "sex.", "sáb.", "dom."],
      "fr": ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."], "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
      "pl": ["pn.", "wt.", "śr.", "czw.", "pt.", "sob.", "nd."]}
HW = {
    "en": dict(daily="Daily", closed="closed", hol="public holidays", xmas="Christmas Day", some="some public holidays",
               months="(October–March; check other months)"),
    "pt": dict(daily="Todos os dias", closed="encerrado", hol="feriados", xmas="dia de Natal", some="alguns feriados",
               months="(outubro a março; confirme nos outros meses)"),
    "fr": dict(daily="Tous les jours", closed="fermé", hol="jours fériés", xmas="jour de Noël", some="certains jours fériés",
               months="(octobre à mars ; vérifiez les autres mois)"),
    "de": dict(daily="Täglich", closed="geschlossen", hol="Feiertage", xmas="1. Weihnachtstag", some="einige Feiertage",
               months="(Oktober bis März; in anderen Monaten bitte prüfen)"),
    "pl": dict(daily="Codziennie", closed="nieczynne", hol="święta", xmas="Boże Narodzenie", some="niektóre święta",
               months="(październik–marzec; w innych miesiącach sprawdź)"),
}


def spans_txt(sp):
    return ", ".join(f"{a}–{b}" for a, b in sp)


def hours_text(p, lang):
    d, w = DN[lang], HW[lang]
    h = p["hours"]
    open_days = [k for k in DAYS if h.get(k)]
    parts, i = [], 0
    if len(open_days) == 7 and all(h[k] == h["mon"] for k in DAYS):
        parts.append(f"{w['daily']} {spans_txt(h['mon'])}")
    else:
        while i < 7:
            k = DAYS[i]
            if not h.get(k):
                i += 1
                continue
            j = i
            while j + 1 < 7 and h.get(DAYS[j + 1]) == h[k]:
                j += 1
            parts.append((d[i] if i == j else f"{d[i]}–{d[j]}") + " " + spans_txt(h[k]))
            i = j + 1
    closed = [d[DAYS.index(k)] for k in DAYS if not h.get(k)]
    if "hol" not in h:
        closed.append(w["hol"])
    extra = p.get("closed") or []
    if extra == ["12-25"]:
        closed.append(w["xmas"])
    elif extra:
        closed.append(w["some"])
    txt = "; ".join(parts)
    if closed:
        txt += f"; {w['closed']}: " + ", ".join(closed)
    if p.get("months"):
        txt += " " + w["months"]
    return txt


# --------------------------------------------------------------------------- copy
KIND_ORDER = ("market", "cable", "toboggan", "garden", "museum")
C = {
 "en": dict(
  title="Funchal today: what's on, what's open, what to do",
  desc="What's on in Funchal today: events, what's open right now, the market, museums, lidos, sunset and the last bus back. Check before you head out.",
  h1="Funchal today: what's on and what's open",
  sub="Events, what's open right now, the market, the lidos and the last bus back: for when you're in the city.",
  now_static="Most museums in Funchal close on Sundays, Mondays and public holidays, the Mercado dos Lavradores closes on Sundays and holidays, and the cable car to Monte runs every day from 08:45 to 17:45.",
  ask="Ask Levadinho anything else",
  ev_h="What's on this week",
  ev_note="From the city's culture agenda and the Region's events guide. Several days a month the market's top floor holds a themed fair (antiques, handcraft, gastronomy, fashion), 09:00–17:00: Levadinho says so at the top on the day.",
  open_h="What's open today", open_th=("Place", "Hours", "Now"),
  open_note="Most public museums close on Sundays, Mondays and public holidays. On a Sunday the open ones are the gardens, the cable cars, MAMMA, the Design Center and the Natural History Museum.",
  kinds={"market": "Market", "cable": "Cable cars", "toboggan": "Toboggans", "garden": "Gardens", "museum": "Museums"},
  lido_h="Lidos and the sea",
  lido_p="Funchal's seafront pools are run by Frente MarFunchal. Entry: adults €6, ages 7–17 €2, under 7 free; Praia Formosa beach is free. Hours change with the season.",
  area_h="The city by area",
  areas=[("Zona Velha (Old Town)", "Rua de Santa Maria and its painted doors, the Mercado dos Lavradores, the cable car station up to Monte, the Fortaleza de São Tiago and the Barreirinha lido."),
         ("The centre", "The Sé cathedral, Avenida Arriaga and the Jardim Municipal, Praça do Município with the Museu de Arte Sacra, the Madeira Wine Company lodge, and the marina and Avenida do Mar on the seafront."),
         ("Up the hill (São Pedro, Santa Clara)", "The Museu Quinta das Cruzes, the Convento de Santa Clara, the Casa-Museu Frederico de Freitas, the Natural History Museum, and the Fortaleza do Pico above the city."),
         ("Lido and Estrada Monumental (west)", "The hotel district, the Lido and Ponta Gorda pools, and the seafront promenade on to Praia Formosa and Câmara de Lobos."),
         ("Monte (above the city)", "Up by cable car from the Old Town: the Monte Palace garden, the church of Nossa Senhora do Monte, the toboggan ride down, and the second cable car to the Botanical Garden.")],
  bus_cap="Time the last bus leaves (bus line)",
  bus_h="Getting back: last buses to the centre",
  bus_th=("From", "Weekdays", "Saturdays", "Sundays and holidays"),
  bus_note="Most people ride the cable car down from Monte too; the bus is the way down after the cable car stops at 17:45, or if you'd rather not pay for the ride back. You can also walk down. Times are when the last bus leaves that stop, from the Horários do Funchal timetable.",
  park="Street parking (pay-and-display) is charged Monday to Friday 08:00–20:00 and Saturday 08:00–14:00; on Sundays and public holidays it is free.",
  faq_h="Questions",
  faq=[("Is the Mercado dos Lavradores open on Sunday?", "No. The market opens Monday to Friday 07:00–19:00 and Saturday 07:00–14:00; it is closed on Sundays and public holidays."),
       ("Which museums are open on Mondays in Funchal?", "The Museu de Arte Sacra, the Museu A Cidade do Açúcar, the Fortaleza do Pico, the Madeira Wine Company lodge and the Design Center. Most other museums close on Mondays."),
       ("Is street parking free on Sundays in Funchal?", "Yes. Pay-and-display street parking is charged Monday to Friday 08:00–20:00 and Saturday 08:00–14:00; on Sundays and public holidays it is free."),
       ("What time does the Monte cable car run?", "Every day from 08:45 to 17:45, except Christmas Day. After that, city buses run from Monte down to the centre until late evening, or you can walk down.")],
  src_h="Sources",
  src="Events: the city's culture agenda (cultura.funchal.pt) and the Region's events guide (eventsmadeira.com). Hours: each operator's site and the Regional Directorate for Culture. Market fairs: Mercados do Funchal. Lidos and parking: Frente MarFunchal. Weather and sea: IPMA. Buses: Horários do Funchal.",
 ),
 "pt": dict(
  title="Funchal hoje: o que há, o que está aberto, o que fazer",
  desc="O que há no Funchal hoje: eventos, o que está aberto agora, o mercado, museus, complexos balneares, pôr do sol e o último autocarro. Veja antes de sair.",
  h1="Funchal hoje: o que há e o que está aberto",
  sub="Eventos, o que está aberto agora, o mercado, os complexos balneares e o último autocarro: para quando está na cidade.",
  now_static="A maioria dos museus do Funchal fecha aos domingos, às segundas-feiras e nos feriados, o Mercado dos Lavradores fecha aos domingos e feriados, e o teleférico para o Monte funciona todos os dias das 08:45 às 17:45.",
  ask="Pergunte mais ao Levadinho",
  ev_h="O que há esta semana",
  ev_note="Da agenda cultural da Câmara e do guia de eventos da Região. Alguns dias por mês o último piso do mercado recebe uma feira temática (antiguidades, artesanato, gastronomia, moda), das 09:00 às 17:00: o Levadinho avisa no topo da página nesse dia.",
  open_h="O que está aberto hoje", open_th=("Local", "Horário", "Agora"),
  open_note="A maioria dos museus públicos fecha aos domingos, às segundas-feiras e nos feriados. Ao domingo estão abertos os jardins, os teleféricos, o MAMMA, o Design Center e o Museu de História Natural.",
  kinds={"market": "Mercado", "cable": "Teleféricos", "toboggan": "Carros de cesto", "garden": "Jardins", "museum": "Museus"},
  lido_h="Complexos balneares e o mar",
  lido_p="As piscinas da frente mar do Funchal são geridas pela Frente MarFunchal. Entrada: adultos 6 €, dos 7 aos 17 anos 2 €, menores de 7 grátis; a Praia Formosa é gratuita. O horário muda com a época.",
  area_h="A cidade por zonas",
  areas=[("Zona Velha", "A Rua de Santa Maria e as suas portas pintadas, o Mercado dos Lavradores, a estação do teleférico para o Monte, a Fortaleza de São Tiago e o complexo balnear da Barreirinha."),
         ("O centro", "A Sé, a Avenida Arriaga e o Jardim Municipal, a Praça do Município com o Museu de Arte Sacra, a Madeira Wine Company, e a marina e a Avenida do Mar junto ao mar."),
         ("A subir (São Pedro, Santa Clara)", "O Museu Quinta das Cruzes, o Convento de Santa Clara, a Casa-Museu Frederico de Freitas, o Museu de História Natural e, por cima da cidade, a Fortaleza do Pico."),
         ("Lido e Estrada Monumental (oeste)", "A zona hoteleira, os complexos do Lido e da Ponta Gorda, e o passeio marítimo até à Praia Formosa e a Câmara de Lobos."),
         ("Monte (acima da cidade)", "Sobe-se de teleférico a partir da Zona Velha: o jardim Monte Palace, a igreja de Nossa Senhora do Monte, a descida nos carros de cesto e o segundo teleférico até ao Jardim Botânico.")],
  bus_cap="Hora de partida do último autocarro (linha)",
  bus_h="Regressar: últimos autocarros para o centro",
  bus_th=("De", "Dias úteis", "Sábados", "Domingos e feriados"),
  bus_note="A maioria das pessoas também desce do Monte de teleférico; o autocarro é a alternativa depois de o teleférico parar às 17:45, ou para quem não quer pagar a descida. Também pode descer a pé. Horas de partida do último autocarro nessa paragem, segundo os Horários do Funchal.",
  park="O estacionamento tarifado na rua paga-se de segunda a sexta das 08:00 às 20:00 e ao sábado das 08:00 às 14:00; aos domingos e feriados é gratuito.",
  faq_h="Perguntas",
  faq=[("O Mercado dos Lavradores está aberto ao domingo?", "Não. O mercado abre de segunda a sexta das 07:00 às 19:00 e ao sábado das 07:00 às 14:00; fecha aos domingos e feriados."),
       ("Que museus abrem à segunda-feira no Funchal?", "O Museu de Arte Sacra, o Museu A Cidade do Açúcar, a Fortaleza do Pico, a Madeira Wine Company e o Design Center. A maioria dos outros museus fecha à segunda-feira."),
       ("O estacionamento na rua é gratuito ao domingo no Funchal?", "Sim. O estacionamento tarifado na rua paga-se de segunda a sexta das 08:00 às 20:00 e ao sábado das 08:00 às 14:00; aos domingos e feriados é gratuito."),
       ("A que horas funciona o teleférico do Monte?", "Todos os dias das 08:45 às 17:45, exceto no dia de Natal. Depois disso há autocarros urbanos do Monte para o centro até ao fim da noite, ou pode descer a pé.")],
  src_h="Fontes",
  src="Eventos: agenda cultural da Câmara (cultura.funchal.pt) e guia de eventos da Região (eventsmadeira.com). Horários: o site de cada operador e a Direção Regional da Cultura. Feiras do mercado: Mercados do Funchal. Complexos balneares e estacionamento: Frente MarFunchal. Tempo e mar: IPMA. Autocarros: Horários do Funchal.",
 ),
 "fr": dict(
  title="Funchal aujourd'hui : que faire, ce qui est ouvert",
  desc="Que faire à Funchal aujourd'hui : événements, ce qui est ouvert maintenant, le marché, les musées, les piscines, le coucher du soleil et le dernier bus.",
  h1="Funchal aujourd'hui : que faire, ce qui est ouvert",
  sub="Événements, ce qui est ouvert maintenant, le marché, les piscines et le dernier bus : pour quand vous êtes en ville.",
  now_static="La plupart des musées de Funchal ferment le dimanche, le lundi et les jours fériés, le Mercado dos Lavradores ferme le dimanche et les jours fériés, et le téléphérique du Monte fonctionne tous les jours de 08:45 à 17:45.",
  ask="Posez une autre question à Levadinho",
  ev_h="Les événements de la semaine",
  ev_note="D'après l'agenda culturel de la ville et l'agenda des événements de la Région. Certains jours du mois, le dernier étage du marché accueille une foire thématique (antiquités, artisanat, gastronomie, mode), de 09:00 à 17:00 : Levadinho le signale en haut de la page ce jour-là.",
  open_h="Ce qui est ouvert aujourd'hui", open_th=("Lieu", "Horaires", "Maintenant"),
  open_note="La plupart des musées publics ferment le dimanche, le lundi et les jours fériés. Le dimanche, sont ouverts les jardins, les téléphériques, le MAMMA, le Design Center et le Muséum d'histoire naturelle.",
  kinds={"market": "Marché", "cable": "Téléphériques", "toboggan": "Luges", "garden": "Jardins", "museum": "Musées"},
  lido_h="Piscines et mer",
  lido_p="Les piscines du front de mer de Funchal sont gérées par Frente MarFunchal. Entrée : adultes 6 €, 7–17 ans 2 €, moins de 7 ans gratuit ; la plage de Praia Formosa est gratuite. Les horaires changent selon la saison.",
  area_h="La ville par quartier",
  areas=[("Zona Velha (vieille ville)", "La Rua de Santa Maria et ses portes peintes, le Mercado dos Lavradores, la station du téléphérique vers le Monte, la Fortaleza de São Tiago et la piscine de Barreirinha."),
         ("Le centre", "La cathédrale (Sé), l'Avenida Arriaga et le Jardim Municipal, la Praça do Município avec le Museu de Arte Sacra, la Madeira Wine Company, puis la marina et l'Avenida do Mar en bord de mer."),
         ("Sur les hauteurs (São Pedro, Santa Clara)", "Le Museu Quinta das Cruzes, le Convento de Santa Clara, la Casa-Museu Frederico de Freitas, le Muséum d'histoire naturelle et, au-dessus de la ville, la Fortaleza do Pico."),
         ("Lido et Estrada Monumental (ouest)", "Le quartier des hôtels, les piscines du Lido et de Ponta Gorda, et la promenade du bord de mer jusqu'à Praia Formosa et Câmara de Lobos."),
         ("Le Monte (au-dessus de la ville)", "On y monte en téléphérique depuis la vieille ville : le jardin Monte Palace, l'église Nossa Senhora do Monte, la descente en luge et le second téléphérique vers le Jardin botanique.")],
  bus_cap="Heure de départ du dernier bus (ligne)",
  bus_h="Rentrer : derniers bus vers le centre",
  bus_th=("Depuis", "En semaine", "Le samedi", "Dimanche et jours fériés"),
  bus_note="La plupart des visiteurs redescendent aussi du Monte en téléphérique ; le bus sert après l'arrêt du téléphérique à 17:45, ou si vous ne voulez pas payer la descente. On peut aussi descendre à pied. Heures de départ du dernier bus à cet arrêt, d'après Horários do Funchal.",
  park="Le stationnement payant dans la rue s'applique du lundi au vendredi de 08:00 à 20:00 et le samedi de 08:00 à 14:00 ; le dimanche et les jours fériés, il est gratuit.",
  faq_h="Questions",
  faq=[("Le Mercado dos Lavradores est-il ouvert le dimanche ?", "Non. Le marché ouvre du lundi au vendredi de 07:00 à 19:00 et le samedi de 07:00 à 14:00 ; il est fermé le dimanche et les jours fériés."),
       ("Quels musées sont ouverts le lundi à Funchal ?", "Le Museu de Arte Sacra, le Museu A Cidade do Açúcar, la Fortaleza do Pico, la Madeira Wine Company et le Design Center. La plupart des autres musées ferment le lundi."),
       ("Le stationnement dans la rue est-il gratuit le dimanche à Funchal ?", "Oui. Le stationnement payant dans la rue s'applique du lundi au vendredi de 08:00 à 20:00 et le samedi de 08:00 à 14:00 ; le dimanche et les jours fériés, il est gratuit."),
       ("À quelle heure fonctionne le téléphérique du Monte ?", "Tous les jours de 08:45 à 17:45, sauf le jour de Noël. Ensuite, des bus urbains descendent du Monte au centre jusqu'en fin de soirée, ou vous pouvez descendre à pied.")],
  src_h="Sources",
  src="Événements : agenda culturel de la ville (cultura.funchal.pt) et agenda des événements de la Région (eventsmadeira.com). Horaires : le site de chaque exploitant et la Direction régionale de la culture. Foires du marché : Mercados do Funchal. Piscines et stationnement : Frente MarFunchal. Météo et mer : IPMA. Bus : Horários do Funchal.",
 ),
 "de": dict(
  title="Funchal heute: was los ist, was geöffnet hat",
  desc="Was heute in Funchal los ist: Veranstaltungen, was jetzt geöffnet hat, Markthalle, Museen, Badeanlagen, Sonnenuntergang und der letzte Bus. Vorher prüfen.",
  h1="Funchal heute: was los ist und was geöffnet hat",
  sub="Veranstaltungen, was jetzt geöffnet hat, die Markthalle, die Badeanlagen und der letzte Bus: für Ihre Zeit in der Stadt.",
  now_static="Die meisten Museen in Funchal schließen sonntags, montags und an Feiertagen, der Mercado dos Lavradores schließt sonntags und an Feiertagen, und die Seilbahn zum Monte fährt täglich von 08:45 bis 17:45 Uhr.",
  ask="Fragen Sie Levadinho noch etwas",
  ev_h="Was diese Woche los ist",
  ev_note="Aus dem Kulturkalender der Stadt und dem Veranstaltungskalender der Region. An einigen Tagen im Monat findet im obersten Stock der Markthalle ein Themenmarkt statt (Antiquitäten, Kunsthandwerk, Gastronomie, Mode), 09:00–17:00 Uhr: Levadinho sagt es an dem Tag oben auf der Seite.",
  open_h="Was heute geöffnet hat", open_th=("Ort", "Öffnungszeiten", "Jetzt"),
  open_note="Die meisten öffentlichen Museen schließen sonntags, montags und an Feiertagen. Sonntags geöffnet sind die Gärten, die Seilbahnen, das MAMMA, das Design Center und das Naturkundemuseum.",
  kinds={"market": "Markthalle", "cable": "Seilbahnen", "toboggan": "Korbschlitten", "garden": "Gärten", "museum": "Museen"},
  lido_h="Badeanlagen und Meer",
  lido_p="Funchals Meerwasserbäder an der Uferfront betreibt Frente MarFunchal. Eintritt: Erwachsene 6 €, 7–17 Jahre 2 €, unter 7 frei; der Strand Praia Formosa ist kostenlos. Die Öffnungszeiten wechseln mit der Saison.",
  area_h="Die Stadt nach Vierteln",
  areas=[("Zona Velha (Altstadt)", "Die Rua de Santa Maria mit ihren bemalten Türen, der Mercado dos Lavradores, die Talstation der Seilbahn zum Monte, die Fortaleza de São Tiago und das Bad Barreirinha."),
         ("Das Zentrum", "Die Kathedrale (Sé), die Avenida Arriaga und der Jardim Municipal, die Praça do Município mit dem Museu de Arte Sacra, die Madeira Wine Company sowie Marina und Avenida do Mar am Meer."),
         ("Den Hang hinauf (São Pedro, Santa Clara)", "Das Museu Quinta das Cruzes, das Convento de Santa Clara, die Casa-Museu Frederico de Freitas, das Naturkundemuseum und über der Stadt die Fortaleza do Pico."),
         ("Lido und Estrada Monumental (Westen)", "Das Hotelviertel, die Bäder Lido und Ponta Gorda und die Uferpromenade weiter bis Praia Formosa und Câmara de Lobos."),
         ("Monte (über der Stadt)", "Mit der Seilbahn ab der Altstadt hinauf: der Garten Monte Palace, die Kirche Nossa Senhora do Monte, die Fahrt im Korbschlitten hinab und die zweite Seilbahn zum Botanischen Garten.")],
  bus_cap="Abfahrt des letzten Busses (Linie)",
  bus_h="Zurück: letzte Busse ins Zentrum",
  bus_th=("Ab", "Werktags", "Samstags", "Sonn- und Feiertags"),
  bus_note="Die meisten fahren auch mit der Seilbahn vom Monte hinunter; der Bus ist die Alternative, wenn die Seilbahn um 17:45 Uhr den Betrieb einstellt oder wenn Sie die Talfahrt nicht bezahlen möchten. Man kann auch zu Fuß hinuntergehen. Abfahrtszeit des letzten Busses an dieser Haltestelle laut Horários do Funchal.",
  park="Parken an der Straße (Parkscheinautomat) kostet montags bis freitags 08:00–20:00 Uhr und samstags 08:00–14:00 Uhr; sonn- und feiertags ist es kostenlos.",
  faq_h="Fragen",
  faq=[("Hat der Mercado dos Lavradores sonntags geöffnet?", "Nein. Die Markthalle öffnet montags bis freitags 07:00–19:00 Uhr und samstags 07:00–14:00 Uhr; sonntags und an Feiertagen ist sie geschlossen."),
       ("Welche Museen in Funchal haben montags geöffnet?", "Das Museu de Arte Sacra, das Museu A Cidade do Açúcar, die Fortaleza do Pico, die Madeira Wine Company und das Design Center. Die meisten anderen Museen schließen montags."),
       ("Ist Parken an der Straße in Funchal sonntags kostenlos?", "Ja. Parken an der Straße (Parkscheinautomat) kostet montags bis freitags 08:00–20:00 Uhr und samstags 08:00–14:00 Uhr; sonn- und feiertags ist es kostenlos."),
       ("Wann fährt die Seilbahn zum Monte?", "Täglich von 08:45 bis 17:45 Uhr, außer am 1. Weihnachtstag. Danach fahren Stadtbusse vom Monte bis spät abends ins Zentrum, oder Sie gehen zu Fuß hinunter.")],
  src_h="Quellen",
  src="Veranstaltungen: Kulturkalender der Stadt (cultura.funchal.pt) und Veranstaltungskalender der Region (eventsmadeira.com). Öffnungszeiten: die Website jedes Betreibers und die Regionaldirektion für Kultur. Themenmärkte: Mercados do Funchal. Bäder und Parken: Frente MarFunchal. Wetter und Meer: IPMA. Busse: Horários do Funchal.",
 ),
 "pl": dict(
  title="Funchal dziś: co się dzieje, co jest otwarte",
  desc="Co dziś w Funchal: wydarzenia, co jest teraz otwarte, targ, muzea, kąpieliska, zachód słońca i ostatni autobus. Sprawdź, zanim wyjdziesz z hotelu.",
  h1="Funchal dziś: co się dzieje i co jest otwarte",
  sub="Wydarzenia, co jest teraz otwarte, targ, kąpieliska i ostatni autobus: na czas pobytu w mieście.",
  now_static="Większość muzeów w Funchal jest zamknięta w niedziele, poniedziałki i święta, Mercado dos Lavradores jest zamknięty w niedziele i święta, a kolejka linowa na Monte kursuje codziennie od 08:45 do 17:45.",
  ask="Zapytaj Levadinho o coś jeszcze",
  ev_h="Co dzieje się w tym tygodniu",
  ev_note="Z kalendarza kulturalnego miasta i kalendarza wydarzeń regionu. W kilka dni w miesiącu na najwyższym piętrze targu odbywa się jarmark tematyczny (antyki, rękodzieło, gastronomia, moda), 09:00–17:00: Levadinho mówi o tym na górze strony w danym dniu.",
  open_h="Co jest dziś otwarte", open_th=("Miejsce", "Godziny", "Teraz"),
  open_note="Większość muzeów publicznych jest zamknięta w niedziele, poniedziałki i święta. W niedzielę otwarte są ogrody, kolejki linowe, MAMMA, Design Center i Muzeum Historii Naturalnej.",
  kinds={"market": "Targ", "cable": "Kolejki linowe", "toboggan": "Sanie", "garden": "Ogrody", "museum": "Muzea"},
  lido_h="Kąpieliska i morze",
  lido_p="Baseny nad morzem w Funchal prowadzi Frente MarFunchal. Wstęp: dorośli 6 €, 7–17 lat 2 €, poniżej 7 lat bezpłatnie; plaża Praia Formosa jest bezpłatna. Godziny zmieniają się w zależności od sezonu.",
  area_h="Miasto według dzielnic",
  areas=[("Zona Velha (Stare Miasto)", "Rua de Santa Maria z malowanymi drzwiami, Mercado dos Lavradores, stacja kolejki na Monte, Fortaleza de São Tiago i kąpielisko Barreirinha."),
         ("Centrum", "Katedra (Sé), Avenida Arriaga i Jardim Municipal, Praça do Município z Museu de Arte Sacra, Madeira Wine Company oraz marina i Avenida do Mar nad morzem."),
         ("Pod górę (São Pedro, Santa Clara)", "Museu Quinta das Cruzes, Convento de Santa Clara, Casa-Museu Frederico de Freitas, Muzeum Historii Naturalnej i, ponad miastem, Fortaleza do Pico."),
         ("Lido i Estrada Monumental (zachód)", "Dzielnica hoteli, kąpieliska Lido i Ponta Gorda oraz promenada nad morzem do Praia Formosa i Câmara de Lobos."),
         ("Monte (nad miastem)", "Wjazd kolejką linową ze Starego Miasta: ogród Monte Palace, kościół Nossa Senhora do Monte, zjazd saniami i druga kolejka do Ogrodu Botanicznego.")],
  bus_cap="Odjazd ostatniego autobusu (linia)",
  bus_h="Powrót: ostatnie autobusy do centrum",
  bus_th=("Skąd", "Dni robocze", "Soboty", "Niedziele i święta"),
  bus_note="Większość osób zjeżdża z Monte także kolejką; autobus to alternatywa, gdy kolejka kończy kursy o 17:45, albo gdy nie chcesz płacić za zjazd. Można też zejść pieszo. Godziny odjazdu ostatniego autobusu z tego przystanku według Horários do Funchal.",
  park="Płatne parkowanie na ulicy obowiązuje od poniedziałku do piątku 08:00–20:00 i w soboty 08:00–14:00; w niedziele i święta jest bezpłatne.",
  faq_h="Pytania",
  faq=[("Czy Mercado dos Lavradores jest otwarty w niedzielę?", "Nie. Targ jest otwarty od poniedziałku do piątku 07:00–19:00 i w soboty 07:00–14:00; w niedziele i święta jest zamknięty."),
       ("Które muzea w Funchal są otwarte w poniedziałki?", "Museu de Arte Sacra, Museu A Cidade do Açúcar, Fortaleza do Pico, Madeira Wine Company i Design Center. Większość pozostałych muzeów jest w poniedziałki zamknięta."),
       ("Czy parkowanie na ulicy w Funchal jest bezpłatne w niedzielę?", "Tak. Płatne parkowanie na ulicy obowiązuje od poniedziałku do piątku 08:00–20:00 i w soboty 08:00–14:00; w niedziele i święta jest bezpłatne."),
       ("W jakich godzinach kursuje kolejka linowa na Monte?", "Codziennie od 08:45 do 17:45, z wyjątkiem Bożego Narodzenia. Później z Monte do centrum jeżdżą do późnego wieczora autobusy miejskie, można też zejść pieszo.")],
  src_h="Źródła",
  src="Wydarzenia: kalendarz kulturalny miasta (cultura.funchal.pt) i kalendarz wydarzeń regionu (eventsmadeira.com). Godziny otwarcia: strona każdego operatora i Regionalna Dyrekcja Kultury. Jarmarki: Mercados do Funchal. Kąpieliska i parkowanie: Frente MarFunchal. Pogoda i morze: IPMA. Autobusy: Horários do Funchal.",
 ),
}
LIDO_NAMES = [("lido", "Complexo Balnear do Lido", "https://frentemarfunchal.pt/complexos/lido-2/"),
              ("ponta-gorda", "Complexo Balnear da Ponta Gorda", "https://frentemarfunchal.pt/complexos/ponta-gorda/"),
              ("doca-do-cavacas", "Poças do Gomes – Doca do Cavacas", "https://frentemarfunchal.pt/complexos/pocas-do-gomes-doca-do-cavacas/"),
              ("barreirinha", "Complexo Balnear da Barreirinha", "https://frentemarfunchal.pt/complexos/barreirinha/")]

CSS = """<style>
.lvd-now{margin-top:16px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;
  display:grid;grid-template-columns:48px 1fr;gap:12px;align-items:start}
.lvd-now img{width:48px;height:48px;border-radius:50%;object-fit:cover}
.lvd-now .who{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-soft);font-weight:700;margin-bottom:2px}
.lvd-now .now-hi{font-weight:750;margin-bottom:6px}
.lvd-now ul{padding-left:18px;margin:0 0 8px}
.lvd-now li{font-size:15px;margin-bottom:5px}
.lvd-now .now-ask{display:inline-block;font-size:14px;font-weight:700;color:var(--ink)}
.fx-st{font-size:12.5px;font-weight:800;letter-spacing:.02em;color:var(--ink-soft);white-space:nowrap}
.fx-st.OPEN{color:var(--open)} .fx-st.PARTIAL{color:var(--partial)} .fx-st.CLOSED{color:var(--closed)}
ul.fx-places{list-style:none;padding:0;margin:0 0 6px}
ul.fx-places li{border-bottom:1px solid var(--line);padding:7px 0;margin:0}
ul.fx-places .pl{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
ul.fx-places .hr{display:block;font-size:13.5px;color:var(--ink-soft);margin-top:2px}
ul.fx-events{list-style:none;padding:0}
ul.fx-events li{border-bottom:1px solid var(--line);padding:7px 0;margin:0}
dl.areas dt{font-weight:750;margin-top:10px} dl.areas dd{margin:2px 0 0;font-size:15.5px}
</style>"""


def open_table(lang, c):
    """Grouped list (a 3-column table was unreadable on a phone): name and live status on one line, hours below."""
    out = []
    for kind in KIND_ORDER:
        ps = [p for p in PLACES if p["kind"] == kind]
        if not ps:
            continue
        li = "".join(f'<li><span class="pl">{ext(p["url"], html.escape(p["name"]))} <span class="fx-st" data-place="{p["id"]}"></span></span>'
                     f'<span class="hr">{html.escape(hours_text(p, lang))}</span></li>' for p in ps)
        out.append(f'<h3>{c["kinds"][kind]}</h3><ul class="fx-places">{li}</ul>')
    return "\n  ".join(out)


def body(lang):
    c = C[lang]
    lidos = "".join(f'<li>{ext(u, n)} · <span class="fx-st" data-lido="{i}"></span></li>' for i, n, u in LIDO_NAMES)
    bus_th = "".join(f"<th>{h}</th>" for h in c["bus_th"])
    faq = "\n".join(f"  <h3>{html.escape(q)}</h3>\n  <p>{html.escape(a)}</p>" for q, a in c["faq"])
    areas = "".join(f"<dt>{html.escape(t)}</dt><dd>{html.escape(d)}</dd>" for t, d in c["areas"])
    return f"""<section id="events">
  <h2>{c['ev_h']}</h2>
  <div id="fxEvents"><!-- STATIC-FX-EVENTS:START --><!-- STATIC-FX-EVENTS:END --></div>
  <p class="src">{html.escape(c['ev_note'])}</p>
</section>

<section id="open">
  <h2>{c['open_h']}</h2>
  {open_table(lang, c)}
  <p>{html.escape(c['open_note'])}</p>
</section>

<section id="lidos">
  <h2>{c['lido_h']}</h2>
  <ul>{lidos}</ul>
  <p>{html.escape(c['lido_p'])} {ext("https://frentemarfunchal.pt/tarifario/", "Frente MarFunchal")}</p>
</section>

<section id="areas">
  <h2>{c['area_h']}</h2>
  <dl class="areas">{areas}</dl>
</section>

<section id="bus">
  <h2>{c['bus_h']}</h2>
  <div class="tbl-wrap"><table><caption>{c['bus_cap']}</caption><thead><tr>{bus_th}</tr></thead><tbody><!-- STATIC-FX-LASTBUS:START --><!-- STATIC-FX-LASTBUS:END --></tbody></table></div>
  <p>{html.escape(c['bus_note'])}</p>
  <p>{html.escape(c['park'])} {ext(PARKING["url"], "Frente MarFunchal")}</p>
</section>

<section id="faq">
  <h2>{c['faq_h']}</h2>
{faq}
</section>

<section>
  <h2>{c['src_h']}</h2>
  <p class="src">{html.escape(c['src'])}</p>
</section>"""


def now_panel(lang):
    c = C[lang]
    href = html.escape(wa_link("web-funchal", GREET[lang]), quote=True)
    return (f'<section class="lvd-now" id="now" data-page="funchal" aria-live="polite">\n'
            f'  <img src="/img/levadinho-avatar.jpg" alt="" width="48" height="48">\n'
            f'  <div><p class="who">Levadinho</p><div class="now-text"><p>{html.escape(c["now_static"])}</p></div>\n'
            f'  <a class="now-ask" href="{href}" target="_blank" rel="noopener">{html.escape(c["ask"])} →</a></div>\n'
            f'</section>\n')


def build(lang):
    c = C[lang]
    src = os.path.join(ROOT, PREFIX[lang].lstrip("/"), "free-walks", "index.html")
    h = open(src, encoding="utf-8").read()
    url = f"{BASE}{PREFIX[lang]}/{SLUG}/"
    t, d = html.escape(c["title"], quote=True), html.escape(c["desc"], quote=True)
    h = h.replace("/free-walks/", f"/{SLUG}/")
    h = re.sub(r"<title>.*?</title>", f"<title>{t}</title>", h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{d}">', h, count=1)
    h = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', h, count=1)
    h = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{d}">', h, count=1)
    h = re.sub(r'<meta property="og:type" content="[^"]*">', '<meta property="og:type" content="website">', h, count=1)
    h = re.sub(r'\n?<!-- Facts:.*?-->', "", h, count=1, flags=re.S)
    h = re.sub(r'  lastUpdated: "[^"]*"', '  lastUpdated: ""', h, count=1)
    page = {"@context": "https://schema.org", "@type": "WebPage", "url": url, "name": c["title"], "description": c["desc"],
            "inLanguage": lang, "dateModified": "2026-10-08T12:00+01:00",
            "about": {"@type": "City", "name": "Funchal", "containedInPlace": {"@type": "Place", "name": "Madeira"}},
            "isPartOf": {"@id": BASE + "/#website"}, "publisher": {"@id": BASE + "/#owner"}}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in c["faq"]]}
    new_ld = "".join('<script type="application/ld+json">\n' + json.dumps(x, ensure_ascii=False, indent=1) + "\n</script>\n"
                     for x in (page, faq))
    blocks = list(re.finditer(r'<script type="application/ld\+json">.*?</script>\n?', h, re.S))
    head_end = h.index("</head>")
    head_blocks = [m for m in blocks if m.start() < head_end and '"BreadcrumbList"' not in m.group(0)]
    for i, m in enumerate(reversed(head_blocks)):
        h = h[:m.start()] + (new_ld if i == len(head_blocks) - 1 else "") + h[m.end():]
    h = h.replace("</head>", CSS + "\n</head>", 1)
    h = re.sub(r"<h1>.*?</h1>", f"<h1>{html.escape(c['h1'], quote=False)}</h1>", h, count=1, flags=re.S)
    h = re.sub(r'<p class="sub">.*?</p>', f'<p class="sub">{html.escape(c["sub"], quote=False)}</p>', h, count=1, flags=re.S)
    # the Levadinho panel goes right after the header (gen_cta.py then puts the WhatsApp block below it)
    h = re.sub(r"\n*<!-- LEVADINHO-CTA:START.*?<!-- LEVADINHO-CTA:END -->\n*", "\n", h, count=1, flags=re.S)
    i = h.index("</header>\n") + len("</header>\n")
    m2 = h.index("<!-- SITE-NAV-GUIDES:START")
    h = h[:i] + "\n" + now_panel(lang) + "\n" + body(lang) + "\n\n" + h[m2:]
    h = re.sub(r"<script>\n/\* Live status badges:.*?</script>\n", "", h, count=1, flags=re.S)
    h = h.replace("</body>", '<script src="/funchal.js" defer></script>\n</body>', 1)
    out = os.path.join(ROOT, PREFIX[lang].lstrip("/"), SLUG, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else None
    if old:   # keep what the updater wrote, and the page's dateModified
        for key in ("STATIC-FX-EVENTS", "STATIC-FX-LASTBUS"):
            mm = re.search(rf"<!-- {key}:START -->(.*?)<!-- {key}:END -->", old, re.S)
            if mm:
                h = h.replace(f"<!-- {key}:START --><!-- {key}:END -->", f"<!-- {key}:START -->{mm.group(1)}<!-- {key}:END -->")
        dm = re.search(r'"dateModified":\s*"([^"]*)', old)
        if dm:
            h = re.sub(r'("dateModified":\s*")[^"]*', lambda x: x.group(1) + dm.group(1), h, count=1)
        mq = re.search(r"<!-- QR-HEAD:START.*?QR-HEAD:END -->\n?", old, re.S)
        if mq:
            h = h.replace("<title>", mq.group(0) + "<title>", 1)
    if old != h:
        open(out, "w", encoding="utf-8").write(h)
    return out, len(c["title"]), len(c["desc"])


def main():
    for lang in LANGS:
        out, lt, ld = build(lang)
        flag = "" if lt <= 60 and 120 <= ld <= 155 else "  <-- title/description length"
        print(f"{os.path.relpath(out, ROOT)}: title {lt}, description {ld}{flag}")
    for script in ("gen_site_nav.py", "gen_cta.py", "gen_owner.py", "gen_qr.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "update_funchal.py"), "--pages-only"], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
