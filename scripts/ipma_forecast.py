#!/usr/bin/env python3
"""IPMA's 5-day forecast for the weather card's five places + the "bad weather coming" outlook (owner, 2026-11-08:
"lead with the forecast 5 days ahead in all the weather cards ... include rain so people can prepare"; catch storms
before anything closes).

Source: IPMA's public forecast per place (api.ipma.pt/public-data/forecast/aggregate/<id>.json, the data behind
ipma.pt's "previsão por local"): daily rows (idPeriodo 24: weather type, rain probability, rain intensity class 0-3,
wind class 1-4, min/max temperature) plus hourly / 3-hourly rows (wind speed in km/h; the day's maximum is kept).

Outlook = the first coming days (today + 4) where IPMA's forecast for any of the five places shows heavy rain,
thunderstorms, hail or snow, strong rain (class 3) or strong / very strong wind (class >= 3), or where IPMA has a
warning for Madeira that starts more than 24 h ahead. It is IPMA's forecast as published, never our own model.
"""
import datetime
import json
import sys
import urllib.request
import zoneinfo

TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
URL = "https://api.ipma.pt/public-data/forecast/aggregate/{}.json"
SOURCE = "https://www.ipma.pt/pt/otempo/prev.localidade.hora/#Madeira"
POINTS = {   # weather-card region -> IPMA place (public-data/forecast/locations.json)
    "summit": (2310921, "Areeiro"),
    "north": (2310900, "Santana"),
    "west": (2310521, "Bica da Cana"),   # Paul da Serra plateau, the Rabaçal proxy (same as the station)
    "east": (2310424, "Caniçal"),        # the São Lourenço end of the island
    "south": (2310300, "Funchal"),
}
DAYS = 5
HEAVY_TYPES = {8, 11, 14}             # heavy showers / heavy rain / intermittent heavy rain
THUNDER_TYPES = {19, 20, 23}          # thunderstorms
HAIL_SNOW_TYPES = {18, 21, 28}        # snow, hail, snow showers


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f <= -99 else f


def fetch_point(gid, today):
    with urllib.request.urlopen(urllib.request.Request(URL.format(gid), headers={"User-Agent": "Mozilla/5.0"}),
                                timeout=30) as r:
        rows = json.load(r)
    days = [str(today + datetime.timedelta(i)) for i in range(DAYS)]
    wind = {}
    for x in rows:
        if x.get("idPeriodo") in (1, 3):
            d, k = x["dataPrev"][:10], _num(x.get("ffVento"))
            if k is not None:
                wind[d] = max(wind.get(d, 0), k)
    out = []
    for x in rows:
        d = x["dataPrev"][:10]
        if x.get("idPeriodo") != 24 or d not in days:
            continue
        p = _num(x.get("probabilidadePrecipita"))
        out.append({"date": d, "type": int(x.get("idTipoTempo") or 0),
                    "rain_prob": None if p is None else round(p),
                    "rain_int": int(x["idIntensidadePrecipita"]) if x.get("idIntensidadePrecipita") not in (None, -99) else None,
                    "wind_class": int(x["idFfxVento"]) if x.get("idFfxVento") not in (None, -99) else None,
                    "wind_kmh": round(wind[d]) if d in wind else None,
                    "tmin": None if _num(x.get("tMin")) is None else round(_num(x.get("tMin"))),
                    "tmax": None if _num(x.get("tMax")) is None else round(_num(x.get("tMax")))})
    out.sort(key=lambda r: r["date"])
    if len(out) < 3:
        raise ValueError(f"IPMA forecast {gid}: only {len(out)} day(s)")
    return out


def fetch(today=None):
    """{region: [day, ...]} for every place IPMA answered; raises only when none answered."""
    today = today or datetime.datetime.now(TZ).date()
    fc, errors = {}, []
    for key, (gid, _place) in POINTS.items():
        try:
            fc[key] = fetch_point(gid, today)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{key}: {e}")
    if errors:
        print("ipma forecast:", "; ".join(errors), file=sys.stderr)
    if not fc:
        raise RuntimeError("IPMA forecast: no place answered")
    return fc


def bad_reasons(day, mountain=False):
    r = []
    t = day.get("type")
    if t in THUNDER_TYPES:
        r.append("thunder")
    if t in HAIL_SNOW_TYPES:
        r.append("hail" if t == 21 else "snow")
    if t in HEAVY_TYPES or (day.get("rain_int") or 0) >= 3:
        r.append("heavy_rain")
    # strong wind is routine at the summit and on the plateau: there only "very strong" (4) counts
    if (day.get("wind_class") or 0) >= (4 if mountain else 3):
        r.append("strong_wind")
    return r


def outlook(fc, warnings=None, now=None):
    """{"days": [{"date", "reasons": [...], "places": [...]}], "first": date, "source"} or None (nothing coming)."""
    now = now or datetime.datetime.now(TZ)
    days = {}
    for key, rows in (fc or {}).items():
        for d in rows:
            rs = bad_reasons(d, mountain=key in ("summit", "west"))
            if rs:
                e = days.setdefault(d["date"], {"date": d["date"], "reasons": set(), "places": set()})
                e["reasons"].update(rs)
                e["places"].add(key)
    horizon = now + datetime.timedelta(hours=24)
    for w in warnings or []:   # storm.ipma_alert()["all"]: warnings further out than storm mode looks
        start = datetime.datetime.fromisoformat(w["start"]).replace(tzinfo=TZ)
        if start > horizon and w.get("type") != "sea":
            e = days.setdefault(w["start"][:10], {"date": w["start"][:10], "reasons": set(), "places": set()})
            e["reasons"].add("warning_" + w["level"])
    if not days:
        return None
    out = [{"date": d, "reasons": sorted(e["reasons"]), "places": sorted(e["places"])} for d, e in sorted(days.items())]
    return {"days": out, "first": out[0]["date"], "source": SOURCE}


if __name__ == "__main__":
    f = fetch()
    print(json.dumps({"forecast": f, "outlook": outlook(f)}, indent=1, ensure_ascii=False))
