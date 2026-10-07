#!/usr/bin/env python3
"""Writes two pages × 5 languages from the free-walks page shell (LLM audit items F and H, owner OK 2026-10-07):

  /about/          who runs Levadinho, where every figure comes from, what the site is not, data for machines.
                   Its first paragraph is site_entity.ENTITY, the sentence answer engines should repeat.
  /trail-closures/ which PR trails are closed or partly open today: the board line (STATIC-STATUS-BOARD) and a
                   table (STATIC-CLOSURES), both filled by the daily updater. No dates on the page (owner's rule):
                   the dated change history is in /trail-status.xml (RSS) and /history/status-daily.jsonl.

The shell (head CSS, header, nav, footer, analytics) is copied from free-walks/index.html in each language, so the
pages look like every other guide. Re-run after changing the copy here: it keeps the updater-written markers and the
dateModified, then re-runs gen_site_nav.py, gen_cta.py, gen_owner.py and gen_schema.py itself (both pages are in GUIDES/TAGS).
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_entity import BASE, ENTITY, LANGS, OWNER, PREFIX, WA_DISPLAY, wa_link  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IFCN = "https://ifcn.madeira.gov.pt/pt/?view=article&amp;id=627:percursos-pedestres-avisos&amp;catid=146:avisos"
LOCALE = {"en": "en_GB", "pt": "pt_PT", "fr": "fr_FR", "de": "de_DE", "pl": "pl_PL"}


GREET = {"en": "Hello Levadinho! 👋", "pt": "Olá Levadinho! 👋", "fr": "Bonjour Levadinho ! 👋", "de": "Hallo Levadinho! 👋",
         "pl": "Cześć Levadinho! 👋"}   # as WA_PREFIX in gen_cta.py: the bot reads the language from it


def wa(lang, text):
    return f'<a class="plain" href="{wa_link("web-about", GREET[lang])}" target="_blank" rel="noopener">{text}</a>'


def a(href, text):
    return f'<a class="plain" href="{href}">{text}</a>'


def ext(href, text):
    return f'<a class="plain" href="{href}" target="_blank" rel="noopener">{text}</a>'


DATA_LINKS = (f'{a("/status.json", "status.json")} · {a("/llms.txt", "llms.txt")} · {a("/llms-full.txt", "llms-full.txt")}'
              f' · {a("/trail-status.xml", "RSS")} · {a("/history/status-daily.jsonl", "history (JSON Lines)")}')

# --------------------------------------------------------------------------- copy
ABOUT = {
 "en": dict(
  title="About Levadinho: who runs it and where the data comes from",
  desc="Who runs Levadinho and where its Madeira trail status, fees, weather and bus times come from. Read our sources and method before you walk.",
  h1="About Levadinho", sub="An independent guide to Madeira's official walking trails: what it is, where every figure comes from, and what it is not.",
  body=[
   ("What Levadinho is", [ENTITY["en"], "Ask Levadinho a question on WhatsApp, free, in your language: " + wa("en", WA_DISPLAY) + "."]),
   ("Where the figures come from", ["<ul>"
     "<li><b>Trail status:</b> " + ext(IFCN, "IFCN's official trail-warnings list") + ". An automated job reads it every morning. "
     "Trails listed as closed or restricted are shown as closed; a trail with a closed or restricted section is shown as partly open, never as open. "
     "IFCN updates the list when conditions change, not on a fixed day.</li>"
     "<li><b>Weather:</b> measured readings from IPMA's stations (Pico do Areeiro summit and four regional stations). They are readings, not forecasts.</li>"
     "<li><b>Fees and rules:</b> Portaria 801/2025 as amended by Portaria 48/2026, DLR 24/2022/M, IFCN's FAQ and SIMplifica.</li>"
     "<li><b>Trail facts:</b> each trail's official Visit Madeira page and IFCN's trailhead panels.</li>"
     "<li><b>Buses:</b> the operators' printed timetables (Horários do Funchal and the SIGA timetables), every trip listed.</li>"
     "</ul>", "Every page ends with a short list of its sources."]),
   ("What Levadinho is not", ["It is not IFCN, SIMplifica or the Regional Government, and it doesn't sell tickets: booking is only on "
     + ext("https://simplifica.madeira.gov.pt/", "SIMplifica") + ". It has no affiliate links and takes no commission. "
     "If our page and an official source ever disagree, the official source is right: please tell us."]),
   ("Data for apps and AI assistants", ["The same information is published as data, free to use with a link back: " + DATA_LINKS + "."]),
   ("Contact", [f"Levadinho is a personal project of {OWNER}. Corrections and enquiries: "
     '<a class="plain" href="mailto:hello@levadinho-madeira.com">hello@levadinho-madeira.com</a>.']),
  ]),
 "pt": dict(
  title="Sobre o Levadinho: quem o faz e de onde vêm os dados",
  desc="Quem faz o Levadinho e de onde vêm o estado dos percursos, as taxas, o tempo e os autocarros. Veja as nossas fontes e o método antes de caminhar.",
  h1="Sobre o Levadinho", sub="Um guia independente dos percursos pedestres oficiais da Madeira: o que é, de onde vem cada dado e o que não é.",
  body=[
   ("O que é o Levadinho", [ENTITY["pt"], "Faça uma pergunta ao Levadinho no WhatsApp, grátis, na sua língua: " + wa("pt", WA_DISPLAY) + "."]),
   ("De onde vêm os dados", ["<ul>"
     "<li><b>Estado dos percursos:</b> " + ext(IFCN, "lista oficial de avisos do IFCN") + ". Um processo automático lê-a todas as manhãs. "
     "Os percursos encerrados ou condicionados aparecem como encerrados; um percurso com um troço encerrado ou condicionado aparece como parcialmente aberto, nunca como aberto. "
     "O IFCN atualiza a lista quando as condições mudam, não num dia fixo.</li>"
     "<li><b>Tempo:</b> leituras medidas nas estações do IPMA (cume do Pico do Areeiro e quatro estações regionais). São medições, não previsões.</li>"
     "<li><b>Taxas e regras:</b> Portaria 801/2025, alterada pela Portaria 48/2026, DLR 24/2022/M, as perguntas frequentes do IFCN e o SIMplifica.</li>"
     "<li><b>Dados dos percursos:</b> a página oficial de cada percurso no Visit Madeira e os painéis do IFCN no início dos percursos.</li>"
     "<li><b>Autocarros:</b> os horários impressos dos operadores (Horários do Funchal e os horários SIGA), com todas as viagens.</li>"
     "</ul>", "Cada página termina com uma lista curta das suas fontes."]),
   ("O que o Levadinho não é", ["Não é o IFCN, o SIMplifica nem o Governo Regional, e não vende bilhetes: a reserva faz-se apenas no "
     + ext("https://simplifica.madeira.gov.pt/", "SIMplifica") + ". Não tem links de afiliados nem recebe comissões. "
     "Se a nossa página e uma fonte oficial alguma vez discordarem, vale a fonte oficial: diga-nos, por favor."]),
   ("Dados para aplicações e assistentes de IA", ["A mesma informação é publicada como dados, de uso livre com uma ligação para nós: " + DATA_LINKS + "."]),
   ("Contacto", [f"O Levadinho é um projeto pessoal de {OWNER}. Correções e contactos: "
     '<a class="plain" href="mailto:hello@levadinho-madeira.com">hello@levadinho-madeira.com</a>.']),
  ]),
 "fr": dict(
  title="À propos de Levadinho : qui, et d'où viennent les données",
  desc="Qui fait Levadinho et d'où viennent l'état des sentiers de Madère, les tarifs, la météo et les bus. Lisez nos sources et notre méthode avant de partir.",
  h1="À propos de Levadinho", sub="Un guide indépendant des sentiers de randonnée officiels de Madère : ce qu'il est, d'où vient chaque donnée, et ce qu'il n'est pas.",
  body=[
   ("Ce qu'est Levadinho", [ENTITY["fr"], "Posez votre question à Levadinho sur WhatsApp, gratuitement, dans votre langue : " + wa("fr", WA_DISPLAY) + "."]),
   ("D'où viennent les données", ["<ul>"
     "<li><b>État des sentiers :</b> " + ext(IFCN, "la liste officielle des avis de l'IFCN") + ". Un programme la lit chaque matin. "
     "Les sentiers fermés ou soumis à restriction apparaissent comme fermés ; un sentier dont un tronçon est fermé ou restreint apparaît comme partiellement ouvert, jamais comme ouvert. "
     "L'IFCN met la liste à jour quand les conditions changent, pas à jour fixe.</li>"
     "<li><b>Météo :</b> mesures des stations de l'IPMA (sommet du Pico do Areeiro et quatre stations régionales). Ce sont des mesures, pas des prévisions.</li>"
     "<li><b>Tarifs et règles :</b> Portaria 801/2025 modifiée par la Portaria 48/2026, DLR 24/2022/M, la FAQ de l'IFCN et SIMplifica.</li>"
     "<li><b>Caractéristiques des sentiers :</b> la page officielle Visit Madeira de chaque sentier et les panneaux de l'IFCN au départ.</li>"
     "<li><b>Bus :</b> les horaires imprimés des opérateurs (Horários do Funchal et les horaires SIGA), tous les départs.</li>"
     "</ul>", "Chaque page se termine par une courte liste de ses sources."]),
   ("Ce que Levadinho n'est pas", ["Ce n'est ni l'IFCN, ni SIMplifica, ni le Gouvernement régional, et il ne vend pas de billets : la réservation se fait uniquement sur "
     + ext("https://simplifica.madeira.gov.pt/", "SIMplifica") + ". Aucun lien d'affiliation, aucune commission. "
     "Si notre page et une source officielle divergent, c'est la source officielle qui fait foi : dites-le-nous."]),
   ("Données pour applications et assistants IA", ["Les mêmes informations sont publiées sous forme de données, libres d'usage avec un lien vers nous : " + DATA_LINKS + "."]),
   ("Contact", [f"Levadinho est un projet personnel de {OWNER}. Corrections et questions : "
     '<a class="plain" href="mailto:hello@levadinho-madeira.com">hello@levadinho-madeira.com</a>.']),
  ]),
 "de": dict(
  title="Über Levadinho: wer dahintersteht, woher die Daten kommen",
  desc="Wer hinter Levadinho steht und woher Wegestatus, Gebühren, Wetter und Busse auf Madeira kommen. Lesen Sie unsere Quellen, bevor Sie losgehen.",
  h1="Über Levadinho", sub="Ein unabhängiger Ratgeber zu Madeiras offiziellen Wanderwegen: was er ist, woher jede Angabe kommt und was er nicht ist.",
  body=[
   ("Was Levadinho ist", [ENTITY["de"], "Stellen Sie Levadinho Ihre Frage auf WhatsApp, kostenlos, in Ihrer Sprache: " + wa("de", WA_DISPLAY) + "."]),
   ("Woher die Angaben kommen", ["<ul>"
     "<li><b>Wegestatus:</b> " + ext(IFCN, "die offizielle Hinweisliste des IFCN") + ". Ein automatischer Abruf liest sie jeden Morgen. "
     "Gesperrte oder eingeschränkte Wege erscheinen als geschlossen; ein Weg mit gesperrtem oder eingeschränktem Abschnitt erscheint als teilweise geöffnet, nie als geöffnet. "
     "Das IFCN aktualisiert die Liste, wenn sich die Lage ändert, nicht an einem festen Tag.</li>"
     "<li><b>Wetter:</b> Messwerte der IPMA-Stationen (Gipfel des Pico do Areeiro und vier Regionalstationen). Es sind Messungen, keine Vorhersagen.</li>"
     "<li><b>Gebühren und Regeln:</b> Portaria 801/2025 in der Fassung der Portaria 48/2026, DLR 24/2022/M, die FAQ des IFCN und SIMplifica.</li>"
     "<li><b>Wegedaten:</b> die offizielle Visit-Madeira-Seite jedes Weges und die IFCN-Tafeln am Startpunkt.</li>"
     "<li><b>Busse:</b> die gedruckten Fahrpläne der Betreiber (Horários do Funchal und die SIGA-Fahrpläne), jede Fahrt.</li>"
     "</ul>", "Jede Seite endet mit einer kurzen Liste ihrer Quellen."]),
   ("Was Levadinho nicht ist", ["Levadinho ist weder das IFCN noch SIMplifica noch die Regionalregierung und verkauft keine Tickets: gebucht wird nur auf "
     + ext("https://simplifica.madeira.gov.pt/", "SIMplifica") + ". Keine Affiliate-Links, keine Provisionen. "
     "Widersprechen sich unsere Seite und eine offizielle Quelle, gilt die offizielle Quelle: Bitte sagen Sie uns Bescheid."]),
   ("Daten für Apps und KI-Assistenten", ["Dieselben Informationen gibt es als Daten, frei nutzbar mit einem Link zu uns: " + DATA_LINKS + "."]),
   ("Kontakt", [f"Levadinho ist ein privates Projekt von {OWNER}. Korrekturen und Anfragen: "
     '<a class="plain" href="mailto:hello@levadinho-madeira.com">hello@levadinho-madeira.com</a>.']),
  ]),
 "pl": dict(
  title="O Levadinho: kto go prowadzi i skąd są dane",
  desc="Kto prowadzi Levadinho i skąd pochodzą dane o szlakach na Maderze, opłatach, pogodzie i autobusach. Sprawdź nasze źródła i metodę przed wyjściem.",
  h1="O Levadinho", sub="Niezależny przewodnik po oficjalnych szlakach pieszych Madery: czym jest, skąd pochodzi każda informacja i czym nie jest.",
  body=[
   ("Czym jest Levadinho", [ENTITY["pl"], "Zadaj Levadinho pytanie na WhatsAppie, za darmo, w swoim języku: " + wa("pl", WA_DISPLAY) + "."]),
   ("Skąd pochodzą dane", ["<ul>"
     "<li><b>Stan szlaków:</b> " + ext(IFCN, "oficjalna lista komunikatów IFCN") + ". Automatyczny program odczytuje ją każdego ranka. "
     "Szlaki zamknięte lub z ograniczeniami pokazujemy jako zamknięte; szlak z zamkniętym lub ograniczonym odcinkiem pokazujemy jako częściowo otwarty, nigdy jako otwarty. "
     "IFCN aktualizuje listę, gdy zmieniają się warunki, a nie w stały dzień.</li>"
     "<li><b>Pogoda:</b> pomiary ze stacji IPMA (szczyt Pico do Areeiro i cztery stacje regionalne). To pomiary, nie prognozy.</li>"
     "<li><b>Opłaty i zasady:</b> Portaria 801/2025 zmieniona przez Portarię 48/2026, DLR 24/2022/M, FAQ IFCN i SIMplifica.</li>"
     "<li><b>Dane szlaków:</b> oficjalna strona każdego szlaku w Visit Madeira i tablice IFCN na początku szlaku.</li>"
     "<li><b>Autobusy:</b> drukowane rozkłady przewoźników (Horários do Funchal i rozkłady SIGA), każdy kurs.</li>"
     "</ul>", "Każda strona kończy się krótką listą źródeł."]),
   ("Czym Levadinho nie jest", ["To nie jest IFCN, SIMplifica ani Rząd Regionalny i nie sprzedajemy biletów: rezerwacja jest tylko w "
     + ext("https://simplifica.madeira.gov.pt/", "SIMplifica") + ". Bez linków afiliacyjnych i bez prowizji. "
     "Jeśli nasza strona i oficjalne źródło się różnią, rację ma oficjalne źródło: daj nam znać."]),
   ("Dane dla aplikacji i asystentów AI", ["Te same informacje publikujemy jako dane, do swobodnego użytku z linkiem do nas: " + DATA_LINKS + "."]),
   ("Kontakt", [f"Levadinho to prywatny projekt {OWNER}. Poprawki i pytania: "
     '<a class="plain" href="mailto:hello@levadinho-madeira.com">hello@levadinho-madeira.com</a>.']),
  ]),
}

BOARD = "<p class=\"static-status\"><!-- STATIC-STATUS-BOARD:START --><!-- STATIC-STATUS-BOARD:END --></p>"
TABLE = "<!-- STATIC-CLOSURES:START --><!-- STATIC-CLOSURES:END -->"
FEEDS = f'{a("/trail-status.xml", "RSS")} · {a("/history/status-daily.jsonl", "JSON Lines")} · {a("/status.json", "status.json")}'
CLOSURES = {
 "en": dict(
  title="Madeira trail closures today: which PR trails are closed",
  desc="Which Madeira PR trails are closed or partly open today, from IFCN's official trail-warnings list, with each closure note. Check before you book.",
  h1="Madeira trail closures: which trails are closed today?", sub="Every official PR trail that is closed or only partly open on IFCN's trail-warnings list, with IFCN's own note.",
  body=[
   (None, [BOARD]),
   ("Closed and partly open trails", [TABLE, "Every other classified trail is open on IFCN's list. The " + a("/", "live board") + " shows all of them."]),
   ("What closed and partly open mean", ["<ul>"
     "<li><b>Closed:</b> IFCN lists the trail as closed or restricted. Don't walk it: entering a closed trail is an administrative offence, with fines of €250–€2,500 for individuals.</li>"
     "<li><b>Partly open:</b> a section is closed or restricted. IFCN's note says which part you can walk.</li>"
     "<li><b>Already booked?</b> When IFCN or the authorities close or restrict a trail, the fee can be refunded or the booking moved: see " + a("/hiking-fees.html", "the fees page") + ".</li>"
     "</ul>"]),
   ("Follow the changes", ["Each change on IFCN's list, with its date: " + FEEDS + "."]),
   ("Sources", ['<p class="src">' + ext(IFCN, "IFCN trail warnings") + " · Portaria 801/2025 (art. 10) · DLR 24/2022/M (art. 13)</p>"]),
  ]),
 "pt": dict(
  title="Percursos encerrados na Madeira hoje: lista oficial",
  desc="Que percursos pedestres da Madeira estão encerrados ou parcialmente abertos hoje, segundo a lista oficial de avisos do IFCN. Confirme antes de reservar.",
  h1="Percursos encerrados na Madeira: quais estão fechados hoje?", sub="Todos os percursos PR oficiais encerrados ou só parcialmente abertos na lista de avisos do IFCN, com a nota do próprio IFCN.",
  body=[
   (None, [BOARD]),
   ("Percursos encerrados e parcialmente abertos", [TABLE, "Todos os outros percursos classificados estão abertos na lista do IFCN. O " + a("/pt/", "quadro em direto") + " mostra-os todos."]),
   ("O que significa encerrado e parcialmente aberto", ["<ul>"
     "<li><b>Encerrado:</b> o IFCN lista o percurso como encerrado ou condicionado. Não o percorra: entrar num percurso encerrado é contraordenação, com coimas de 250 € a 2500 € para pessoas singulares.</li>"
     "<li><b>Parcialmente aberto:</b> um troço está encerrado ou condicionado. A nota do IFCN diz que parte pode percorrer.</li>"
     "<li><b>Já reservou?</b> Quando o IFCN ou as autoridades encerram ou condicionam um percurso, a taxa pode ser devolvida ou a reserva alterada: veja " + a("/pt/hiking-fees.html", "a página das taxas") + ".</li>"
     "</ul>"]),
   ("Acompanhar as mudanças", ["Cada mudança na lista do IFCN, com a data: " + FEEDS + "."]),
   ("Fontes", ['<p class="src">' + ext(IFCN, "Avisos do IFCN") + " · Portaria 801/2025 (art. 10.º) · DLR 24/2022/M (art. 13.º)</p>"]),
  ]),
 "fr": dict(
  title="Sentiers fermés à Madère aujourd'hui : liste officielle",
  desc="Quels sentiers PR de Madère sont fermés ou partiellement ouverts aujourd'hui, d'après la liste officielle des avis de l'IFCN. Vérifiez avant de réserver.",
  h1="Sentiers fermés à Madère : lesquels sont fermés aujourd'hui ?", sub="Tous les sentiers PR officiels fermés ou seulement partiellement ouverts sur la liste des avis de l'IFCN, avec la note de l'IFCN.",
  body=[
   (None, [BOARD]),
   ("Sentiers fermés et partiellement ouverts", [TABLE, "Tous les autres sentiers classés sont ouverts sur la liste de l'IFCN. Le " + a("/fr/", "tableau en direct") + " les montre tous."]),
   ("Fermé, partiellement ouvert : ce que cela veut dire", ["<ul>"
     "<li><b>Fermé :</b> l'IFCN indique le sentier comme fermé ou soumis à restriction. Ne l'empruntez pas : entrer sur un sentier fermé est une infraction administrative, avec des amendes de 250 € à 2 500 € pour les particuliers.</li>"
     "<li><b>Partiellement ouvert :</b> un tronçon est fermé ou restreint. La note de l'IFCN précise quelle partie reste praticable.</li>"
     "<li><b>Déjà réservé ?</b> Quand l'IFCN ou les autorités ferment ou restreignent un sentier, la taxe peut être remboursée ou la réservation déplacée : voir " + a("/fr/hiking-fees.html", "la page des tarifs") + ".</li>"
     "</ul>"]),
   ("Suivre les changements", ["Chaque changement sur la liste de l'IFCN, avec sa date : " + FEEDS + "."]),
   ("Sources", ['<p class="src">' + ext(IFCN, "Avis de l'IFCN") + " · Portaria 801/2025 (art. 10) · DLR 24/2022/M (art. 13)</p>"]),
  ]),
 "de": dict(
  title="Gesperrte Wanderwege auf Madeira aktuell: offizielle Liste",
  desc="Welche PR-Wanderwege auf Madeira heute gesperrt oder teilweise geöffnet sind, laut offizieller Hinweisliste des IFCN. Prüfen Sie es vor der Buchung.",
  h1="Gesperrte Wanderwege auf Madeira: welche sind heute zu?", sub="Alle offiziellen PR-Wege, die auf der Hinweisliste des IFCN gesperrt oder nur teilweise geöffnet sind, mit dem Hinweis des IFCN.",
  body=[
   (None, [BOARD]),
   ("Gesperrte und teilweise geöffnete Wege", [TABLE, "Alle anderen klassifizierten Wege sind auf der IFCN-Liste geöffnet. Die " + a("/de/", "Live-Übersicht") + " zeigt alle."]),
   ("Was gesperrt und teilweise geöffnet bedeutet", ["<ul>"
     "<li><b>Gesperrt:</b> Das IFCN führt den Weg als gesperrt oder eingeschränkt. Gehen Sie ihn nicht: Das Betreten eines gesperrten Weges ist eine Ordnungswidrigkeit, mit Bußgeldern von 250 € bis 2.500 € für Privatpersonen.</li>"
     "<li><b>Teilweise geöffnet:</b> Ein Abschnitt ist gesperrt oder eingeschränkt. Der Hinweis des IFCN sagt, welcher Teil begehbar ist.</li>"
     "<li><b>Schon gebucht?</b> Wenn das IFCN oder die Behörden einen Weg sperren oder einschränken, kann die Gebühr erstattet oder die Buchung verschoben werden: siehe " + a("/de/hiking-fees.html", "die Gebührenseite") + ".</li>"
     "</ul>"]),
   ("Änderungen verfolgen", ["Jede Änderung auf der IFCN-Liste, mit Datum: " + FEEDS + "."]),
   ("Quellen", ['<p class="src">' + ext(IFCN, "IFCN-Hinweise") + " · Portaria 801/2025 (Art. 10) · DLR 24/2022/M (Art. 13)</p>"]),
  ]),
 "pl": dict(
  title="Zamknięte szlaki na Maderze dziś: oficjalna lista",
  desc="Które szlaki PR na Maderze są dziś zamknięte lub częściowo otwarte, według oficjalnej listy komunikatów IFCN, z notą IFCN. Sprawdź przed rezerwacją.",
  h1="Zamknięte szlaki na Maderze: które są dziś zamknięte?", sub="Wszystkie oficjalne szlaki PR zamknięte lub tylko częściowo otwarte na liście komunikatów IFCN, z notą samego IFCN.",
  body=[
   (None, [BOARD]),
   ("Szlaki zamknięte i częściowo otwarte", [TABLE, "Wszystkie pozostałe szlaki klasyfikowane są otwarte na liście IFCN. " + a("/pl/", "Tablica na żywo") + " pokazuje je wszystkie."]),
   ("Co znaczy zamknięty i częściowo otwarty", ["<ul>"
     "<li><b>Zamknięty:</b> IFCN podaje szlak jako zamknięty lub z ograniczeniami. Nie wchodź na niego: wejście na zamknięty szlak to wykroczenie administracyjne, z karami od 250 € do 2500 € dla osób fizycznych.</li>"
     "<li><b>Częściowo otwarty:</b> odcinek jest zamknięty lub ograniczony. Nota IFCN mówi, którą część można przejść.</li>"
     "<li><b>Masz już rezerwację?</b> Gdy IFCN lub władze zamkną albo ograniczą szlak, opłatę można odzyskać lub przenieść rezerwację: zobacz " + a("/pl/hiking-fees.html", "stronę opłat") + ".</li>"
     "</ul>"]),
   ("Śledź zmiany", ["Każda zmiana na liście IFCN, z datą: " + FEEDS + "."]),
   ("Źródła", ['<p class="src">' + ext(IFCN, "Komunikaty IFCN") + " · Portaria 801/2025 (art. 10) · DLR 24/2022/M (art. 13)</p>"]),
  ]),
}
PAGES = {"about": (ABOUT, "AboutPage"), "trail-closures": (CLOSURES, "WebPage")}


def body_html(sections):
    out = []
    for h2, parts in sections:
        inner = "\n".join(p if p.startswith("<") else f"  <p>{p}</p>" for p in parts)
        out.append("<section>\n" + (f"  <h2>{h2}</h2>\n" if h2 else "") + inner + "\n</section>")
    return "\n\n".join(out)


def build(slug, lang, c, ptype):
    src = os.path.join(ROOT, PREFIX[lang].lstrip("/"), "free-walks", "index.html")
    h = open(src, encoding="utf-8").read()
    url = f"{BASE}{PREFIX[lang]}/{slug}/"
    t, d = html.escape(c["title"], quote=True), html.escape(c["desc"], quote=True)
    h = h.replace("/free-walks/", f"/{slug}/")
    h = re.sub(r"<title>.*?</title>", f"<title>{t}</title>", h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{d}">', h, count=1)
    h = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{t}">', h, count=1)
    h = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{d}">', h, count=1)
    h = re.sub(r'<meta property="og:type" content="[^"]*">', '<meta property="og:type" content="website">', h, count=1)
    h = re.sub(r'\n?<!-- Facts:.*?-->', "", h, count=1, flags=re.S)
    h = re.sub(r'  lastUpdated: "[^"]*"', '  lastUpdated: ""', h, count=1)
    # head JSON-LD: one WebPage/AboutPage block; no FAQ (these pages have no question list)
    ld = {"@context": "https://schema.org", "@type": ptype, "url": url, "name": c["title"], "description": c["desc"],
          "inLanguage": lang, "dateModified": "2026-10-07T12:00+01:00",
          "isPartOf": {"@id": BASE + "/#website"}, "publisher": {"@id": BASE + "/#owner"}}
    blocks = list(re.finditer(r'<script type="application/ld\+json">.*?</script>\n?', h, re.S))
    head_end = h.index("</head>")
    head_blocks = [m for m in blocks if m.start() < head_end and '"BreadcrumbList"' not in m.group(0)]
    new_ld = '<script type="application/ld+json">\n' + json.dumps(ld, ensure_ascii=False, indent=1) + "\n</script>\n"
    for i, m in enumerate(reversed(head_blocks)):
        h = h[:m.start()] + (new_ld if i == len(head_blocks) - 1 else "") + h[m.end():]
    h = re.sub(r"<h1>.*?</h1>", f"<h1>{html.escape(c['h1'], quote=False)}</h1>", h, count=1, flags=re.S)
    h = re.sub(r'<p class="sub">.*?</p>', f'<p class="sub">{html.escape(c["sub"], quote=False)}</p>', h, count=1, flags=re.S)
    # main content: everything between the CTA and the "More guides" block
    m1, m2 = h.index("<!-- LEVADINHO-CTA:END -->") + len("<!-- LEVADINHO-CTA:END -->"), h.index("<!-- SITE-NAV-GUIDES:START")
    h = h[:m1] + "\n\n" + body_html(c["body"]) + "\n\n" + h[m2:]
    # drop the live-badge script (no badges here); the analytics script stays
    h = re.sub(r"<script>\n/\* Live status badges:.*?</script>\n", "", h, count=1, flags=re.S)
    out = os.path.join(ROOT, PREFIX[lang].lstrip("/"), slug, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else None
    if old:  # keep what the updater last wrote between the STATIC markers (else they stay empty until its next run)
        for key in ("STATIC-STATUS-BOARD", "STATIC-CLOSURES"):
            m = re.search(rf"<!-- {key}:START -->(.*?)<!-- {key}:END -->", old, re.S)
            if m:
                h = h.replace(f"<!-- {key}:START --><!-- {key}:END -->", f"<!-- {key}:START -->{m.group(1)}<!-- {key}:END -->")
        h = re.sub(r'("dateModified":\s*")[^"]*', lambda mm: mm.group(1) + (re.search(r'"dateModified":\s*"([^"]*)', old) or [None, ""])[1], h, count=1)
    if old != h:
        open(out, "w", encoding="utf-8").write(h)
    return out, len(c["title"]), len(c["desc"])


def main():
    for slug, (copy, ptype) in PAGES.items():
        for lang in LANGS:
            out, lt, ld = build(slug, lang, copy[lang], ptype)
            flag = "" if lt <= 60 and 120 <= ld <= 155 else "  <-- title/description length"
            print(f"{os.path.relpath(out, ROOT)}: title {lt}, description {ld}{flag}")
    # the shell carries free-walks' nav, CTA and schema: regenerate them for these pages (idempotent elsewhere)
    import subprocess
    for script in ("gen_site_nav.py", "gen_cta.py", "gen_owner.py", "gen_schema.py"):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)], check=True, cwd=ROOT,
                       stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
