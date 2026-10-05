#!/usr/bin/env python3
"""Writes the "Levadas by bus" guide (/levadas-by-bus/ in en/pt/fr/de/pl).

One card per trail whose bus times we have, grouped: there and back by bus, bus + taxi, bus at one end
only, and the plateau trails no bus reaches. Times are the same curated data as the trail pages' "By bus"
sections (scripts/gen_bus.py TRAILS), shown as first bus there / last bus back; PR10 and PR11 (hand-written
CAM sections on their pages) are entered below from the same CAM Santana sheet. Each card carries a live
badge and a STATIC-STATUS marker (filled from the trail page now, refreshed by the daily updater).
Afterwards it runs gen_site_nav.py and gen_cta.py. Re-run whenever gen_bus.py's data changes. Idempotent.
"""
import html, json, pathlib, re, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_bus
from gen_bus import T, S, seg, sentence, line_label
import gen_site_nav

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://levadinho-madeira.com"
LANGS = ["en", "pt", "fr", "de", "pl"]
PFX = {"en": "", "pt": "/pt", "fr": "/fr", "de": "/de", "pl": "/pl"}
SLUG = "/levadas-by-bus/"
import datetime, zoneinfo
TODAY = datetime.datetime.now(zoneinfo.ZoneInfo("Atlantic/Madeira")).date().isoformat()

# CAM Santana sheet, Funchal <-> Ribeiro Frio (as on the hand-written Balcões / Furado sections).
RF_THERE = {"mon_fri": [("08:10", "08:50", ""), ("09:00", "09:41", ""), ("10:00", "10:41", ""), ("13:45", "14:31", "")],
            "sat": [("07:30", "08:12", ""), ("10:00", "10:42", ""), ("13:30", "14:13", "")],
            "sun_hol": [("07:30", "08:12", ""), ("10:30", "11:15", "")]}
RF_BACK = {"mon_fri": [("11:40", "12:30", ""), ("18:12", "19:00", "")], "sat_sun_hol": [("18:30", "19:20", "")]}
EXTRA = {
    "PR11": {"dir": "balcoes", "there": [("loop_stop", "Ribeiro Frio"), seg("CAM", "Santana", "Funchal", "Ribeiro Frio", RF_THERE)],
             "back": [seg("CAM", "Santana", "Ribeiro Frio", "Funchal", RF_BACK)]},
    "PR10": {"dir": "levada-do-furado", "there": [("start_stop", "Ribeiro Frio"), seg("CAM", "Santana", "Funchal", "Ribeiro Frio", RF_THERE)],
             "back": [("portela",)]},
}
DATA = {**gen_bus.TRAILS, **EXTRA}
GROUPS = [("both", ["PR8", "PR11", "PR19", "PR20"]), ("taxi", ["PR9", "PR9.1"]),
          ("one", ["PR2", "PR10", "PR3.1", "PR1.3", "PR17", "PR5"])]
NOBUS = [c for c, t in gen_bus.TRAILS.items() if "nobus" in t]

L = {
    "en": dict(
        title="Levadas by bus from Funchal: which trails? (2026)",
        desc="Which Madeira trails can you reach by public bus from Funchal? First and last buses for 12 trails, and the ones no bus reaches. Check before you go.",
        h1="Levadas by bus: which trails can you reach without a car?",
        sub="Times from the operators' timetables on SIGA, the Region's public transport site. Each trail's page has the full list.",
        alert="<b>The short answer:</b> four trails have a bus to the start <b>and</b> back from the end: <b>PR8 São Lourenço</b>, <b>PR11 Balcões</b>, <b>PR19</b> and <b>PR20</b>. For PR9 Caldeirão Verde you take the bus to Santana and a taxi up. Six more have a bus at one end only. No bus reaches Rabaçal (25 Fontes), the Paul da Serra plateau or the Fanal.",
        both="There and back by bus", taxi="Bus plus a taxi", one="Bus at one end only", nobus="No bus: Rabaçal, Paul da Serra, Fanal",
        nobus_p="None of the bus lines published on SIGA serves these trailheads. You need a car, a taxi or a tour transfer.",
        first="first bus", last="last bus", only="bus", start="start", q="Questions", next="Next steps", srch="Sources",
        all="Which trails are open today?",
        src='Bus times: the operators\' timetables (CAM, Rodoeste, Horários do Funchal) published on <a class="plain" href="https://siga.madeira.gov.pt/horarios" target="_blank" rel="noopener">SIGA</a>, checked 3 Oct 2026. Times at intermediate stops are approximate; no buses on 25 December; check before you travel. Trail status: <a class="plain" href="https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos" target="_blank" rel="noopener">IFCN trail warnings</a>.',
        faq=[("Which levada walks can I do by bus from Funchal?",
              "Four trails have a public bus to the start and back from the end: PR8 São Lourenço (CAM line 113 to Baía d'Abra), PR11 Balcões (CAM's Santana buses to Ribeiro Frio), and PR19 and PR20 (Rodoeste line 142 to Prazeres in the morning, back from Paul do Mar or Jardim do Mar in the afternoon). Six more have a bus at one end only."),
             ("Is there a bus to 25 Fontes and Rabaçal?",
              "No. None of the bus lines published on SIGA serves Rabaçal, the Paul da Serra plateau or the Fanal, so PR6 25 Fontes, PR6.1 Risco, PR13 Fanal and the other trails up there need a car, a taxi or a transfer."),
             ("Is there a bus to São Lourenço?",
              "Yes. CAM line 113 (new no. 702) runs every day from Funchal to Baía d'Abra, where PR8 starts and ends. The first bus leaves Funchal at 07:30."),
             ("Can I get to Caldeirão Verde by bus?",
              "Partly. CAM buses run from Funchal to Santana, but none goes up to the Queimadas forest park where PR9 starts: take a taxi from Santana for the last stretch."),
             ("Where can I find the bus timetables?",
              "On SIGA (siga.madeira.gov.pt/horarios), the Region's public transport site, which publishes the operators' timetables. Check them before you travel: times can change.")]),
    "pt": dict(
        title="Levadas de autocarro a partir do Funchal (2026)",
        desc="Que percursos da Madeira se fazem de autocarro a partir do Funchal? Primeiro e último autocarro para 12 percursos e onde não há autocarro. Confirme já.",
        h1="Levadas de autocarro: que percursos pode fazer sem carro?",
        sub="Horários das tabelas dos operadores publicadas no SIGA, o portal de transportes públicos da Região. Cada página de percurso tem a lista completa.",
        alert="<b>Resposta curta:</b> quatro percursos têm autocarro até ao início <b>e</b> de regresso a partir do fim: <b>PR8 São Lourenço</b>, <b>PR11 Balcões</b>, <b>PR19</b> e <b>PR20</b>. Para o PR9 Caldeirão Verde, apanhe o autocarro até Santana e um táxi até lá acima. Outros seis têm autocarro só numa das pontas. Nenhum autocarro chega ao Rabaçal (25 Fontes), ao planalto do Paul da Serra nem ao Fanal.",
        both="Ida e volta de autocarro", taxi="Autocarro e táxi", one="Autocarro só numa das pontas", nobus="Sem autocarro: Rabaçal, Paul da Serra, Fanal",
        nobus_p="Nenhuma das linhas publicadas no SIGA serve estes pontos de partida. Precisa de carro, táxi ou transfer.",
        first="primeiro autocarro", last="último autocarro", only="autocarro", start="início", q="Perguntas", next="Próximos passos", srch="Fontes",
        all="Que percursos estão abertos hoje?",
        src='Horários dos autocarros: tabelas dos operadores (CAM, Rodoeste, Horários do Funchal) publicadas no <a class="plain" href="https://siga.madeira.gov.pt/horarios" target="_blank" rel="noopener">SIGA</a>, consultadas a 3 de outubro de 2026. As horas nas paragens intermédias são aproximadas; não há autocarros a 25 de dezembro; confirme antes de viajar. Estado dos percursos: <a class="plain" href="https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos" target="_blank" rel="noopener">avisos do IFCN</a>.',
        faq=[("Que levadas posso fazer de autocarro a partir do Funchal?",
              "Quatro percursos têm autocarro público até ao início e de regresso a partir do fim: PR8 São Lourenço (linha 113 da CAM até à Baía d'Abra), PR11 Balcões (autocarros da rede Santana da CAM até ao Ribeiro Frio), e PR19 e PR20 (linha 142 da Rodoeste até aos Prazeres de manhã, regresso do Paul do Mar ou do Jardim do Mar à tarde). Outros seis têm autocarro só numa das pontas."),
             ("Há autocarro para as 25 Fontes e o Rabaçal?",
              "Não. Nenhuma das linhas publicadas no SIGA serve o Rabaçal, o planalto do Paul da Serra nem o Fanal, por isso o PR6 25 Fontes, o PR6.1 Risco, o PR13 Fanal e os outros percursos lá em cima exigem carro, táxi ou transfer."),
             ("Há autocarro para São Lourenço?",
              "Sim. A linha 113 da CAM (novo n.º 702) faz todos os dias o trajeto do Funchal à Baía d'Abra, onde o PR8 começa e acaba. O primeiro autocarro sai do Funchal às 07:30."),
             ("Posso ir ao Caldeirão Verde de autocarro?",
              "Em parte. Os autocarros da CAM vão do Funchal a Santana, mas nenhum sobe ao Parque Florestal das Queimadas, onde começa o PR9: apanhe um táxi em Santana para o último troço."),
             ("Onde encontro os horários dos autocarros?",
              "No SIGA (siga.madeira.gov.pt/horarios), o portal de transportes públicos da Região, que publica as tabelas dos operadores. Confirme antes de viajar: os horários podem mudar.")]),
    "fr": dict(
        title="Levadas en bus depuis Funchal : quels sentiers ? (2026)",
        desc="Quels sentiers de Madère rejoindre en bus depuis Funchal ? Premier et dernier bus pour 12 sentiers, et ceux sans bus. Vérifiez avant de partir.",
        h1="Levadas en bus : quels sentiers sans voiture ?",
        sub="Horaires tirés des fiches des transporteurs publiées sur SIGA, le site des transports publics de la Région. La page de chaque sentier donne la liste complète.",
        alert="<b>En bref :</b> quatre sentiers ont un bus jusqu'au départ <b>et</b> un bus retour depuis l'arrivée : <b>PR8 São Lourenço</b>, <b>PR11 Balcões</b>, <b>PR19</b> et <b>PR20</b>. Pour le PR9 Caldeirão Verde, prenez le bus jusqu'à Santana puis un taxi. Six autres n'ont un bus qu'à un bout. Aucun bus ne va au Rabaçal (25 Fontes), sur le plateau du Paul da Serra ni au Fanal.",
        both="Aller et retour en bus", taxi="Bus et taxi", one="Bus à un seul bout", nobus="Pas de bus : Rabaçal, Paul da Serra, Fanal",
        nobus_p="Aucune ligne publiée sur SIGA ne dessert ces départs. Il vous faut une voiture, un taxi ou un transfert.",
        first="premier bus", last="dernier bus", only="bus", start="départ", q="Questions", next="Et ensuite", srch="Sources",
        all="Quels sentiers sont ouverts aujourd'hui ?",
        src='Horaires des bus : fiches des transporteurs (CAM, Rodoeste, Horários do Funchal) publiées sur <a class="plain" href="https://siga.madeira.gov.pt/horarios" target="_blank" rel="noopener">SIGA</a>, consultées le 3 octobre 2026. Les heures aux arrêts intermédiaires sont approximatives ; pas de bus le 25 décembre ; vérifiez avant de partir. État des sentiers : <a class="plain" href="https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos" target="_blank" rel="noopener">avis de l\'IFCN</a>.',
        faq=[("Quelles levadas faire en bus depuis Funchal ?",
              "Quatre sentiers ont un bus public jusqu'au départ et un retour depuis l'arrivée : PR8 São Lourenço (ligne 113 de la CAM jusqu'à Baía d'Abra), PR11 Balcões (bus du réseau Santana de la CAM jusqu'à Ribeiro Frio), et PR19 et PR20 (ligne 142 de Rodoeste jusqu'à Prazeres le matin, retour depuis Paul do Mar ou Jardim do Mar l'après-midi). Six autres n'ont un bus qu'à un bout."),
             ("Y a-t-il un bus pour 25 Fontes et le Rabaçal ?",
              "Non. Aucune ligne publiée sur SIGA ne dessert le Rabaçal, le plateau du Paul da Serra ni le Fanal : le PR6 25 Fontes, le PR6.1 Risco, le PR13 Fanal et les autres sentiers de là-haut demandent une voiture, un taxi ou un transfert."),
             ("Y a-t-il un bus pour São Lourenço ?",
              "Oui. La ligne 113 de la CAM (nouveau n° 702) relie chaque jour Funchal à Baía d'Abra, où le PR8 commence et se termine. Le premier bus part de Funchal à 07:30."),
             ("Peut-on aller au Caldeirão Verde en bus ?",
              "En partie. Les bus de la CAM vont de Funchal à Santana, mais aucun ne monte au parc forestier de Queimadas, départ du PR9 : prenez un taxi à Santana pour la fin du trajet."),
             ("Où trouver les horaires des bus ?",
              "Sur SIGA (siga.madeira.gov.pt/horarios), le site des transports publics de la Région, qui publie les fiches des transporteurs. Vérifiez avant de partir : les horaires peuvent changer.")]),
    "de": dict(
        title="Levadas mit dem Bus ab Funchal: welche Wege? (2026)",
        desc="Welche Wanderwege auf Madeira erreichen Sie mit dem Bus ab Funchal? Erster und letzter Bus für 12 Wege und wo kein Bus fährt. Vor der Fahrt prüfen.",
        h1="Levadas mit dem Bus: welche Wege ohne Auto?",
        sub="Zeiten aus den Fahrplänen der Busunternehmen auf SIGA, dem Nahverkehrsportal der Region. Die Seite jedes Wegs hat die vollständige Liste.",
        alert="<b>Kurz gesagt:</b> Vier Wege haben einen Bus zum Start <b>und</b> zurück vom Ziel: <b>PR8 São Lourenço</b>, <b>PR11 Balcões</b>, <b>PR19</b> und <b>PR20</b>. Zum PR9 Caldeirão Verde fahren Sie mit dem Bus nach Santana und dann mit dem Taxi hinauf. Sechs weitere haben nur an einem Ende einen Bus. Kein Bus fährt zum Rabaçal (25 Fontes), auf die Hochebene Paul da Serra oder zum Fanal.",
        both="Hin und zurück mit dem Bus", taxi="Bus plus Taxi", one="Bus nur an einem Ende", nobus="Kein Bus: Rabaçal, Paul da Serra, Fanal",
        nobus_p="Keine der auf SIGA veröffentlichten Linien bedient diese Startpunkte. Sie brauchen ein Auto, ein Taxi oder einen Transfer.",
        first="erster Bus", last="letzter Bus", only="Bus", start="Start", q="Fragen", next="Weiter", srch="Quellen",
        all="Welche Wanderwege sind heute offen?",
        src='Busfahrzeiten: Fahrpläne der Busunternehmen (CAM, Rodoeste, Horários do Funchal) auf <a class="plain" href="https://siga.madeira.gov.pt/horarios" target="_blank" rel="noopener">SIGA</a>, geprüft am 3. Oktober 2026. Zeiten an Zwischenhalten sind ungefähr; am 25. Dezember fahren keine Busse; vor der Fahrt prüfen. Status der Wege: <a class="plain" href="https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos" target="_blank" rel="noopener">IFCN-Hinweise</a>.',
        faq=[("Welche Levadas kann ich ab Funchal mit dem Bus wandern?",
              "Vier Wege haben einen öffentlichen Bus zum Start und zurück vom Ziel: PR8 São Lourenço (CAM-Linie 113 nach Baía d'Abra), PR11 Balcões (CAM-Busse des Santana-Netzes nach Ribeiro Frio) sowie PR19 und PR20 (Rodoeste-Linie 142 morgens nach Prazeres, nachmittags zurück ab Paul do Mar oder Jardim do Mar). Sechs weitere haben nur an einem Ende einen Bus."),
             ("Fährt ein Bus zu den 25 Fontes und zum Rabaçal?",
              "Nein. Keine der auf SIGA veröffentlichten Linien bedient den Rabaçal, die Hochebene Paul da Serra oder den Fanal. Für PR6 25 Fontes, PR6.1 Risco, PR13 Fanal und die anderen Wege dort oben brauchen Sie ein Auto, ein Taxi oder einen Transfer."),
             ("Fährt ein Bus nach São Lourenço?",
              "Ja. Die CAM-Linie 113 (neue Nr. 702) fährt täglich von Funchal nach Baía d'Abra, wo der PR8 beginnt und endet. Der erste Bus verlässt Funchal um 07:30."),
             ("Komme ich mit dem Bus zum Caldeirão Verde?",
              "Teilweise. CAM-Busse fahren von Funchal nach Santana, aber keiner fährt hinauf zum Waldpark Queimadas, wo der PR9 beginnt: Nehmen Sie für das letzte Stück ein Taxi ab Santana."),
             ("Wo finde ich die Busfahrpläne?",
              "Auf SIGA (siga.madeira.gov.pt/horarios), dem Nahverkehrsportal der Region, das die Fahrpläne der Busunternehmen veröffentlicht. Prüfen Sie vor der Fahrt: Zeiten können sich ändern.")]),
    "pl": dict(
        title="Lewady autobusem z Funchal: które szlaki? (2026)",
        desc="Na które szlaki Madery dojedziesz autobusem z Funchal? Pierwszy i ostatni autobus dla 12 szlaków i te bez autobusu. Sprawdź przed wyjazdem.",
        h1="Lewady autobusem: które szlaki bez samochodu?",
        sub="Godziny z rozkładów przewoźników opublikowanych w SIGA, regionalnym serwisie transportu publicznego. Strona każdego szlaku ma pełną listę.",
        alert="<b>W skrócie:</b> cztery szlaki mają autobus na start <b>i</b> powrotny z mety: <b>PR8 São Lourenço</b>, <b>PR11 Balcões</b>, <b>PR19</b> i <b>PR20</b>. Na PR9 Caldeirão Verde jedź autobusem do Santany, a dalej taksówką. Sześć kolejnych ma autobus tylko na jednym końcu. Żaden autobus nie dojeżdża do Rabaçal (25 Fontes), na płaskowyż Paul da Serra ani do Fanalu.",
        both="Tam i z powrotem autobusem", taxi="Autobus i taksówka", one="Autobus tylko na jednym końcu", nobus="Bez autobusu: Rabaçal, Paul da Serra, Fanal",
        nobus_p="Żadna z linii opublikowanych w SIGA nie obsługuje tych punktów startowych. Potrzebny jest samochód, taksówka lub transfer.",
        first="pierwszy autobus", last="ostatni autobus", only="autobus", start="start", q="Pytania", next="Dalej", srch="Źródła",
        all="Które szlaki są dziś otwarte?",
        src='Godziny autobusów: rozkłady przewoźników (CAM, Rodoeste, Horários do Funchal) opublikowane w <a class="plain" href="https://siga.madeira.gov.pt/horarios" target="_blank" rel="noopener">SIGA</a>, sprawdzone 3 października 2026. Godziny na przystankach pośrednich są orientacyjne; 25 grudnia autobusy nie kursują; sprawdź przed podróżą. Stan szlaków: <a class="plain" href="https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos" target="_blank" rel="noopener">komunikaty IFCN</a>.',
        faq=[("Które lewady można przejść, dojeżdżając autobusem z Funchal?",
              "Cztery szlaki mają autobus publiczny na start i powrotny z mety: PR8 São Lourenço (linia 113 CAM do Baía d'Abra), PR11 Balcões (autobusy sieci Santana CAM do Ribeiro Frio) oraz PR19 i PR20 (linia 142 Rodoeste rano do Prazeres, powrót po południu z Paul do Mar lub Jardim do Mar). Sześć kolejnych ma autobus tylko na jednym końcu."),
             ("Czy jest autobus do 25 Fontes i Rabaçal?",
              "Nie. Żadna z linii opublikowanych w SIGA nie obsługuje Rabaçal, płaskowyżu Paul da Serra ani Fanalu, więc na PR6 25 Fontes, PR6.1 Risco, PR13 Fanal i inne tamtejsze szlaki potrzebny jest samochód, taksówka lub transfer."),
             ("Czy jest autobus do São Lourenço?",
              "Tak. Linia 113 CAM (nowy nr 702) kursuje codziennie z Funchal do Baía d'Abra, gdzie PR8 się zaczyna i kończy. Pierwszy autobus odjeżdża z Funchal o 07:30."),
             ("Czy na Caldeirão Verde dojadę autobusem?",
              "Częściowo. Autobusy CAM jeżdżą z Funchal do Santany, ale żaden nie dojeżdża do parku leśnego Queimadas, gdzie zaczyna się PR9: ostatni odcinek pokonaj taksówką z Santany."),
             ("Gdzie znajdę rozkłady jazdy autobusów?",
              "W SIGA (siga.madeira.gov.pt/horarios), regionalnym serwisie transportu publicznego, który publikuje rozkłady przewoźników. Sprawdź przed podróżą: godziny mogą się zmienić.")]),
}
NEXT = ["back", "sunrise", "free", "best"]   # gen_site_nav GUIDES keys


def esc(s):
    return html.escape(s, quote=False)


def summary(s, lang, first):
    """One segment as "Line, A → B, first bus: Monday to Friday 07:30 → 08:50; …"."""
    days = s["trips"]
    lab = L[lang]["only"] if all(len(v) == 1 for v in days.values()) else L[lang]["first" if first else "last"]
    parts, star = [], False
    for day, trips in days.items():
        dep, arr, marks = trips[0] if first else trips[-1]
        x = dep if arr is None else f"{dep} → {arr}"
        m = marks.split()
        if "T" in m:
            x += "*"; star = True
        if "PE" in m:
            x += T["PE"][lang]
        if "PNE" in m:
            x += T["PNE"][lang]
        d = T["days"][day][lang]
        if lang in ("pt", "fr", "pl") or day == "daily" or (lang == "de" and day == "sat"):   # mid-sentence
            d = d[0].lower() + d[1:]
        parts.append(f"{d} {x}")
    line = line_label(s, lang)
    out = f"{line[0].upper() + line[1:]}, {esc(s['a'])} → {esc(s['b'])}, {lab}{' :' if lang == 'fr' else ':'} " + "; ".join(parts) + "."
    if star and s["change_at"]:
        out += " " + T["change"][lang].format(p=esc(s["change_at"]))
    return out


def block(items, lang, first):
    return " ".join(summary(i, lang, first) if isinstance(i, dict) else sentence(i, lang) for i in items)


def static_status(code, lang, page):
    """The updater's current line for this trail, copied from the trail page in the same language."""
    f = ROOT / PFX[lang].lstrip("/") / page.strip("/") / "index.html"
    m = re.search(rf"<!-- STATIC-STATUS:{re.escape(code)}:START -->(.*?)<!-- STATIC-STATUS:{re.escape(code)}:END -->",
                  f.read_text(encoding="utf-8"), re.S)
    return m.group(1) if m else ""


def card(code, lang, trails):
    t, d = trails[code], DATA[code]
    href = f"{PFX[lang]}{t['page']}"
    return (f'  <div class="opt">\n'
            f'    <h3><a class="plain" href="{href}">{code} {esc(t["name"])}</a> <span class="tbadge" data-code="{code}">…</span></h3>\n'
            f'    <p><b>{T["there"][lang]}</b> {block(d["there"], lang, True)}</p>\n'
            f'    <p><b>{T["back"][lang]}</b> {block(d["back"], lang, False)}</p>\n'
            f'    <span class="static-status"><!-- STATIC-STATUS:{code}:START -->{static_status(code, lang, t["page"])}'
            f'<!-- STATIC-STATUS:{code}:END --></span>\n  </div>')


def template(lang):
    """CSS, brand line, footer and live-badge script, taken from the same language's free-walks page."""
    h = (ROOT / PFX[lang].lstrip("/") / "free-walks" / "index.html").read_text(encoding="utf-8")
    css = re.search(r"<style>\n:root\{.*?</style>", h, re.S).group(0)
    brand = re.search(r'<div class="brand">.*?</div>', h).group(0)
    footer = re.search(r"<footer>.*?</footer>", h, re.S).group(0)
    badge = re.search(r"<script>\n/\* Live status badges.*?</script>", h, re.S).group(0)
    return css, brand, footer, badge


def page(lang, trails):
    c = L[lang]
    assert len(c["title"]) <= 60, (lang, len(c["title"]))
    assert 120 <= len(c["desc"]) <= 155, (lang, len(c["desc"]))
    url = f"{BASE}{PFX[lang]}{SLUG}"
    css, brand, footer, badge = template(lang)
    alts = "\n".join(f'<link rel="alternate" hreflang="{l}" href="{BASE}{PFX[l]}{SLUG}">' for l in LANGS)
    alts += f'\n<link rel="alternate" hreflang="x-default" href="{BASE}{SLUG}">'
    langs = "\n".join(f'    <a href="{PFX[l]}{SLUG}" hreflang="{l}"{" aria-current=\"page\"" if l == lang else ""}>{l.upper()}</a>' for l in LANGS)
    webpage = {"@context": "https://schema.org", "@type": "WebPage", "url": url, "name": c["title"], "description": c["desc"],
               "inLanguage": lang, "dateModified": TODAY, "isPartOf": {"@type": "WebSite", "name": "Levadinho", "url": f"{BASE}/"}}
    faq = {"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in c["faq"]]}
    secs = []
    for key, codes in GROUPS:
        secs.append(f'<section>\n  <h2>{c[key]}</h2>\n' + "\n".join(card(x, lang, trails) for x in codes) + "\n</section>")
    items = "\n".join(f'    <li><a class="plain" href="{PFX[lang]}{trails[x]["page"]}">{x} {esc(trails[x]["name"])}</a> '
                      f'<span class="tbadge" data-code="{x}">…</span> · {c["start"]}: {esc(gen_bus.TRAILS[x]["nobus"][0][1])}</li>'
                      for x in NOBUS)
    secs.append(f'<section>\n  <h2>{c["nobus"]}</h2>\n  <p>{c["nobus_p"]}</p>\n  <ul>\n{items}\n  </ul>\n</section>')
    qa = "\n".join(f"  <h3>{esc(q)}</h3>\n  <p>{esc(a)}</p>" for q, a in c["faq"])
    secs.append(f'<section>\n  <h2>{c["q"]}</h2>\n{qa}\n</section>')
    nxt = "\n".join(f'    <li><a class="plain" href="{PFX[lang]}{gen_site_nav.GUIDE[k][1]}">{esc(gen_site_nav.GUIDE[k][4][lang])}</a></li>' for k in NEXT)
    nxt += f'\n    <li><a class="plain" href="{PFX[lang]}/">{esc(c["all"])}</a></li>'
    secs.append(f'<section>\n  <h2>{c["next"]}</h2>\n  <ul>\n{nxt}\n  </ul>\n</section>')
    secs.append(f'<section>\n  <h2>{c["srch"]}</h2>\n  <p class="src">{c["src"]}</p>\n</section>')
    ld = lambda o: '<script type="application/ld+json">\n' + json.dumps(o, ensure_ascii=False, indent=2) + "\n</script>"
    locale = {"en": "en_GB", "pt": "pt_PT", "fr": "fr_FR", "de": "de_DE", "pl": "pl_PL"}[lang]
    a = lambda s: html.escape(s, quote=True)
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<!-- ================= CONFIG — edit as needed ================== -->
<script>
const CONFIG = {{
  goatcounterCode: "madeira-levadinho",
  lastUpdated: "{TODAY}"
}};
</script>
<!-- ============================================================ -->

<title>{esc(c["title"])}</title>
<meta name="description" content="{a(c["desc"])}">

<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{a(c["title"])}">
<meta property="og:description" content="{a(c["desc"])}">
<meta property="og:image" content="{BASE}/img/og-default.jpg">
<meta property="og:image:alt" content="Levadinho: Madeira trail status, fees and booking">
<meta property="og:locale" content="{locale}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/img/icon-180.png">

{alts}

<!-- Generated by scripts/gen_bus_hub.py from scripts/gen_bus.py (bus times: SIGA timetables, seo_research/facts/bus/). Don't hand-edit. -->
{ld(webpage)}
{ld(faq)}

{css}
</head>
<body>

<div class="waymark" aria-hidden="true"></div>

<header>
  <nav class="langs" aria-label="Language">
{langs}
  </nav>
  {brand}
  <h1>{esc(c["h1"])}</h1>
  <p class="sub">{esc(c["sub"])}</p>
</header>

<div class="alert">
  {c["alert"]}
</div>

{chr(10).join(secs) + chr(10)}
{footer}

{badge}
<script>
(function(){{
  const c = CONFIG;
  try {{
    if (location.hash === '#skipgc') localStorage.setItem('gc-skip','1');
    if (location.hash === '#countme') localStorage.removeItem('gc-skip');
  }} catch(e){{}}
  const SKIP_ANALYTICS = (function(){{ try {{ return localStorage.getItem('gc-skip')==='1'; }} catch(e){{ return false; }} }})();
  if (c.goatcounterCode && !SKIP_ANALYTICS){{
    const s = document.createElement('script');
    s.dataset.goatcounter = 'https://' + c.goatcounterCode + '.goatcounter.com/count';
    s.async = true; s.src = '//gc.zgo.at/count.js';
    document.body.appendChild(s);
  }}
}})();
</script>
</body>
</html>
"""


def main():
    trails = {t["code"]: t for t in json.loads((ROOT / "status.json").read_text())["trails"]}
    for lang in LANGS:
        f = ROOT / PFX[lang].lstrip("/") / SLUG.strip("/") / "index.html"
        f.parent.mkdir(parents=True, exist_ok=True)
        new = page(lang, trails)
        if f.exists():   # unchanged copy -> leave the file (and its dates) alone
            norm = lambda h: re.sub(r'("dateModified": "|lastUpdated: ")[0-9-]+', r"\1", re.sub(r"\n{3,}", "\n\n", strip_generated(h)))
            if norm(f.read_text(encoding="utf-8")) == norm(new):
                continue
        f.write_text(new, encoding="utf-8")
        print("wrote", f.relative_to(ROOT))
    for s in ("gen_site_nav.py", "gen_cta.py", "gen_owner.py"):
        subprocess.run([sys.executable, str(ROOT / "scripts" / s)], check=True, cwd=ROOT)


def strip_generated(h):
    """The page minus the blocks gen_site_nav / gen_cta / gen_owner insert, to compare with a fresh render."""
    h = re.sub(r"<!-- (SITE-NAV[A-Z-]*|LEVADINHO-CTA[A-Z-]*|OWNER-[A-Z]+):START.*?<!-- \1:END -->\n?", "", h, flags=re.S)
    return h


if __name__ == "__main__":
    main()
