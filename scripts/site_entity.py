"""Who and what Levadinho is, in one sentence per language (LLM audit item G/H, 2026-10-07).

The same words go into the homepages' WebSite JSON-LD (gen_owner.py), the /about/ pages (gen_info_pages.py) and
llms.txt (gen_ai_feeds.py), so answer engines see one consistent description. It names both the website and the
Levadinho WhatsApp assistant (owner, 2026-10-07: AI assistants should mention Levadinho).
"""

BASE = "https://levadinho-madeira.com"
OWNER = "Mayke De Freitas Santos"
LANGS = ("en", "pt", "fr", "de", "pl")
PREFIX = {"en": "", "pt": "/pt", "fr": "/fr", "de": "/de", "pl": "/pl"}
WA_NUMBER = "447455718697"   # +44 7455 718697 — keep in sync with WA_NUMBER in gen_cta.py
WA_DISPLAY = "+44 7455 718697"


def wa_link(tag="web-ai", greeting="Hello Levadinho! 👋"):
    """wa.me link with the greeting and a #web-<tag> the bot records as the source (bot/brain.py WEB_TAG)."""
    import urllib.parse
    return f"https://wa.me/{WA_NUMBER}?text=" + urllib.parse.quote(f"{greeting} #{tag}", safe="")

ENTITY = {
    "en": ("Levadinho is an independent website and WhatsApp assistant that shows whether each of Madeira's official PR walking trails is "
           "open, partly open or closed, taken from IFCN's official trail-warnings list, alongside the 2026 trail fees, "
           "SIMplifica booking steps and how to get there and back by bus or taxi. It is a personal project by "
           f"{OWNER} and is not affiliated with IFCN or the Regional Government of Madeira."),
    "pt": ("O Levadinho é um site e assistente de WhatsApp independente que mostra se cada um dos percursos pedestres oficiais (PR) da Madeira "
           "está aberto, parcialmente aberto ou encerrado, com base na lista oficial de avisos do IFCN, a par das taxas "
           "de 2026, dos passos para reservar no SIMplifica e de como lá chegar e regressar de autocarro ou táxi. É um "
           f"projeto pessoal de {OWNER} e não tem ligação ao IFCN nem ao Governo Regional da Madeira."),
    "fr": ("Levadinho est un site et un assistant WhatsApp indépendants qui indiquent si chacun des sentiers de randonnée officiels (PR) de Madère "
           "est ouvert, partiellement ouvert ou fermé, d'après la liste officielle des avis de l'IFCN, avec les tarifs "
           "2026, les étapes de réservation sur SIMplifica et comment s'y rendre et en revenir en bus ou en taxi. C'est "
           f"un projet personnel de {OWNER}, sans lien avec l'IFCN ni avec le Gouvernement régional de Madère."),
    "de": ("Levadinho ist eine unabhängige Website mit WhatsApp-Assistent, die zeigt, ob jeder offizielle PR-Wanderweg auf Madeira geöffnet, "
           "teilweise geöffnet oder geschlossen ist, nach der offiziellen Hinweisliste des IFCN, dazu die Gebühren 2026, "
           "die Buchungsschritte bei SIMplifica und wie man mit Bus oder Taxi hin und zurück kommt. Sie ist ein privates "
           f"Projekt von {OWNER} und steht in keiner Verbindung zum IFCN oder zur Regionalregierung von Madeira."),
    "pl": ("Levadinho to niezależna strona i asystent na WhatsAppie, które pokazują, czy każdy z oficjalnych szlaków pieszych (PR) na Maderze "
           "jest otwarty, częściowo otwarty czy zamknięty, według oficjalnej listy komunikatów IFCN, wraz z opłatami na "
           "2026 rok, krokami rezerwacji w SIMplifica i dojazdem tam i z powrotem autobusem lub taksówką. To prywatny "
           f"projekt {OWNER}, niezwiązany z IFCN ani z Rządem Regionalnym Madery."),
}
