#!/usr/bin/env python3
"""Renders the map for /funchal-gardens-trail/ (owner, 2026-11-07): OSM tiles stitched with PIL, the route drawn from
OpenStreetMap routing (routing.openstreetmap.de: taxi legs by car, the walk down on foot), numbered pins, the pier
anchor and the optional Pico dos Barcelos detour. Writes img/gardens-trail/map.webp (660 wide) and map-full.webp.
Same pattern as scripts/gen_twoday_map.py; attribution in the page's figcaption. Run once per change.

Coordinates: OpenStreetMap / Nominatim (7 Nov 2026). Quinta do Poço has no OSM entry: placed by the Imaculado
Coração de Maria church at Estrada dos Marmeleiros 1 (visit.funchal.pt address); Pico dos Barcelos = the OSM viewpoint.
Keep the numbering in step with MAP_NAMES in gen_gardens_trail_page.py.
"""
import io
import json
import math
import os
import time
import urllib.request

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "levadinho-madeira.com page build (hello@levadinho-madeira.com)"}

P = {  # (lat, lon, label)
    "pier": (32.6414, -16.9151, "anchor"),
    "orchid": (32.65353, -16.8965, "1"),
    "botanic": (32.6622, -16.8953, "2"),
    "poco": (32.66154, -16.9151, "3"),
    "cruzes": (32.65104, -16.9138, "4"),
    "municipal": (32.647849, -16.9115165, "5"),
    "catarina": (32.64528, -16.9147, "6"),
    "barcelos": (32.6586625, -16.9394112, "V"),
}
LEGS = [  # (from, to, profile, kind)
    ("pier", "orchid", "car", "taxi"), ("orchid", "botanic", "car", "taxi"), ("botanic", "poco", "car", "taxi"),
    ("poco", "cruzes", "foot", "walk"), ("cruzes", "municipal", "foot", "walk"), ("municipal", "catarina", "foot", "walk"),
    ("catarina", "pier", "foot", "walk"), ("poco", "barcelos", "car", "opt"), ("barcelos", "cruzes", "car", "opt"),
]
STYLE = {"taxi": ("#2B6CB0", 8, True), "walk": ("#2F855A", 9, False), "opt": ("#E07A1F", 7, True)}
Z = 15
PAD, PAD_LON = 0.0025, 0.0035


def xy(lat, lon, z=Z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def route(a, b, profile):
    (la, lo, _), (lb, lob, _) = P[a], P[b]
    url = (f"https://routing.openstreetmap.de/routed-{profile}/route/v1/driving/{lo},{la};{lob},{lb}"
           "?overview=full&geometries=geojson")
    r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
    time.sleep(1)
    return [(y, x) for x, y in r["routes"][0]["geometry"]["coordinates"]]


def main():
    lines = [(kind, route(a, b, prof)) for a, b, prof, kind in LEGS]
    lats = [p[0] for p in P.values()] + [c[0] for _, l in lines for c in l]
    lons = [p[1] for p in P.values()] + [c[1] for _, l in lines for c in l]
    x0, y1 = xy(max(lats) + PAD, min(lons) - PAD_LON)
    x1, y0 = xy(min(lats) - PAD, max(lons) + PAD_LON)
    tx0, tx1, ty0, ty1 = int(x0), int(x1), int(y1), int(y0)
    im = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), "#eee")
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            req = urllib.request.Request(f"https://tile.openstreetmap.org/{Z}/{tx}/{ty}.png", headers=UA)
            im.paste(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB"),
                     ((tx - tx0) * 256, (ty - ty0) * 256))
            time.sleep(0.3)
    cx0, cy0 = int((x0 - tx0) * 256), int((y1 - ty0) * 256)
    im = im.crop((cx0, cy0, int((x1 - tx0) * 256), int((y0 - ty0) * 256)))

    def px(lat, lon):
        X, Y = xy(lat, lon)
        return (X - tx0) * 256 - cx0, (Y - ty0) * 256 - cy0

    d = ImageDraw.Draw(im)
    for kind in ("opt", "taxi", "walk"):          # optional under, walk on top
        col, w, dashed = STYLE[kind]
        for k, l in lines:
            if k != kind:
                continue
            pts = [px(*c) for c in l]
            if not dashed:
                d.line(pts, fill=col, width=w, joint="curve")
                continue
            acc, on = 0.0, True                    # dashes: 16 px on, 11 px off along the path
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                seg = math.hypot(bx - ax, by - ay)
                t = 0.0
                while t < seg:
                    step = min((16 if on else 11) - acc, seg - t)
                    if on:
                        f0, f1 = t / seg, (t + step) / seg
                        d.line([(ax + (bx - ax) * f0, ay + (by - ay) * f0), (ax + (bx - ax) * f1, ay + (by - ay) * f1)],
                               fill=col, width=w)
                    t += step
                    acc += step
                    if acc >= (16 if on else 11):
                        acc, on = 0.0, not on
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    for key, (lat, lon, lab) in P.items():
        x, y = px(lat, lon)
        r = 26
        fill = "#E07A1F" if key == "barcelos" else "#1b4332"
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline="white", width=4)
        if lab == "anchor":
            d.text((x, y - 1), "⚓", fill="white", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32), anchor="mm")
        else:
            d.text((x, y - 1), lab, fill="white", font=font, anchor="mm")
    out = os.path.join(ROOT, "img", "gardens-trail")
    os.makedirs(out, exist_ok=True)
    im.save(os.path.join(out, "map-full.webp"), quality=86)
    small = im.resize((660, round(im.height * 660 / im.width)), Image.LANCZOS)
    small.save(os.path.join(out, "map.webp"), quality=84)
    print(f"gardens map: full {im.size}, small {small.size}")


if __name__ == "__main__":
    main()
