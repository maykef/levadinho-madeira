#!/usr/bin/env python3
"""Build /trail_extras.json: tunnels / torch / exposure (vertigo) per PR trail.

Source of truth: seo_research/facts/tunnels_exposure.json (agent B, 2026-09-30),
which reads IFCN's official trailhead panels ("Atenção / Caution" box) plus
Visit Madeira and named guides. This script only reshapes those sourced values
and adds short localised notes. null stays null: no data is never "no tunnel".

Also exposes helpers used by the spoke pages:
  facts_block(code, lang, extras) -> HTML for the "Tunnels / headlamp" and
                                     "Exposure / vertigo" rows (or "" if no data)
and a --patch-hand mode that writes that block into the hand-authored spokes
between <!-- TRAIL-EXTRAS:START --> / <!-- TRAIL-EXTRAS:END --> markers.

Run from the repo root:
  python scripts/gen_trail_extras.py               # writes trail_extras.json
  python scripts/gen_trail_extras.py --patch-hand  # + refreshes hand-authored spokes
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = os.path.join(ROOT, "seo_research", "facts", "tunnels_exposure.json")
OUT = os.path.join(ROOT, "trail_extras.json")
IFCN_LIST = ("https://ifcn.madeira.gov.pt/en/atividades-de-natureza/percursos-pedestres-recomendados/"
             "percursos-pedestres-recomendados.html")
LANGS = ("en", "pt", "fr", "de", "pl")

# Only sourced counts (Visit Madeira PR9: "you will pass through four tunnels").
TUNNEL_COUNT = {"PR9": 4}

# Where the row's data comes from when it is not a 2026 IFCN trailhead panel.
SOURCE_KIND = {"PR1": "leaflet", "PR6.2": "guides", "PR9.1": "visitmadeira"}

# Short localised notes, one sentence or two, drawn only from the facts file.
NOTES = {
    "PR1": {
        "en": "Tunnels on the west variant; narrow ridge and steep rock stairs — not for vertigo sufferers.",
        "pt": "Túneis na variante oeste; crista estreita e escadas íngremes na rocha — não é para quem sofre de vertigens.",
        "fr": "Tunnels sur la variante ouest ; crête étroite et escaliers raides taillés dans la roche — déconseillé en cas de vertige.",
        "de": "Tunnel auf der Westvariante; schmaler Grat und steile Felstreppen — nichts für Menschen mit Höhenangst.",
        "pl": "Tunele na wariancie zachodnim; wąska grań i strome skalne schody — nie dla osób z lękiem wysokości.",
    },
    "PR6": {
        "en": "IFCN panel: PR6 can cause vertigo; don't lean on the barriers. No tunnel on the standard route (the ~800 m tunnel is PR6.6).",
        "pt": "Painel do IFCN: o PR6 pode causar vertigens; não se apoie nas proteções. Sem túnel no percurso normal (o túnel de ~800 m é o PR6.6).",
        "fr": "Panneau IFCN : le PR6 peut donner le vertige ; ne vous appuyez pas sur les barrières. Pas de tunnel sur l'itinéraire standard (le tunnel de ~800 m, c'est le PR6.6).",
        "de": "IFCN-Tafel: Der PR6 kann Schwindel auslösen; nicht auf die Geländer stützen. Kein Tunnel auf der Standardroute (der ~800-m-Tunnel gehört zum PR6.6).",
        "pl": "Tablica IFCN: PR6 może wywołać zawroty głowy; nie opieraj się o barierki. Na standardowej trasie nie ma tunelu (tunel ~800 m to PR6.6).",
    },
    "PR6.2": {
        "en": "Guides rate it low-exposure. Its 'heather tunnels' are plant arches, not rock tunnels.",
        "pt": "Os guias consideram-no pouco exposto. Os «túneis de urze» são arcos de vegetação, não túneis na rocha.",
        "fr": "Les guides le jugent peu exposé. Ses « tunnels de bruyère » sont des arches végétales, pas des tunnels rocheux.",
        "de": "Führer stufen ihn als wenig ausgesetzt ein. Die „Heidetunnel“ sind Pflanzenbögen, keine Felstunnel.",
        "pl": "Przewodniki oceniają ekspozycję jako niską. „Tunele z wrzośca” to roślinne łuki, nie skalne tunele.",
    },
    "PR6.4": {
        "en": "IFCN panel: tunnels on the way, carry a flashlight (Túnel das Estrebarias is on a side branch).",
        "pt": "Painel do IFCN: túneis pelo caminho, leve lanterna (o Túnel das Estrebarias fica num ramal).",
        "fr": "Panneau IFCN : tunnels sur le parcours, prenez une lampe (le Túnel das Estrebarias est sur un embranchement).",
        "de": "IFCN-Tafel: Tunnel unterwegs, Lampe mitnehmen (der Túnel das Estrebarias liegt an einem Abzweig).",
        "pl": "Tablica IFCN: tunele po drodze, weź latarkę (Túnel das Estrebarias leży na odgałęzieniu).",
    },
    "PR6.6": {
        "en": "Túnel do Cavalo, about 800 m long (Visit Madeira). IFCN panel: carry a flashlight.",
        "pt": "Túnel do Cavalo, com cerca de 800 m (Visit Madeira). Painel do IFCN: leve lanterna.",
        "fr": "Túnel do Cavalo, environ 800 m (Visit Madeira). Panneau IFCN : prenez une lampe.",
        "de": "Túnel do Cavalo, rund 800 m lang (Visit Madeira). IFCN-Tafel: Lampe mitnehmen.",
        "pl": "Túnel do Cavalo, ok. 800 m (Visit Madeira). Tablica IFCN: weź latarkę.",
    },
    "PR6.8": {
        "en": "Built for accessibility ('Um caminho para todos'), about 1.2 km each way.",
        "pt": "Preparado para acessibilidade («Um caminho para todos»), cerca de 1,2 km por sentido.",
        "fr": "Aménagé pour l'accessibilité (« Um caminho para todos »), environ 1,2 km à l'aller.",
        "de": "Barrierearm angelegt („Um caminho para todos“), rund 1,2 km pro Richtung.",
        "pl": "Przystosowany dla osób z niepełnosprawnościami („Um caminho para todos”), ok. 1,2 km w jedną stronę.",
    },
    "PR8": {
        "en": "IFCN panel: keep away from the cliff edge; the ground is unstable in many places.",
        "pt": "Painel do IFCN: não se aproxime da arriba; o terreno é instável em muitos pontos.",
        "fr": "Panneau IFCN : ne vous approchez pas du bord de la falaise ; le sol est instable par endroits.",
        "de": "IFCN-Tafel: Abstand zur Klippenkante halten; der Boden ist vielerorts instabil.",
        "pl": "Tablica IFCN: nie podchodź do krawędzi klifu; grunt w wielu miejscach jest niestabilny.",
    },
    "PR9": {
        "en": "Four rock tunnels (Visit Madeira). IFCN panel: carry a torch; danger of vertigo.",
        "pt": "Quatro túneis na rocha (Visit Madeira). Painel do IFCN: leve lanterna; perigo de vertigens.",
        "fr": "Quatre tunnels dans la roche (Visit Madeira). Panneau IFCN : prenez une lampe ; risque de vertige.",
        "de": "Vier Felstunnel (Visit Madeira). IFCN-Tafel: Lampe mitnehmen; Schwindelgefahr.",
        "pl": "Cztery skalne tunele (Visit Madeira). Tablica IFCN: weź latarkę; ryzyko zawrotów głowy.",
    },
    "PR9.1": {
        "en": "Built for accessibility ('Um caminho para todos'), about 2 km.",
        "pt": "Preparado para acessibilidade («Um caminho para todos»), cerca de 2 km.",
        "fr": "Aménagé pour l'accessibilité (« Um caminho para todos »), environ 2 km.",
        "de": "Barrierearm angelegt („Um caminho para todos“), rund 2 km.",
        "pl": "Przystosowany dla osób z niepełnosprawnościami („Um caminho para todos”), ok. 2 km.",
    },
    "PR10": {
        "en": "IFCN panel: danger of vertigo, and tunnels — carry a torch. Some guides rate the exposure low.",
        "pt": "Painel do IFCN: perigo de vertigens e túneis — leve lanterna. Alguns guias consideram a exposição baixa.",
        "fr": "Panneau IFCN : risque de vertige et tunnels — prenez une lampe. Certains guides jugent l'exposition faible.",
        "de": "IFCN-Tafel: Schwindelgefahr und Tunnel — Lampe mitnehmen. Manche Führer stufen die Ausgesetztheit als gering ein.",
        "pl": "Tablica IFCN: ryzyko zawrotów głowy i tunele — weź latarkę. Niektóre przewodniki oceniają ekspozycję jako niską.",
    },
    "PR11": {
        "en": "Wide, easy path; no vertigo warning on the IFCN panel. The Balcões viewpoint has big (fenced) drops.",
        "pt": "Caminho largo e fácil; sem aviso de vertigens no painel do IFCN. O miradouro dos Balcões tem grandes desníveis (vedados).",
        "fr": "Chemin large et facile ; pas d'avertissement de vertige sur le panneau IFCN. Le belvédère des Balcões surplombe de grands à-pics (clôturés).",
        "de": "Breiter, leichter Weg; keine Schwindelwarnung auf der IFCN-Tafel. Am Aussichtspunkt Balcões geht es tief hinab (gesichert).",
        "pl": "Szeroka, łatwa ścieżka; brak ostrzeżenia o zawrotach głowy na tablicy IFCN. Przy punkcie widokowym Balcões są duże (ogrodzone) urwiska.",
    },
    "PR13": {
        "en": "No vertigo warning on the IFCN panel; the risk here is fog — stay on the trail.",
        "pt": "Sem aviso de vertigens no painel do IFCN; aqui o risco é o nevoeiro — não saia do trilho.",
        "fr": "Pas d'avertissement de vertige sur le panneau IFCN ; le risque ici, c'est le brouillard — restez sur le sentier.",
        "de": "Keine Schwindelwarnung auf der IFCN-Tafel; das Risiko hier ist Nebel — bleiben Sie auf dem Weg.",
        "pl": "Brak ostrzeżenia o zawrotach głowy na tablicy IFCN; tu ryzykiem jest mgła — nie schodź ze szlaku.",
    },
    "PR14": {
        "en": "The IFCN panel warns of vertigo, although guides call it an easy walk.",
        "pt": "O painel do IFCN alerta para vertigens, embora os guias o considerem um passeio fácil.",
        "fr": "Le panneau IFCN avertit d'un risque de vertige, même si les guides la jugent facile.",
        "de": "Die IFCN-Tafel warnt vor Schwindelgefahr, obwohl Führer sie als leichte Wanderung einstufen.",
        "pl": "Tablica IFCN ostrzega przed zawrotami głowy, choć przewodniki uznają trasę za łatwą.",
    },
    "PR16": {
        "en": "IFCN panel: danger of vertigo; tunnels — carry a torch. The last tunnel is about 1 km long (20–25 min).",
        "pt": "Painel do IFCN: perigo de vertigens; túneis — leve lanterna. O último túnel tem cerca de 1 km (20–25 min).",
        "fr": "Panneau IFCN : risque de vertige ; tunnels — prenez une lampe. Le dernier tunnel fait environ 1 km (20–25 min).",
        "de": "IFCN-Tafel: Schwindelgefahr; Tunnel — Lampe mitnehmen. Der letzte Tunnel ist rund 1 km lang (20–25 Min.).",
        "pl": "Tablica IFCN: ryzyko zawrotów głowy; tunele — weź latarkę. Ostatni tunel ma ok. 1 km (20–25 min).",
    },
    "PR17": {
        "en": "IFCN panel: tunnels, carry a torch. Guides say it is not for vertigo sufferers.",
        "pt": "Painel do IFCN: túneis, leve lanterna. Os guias dizem que não é para quem sofre de vertigens.",
        "fr": "Panneau IFCN : tunnels, prenez une lampe. Selon les guides, déconseillé en cas de vertige.",
        "de": "IFCN-Tafel: Tunnel, Lampe mitnehmen. Laut Führern nichts für Menschen mit Höhenangst.",
        "pl": "Tablica IFCN: tunele, weź latarkę. Według przewodników nie dla osób z lękiem wysokości.",
    },
    "PR18": {
        "en": "Mostly wide and gentle, but the IFCN panel warns of vertigo. The short tunnel needs no torch (guides).",
        "pt": "Sobretudo largo e suave, mas o painel do IFCN alerta para vertigens. O túnel curto dispensa lanterna (guias).",
        "fr": "Surtout large et doux, mais le panneau IFCN avertit d'un risque de vertige. Le court tunnel ne demande pas de lampe (guides).",
        "de": "Meist breit und sanft, doch die IFCN-Tafel warnt vor Schwindelgefahr. Der kurze Tunnel braucht keine Lampe (Führer).",
        "pl": "Przeważnie szeroko i łagodnie, ale tablica IFCN ostrzega przed zawrotami głowy. Krótki tunel nie wymaga latarki (przewodniki).",
    },
    "PR19": {
        "en": "IFCN panel: danger of vertigo.",
        "pt": "Painel do IFCN: perigo de vertigens.",
        "fr": "Panneau IFCN : risque de vertige.",
        "de": "IFCN-Tafel: Schwindelgefahr.",
        "pl": "Tablica IFCN: ryzyko zawrotów głowy.",
    },
    "PR28": {
        "en": "IFCN panel: tunnels (carry a flashlight) and technical sections. The ~1.7 km tunnel is on the Calheta access route, not on PR28.",
        "pt": "Painel do IFCN: túneis (leve lanterna) e troços técnicos. O túnel de ~1,7 km fica no acesso pela Calheta, não no PR28.",
        "fr": "Panneau IFCN : tunnels (prenez une lampe) et passages techniques. Le tunnel de ~1,7 km se trouve sur l'accès depuis Calheta, pas sur le PR28.",
        "de": "IFCN-Tafel: Tunnel (Lampe mitnehmen) und technische Abschnitte. Der ~1,7-km-Tunnel liegt am Zugang von Calheta, nicht am PR28.",
        "pl": "Tablica IFCN: tunele (weź latarkę) i odcinki techniczne. Tunel ~1,7 km leży na dojściu od Calheta, nie na PR28.",
    },
}

# ---- page strings ------------------------------------------------------------
L_TUN = {"en": "Tunnels / headlamp", "pt": "Túneis / lanterna", "fr": "Tunnels / frontale",
         "de": "Tunnel / Stirnlampe", "pl": "Tunele / czołówka"}
L_EXP = {"en": "Exposure / vertigo", "pt": "Exposição / vertigens", "fr": "Exposition / vertige",
         "de": "Ausgesetztheit / Schwindel", "pl": "Ekspozycja / lęk wysokości"}
V_TORCH = {  # tunnels true + torch value
    "yes": {"en": "Yes · bring a torch", "pt": "Sim · leve lanterna", "fr": "Oui · prenez une lampe",
            "de": "Ja · Lampe mitnehmen", "pl": "Tak · weź latarkę"},
    "recommended": {"en": "Yes · torch advised", "pt": "Sim · lanterna aconselhada", "fr": "Oui · lampe conseillée",
                    "de": "Ja · Lampe empfohlen", "pl": "Tak · latarka zalecana"},
    "no": {"en": "Short tunnel · no torch needed", "pt": "Túnel curto · sem lanterna", "fr": "Tunnel court · lampe inutile",
           "de": "Kurzer Tunnel · keine Lampe nötig", "pl": "Krótki tunel · latarka zbędna"},
    None: {"en": "Yes", "pt": "Sim", "fr": "Oui", "de": "Ja", "pl": "Tak"},
}
V_COUNT_TORCH = {"en": "{n} · bring a torch", "pt": "{n} · leve lanterna", "fr": "{n} · prenez une lampe",
                 "de": "{n} · Lampe mitnehmen", "pl": "{n} · weź latarkę"}
V_EXP = {
    "low": {"en": "Low", "pt": "Baixa", "fr": "Faible", "de": "Gering", "pl": "Niska"},
    "moderate": {"en": "Moderate", "pt": "Moderada", "fr": "Modérée", "de": "Mittel", "pl": "Umiarkowana"},
    "high": {"en": "High", "pt": "Alta", "fr": "Élevée", "de": "Hoch", "pl": "Wysoka"},
}
SRC_WORD = {"en": "Source", "pt": "Fonte", "fr": "Source", "de": "Quelle", "pl": "Źródło"}
SRC_LABEL = {
    "panel": {"en": "IFCN trailhead panel", "pt": "painel do IFCN no início do percurso",
              "fr": "panneau IFCN au départ du sentier", "de": "IFCN-Infotafel am Wegbeginn",
              "pl": "tablica IFCN na początku szlaku"},
    "leaflet": {"en": "IFCN PR1 leaflet", "pt": "folheto do PR1 do IFCN", "fr": "dépliant PR1 de l'IFCN",
                "de": "IFCN-Faltblatt zum PR1", "pl": "ulotka IFCN o PR1"},
    "guides": {"en": "hiking guides (no IFCN panel online)", "pt": "guias de caminhada (sem painel do IFCN online)",
               "fr": "guides de randonnée (pas de panneau IFCN en ligne)",
               "de": "Wanderführer (keine IFCN-Tafel online)", "pl": "przewodniki turystyczne (brak tablicy IFCN online)"},
    "visitmadeira": {"en": "Visit Madeira", "pt": "Visit Madeira", "fr": "Visit Madeira", "de": "Visit Madeira",
                     "pl": "Visit Madeira"},
}
LIST_LABEL = {"en": "IFCN trail list", "pt": "lista de percursos do IFCN", "fr": "liste des sentiers IFCN",
              "de": "IFCN-Wegeliste", "pl": "lista szlaków IFCN"}


def _panel_url(sources):
    for s in sources:
        if re.search(r"/paineis(_net)?/", s, re.I) and "Mapa_" not in s:
            return s
    return None


def build():
    src = json.load(open(FACTS, encoding="utf-8"))
    out = {"_meta": {
        "generated_by": "scripts/gen_trail_extras.py",
        "from": "seo_research/facts/tunnels_exposure.json",
        "facts_generated": src.get("_meta", {}).get("generated"),
        "primary_source": "IFCN trailhead information panels ('Atenção / Caution' box), linked from " + IFCN_LIST,
        "schema": ("tunnels: true or null (never false: no mention is not proof of no tunnel); "
                   "torch: yes|no|recommended|null; exposure: low|moderate|high|null; "
                   "ifcn_warning: vertigo/cliff/torch flags + EN text of the IFCN panel's caution box (null if no panel); "
                   "source: where the tunnel/exposure values come from; notes: short localised note or null."),
    }}
    for code, r in src.items():
        if code.startswith("_"):
            continue
        warn = r.get("official_warning")
        panel = _panel_url(r.get("sources", []))
        kind = SOURCE_KIND.get(code, "panel" if panel else None)
        if kind == "leaflet":
            url = next((s for s in r["sources"] if s.endswith("PR1.pdf")), IFCN_LIST)
        elif kind == "panel":
            url = panel
        elif kind == "guides":
            url = next((s for s in r["sources"] if "visitmadeira" not in s), r["sources"][0])
        elif r.get("sources"):
            url = r["sources"][0]
        else:
            url = None
        has = any(r.get(k) is not None for k in ("tunnels", "torch", "exposure"))
        if has and code not in NOTES:
            sys.exit(f"{code} has tunnel/exposure data but no localised note")
        wl = (warn or "").lower()
        out[code] = {
            "tunnels": True if r.get("tunnels") else None,
            "torch": r.get("torch"),
            "exposure": r.get("exposure"),
            "tunnel_count": TUNNEL_COUNT.get(code),
            "ifcn_warning": ({
                "vertigo": "vertigo" in wl,
                "cliff": "cliff" in wl,
                "torch": ("torch" in wl) or ("flashlight" in wl),
                "text_en": warn,
                "panel": panel if kind != "leaflet" else url,
            } if warn else None),
            "source": {"kind": kind, "url": url} if has else None,
            "notes": NOTES.get(code) if has else None,
        }
    return out


def load(path=OUT):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def facts_rows(code, lang, extras):
    """(label, value) rows for the facts box; omits a row whose value is null."""
    x = extras.get(code) or {}
    rows = []
    if x.get("tunnels"):
        if x.get("tunnel_count") and x.get("torch") == "yes":
            v = V_COUNT_TORCH[lang].format(n=x["tunnel_count"])
        else:
            v = V_TORCH.get(x.get("torch"), V_TORCH[None])[lang]
        rows.append((L_TUN[lang], v))
    if x.get("exposure") in V_EXP:
        rows.append((L_EXP[lang], V_EXP[x["exposure"]][lang]))
    return rows


def facts_block(code, lang, extras):
    """HTML placed inside <aside class="facts"> after the main <dl>; "" if no data."""
    rows = facts_rows(code, lang, extras)
    if not rows:
        return ""
    x = extras[code]
    s = x.get("source") or {}
    label = SRC_LABEL.get(s.get("kind"), SRC_LABEL["panel"])[lang]
    link = f'<a href="{s["url"]}" target="_blank" rel="noopener">{label}</a>' if s.get("url") else label
    lst = f'<a href="{IFCN_LIST}" target="_blank" rel="noopener">{LIST_LABEL[lang]}</a>'
    note = (x.get("notes") or {}).get(lang, "")
    sep = " :" if lang == "fr" else ":"
    dd = "".join(f"    <dt>{k}</dt><dd>{v}</dd>\n" for k, v in rows)
    return (f'  <dl style="margin-top:5px">\n{dd}  </dl>\n'
            f'  <p style="font-size:12px;color:var(--ink-soft);margin:8px 0 0;line-height:1.45">'
            f'{note} {SRC_WORD[lang]}{sep} {link} · {lst}.</p>\n')


# ---- hand-authored spokes -----------------------------------------------------
# 25-fontes (PR6) and pr1 belong to other owners; they can opt in by adding the
# marker pair inside their facts <aside> and listing the slug here.
HAND = {"pico-ruivo": "PR1.2", "caldeirao-verde": "PR9", "sao-lourenco": "PR8", "balcoes": "PR11",
        "fanal": "PR13", "levada-do-furado": "PR10", "levada-do-rei": "PR18", "levada-dos-cedros": "PR14"}
M_START, M_END = "<!-- TRAIL-EXTRAS:START (scripts/gen_trail_extras.py) -->", "<!-- TRAIL-EXTRAS:END -->"


def patch_page(path, code, lang, extras):
    t = open(path, encoding="utf-8").read()
    block = f"{M_START}\n{facts_block(code, lang, extras)}  {M_END}"
    if M_START in t:
        t2 = re.sub(re.escape(M_START) + r".*?" + re.escape(M_END), lambda m: block, t, flags=re.S)
    else:
        i = t.find('<aside class="facts">')
        j = t.find("</aside>", i)
        if i < 0 or j < 0:
            print("  no facts box:", path); return False
        t2 = t[:j] + "  " + block + "\n" + t[j:]
    if t2 != t:
        open(path, "w", encoding="utf-8").write(t2)
        return True
    return False


def patch_hand(extras):
    n = 0
    for slug, code in HAND.items():
        for lang in LANGS:
            p = os.path.join(ROOT, slug if lang == "en" else os.path.join(lang, slug), "index.html")
            if os.path.exists(p) and patch_page(p, code, lang, extras):
                n += 1
    print(f"patched {n} hand-authored spoke pages")


def main():
    data = build()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    codes = [k for k in data if not k.startswith("_")]
    tun = sum(1 for k in codes if data[k]["tunnels"])
    exp = sum(1 for k in codes if data[k]["exposure"])
    none = sum(1 for k in codes if not data[k]["tunnels"] and not data[k]["exposure"])
    print(f"wrote trail_extras.json: {len(codes)} trails, tunnels={tun}, exposure={exp}, no data={none}")
    if "--patch-hand" in sys.argv:
        patch_hand(data)


if __name__ == "__main__":
    main()
