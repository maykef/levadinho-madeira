#!/usr/bin/env python3
"""Daily data for the Funchal page (/funchal/, 5 languages): writes funchal.json and the page's static event list.

Separate from update_status.py on purpose: a broken Funchal source must never stop the trail board, so every
module here degrades on its own (keeps the previous run's value, flags it in "ok") and the script exits 0.

Modules (all official or operator sources; nothing estimated):
  days      the next 14 days in Madeira: weekday / Saturday / Sunday / public holiday (national, Madeira, Funchal),
            the city bus service that day (Horários do Funchal GTFS calendar), sunrise and sunset (computed),
            IPMA's daily forecast for Funchal (2310300) and UV, and the market's theme fair
  events    cultura.funchal.pt (the council's events API) + eventsmadeira.com (the Regional Tourism events guide),
            Funchal only, next 14 days; spans over 31 days (permanent exhibitions) are left out
  lidos     Frente MarFunchal: each lido's opening hours and the date window they apply to
  sea       IPMA sea forecast for "Funchal, costa" (2310326): water temperature, waves; IPMA warnings for the
            south coast (MCS) above green
  last_bus  last departure towards the centre from Monte, the Botanical Garden, the Lido and Praia Formosa, per bus
            service day, computed from the Horários do Funchal GTFS feed
  places    opening rules (market, cable cars, toboggans, gardens, museums) transcribed from each operator's or the
            Regional Directorate for Culture's page; funchal.js tells "open now" from them and the Madeira clock

funchal.js renders the page from this file; the "now" panel (Levadinho at the top) picks what leads by Madeira
time, the landing page and whether the visitor arrived by scanning a Levadinho QR code (see /qr.js).
Run from the repo root: python scripts/update_funchal.py   (--pages-only: refill the pages from funchal.json, no fetching)
"""
import csv
import datetime as dt
import html
import io
import json
import math
import os
import re
import sys
import zipfile
from zoneinfo import ZoneInfo

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "funchal.json")
TZ = ZoneInfo("Atlantic/Madeira")
LAT, LON = 32.6485, -16.9084          # IPMA's Funchal point
DAYS = 14
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
      "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8"}
IPMA = "https://api.ipma.pt/open-data"
GTFS = "https://www.horariosdofunchal.pt/googletransit.zip"
LANGS = ("en", "pt", "fr", "de", "pl")
PREFIX = {"en": "", "pt": "pt/", "fr": "fr/", "de": "de/", "pl": "pl/"}


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=60, **kw)
    r.raise_for_status()
    if "json" not in r.headers.get("Content-Type", "") and "zip" not in r.headers.get("Content-Type", ""):
        r.encoding = "utf-8"   # eventsmadeira.com sends no charset: requests would guess Latin-1
    return r


def text_of(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


# --------------------------------------------------------------------------- calendar
def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return dt.date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def holidays(y):
    """Public holidays in Funchal: national (Código do Trabalho art. 234), Madeira Day (1 July) and 26 December
    (regional), Funchal City Day (21 August, municipal)."""
    e = easter(y)
    return {
        dt.date(y, 1, 1): "Ano Novo", e - dt.timedelta(days=2): "Sexta-feira Santa", e: "Páscoa",
        dt.date(y, 4, 25): "Dia da Liberdade", dt.date(y, 5, 1): "Dia do Trabalhador",
        e + dt.timedelta(days=60): "Corpo de Deus", dt.date(y, 6, 10): "Dia de Portugal",
        dt.date(y, 7, 1): "Dia da Região", dt.date(y, 8, 15): "Assunção", dt.date(y, 8, 21): "Dia da Cidade do Funchal",
        dt.date(y, 10, 5): "Implantação da República", dt.date(y, 11, 1): "Todos os Santos",
        dt.date(y, 12, 1): "Restauração da Independência", dt.date(y, 12, 8): "Imaculada Conceição",
        dt.date(y, 12, 25): "Natal", dt.date(y, 12, 26): "Primeira Oitava",
    }


def day_type(d):
    if d in holidays(d.year):
        return "holiday"
    return {5: "saturday", 6: "sunday"}.get(d.weekday(), "weekday")


def sun_times(d):
    """Sunrise and sunset in Madeira local time (NOAA solar position algorithm, about ±1 min)."""
    n = d.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lat = math.radians(LAT)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(lat) * math.cos(decl))
                                - math.tan(lat) * math.tan(decl)))
    out = []
    for sign in (1, -1):
        utc_min = 720 - 4 * (LON + sign * ha) - eqt
        t = dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc) + dt.timedelta(minutes=utc_min)
        out.append(t.astimezone(TZ).strftime("%H:%M"))
    return out   # [sunrise, sunset]


# --------------------------------------------------------------------------- modules
def mod_weather():
    fc = get(f"{IPMA}/forecast/meteorology/cities/daily/2310300.json").json()["data"]
    uv = {u["data"]: float(u["iUv"]) for u in get(f"{IPMA}/forecast/meteorology/uv/uv.json").json()
          if u["globalIdLocal"] == 2310300}
    out = {}
    for f in fc:
        out[f["forecastDate"]] = {"tmin": round(float(f["tMin"])), "tmax": round(float(f["tMax"])),
                                  "rain": round(float(f["precipitaProb"])), "wtype": int(f["idWeatherType"]),
                                  "uv": uv.get(f["forecastDate"])}
    return out


def mod_sea():
    d = get(f"{IPMA}/forecast/oceanography/daily/hp-daily-sea-forecast-day0.json").json()
    p = next(x for x in d["data"] if x["globalIdLocal"] == 2310326)
    warn = [{"type": w["awarenessTypeName"], "level": w["awarenessLevelID"], "start": w["startTime"], "end": w["endTime"]}
            for w in get(f"{IPMA}/forecast/warnings/warnings_www.json").json()
            if w["idAreaAviso"] == "MCS" and w["awarenessLevelID"] not in ("green", "")]
    return {"date": d["forecastDate"], "sst": round(float(p["sstMax"])),
            "wave": [float(p["waveHighMin"]), float(p["waveHighMax"])], "warnings": warn}


def mod_fair(today):
    """Theme fairs at the Mercado dos Lavradores: the market's monthly post lists "08 – Artesanato" etc."""
    posts = get("https://mercados.funchal.pt/wp-json/wp/v2/posts",
                params={"search": "Feiras Temáticas", "per_page": 3, "_fields": "date,title,content,link"}).json()
    months = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
              "outubro", "novembro", "dezembro"]
    out = {}
    for p in posts:
        title = text_of(p["title"]["rendered"]).lower()
        m = re.search(r"(" + "|".join(months) + r")\s+(\d{4})", title)
        if not m:
            continue
        month, year = months.index(m[1]) + 1, int(m[2])
        body = text_of(p["content"]["rendered"])
        pt = body.split("The fairs")[0]
        hours = re.search(r"Horário:\s*(\d{2})h(\d{2})\s*[–-]\s*(\d{2})h(\d{2})", pt)
        for day, theme in re.findall(r"\b(\d{2}) – ([^0-9]+?)(?= \d{2} – | Local:|$)", pt):
            try:
                d = dt.date(year, month, int(day))
            except ValueError:
                continue
            out[d.isoformat()] = {"theme": FAIR_KEY.get(theme.strip().lower(), "other"), "pt": theme.strip(),
                                  "hours": [f"{hours[1]}:{hours[2]}", f"{hours[3]}:{hours[4]}"] if hours else None,
                                  "url": p["link"]}
    return out


FAIR_KEY = {"antiguidades e alfarrabista": "antiques", "artesanato": "handcraft", "gastronomia": "gastronomy",
            "moda, bijuteria e decoração": "fashion"}


def mod_events(today):
    end = today + dt.timedelta(days=DAYS)
    evs = []
    # 1. the council's culture events (The Events Calendar REST API)
    d = get("https://cultura.funchal.pt/wp-json/tribe/events/v1/events",
            params={"start_date": today.isoformat(), "end_date": end.isoformat(), "per_page": 50}).json()
    for e in d.get("events", []):
        venue = e.get("venue") if isinstance(e.get("venue"), dict) else {}
        evs.append({"title": text_of(e["title"]), "venue": text_of(venue.get("venue", "")),
                    "start": e["start_date"][:16].replace(" ", "T"), "end": e["end_date"][:16].replace(" ", "T"),
                    "all_day": bool(e.get("all_day")), "url": e["url"], "src": "cultura.funchal.pt"})
    # 2. the Regional Tourism events guide, list view (its REST API has no dates); Funchal only
    for page in range(1, 9):
        url = "https://eventsmadeira.com/en/list-calendar/" + (f"page/{page}/" if page > 1 else "")
        try:
            h = get(url).text
        except requests.HTTPError:
            break
        cards = re.split(r'class="gt-event-style-4"', h)[1:]
        if not cards:
            break
        last_start = None
        for c in cards:
            t = re.search(r'gt-title"><a href="([^"]+)">(.*?)</a>', c, re.S)
            ds = re.search(r'gt-date">.*?<span>(.*?)</span>', c, re.S)
            if not t or not ds:
                continue
            dd = re.findall(r"(\d{2})/(\d{2})/(\d{4})", ds[1])
            if not dd:
                continue
            s = dt.date(int(dd[0][2]), int(dd[0][1]), int(dd[0][0]))
            e = dt.date(int(dd[-1][2]), int(dd[-1][1]), int(dd[-1][0]))
            last_start = s
            if "funchal-en" not in c or (e - s).days > 31 or e < today or s > end:
                continue
            if text_of(t[2]).lower().startswith("thematic fair"):
                continue   # the market's theme fairs come from the market itself (mod_fair), with their hours
            evs.append({"title": text_of(t[2]), "venue": "", "start": s.isoformat(), "end": e.isoformat(),
                        "all_day": True, "url": t[1], "src": "eventsmadeira.com"})
        if last_start and last_start > end:
            break
    # de-duplicate: same start day and mostly the same words
    def words(s):
        return set(re.findall(r"[a-zà-ÿ]{4,}", s.lower()))
    out = []
    for e in sorted(evs, key=lambda e: (e["start"], e["src"])):
        if any(o["start"][:10] == e["start"][:10] and len(words(o["title"]) & words(e["title"])) >= 2 for o in out):
            continue
        out.append(e)
    return out


LIDOS = [("lido", "Complexo Balnear do Lido", "lido-2"), ("ponta-gorda", "Complexo Balnear da Ponta Gorda", "ponta-gorda"),
         ("barreirinha", "Complexo Balnear da Barreirinha", "barreirinha"),
         ("doca-do-cavacas", "Poças do Gomes – Doca do Cavacas", "pocas-do-gomes-doca-do-cavacas")]
MONTHS_PT = {m: i for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                                          "setembro", "outubro", "novembro", "dezembro"], 1)}


def mod_lidos(today):
    out = []
    for lid, name, slug in LIDOS:
        url = f"https://frentemarfunchal.pt/complexos/{slug}/"
        t = text_of(get(url).text)
        m = re.search(r"Horário de funcionamento\s+(.*?)\s+das\s+(\d{2})h(\d{2})\s+às\s+(\d{2})h(\d{2})\s+De\s+(\d{1,2})"
                      r"(?:\s+de\s+(\w+))?\s+a\s+(\d{1,2})\s+de\s+(\w+)", t)
        rec = {"id": lid, "name": name, "url": url, "hours": None, "window": None, "days": None}
        if m and m[9].lower() in MONTHS_PT:
            m2 = MONTHS_PT[m[9].lower()]
            m1 = MONTHS_PT.get((m[7] or m[9]).lower(), m2)
            y = today.year
            w0, w1 = dt.date(y, m1, int(m[6])), dt.date(y, m2, int(m[8]))
            if w1 < w0:
                w1 = w1.replace(year=y + 1)
            rec.update(hours=[f"{m[2]}:{m[3]}", f"{m[4]}:{m[5]}"], window=[w0.isoformat(), w1.isoformat()],
                       days="daily" if "todos os dias" in m[1].lower() else m[1])
        out.append(rec)
    return out


LAST_BUS_FROM = {   # stop ids in the Horários do Funchal feed
    "monte": {"00540", "00569", "00567", "00615"},             # Largo da Fonte (line 20/21), Babosas (22)
    "garden": {"00312", "00349", "00432", "00895"},            # Jardim Botânico (29, 31), cable-car station (131)
    "lido": {"00018", "00829", "00475", "00047"},
    "formosa": {"01611", "01490", "01289"},
}


def mod_gtfs(days):
    z = zipfile.ZipFile(io.BytesIO(get(GTFS).content))

    def rows(name):
        return csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"))
    service = {}
    for r in rows("calendar_dates.txt"):
        if r["exception_type"] == "1":
            service[r["date"]] = r["service_id"]
    kind = {"UE": "weekday", "S": "saturday", "D": "sunday"}
    by_day = {d: kind.get(service.get(d.replace("-", ""), "").split("_")[0]) for d in days}
    routes = {r["route_id"]: r["route_short_name"] for r in rows("routes.txt")}
    trips = {r["trip_id"]: (r["service_id"].split("_")[0], routes.get(r["route_id"], ""), r["trip_headsign"])
             for r in rows("trips.txt")}
    stops = {}
    for r in rows("stop_times.txt"):
        stops.setdefault(r["trip_id"], []).append((int(r["stop_sequence"]), r["stop_id"], r["departure_time"]))
    last = {k: {} for k in LAST_BUS_FROM}
    for tid, st in stops.items():
        sk, line, head = trips.get(tid, ("", "", ""))
        if sk not in kind or not head.lower().startswith("centro"):
            continue
        st.sort()
        for place, ids in LAST_BUS_FROM.items():
            dep = next((tm for _, sid, tm in st if sid in ids), None)
            if dep and dep[:5] > last[place].get(kind[sk], ["00:00"])[0]:
                last[place][kind[sk]] = [dep[:5], line.lstrip("0") or line]
    for place in last:   # GTFS writes after-midnight trips as 24:xx
        for k, (tm, line) in last[place].items():
            h = int(tm[:2])
            last[place][k] = [f"{h - 24:02d}{tm[2:]}" if h >= 24 else tm, line]
    feed_end = next(rows("feed_info.txt"))["feed_end_date"]
    return by_day, last, f"{feed_end[:4]}-{feed_end[4:6]}-{feed_end[6:]}"


# --------------------------------------------------------------------------- places (opening rules)
# Days: mon tue wed thu fri sat sun hol ("hol" = public holiday; a missing key = closed that day).
# "closed" = fixed dates (MM-DD) on which a daily opening doesn't apply. "months" = the hours only hold in these
# months; outside them the page says "check the hours". Transcribed 2026-10-07 from each page in "url".
WK = ("mon", "tue", "wed", "thu", "fri")
DRC = "https://cultura.madeira.gov.pt/index.php/"


def H(days, *spans):
    return {d: [list(s) for s in spans] for d in days}


def merge(*parts):
    out = {}
    for p in parts:
        out.update(p)
    return out


PLACES = [
    {"id": "market", "kind": "market", "area": "zona-velha", "name": "Mercado dos Lavradores",
     "hours": merge(H(WK, ("07:00", "19:00")), H(("sat",), ("07:00", "14:00"))),
     "url": "https://mercados.funchal.pt/contactos/"},
    {"id": "cablecar", "kind": "cable", "area": "zona-velha", "name": "Teleférico do Funchal (Funchal – Monte)",
     "hours": H(WK + ("sat", "sun", "hol"), ("08:45", "17:45")), "closed": ["12-25"],
     "url": "https://www.madeiracablecar.com/"},
    {"id": "gardencable", "kind": "cable", "area": "monte", "name": "Teleférico do Jardim Botânico (Monte – Jardim Botânico)",
     "hours": H(WK + ("sat", "sun", "hol"), ("09:00", "17:00")), "closed": ["12-25"],
     "url": "https://www.telefericojardimbotanico.com/en/"},
    {"id": "toboggan", "kind": "toboggan", "area": "monte", "name": "Carreiros do Monte",
     "hours": H(WK + ("sat",), ("09:00", "18:00")), "url": "https://www.carreirosdomonte.com/v3/en/"},
    {"id": "montepalace", "kind": "garden", "area": "monte", "name": "Monte Palace Madeira",
     "hours": H(WK + ("sat", "sun", "hol"), ("09:00", "18:00")), "months": [10, 11, 12, 1, 2, 3],
     "url": "https://montepalacemadeira.com/visita/"},
    {"id": "botanical", "kind": "garden", "area": "monte", "name": "Jardim Botânico da Madeira",
     "hours": H(WK + ("sat", "sun", "hol"), ("09:00", "17:30")), "closed": ["12-25"],
     "url": "https://visitmadeira.com/"},
    {"id": "quintadascruzes", "kind": "museum", "area": "sao-pedro", "name": "Museu Quinta das Cruzes",
     "hours": H(("tue", "wed", "thu", "fri", "sat"), ("10:00", "17:30")), "url": DRC + "museu-quinta-das-cruzes"},
    {"id": "fredericodefreitas", "kind": "museum", "area": "sao-pedro", "name": "Casa-Museu Frederico de Freitas",
     "hours": H(("tue", "wed", "thu", "fri", "sat"), ("10:00", "17:30")), "url": DRC + "casa-museu-frederico-de-freitas"},
    {"id": "santaclara", "kind": "museum", "area": "sao-pedro", "name": "Convento de Santa Clara",
     "hours": H(("tue", "wed", "thu", "fri", "sat"), ("10:00", "12:30"), ("14:00", "17:00")), "url": DRC + "convento-de-santa-clara"},
    {"id": "artesacra", "kind": "museum", "area": "centre", "name": "Museu de Arte Sacra do Funchal",
     "hours": merge(H(WK, ("10:00", "17:30")), H(("sat",), ("10:00", "13:30"))), "url": DRC + "museu-de-arte-sacra-do-funchal"},
    {"id": "acucar", "kind": "museum", "area": "centre", "name": "Museu A Cidade do Açúcar", "free": True,
     "hours": H(WK, ("09:00", "17:30")), "url": DRC + "museu-a-cidade-do-acucar"},
    {"id": "historianatural", "kind": "museum", "area": "sao-pedro", "name": "Museu de História Natural do Funchal",
     "hours": H(("tue", "wed", "thu", "fri", "sat", "sun", "hol"), ("10:00", "18:00")), "closed": ["01-01", "05-01", "08-21", "12-25", "12-26"],
     "url": DRC + "museu-de-historia-natural-do-funchal"},
    {"id": "fotografia", "kind": "museum", "area": "centre", "name": "Museu de Fotografia da Madeira – Atelier Vicente's",
     "hours": H(("tue", "wed", "thu", "fri", "sat"), ("10:00", "17:00")), "url": DRC + "museu-de-fotografia-da-madeira-atelier-vicente-s"},
    {"id": "casadaluz", "kind": "museum", "area": "zona-velha", "name": "Museu da Electricidade – Casa da Luz",
     "hours": H(("tue", "wed", "thu", "fri", "sat"), ("10:00", "12:30"), ("14:00", "18:00")), "url": DRC + "museu-da-electricidade-casa-da-luz"},
    {"id": "fortalezapico", "kind": "museum", "area": "sao-pedro", "name": "Fortaleza de São João Baptista do Pico",
     "hours": H(WK, ("10:00", "12:30"), ("14:00", "17:00")), "url": DRC + "fortaleza-de-sao-joao-baptista-do-pico"},
    {"id": "mamma", "kind": "museum", "area": "centre", "name": "MAMMA – A Star is Born",
     "hours": merge(H(("tue", "wed", "thu", "fri", "sat"), ("10:00", "18:00")), H(("sun",), ("10:00", "15:00"))),
     "url": DRC + "mamma-a-star-is-born"},
    {"id": "designcenter", "kind": "museum", "area": "centre", "name": "Design Center Nini Andrade Silva",
     "hours": H(WK + ("sat", "sun"), ("10:00", "23:00")), "url": DRC + "design-center-nini-andrade-silva"},
    {"id": "winecompany", "kind": "museum", "area": "centre", "name": "Madeira Wine Company – Adegas de São Francisco",
     "hours": merge(H(WK, ("10:00", "18:30")), H(("sat",), ("10:00", "13:00"))),
     "url": DRC + "madeira-wine-company---adegas-de-sao-francisco"},
]
PARKING = {"paid": merge(H(WK, ("08:00", "20:00")), H(("sat",), ("08:00", "14:00"))),
           "url": "https://frentemarfunchal.pt/mobilidade-2/parquimetros/"}


# --------------------------------------------------------------------------- static event list in the pages
WEEKDAYS = {"en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "pt": ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"],
            "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
            "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
            "pl": ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]}
NO_EVENTS = {"en": "No events listed for the coming days by the city's or the Region's events guides.",
             "pt": "Os guias de eventos da Câmara e da Região não listam eventos para os próximos dias.",
             "fr": "Les agendas de la ville et de la Région n'annoncent aucun événement pour les prochains jours.",
             "de": "Die Veranstaltungskalender der Stadt und der Region nennen für die nächsten Tage keine Termine.",
             "pl": "Kalendarze wydarzeń miasta i regionu nie podają wydarzeń na najbliższe dni."}
UNTIL = {"en": "until", "pt": "até", "fr": "jusqu'à", "de": "bis", "pl": "do"}
ONGOING = {"en": "On now", "pt": "A decorrer", "fr": "En cours", "de": "Laufend", "pl": "Trwa"}


def events_html(events, today, lang):
    """Next 7 days only, so a weekday name is never ambiguous; no dates on the page (owner's rule)."""
    soon = [e for e in events if e["start"][:10] <= (today + dt.timedelta(days=6)).isoformat()
            and e["end"][:10] >= today.isoformat()]
    if not soon:
        return f"<p>{NO_EVENTS[lang]}</p>"
    li = []
    for e in soon[:12]:
        s = dt.date.fromisoformat(e["start"][:10])
        when = WEEKDAYS[lang][s.weekday()] if s >= today else ""
        if not e["all_day"] and len(e["start"]) > 10:
            when += f" {e['start'][11:16]}"
        if e["end"][:10] > e["start"][:10]:
            en = dt.date.fromisoformat(e["end"][:10])
            if (en - today).days <= 6:
                when = (when + " " if when else "") + f"{UNTIL[lang]} {WEEKDAYS[lang][en.weekday()]}"
        if not when.strip():
            when = ONGOING[lang]
        venue = f" · {html.escape(e['venue'])}" if e["venue"] else ""
        li.append(f'<li><b>{html.escape(when.strip())}</b> · <a class="plain" href="{html.escape(e["url"])}" '
                  f'target="_blank" rel="noopener">{html.escape(e["title"])}</a>{venue}</li>')
    return "<ul class=\"fx-events\">" + "".join(li) + "</ul>"


BUS_FROM = {
    "monte": {"en": "Monte (Largo da Fonte, Babosas)", "pt": "Monte (Largo da Fonte, Babosas)", "fr": "Monte (Largo da Fonte, Babosas)",
              "de": "Monte (Largo da Fonte, Babosas)", "pl": "Monte (Largo da Fonte, Babosas)"},
    "garden": {"en": "Botanical Garden", "pt": "Jardim Botânico", "fr": "Jardin botanique", "de": "Botanischer Garten",
               "pl": "Ogród Botaniczny"},
    "lido": {l: "Lido" for l in LANGS},
    "formosa": {l: "Praia Formosa" for l in LANGS},
}
LINE = {"en": "line", "pt": "linha", "fr": "ligne", "de": "Linie", "pl": "linia"}


def lastbus_html(data, lang):
    lb = data.get("last_bus") or {}
    rows = []
    for k in ("monte", "garden", "lido", "formosa"):
        v = lb.get(k) or {}
        cells = "".join(f"<td>{v[d][0]} ({v[d][1]})</td>" if v.get(d) else "<td>–</td>"
                        for d in ("weekday", "saturday", "sunday"))
        rows.append(f'<tr><td class="w">{BUS_FROM[k][lang]}</td>{cells}</tr>')
    return "".join(rows)


def fill_pages(data, today):
    changed = []
    for lang in LANGS:
        path = os.path.join(ROOT, PREFIX[lang], "funchal", "index.html")
        if not os.path.exists(path):
            continue
        s = open(path, encoding="utf-8").read()
        new = re.sub(r"(<!-- STATIC-FX-EVENTS:START -->).*?(<!-- STATIC-FX-EVENTS:END -->)",
                     lambda m: m[1] + events_html(data["events"], today, lang) + m[2], s, flags=re.S)
        new = re.sub(r"(<!-- STATIC-FX-LASTBUS:START -->).*?(<!-- STATIC-FX-LASTBUS:END -->)",
                     lambda m: m[1] + lastbus_html(data, lang) + m[2], new, flags=re.S)
        if new != s:
            open(path, "w", encoding="utf-8").write(new)
            changed.append(os.path.relpath(path, ROOT))
    return changed


def bump(changed, now):
    """dateModified + sitemap <lastmod> only for pages whose event list changed (as update_status.py does)."""
    if not changed:
        return
    for p in changed:
        f = os.path.join(ROOT, p)
        s = open(f, encoding="utf-8").read()
        open(f, "w", encoding="utf-8").write(re.sub(r'("dateModified":\s*")[^"]*', lambda m: m[1] + now, s, count=1))
    sm = os.path.join(ROOT, "sitemap.xml")
    s = open(sm, encoding="utf-8").read()
    urls = {"https://levadinho-madeira.com/" + p[: -len("index.html")] for p in changed}

    def sub(m):
        b = m.group(0)
        loc = re.search(r"<loc>([^<]+)</loc>", b)
        return re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{now[:10]}</lastmod>", b) if loc and loc[1] in urls else b
    open(sm, "w", encoding="utf-8").write(re.sub(r"<url>.*?</url>", sub, s, flags=re.S))


# --------------------------------------------------------------------------- main
def main():
    now = dt.datetime.now(TZ)
    today = now.date()
    if "--pages-only" in sys.argv:   # gen_funchal.py: refill the static markers from the current funchal.json
        changed = fill_pages(json.load(open(OUT, encoding="utf-8")), today)
        print(f"funchal pages filled from funchal.json: {len(changed)} changed")
        return
    try:
        prev = json.load(open(OUT, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        prev = {}
    dates = [(today + dt.timedelta(days=i)).isoformat() for i in range(DAYS)]
    ok, res = {}, {}

    def run(name, fn, *a):
        try:
            res[name] = fn(*a)
            ok[name] = True
        except Exception as e:   # one broken source never blanks the page: keep the previous value
            print(f"funchal: {name} failed: {type(e).__name__}: {e}", file=sys.stderr)
            res[name] = None
            ok[name] = False

    run("weather", mod_weather)
    run("sea", mod_sea)
    run("fair", mod_fair, today)
    run("events", mod_events, today)
    run("lidos", mod_lidos, today)
    run("gtfs", mod_gtfs, dates)

    prev_days = {d["date"]: d for d in prev.get("days", [])}
    bus_days, last_bus, feed_end = res["gtfs"] or ({}, prev.get("last_bus"), prev.get("bus_feed_end"))
    wx = res["weather"] or {}
    fair = res["fair"] if res["fair"] is not None else {k: v.get("fair") for k, v in prev_days.items() if v.get("fair")}
    days = []
    for d in dates:
        dd = dt.date.fromisoformat(d)
        rise, set_ = sun_times(dd)
        p = prev_days.get(d, {})
        days.append({"date": d, "type": day_type(dd), "holiday": holidays(dd.year).get(dd),
                     "bus": bus_days.get(d) if res["gtfs"] else p.get("bus"),
                     "sunrise": rise, "sunset": set_,
                     "weather": wx.get(d) or (p.get("weather") if not res["weather"] else None),
                     "fair": fair.get(d)})
    events = res["events"] if res["events"] is not None else [
        e for e in prev.get("events", []) if e["end"][:10] >= today.isoformat()]
    data = {
        "stamp": now.isoformat(timespec="minutes"),
        "tz": "Atlantic/Madeira",
        "days": days,
        "events": events,
        "sea": res["sea"] or prev.get("sea"),
        "lidos": res["lidos"] or prev.get("lidos", []),
        "lido_price": {"adult": 6, "youth_7_17": 2, "free_under": 7, "free": ["Praia Formosa"],
                       "url": "https://frentemarfunchal.pt/tarifario/"},
        "last_bus": last_bus,
        "bus_feed_end": feed_end,
        "places": PLACES,
        "parking": PARKING,
        "ok": ok,
        "sources": {
            "events": ["https://cultura.funchal.pt/", "https://eventsmadeira.com/"],
            "weather": "https://www.ipma.pt/", "bus": "https://www.horariosdofunchal.pt/",
            "market_fairs": "https://mercados.funchal.pt/", "lidos": "https://frentemarfunchal.pt/",
        },
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    changed = fill_pages(data, today)
    bump(changed, now.strftime("%Y-%m-%dT%H:%M%z")[:-2] + ":" + now.strftime("%z")[-2:])
    print(f"funchal.json: {len(events)} events, modules ok: {', '.join(k for k, v in ok.items() if v) or 'none'}"
          f"; failed: {', '.join(k for k, v in ok.items() if not v) or 'none'}; pages changed: {len(changed)}")


if __name__ == "__main__":
    main()
