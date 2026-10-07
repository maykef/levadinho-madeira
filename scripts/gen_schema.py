#!/usr/bin/env python3
"""Completes the TouristAttraction JSON-LD on every trail page (generated and hand-authored, 5 languages).

Adds, without touching the existing facts:
  - "description": one factual sentence in the page's language, built from the page's own facts
    (name, distance, difficulty as shown in the facts box; never the "open today?" meta description,
    which carries a changing IFCN date on some pages);
  - "address" (PostalAddress: Madeira, PT) and "containedInPlace" (Madeira);
  - "image": the page's og:image when the block has none (hero photo or /img/og-default.jpg).
Keys are re-ordered into one fixed order so the output is stable. Idempotent; gen_spokes.py calls it last.

Entity links (LLM audit item G, 2026-10-07), on every page (not only trail pages):
  - TouristAttraction gets "@id": <page url>#trail;
  - every WebPage gets "isPartOf" -> the site (#website, defined on the homepages by gen_owner.py),
    "publisher" -> the owner (#owner) and, on trail pages, "about" -> the page's #trail.
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LD_RE = re.compile(r'(<script type="application/ld\+json">\n)(.*?)(\n</script>)', re.S)
DIST = {"Distance", "Distância", "Distanz", "Dystans", "Długość", "Länge"}
DIFF = {"Difficulty", "Difficulté", "Dificuldade", "Schwierigkeit", "Trudność"}
SENT = {
    "en": ("{n}, a classified walking trail (PR) in Madeira, Portugal.", " Distance: {d}.", " Difficulty: {x}."),
    "pt": ("{n}, percurso pedestre classificado (PR) na Madeira, Portugal.", " Distância: {d}.", " Dificuldade: {x}."),
    "fr": ("{n}, sentier de randonnée classé (PR) à Madère, Portugal.", " Distance : {d}.", " Difficulté : {x}."),
    "de": ("{n}, ein klassifizierter Wanderweg (PR) auf Madeira, Portugal.", " Länge: {d}.", " Schwierigkeit: {x}."),
    "pl": ("{n}, oficjalny szlak pieszy (PR) na Maderze w Portugalii.", " Długość: {d}.", " Trudność: {x}."),
}
BASE = "https://levadinho-madeira.com"
WEBPAGE_LINKS = {"isPartOf": {"@id": BASE + "/#website"}, "publisher": {"@id": BASE + "/#owner"}}
ANY_LD_RE = re.compile(r'(<script type="application/ld\+json">\s*)(.*?)(\s*</script>)', re.S)
ORDER = ["@context", "@type", "@id", "name", "alternateName", "description", "url", "image", "touristType",
         "isAccessibleForFree", "address", "containedInPlace", "geo", "additionalProperty"]
ADDRESS = {"@type": "PostalAddress", "addressRegion": "Madeira", "addressCountry": "PT"}
PLACE = {"@type": "AdministrativeArea", "name": "Madeira",
         "containedInPlace": {"@type": "Country", "name": "Portugal"}}


def complete(o, lang, og_image):
    props = {p["name"]: p["value"] for p in o.get("additionalProperty", [])}
    d = next((v for k, v in props.items() if k in DIST), None)
    x = next((v for k, v in props.items() if k in DIFF), None)
    base, sd, sx = SENT[lang]
    o["description"] = base.format(n=o["name"]) + (sd.format(d=d) if d else "") + (sx.format(x=x) if x else "")
    o["address"], o["containedInPlace"] = ADDRESS, PLACE
    if "image" not in o and og_image:
        o["image"] = og_image
    if o.get("url"):
        o["@id"] = o["url"] + "#trail"
    return {k: o[k] for k in ORDER if k in o} | {k: v for k, v in o.items() if k not in ORDER}


def main():
    n = 0
    os.chdir(ROOT)
    for f in sorted(glob.glob("**/*.html", recursive=True)):
        if f.split(os.sep)[0] in ("bot", "seo_research", "reports", "google_search_console", ".claude"):
            continue
        h = open(f, encoding="utf-8").read()
        if '"TouristAttraction"' not in h:
            continue
        lang = re.search(r'<html lang="([a-z]{2})', h).group(1)
        m = re.search(r'<meta property="og:image" content="([^"]+)"', h)

        def fix(mm):
            o = json.loads(mm.group(2))
            if o.get("@type") != "TouristAttraction":
                return mm.group(0)
            return mm.group(1) + json.dumps(complete(o, lang, m and m.group(1)), ensure_ascii=False, indent=2) + mm.group(3)

        new = LD_RE.sub(fix, h)
        if new != h:
            open(f, "w", encoding="utf-8").write(new); n += 1
    print(f"TouristAttraction completed on {n} page(s)")
    print(f"WebPage entity links on {link_webpages()} page(s)")


def link_webpages():
    """isPartOf / publisher on every WebPage block; about -> #trail where the page has a TouristAttraction."""
    n = 0
    for f in sorted(glob.glob("**/*.html", recursive=True)):
        if f.split(os.sep)[0] in ("bot", "seo_research", "reports", "google_search_console", ".claude", "node_modules"):
            continue
        h = open(f, encoding="utf-8").read()
        if '"WebPage"' not in h:
            continue
        trail = re.search(r'"@type":\s*"TouristAttraction"', h) is not None

        def fix(mm):
            try:
                o = json.loads(mm.group(2))
            except ValueError:
                return mm.group(0)
            if not isinstance(o, dict) or o.get("@type") != "WebPage":
                return mm.group(0)
            o.update(WEBPAGE_LINKS)
            if trail and o.get("url"):
                o["about"] = {"@id": o["url"] + "#trail"}
            return mm.group(1) + json.dumps(o, ensure_ascii=False, indent=1) + mm.group(3)

        new = ANY_LD_RE.sub(fix, h)
        if new != h:
            open(f, "w", encoding="utf-8").write(new); n += 1
    return n


if __name__ == "__main__":
    main()
