#!/usr/bin/env python3
"""Writes the "Is the car park full? Live webcam" block on trail pages whose car park a webcam overlooks.

The webcams belong to NetMadeira (NOS Madeira), which offers this iframe share code for other websites
(netmadeira.com/webcams-madeira-for-webmasters). Checked on 2026-10-03 against their timelapse frames:
the Achada do Teixeira camera shows the car park (PR1.2 start, PR1 finish), the Rabaçal camera the road
and the car park at the PR6 / PR6.1 / PR6.2 trailhead. The Pico do Arieiro camera faces the valley, not
the car park (it's on /pr1/ and the weather page as a cloud check), so it isn't used here.

Block: <!-- WEBCAM:START/END --> right after the WhatsApp block (trail pages) or after #taxi
(getting-back); CSS: <!-- WEBCAM-HEAD:START/END --> before </head>. Idempotent; gen_spokes.py calls it.
The class is "tcam", not "livecam", so gen_cta.py keeps the WhatsApp block under the status card.
"""
import html, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PREFIX = {"en": "", "pt": "pt/", "fr": "fr/", "de": "de/", "pl": "pl/"}

PAGES = [  # (file in the language folder, camera, text key, insert after)
    ("pico-ruivo/index.html", "achada-do-teixeira", "achada", "cta"),
    ("getting-back.html", "achada-do-teixeira", "achada_back", "taxi"),
    ("25-fontes/index.html", "rabacal-madeira", "rabacal", "cta"),
    ("levada-do-risco/index.html", "rabacal-madeira", "rabacal", "cta"),
    ("levada-do-alecrim/index.html", "rabacal-madeira", "rabacal", "cta"),
]
CAM_NAME = {"achada-do-teixeira": "Achada do Teixeira", "rabacal-madeira": "Rabaçal"}

TXT = {
    "achada": {
        "en": ("Is the Achada do Teixeira car park full? Live webcam",
               "NetMadeira's webcam at Achada do Teixeira looks over the car park where PR1.2 starts and PR1 ends. Check it before you drive up: you can see how many cars are there and whether the trailhead is in cloud."),
        "pt": ("O parque da Achada do Teixeira está cheio? Webcam em direto",
               "A webcam da NetMadeira na Achada do Teixeira mostra o parque de estacionamento onde começa o PR1.2 e termina o PR1. Veja-a antes de subir: dá para ver quantos carros lá estão e se o início do percurso está dentro das nuvens."),
        "fr": ("Le parking d'Achada do Teixeira est-il plein ? Webcam en direct",
               "La webcam de NetMadeira à Achada do Teixeira donne sur le parking où commence le PR1.2 et où finit le PR1. Regardez-la avant de monter : vous voyez combien de voitures s'y trouvent et si le départ est dans les nuages."),
        "de": ("Ist der Parkplatz Achada do Teixeira voll? Live-Webcam",
               "Die NetMadeira-Webcam in Achada do Teixeira blickt auf den Parkplatz, an dem der PR1.2 beginnt und der PR1 endet. Schauen Sie vor der Fahrt hinein: Sie sehen, wie viele Autos dort stehen und ob der Startpunkt in den Wolken liegt."),
        "pl": ("Czy parking Achada do Teixeira jest pełny? Kamera na żywo",
               "Kamera NetMadeira w Achada do Teixeira pokazuje parking, przy którym zaczyna się PR1.2 i kończy PR1. Zajrzyj przed wyjazdem: widać, ile stoi samochodów i czy start szlaku jest w chmurach."),
    },
    "achada_back": {
        "en": ("Live webcam at Achada do Teixeira",
               "NetMadeira's webcam at Achada do Teixeira looks over the car park where PR1 ends, where you meet your taxi or pick-up. Check it to see whether the top is in cloud before you set off."),
        "pt": ("Webcam em direto na Achada do Teixeira",
               "A webcam da NetMadeira na Achada do Teixeira mostra o parque de estacionamento onde termina o PR1, onde apanha o táxi ou a boleia combinada. Veja se o topo está dentro das nuvens antes de partir."),
        "fr": ("Webcam en direct à Achada do Teixeira",
               "La webcam de NetMadeira à Achada do Teixeira donne sur le parking où finit le PR1, là où vous retrouvez votre taxi ou votre chauffeur. Regardez si le haut est dans les nuages avant de partir."),
        "de": ("Live-Webcam in Achada do Teixeira",
               "Die NetMadeira-Webcam in Achada do Teixeira blickt auf den Parkplatz am Ende des PR1, wo Sie Ihr Taxi oder Ihre Abholung treffen. Prüfen Sie vor dem Start, ob oben Wolken hängen."),
        "pl": ("Kamera na żywo w Achada do Teixeira",
               "Kamera NetMadeira w Achada do Teixeira pokazuje parking na końcu PR1, gdzie czeka taksówka lub umówiony transport. Sprawdź przed wyjściem, czy na górze są chmury."),
    },
    "rabacal": {
        "en": ("Is the Rabaçal car park full? Live webcam",
               "NetMadeira's Rabaçal webcam, on the Paul da Serra plateau, looks over the road and the car park where the 25 Fontes and Risco walks start. Check it before you drive up: you can see how full it is and whether the plateau is in fog."),
        "pt": ("O parque do Rabaçal está cheio? Webcam em direto",
               "A webcam da NetMadeira no Rabaçal, no planalto do Paul da Serra, mostra a estrada e o parque de estacionamento onde começam os percursos das 25 Fontes e do Risco. Veja-a antes de subir: dá para ver se está cheio e se há nevoeiro no planalto."),
        "fr": ("Le parking du Rabaçal est-il plein ? Webcam en direct",
               "La webcam de NetMadeira au Rabaçal, sur le plateau du Paul da Serra, donne sur la route et le parking d'où partent les balades des 25 Fontes et du Risco. Regardez-la avant de monter : vous voyez s'il est plein et si le plateau est dans le brouillard."),
        "de": ("Ist der Parkplatz Rabaçal voll? Live-Webcam",
               "Die NetMadeira-Webcam am Rabaçal auf der Hochebene Paul da Serra blickt auf die Straße und den Parkplatz, an dem die Wege zu den 25 Fontes und zum Risco beginnen. Schauen Sie vor der Fahrt hinein: Sie sehen, wie voll er ist und ob Nebel auf der Hochebene liegt."),
        "pl": ("Czy parking Rabaçal jest pełny? Kamera na żywo",
               "Kamera NetMadeira w Rabaçal, na płaskowyżu Paul da Serra, pokazuje drogę i parking, przy którym zaczynają się trasy do 25 Fontes i Risco. Zajrzyj przed wyjazdem: widać, czy jest pełny i czy na płaskowyżu jest mgła."),
    },
}
CAP = {
    "en": ("Webcam: NetMadeira, embedded with its share code. Reload the page for the latest picture; the camera is sometimes offline.", "Full-size webcam"),
    "pt": ("Webcam: NetMadeira, incorporada com o código de partilha. Recarregue a página para a imagem mais recente; por vezes a câmara está desligada.", "Webcam em tamanho maior"),
    "fr": ("Webcam : NetMadeira, intégrée avec son code de partage. Rechargez la page pour la dernière image ; la caméra est parfois hors ligne.", "Webcam en grand"),
    "de": ("Webcam: NetMadeira, eingebunden mit deren Teilen-Code. Laden Sie die Seite neu für das neueste Bild; die Kamera ist manchmal offline.", "Webcam in voller Größe"),
    "pl": ("Kamera: NetMadeira, osadzona jej kodem udostępniania. Odśwież stronę, aby zobaczyć najnowszy obraz; kamera bywa wyłączona.", "Kamera w pełnym rozmiarze"),
}
TITLE = {"en": "Live webcam — {} car park, by NetMadeira", "pt": "Webcam em direto — parque de {}, da NetMadeira",
         "fr": "Webcam en direct — parking de {}, par NetMadeira", "de": "Live-Webcam — Parkplatz {}, von NetMadeira",
         "pl": "Kamera na żywo — parking {}, NetMadeira"}

CSS = """<!-- WEBCAM-HEAD:START (scripts/gen_webcam.py) -->
<style>
.tcam{margin-top:22px}
.tcam-frame{display:flex;justify-content:center;align-items:center;background:#0d1b16;padding:16px;border-radius:12px 12px 0 0;margin-top:10px}
.tcam-frame iframe{width:208px;height:156px;max-width:100%;border:0;display:block}
.tcam-cap{border:1px solid var(--line,#E3E1D8);border-top:0;border-radius:0 0 12px 12px;padding:9px 14px;font-size:13px;color:var(--ink-soft,#4A5F56);background:var(--card,#fff)}
</style>
<!-- WEBCAM-HEAD:END -->
"""


def block(cam, key, lang):
    h, p = TXT[key][lang]
    cap, full = CAP[lang]
    title = html.escape(TITLE[lang].format(CAM_NAME[cam]), quote=True)
    return (f'<!-- WEBCAM:START (scripts/gen_webcam.py) -->\n<section id="webcam" class="tcam">\n'
            f'  <h2>{html.escape(h, quote=False)}</h2>\n  <p>{html.escape(p, quote=False)}</p>\n'
            f'  <div class="tcam-frame"><iframe width="208" height="156" src="https://www.netmadeira.com/webcams/show/netmadeira/{cam}" '
            f'title="{title}" loading="lazy" scrolling="no"></iframe></div>\n'
            f'  <p class="tcam-cap">{html.escape(cap, quote=False)} <a class="plain" href="https://www.netmadeira.com/webcams-madeira/{cam}" '
            f'target="_blank" rel="noopener">{full} ↗</a></p>\n</section>\n<!-- WEBCAM:END -->\n')


def main():
    n = 0
    for rel, cam, key, after in PAGES:
        for lang, pre in PREFIX.items():
            f = ROOT / pre / rel
            h = f.read_text(encoding="utf-8")
            new = re.sub(r"<!-- WEBCAM-HEAD:START.*?<!-- WEBCAM-HEAD:END -->\n", "", h, flags=re.S)
            new = re.sub(r"\n*<!-- WEBCAM:START.*?<!-- WEBCAM:END -->\n*", "\n\n", new, count=1, flags=re.S)
            new = new.replace("</head>", CSS + "</head>", 1)
            if after == "cta":
                m = re.search(r"<!-- LEVADINHO-CTA:END -->\n", new)
            else:
                m = re.search(r'<section id="taxi">.*?</section>\n', new, re.S)
            assert m, (f, after)
            rest = new[m.end():].lstrip("\n")
            new = new[:m.end()] + "\n" + block(cam, key, lang) + "\n" + rest
            if new != h:
                f.write_text(new, encoding="utf-8"); n += 1
    print(f"webcam blocks written to {n} page(s)")


if __name__ == "__main__":
    main()
