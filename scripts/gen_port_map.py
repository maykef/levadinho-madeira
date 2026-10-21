#!/usr/bin/env python3
"""Renders the day-2 stops map for /two-days-in-madeira/ (owner, 2026-10-20: like the Balcões page's
funchal-stops-map): OSM tiles stitched with PIL, numbered pins, written to img/two-days/port-map.webp (660 wide)
and port-map-full.webp (2x). Coordinates from OpenStreetMap (Overpass, 2026-10-20). Attribution is in the page's
figcaption ("Map © OpenStreetMap contributors"). Run once per change; the tiles come from tile.openstreetmap.org.
"""
import io
import math
import os
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

PTS = [  # (lat, lon) — keep in step with MAP_PTS in gen_port_page.py
    (32.64189, -16.91008),  # 1 cruise terminal (Gare Marítima, Pontinha pier)
    (32.64637, -16.90520),  # 2 Praça do Povo
    (32.64775, -16.90930),  # 3 centre: Avenida Arriaga / cathedral
    (32.64869, -16.90351),  # 4 Mercado dos Lavradores
    (32.64716, -16.90230),  # 5 cable car base station
    (32.64790, -16.90090),  # 6 Old Town (Zona Velha)
]
Z = 16
PAD = 0.0028       # latitude margin around the pins
PAD_LON = 0.0045   # the port area is wide and flat: landscape shape


def xy(lat, lon, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def main():
    lats, lons = [p[0] for p in PTS], [p[1] for p in PTS]
    x0, y1 = xy(max(lats) + PAD, min(lons) - PAD_LON, Z)   # top-left
    x1, y0 = xy(min(lats) - PAD, max(lons) + PAD_LON, Z)   # bottom-right
    tx0, tx1, ty0, ty1 = int(x0), int(x1), int(y1), int(y0)
    w, h = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
    im = Image.new("RGB", (w, h), "#eee")
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            url = f"https://tile.openstreetmap.org/{Z}/{tx}/{ty}.png"
            req = urllib.request.Request(url, headers={"User-Agent": "levadinho-madeira.com page build (hello@levadinho-madeira.com)"})
            im.paste(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB"),
                     ((tx - tx0) * 256, (ty - ty0) * 256))
            time.sleep(0.3)
    # crop to the padded bbox
    cx0, cy0 = int((x0 - tx0) * 256), int((y1 - ty0) * 256)
    cx1, cy1 = int((x1 - tx0) * 256), int((y0 - ty0) * 256)
    im = im.crop((cx0, cy0, cx1, cy1))
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for i, (lat, lon) in enumerate(PTS, 1):
        px, py = xy(lat, lon, Z)
        x, y = (px - tx0) * 256 - cx0, (py - ty0) * 256 - cy0
        r = 19
        d.ellipse([x - r, y - r, x + r, y + r], fill="#1b4332", outline="white", width=3)
        d.text((x, y - 1), str(i), fill="white", font=font, anchor="mm")
    out = os.path.join(ROOT, "img", "cruise-port")
    os.makedirs(out, exist_ok=True)
    im.save(os.path.join(out, "port-map-full.webp"), quality=86)
    small = im.resize((660, round(im.height * 660 / im.width)), Image.LANCZOS)
    small.save(os.path.join(out, "port-map.webp"), quality=84)
    print(f"port-map: full {im.size}, small {small.size}")


if __name__ == "__main__":
    main()
