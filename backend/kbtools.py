"""Levadinho knowledge tools: read-only queries on the kb schema, shared by the MCP server (mcp_server.py), the bot
(phase 3) and the site generators. Plain functions returning JSON-able dicts; every record carries its source.

Connection: KB_URL (environment) or ~/.config/levadinho/kb-reader-url, the read-only kb_reader role.
"""
import datetime
import os
import re
import threading
import zoneinfo

import psycopg
from psycopg.rows import dict_row

MADEIRA = zoneinfo.ZoneInfo("Atlantic/Madeira")
LANGS = ("en", "pt", "fr", "de", "pl")
TS_CFG = {"en": "english", "pt": "portuguese", "fr": "french", "de": "german", "pl": "simple"}
SITE = "https://levadinho-madeira.com"
STATUS_WORDS = {"OPEN", "PARTIAL", "CLOSED"}
REGIONS = ("summit", "north", "west", "east", "south")
FORECAST_SPOT = {"PR1": "pico-do-arieiro", "PR1.1": "achada-do-teixeira", "PR1.2": "achada-do-teixeira",
                 "PR1.3": "achada-do-teixeira", "summit": "pico-do-arieiro", "west": "rabacal-madeira"}
FORECAST_NAMES = {"pico-do-arieiro": "Pico do Areeiro", "achada-do-teixeira": "Achada do Teixeira",
                  "rabacal-madeira": "Rabaçal"}

_local = threading.local()


def _url():
    if os.environ.get("KB_URL"):
        return os.environ["KB_URL"]
    return open(os.path.expanduser("~/.config/levadinho/kb-reader-url"), encoding="utf-8").read().strip()


def _conn():
    c = getattr(_local, "conn", None)
    if c is None or c.closed or c.broken:
        c = psycopg.connect(_url(), row_factory=dict_row, autocommit=True)
        _local.conn = c
    return c


def _q(sql, args=()):
    try:
        return _conn().execute(sql, args).fetchall()
    except psycopg.OperationalError:
        _local.conn = None
        return _conn().execute(sql, args).fetchall()


def _lang(lang):
    lang = (lang or "en").lower()[:2]
    return lang if lang in LANGS else "en"


def _pick(j, lang):
    """A {"en": …, "pt": …} value in the asked language, else English, else the Portuguese original."""
    if not j:
        return None
    if isinstance(j, str):
        return j
    return j.get(lang) or j.get("en") or j.get("pt") or next(iter(j.values()), None)


def _page(url, lang):
    if not url or lang == "en" or not url.startswith(SITE):
        return url
    return SITE + f"/{lang}" + url[len(SITE):]


_SOURCES = {}


def _source(sid):
    if not _SOURCES:
        _SOURCES.update({r["id"]: {"name": r["name"], "url": r["url"]} for r in _q("SELECT id, name, url FROM kb.source")})
    return _SOURCES.get(sid, {"name": sid, "url": None})


def _day(ts):
    return ts.astimezone(MADEIRA).date().isoformat() if ts else None


def resolve_trail(text):
    """'pr 6.1', 'PR6,1', 'risco', 'Levada do Risco' → 'PR6.1' (or None)."""
    if not text:
        return None
    m = re.search(r"\bpr\s?-?(\d{1,2}(?:[.,]\d)?)\b", text.lower())
    if m:
        code = "PR" + m.group(1).replace(",", ".")
        if _q("SELECT 1 FROM kb.trail WHERE code = %s", (code,)):
            return code
    rows = _q("""SELECT code FROM kb.trail WHERE kb.unaccent_i(name) ILIKE '%%' || kb.unaccent_i(%s) || '%%' ORDER BY code LIMIT 1""", (text,))
    if rows:
        return rows[0]["code"]
    rows = _q("""SELECT code, similarity(name, %s) s FROM kb.trail
                 WHERE name ILIKE '%%' || %s || '%%' OR similarity(name, %s) > 0.3
                 ORDER BY (name ILIKE '%%' || %s || '%%') DESC, s DESC LIMIT 1""", (text, text, text, text))
    return rows[0]["code"] if rows else None


def _need_trail(code):
    c = resolve_trail(code)
    if not c:
        known = ", ".join(r["code"] for r in _q("SELECT code FROM kb.trail ORDER BY code"))
        raise ValueError(f"Unknown trail '{code}'. Known codes: {known}")
    return c


# ---------------------------------------------------------------- tools
def trail_status(code: str | None = None, lang: str = "en") -> dict:
    """Today's official status (IFCN warnings list) of one trail, or of every trail when no code is given."""
    lang = _lang(lang)
    src = _source("ifcn_warnings")
    if code:
        c = _need_trail(code)
        r = _q("""SELECT t.code, t.name, s.status, s.note, s.checked_at, t.page_url FROM kb.trail t
                  JOIN kb.trail_status s USING (code) WHERE t.code = %s""", (c,))[0]
        rules = _q("""SELECT text, source_id FROM kb.fact WHERE subject = %s AND topic IN ('one_way', 'getting_back')
                      AND confirmed ORDER BY topic DESC, id""", (c,))
        return {"code": r["code"], "name": r["name"], "status": r["status"], "note": _pick(r["note"], lang),
                **({"rules": [_pick(x["text"], lang) for x in rules]} if rules else {}),
                "page": _page(r["page_url"], lang), "source": src}
    rows = _q("""SELECT t.code, t.name, s.status, s.note, s.checked_at FROM kb.trail t
                 JOIN kb.trail_status s USING (code) ORDER BY s.status, t.code""")
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"counts": counts,
            "trails": [{"code": r["code"], "name": r["name"], "status": r["status"],
                        **({"note": _pick(r["note"], lang)} if r["status"] != "OPEN" and r["note"] else {})} for r in rows],
            "source": src}


def trail_facts(code: str, lang: str = "en") -> dict:
    """Facts about one trail: distance, time, difficulty, altitude, start/end, fee, tunnels/torch/exposure,
    trailhead coordinates, today's status, our page and the official page, plus curated notes."""
    lang = _lang(lang)
    c = _need_trail(code)
    t = _q("""SELECT t.*, ST_Y(trailhead::geometry) lat, ST_X(trailhead::geometry) lon, s.status, s.note
              FROM kb.trail t LEFT JOIN kb.trail_status s USING (code) WHERE code = %s""", (c,))[0]
    notes = _q("""SELECT topic, text, source_id FROM kb.fact WHERE subject = %s AND confirmed AND topic <> 'bus'
                  ORDER BY id""", (c,))
    return {
        "code": t["code"], "name": t["name"], "status": t["status"], "status_note": _pick(t["note"], lang),
        "distance": t["distance_txt"], "duration": t["duration"], "difficulty": t["difficulty"],
        "altitude_m": [t["alt_min_m"], t["alt_max_m"]] if t["alt_min_m"] else None,
        "route_type": t["route_type"], "start": t["start_name"], "end": t["end_name"], "region": t["region"],
        "fee_eur": float(t["fee_eur"]) if t["fee_eur"] is not None else None,
        "fee_note": None if t["fee_eur"] is not None else "No IFCN fee for this trail.",
        "tunnels": t["tunnels"], "torch_needed": {True: "yes", False: "no"}.get(t["torch"]), "exposure": t["exposure"],
        **({"panel_notes": _pick((t["extras"] or {}).get("notes"), lang)} if (t["extras"] or {}).get("notes") else {}),
        **({"ifcn_panel_warning": t["extras"]["ifcn_warning"].get("text_en")}
           if ((t["extras"] or {}).get("ifcn_warning") or {}).get("text_en") else {}),
        "tunnels_note": "tunnels/torch_needed/exposure null = no sourced data, not 'none'.",
        "trailhead": {"lat": t["lat"], "lon": t["lon"]},
        "page": _page(t["page_url"], lang), "official_page": t["official_url"],
        "notes": [{"topic": n["topic"], "text": _pick(n["text"], lang), "source": _source(n["source_id"])} for n in notes],
        "source": _source(t["source_id"]), "status_source": _source("ifcn_warnings"),
    }


def find_trails(region: str | None = None, max_km: float | None = None, difficulty: str | None = None,
                no_vertigo: bool = False, has_tunnels: bool | None = None, open_only: bool = True,
                near_lat: float | None = None, near_lon: float | None = None, near_trail: str | None = None,
                exclude: str | None = None, limit: int = 8, lang: str = "en") -> dict:
    """Trails matching filters, e.g. alternatives when one is closed or full. region: summit|north|west|east|south.
    no_vertigo keeps only trails whose IFCN panel exposure is 'low'. near_lat/near_lon (or near_trail, a trail code:
    its trailhead, and that trail itself is left out) sorts by trailhead distance."""
    lang = _lang(lang)
    if near_trail:
        nt = _need_trail(near_trail)
        r = _q("SELECT ST_Y(trailhead::geometry) lat, ST_X(trailhead::geometry) lon FROM kb.trail WHERE code = %s", (nt,))[0]
        near_lat, near_lon, exclude = r["lat"], r["lon"], exclude or nt
    where, args = ["TRUE"], []
    if region:
        where.append("t.region = %s"); args.append(region.lower())
    if max_km is not None:
        where.append("t.distance_km <= %s"); args.append(max_km)
    if difficulty:
        where.append("t.difficulty ILIKE %s"); args.append(difficulty)
    if no_vertigo:
        where.append("t.exposure = 'low'")
    if has_tunnels is True:
        where.append("t.tunnels IS TRUE")
    if open_only:
        where.append("s.status = 'OPEN'")
    if exclude:
        ex = resolve_trail(exclude)
        if ex:
            where.append("t.code <> %s"); args.append(ex)
    order = "t.code"
    dist = "NULL::float"
    if near_lat is not None and near_lon is not None:
        dist = "ST_Distance(t.trailhead, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000"
        args = [near_lon, near_lat] + args
        order = "km"
    rows = _q(f"""SELECT t.code, t.name, t.region, t.distance_txt, t.duration, t.difficulty, t.exposure, t.tunnels,
                         t.fee_eur, t.page_url, s.status, s.note, {dist} AS km
                  FROM kb.trail t JOIN kb.trail_status s USING (code)
                  WHERE {' AND '.join(where)} ORDER BY {order} LIMIT %s""", args + [max(1, min(limit, 40))])
    return {"trails": [{"code": r["code"], "name": r["name"], "status": r["status"],
                        **({"note": _pick(r["note"], lang)} if r["status"] != "OPEN" and r["note"] else {}),
                        "region": r["region"], "distance": r["distance_txt"], "duration": r["duration"],
                        "difficulty": r["difficulty"], "exposure": r["exposure"], "tunnels": r["tunnels"],
                        "fee_eur": float(r["fee_eur"]) if r["fee_eur"] is not None else None,
                        **({"km_from_point": round(r["km"], 1)} if r["km"] is not None else {}),
                        "page": _page(r["page_url"], lang)} for r in rows],
            "source": {"facts": _source("visitmadeira"), "status": _source("ifcn_warnings"),
                       "exposure": _source("ifcn_panels")}}


FEE_TOPICS = {"fees": ("fees_booking",), "booking": ("fees_booking",), "refunds": ("refunds",),
              "sold_out": ("sold_out",), "one_way": ("one_way", "getting_back"), "fines": ("fees_booking",)}


def fees_and_rules(topic: str | None = None, lang: str = "en") -> dict:
    """Trail fees, multi-day rates, exemptions and fines (exact amounts), plus the rules for booking, refunds,
    one-way PR1, and what to do when a trail is SOLD OUT / fully booked / has no slots left.
    topic: fees | booking | refunds | sold_out | one_way | fines (default: all)."""
    lang = _lang(lang)
    topics = FEE_TOPICS.get((topic or "").lower(), ("fees_booking", "refunds", "sold_out", "one_way", "getting_back"))
    fees = _q("SELECT * FROM kb.fee ORDER BY amount_eur DESC")
    if topic == "fines":
        fees = [f for f in fees if f["item"].startswith("fine")]
    rules = _q("SELECT topic, text, source_id FROM kb.fact WHERE topic = ANY(%s) AND confirmed ORDER BY id", (list(topics),))
    return {"fees": [{"item": f["item"], "what": _pick(f["label"], lang), "eur": float(f["amount_eur"]),
                      **({"max_eur": f["conditions"]["max_eur"]} if (f["conditions"] or {}).get("max_eur") else {}),
                      "applies_to": f["applies_to"], **({"conditions": f["conditions"]} if f["conditions"] else {}),
                      "source": _source(f["source_id"])} for f in fees] if topic not in ("refunds", "sold_out", "one_way") else [],
            "rules": [{"topic": r["topic"], "text": _pick(r["text"], lang), "source": _source(r["source_id"])} for r in rules],
            "booking_url": _source("simplifica")["url"]}


DAYS_FOR = {"mon_fri": ("daily", "mon_fri"), "sat": ("daily", "sat", "sat_sun", "sat_sun_hol"),
            "sun_hol": ("daily", "sun_hol", "sat_sun", "sat_sun_hol")}
MARKS = {"T": "change bus", "PE": "school term only", "PNE": "school holidays only"}


def _day_type(day):
    if not day:
        return None, None
    d = day.lower()
    if d in DAYS_FOR:
        return d, None
    try:
        date = datetime.date.fromisoformat(day)
    except ValueError:
        wd = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6, "today": None, "tomorrow": None}
        key = d[:3] if d[:3] in wd else d
        if key not in wd:
            raise ValueError("day: YYYY-MM-DD, today, tomorrow, a weekday name, mon_fri, sat or sun_hol")
        today = datetime.datetime.now(MADEIRA).date()
        if wd[key] is None:
            date = today + datetime.timedelta(days=1 if key == "tomorrow" else 0)
        else:
            date = today + datetime.timedelta(days=(wd[key] - today.weekday()) % 7)
    return ("mon_fri" if date.weekday() < 5 else "sat" if date.weekday() == 5 else "sun_hol"), date


DAY_NAMES = {"daily": "Every day", "mon_fri": "Monday to Friday", "sat": "Saturdays", "sun_hol": "Sundays and holidays",
             "sat_sun": "Saturdays and Sundays", "sat_sun_hol": "Saturdays, Sundays and holidays"}


def _timetable(rows):
    """One line per leg, route and day type with EVERY departure, e.g. 'there · CAM 113 (new no. 702) Funchal → Baía
    d'Abra · Monday to Friday: 07:30→08:50, 11:00→12:30 (change bus at Machico), …'. Copy these lines as they are."""
    groups = {}
    for r in rows:
        line = r["line"] + (f" (new no. {r['new_line']})" if r["new_line"] else "")
        key = (r["leg"], r["operator"], line, r["from_stop"], r["to_stop"], r["days"])
        marks = [MARKS.get(m, m) + (f" at {r['change_at']}" if m == "T" and r["change_at"] else "") for m in r["marks"]]
        groups.setdefault(key, []).append(r["dep"].strftime("%H:%M") + (f"→{r['arr'].strftime('%H:%M')}" if r["arr"] else "")
                                          + (f" ({', '.join(marks)})" if marks else ""))
    order = list(DAY_NAMES)
    return [f"{leg} · {op} {line} {a} → {b} · {DAY_NAMES[d]}: " + ", ".join(deps)
            for (leg, op, line, a, b, d), deps in sorted(groups.items(), key=lambda kv: (kv[0][0] != "there", kv[0][3], order.index(kv[0][5])))]


def bus(trail: str | None = None, from_stop: str | None = None, to_stop: str | None = None, day: str | None = None,
        lang: str = "en") -> dict:
    """Printed bus trips: to and from a trail (trail='PR8'), or between two stops (from_stop/to_stop, partial names).
    day: YYYY-MM-DD, today, tomorrow, a weekday, mon_fri, sat or sun_hol (public holidays run the sun_hol timetable).
    Lists every printed trip; also the notes our pages give (no bus at the start, take a taxi from Santana…)."""
    lang = _lang(lang)
    where, args = ["TRUE"], []
    code = None
    if trail:
        code = _need_trail(trail)
        where.append("trail_code = %s"); args.append(code)
    if from_stop:
        where.append("from_stop ILIKE '%%' || %s || '%%'"); args.append(from_stop)
    if to_stop:
        where.append("to_stop ILIKE '%%' || %s || '%%'"); args.append(to_stop)
    if not (trail or from_stop or to_stop):
        raise ValueError("Give a trail, or from_stop and/or to_stop.")
    dtype, date = _day_type(day)
    if dtype:
        where.append("days = ANY(%s)"); args.append(list(DAYS_FOR[dtype]))
    date = date or datetime.datetime.now(MADEIRA).date()
    where.append("(valid_from IS NULL OR valid_from <= %s) AND (valid_to IS NULL OR valid_to >= %s)")
    args += [date, date]
    rows = _q(f"""SELECT operator, line, new_line, from_stop, to_stop, dep, arr, days, marks, change_at, leg, source_id,
                         array_agg(DISTINCT trail_code ORDER BY trail_code) trails
                  FROM kb.bus_trip WHERE {' AND '.join(where)}
                  GROUP BY operator, line, new_line, from_stop, to_stop, dep, arr, days, marks, change_at, leg, source_id
                  ORDER BY leg, from_stop, days, dep""", args)
    if not rows and not code:
        guess = resolve_trail(to_stop or "") or resolve_trail(from_stop or "")
        if guess:  # "São Lourenço" is PR8, whose stop is Baía d'Abra
            return {"note": f"No bus stop named '{to_stop or from_stop}' in our data; it is trail {guess}. Its buses:",
                    **bus(trail=guess, day=day, lang=lang)}
    out = {"trips": [{"leg": r["leg"], "operator": r["operator"],
                      "line": r["line"] + (f" (new no. {r['new_line']})" if r["new_line"] else ""),
                      "from": r["from_stop"], "to": r["to_stop"], "dep": r["dep"].strftime("%H:%M"),
                      "arr": r["arr"].strftime("%H:%M") if r["arr"] else None, "days": r["days"],
                      **({"marks": [MARKS.get(m, m) + (f" at {r['change_at']}" if m == "T" and r["change_at"] else "")
                                    for m in r["marks"]]} if r["marks"] else {}),
                      **({"for_trails": r["trails"]} if not code else {})} for r in rows],
           "timetable": _timetable(rows),
           "days_key": {"daily": "every day", "mon_fri": "Monday to Friday", "sat": "Saturdays", "sun_hol": "Sundays and holidays",
                        "sat_sun": "Saturdays and Sundays", "sat_sun_hol": "Saturdays, Sundays and holidays"},
           "caveat": "Times as printed on the operators' timetables (SIGA / Horários do Funchal); times at intermediate "
                     "stops are approximate. No buses on 25 December.",
           "source": [_source(s) for s in sorted({r["source_id"] for r in rows})] or [_source("siga")]}
    fares = _q("""SELECT DISTINCT f.label, f.amount_eur, f.conditions, f.source_id FROM kb.fee f
                  WHERE f.item LIKE 'bus%%' AND EXISTS (SELECT 1 FROM unnest(%s::text[]) l WHERE f.applies_to ILIKE '%%' || l || '%%')""",
               (sorted({r["line"] for r in rows}),))
    if fares:
        out["fares"] = [{"what": _pick(f["label"], lang), "eur": float(f["amount_eur"]),
                         **({"note": f["conditions"].get("note")} if f["conditions"] else {}), "source": _source(f["source_id"])}
                        for f in fares]
    if code:
        t = _q("SELECT name, start_name, end_name, route_type FROM kb.trail WHERE code = %s", (code,))[0]
        out["trail"] = {"code": code, "name": t["name"], "starts_at": t["start_name"], "ends_at": t["end_name"],
                        "route_type": t["route_type"]}
        notes = _q("SELECT text FROM kb.fact WHERE topic = 'bus' AND subject = %s ORDER BY id", (code,))
        out["notes"] = [_pick(n["text"], lang) for n in notes]
        if not rows and not notes:
            out["notes"] = ["No bus information for this trail in our data: suggest a taxi (see the transport tool)."]
    return out


def _ranks_for(place):
    """Taxi ranks for a place: ranks in that town, or printed on the panels of trails starting/ending there."""
    ends = [r["code"] for r in _q("""SELECT code FROM kb.trail WHERE kb.unaccent_i(start_name) ILIKE '%%' || kb.unaccent_i(%s) || '%%'
                                      OR kb.unaccent_i(end_name) ILIKE '%%' || kb.unaccent_i(%s) || '%%'""", (place, place))]
    code = resolve_trail(place)
    if code and code not in ends and not _q("SELECT 1 FROM kb.transport WHERE kb.unaccent_i(town) ILIKE '%%' || kb.unaccent_i(%s) || '%%'", (place,)):
        ends.append(code)
    return _q("""SELECT * FROM kb.transport WHERE kind = 'taxi' AND (kb.unaccent_i(town) ILIKE '%%' || kb.unaccent_i(%s) || '%%'
                 OR trails && %s) ORDER BY id""", (place, ends))


def transport(pickup: str | None = None, destination: str | None = None, trail: str | None = None) -> dict:
    """Taxis for a trip: the ranks serving the PICK-UP place (a town, or a trailhead such as Achada do Teixeira or
    Rabaçal: the ranks printed on IFCN's panels there) and the DESTINATION town, plus the island-wide contacts Visit
    Madeira lists, the rules for taxis and transfers (metered fares, no quoted prices) and, for a trailhead, how to get
    back from there. trail = the ranks on that trail's panels."""
    out, seen = [], set()

    def add(rows, role):
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append({"name": r["name"], "town": r["town"], "phone": r["phone"], "role": role,
                            **({"booking_url": r["url"]} if r["url"] else {}),
                            **({"printed_on_panels_of": r["trails"]} if r["trails"] else {}), "source": _source(r["source_id"])})
    if pickup:
        add(_ranks_for(pickup), f"serves the pick-up place ({pickup})")
    if trail:
        add(_q("SELECT * FROM kb.transport WHERE kind = 'taxi' AND %s = ANY(trails)", (_need_trail(trail),)), f"printed on the {trail} panels")
    if destination:
        add(_ranks_for(destination), f"serves the destination ({destination})")
    if not (pickup or destination or trail):
        add(_q("SELECT * FROM kb.transport WHERE kind = 'taxi' ORDER BY id"), "taxi rank")
    add(_q("SELECT * FROM kb.transport WHERE kind = 'taxi_island' ORDER BY id"), "island-wide")
    facts = _q("SELECT text, source_id FROM kb.fact WHERE topic IN ('taxi', 'transfer') ORDER BY id")
    res = {"taxis": out, "rules": [{"text": _pick(f["text"], "en"), "source": _source(f["source_id"])} for f in facts]}
    # a trail starting or ending at the pick-up/destination place (PR1 starts at Areeiro, ends at Achada do Teixeira):
    # how to get back from its end
    places = [p for p in (pickup, destination) if p]
    codes = sorted({r["code"] for p in places for r in _q(
        """SELECT code FROM kb.trail WHERE kb.unaccent_i(start_name) ILIKE '%%' || kb.unaccent_i(%s) || '%%'
           OR kb.unaccent_i(end_name) ILIKE '%%' || kb.unaccent_i(%s) || '%%'""", (p, p))} | ({_need_trail(trail)} if trail else set()))
    back = _q("""SELECT DISTINCT ON (id) id, subject, text, source_id FROM kb.fact WHERE topic = 'getting_back' AND confirmed
                 AND (subject = ANY(%s) OR """ + " OR ".join(["kb.unaccent_i(text->>'en') ILIKE '%%' || kb.unaccent_i(%s) || '%%'"] * len(places) or ["FALSE"])
              + ") ORDER BY id", [codes] + places)
    if back:
        res["getting_back"] = [{"trail": b["subject"], "text": _pick(b["text"], "en"), "source": _source(b["source_id"])} for b in back]
    res["note"] = "Give the ranks serving the pick-up place first (call them and the destination's, compare quotes); never quote a fare."
    return res


def weather_now(trail: str | None = None, region: str | None = None) -> dict:
    """The latest measured IPMA reading for a trail's area (or a region: summit|north|west|east|south; all regions
    when neither is given). The summit station also says whether Pico do Areeiro is most likely in cloud."""
    regions = list(REGIONS)
    if trail:
        r = _q("SELECT region FROM kb.trail WHERE code = %s", (_need_trail(trail),))
        regions = [r[0]["region"]]
    elif region:
        regions = [region.lower()]
    if "summit" in regions:
        regions.append("summit_station")
    rows = _q("""SELECT DISTINCT ON (region) * FROM kb.weather_obs WHERE region = ANY(%s)
                 ORDER BY region, observed_at DESC""", (regions,))
    return {"readings": [{"region": r["region"], "place": r["place"], "observed_time": r["observed_at"].astimezone(MADEIRA).strftime("%H:%M"),
                          "temp_c": float(r["temp_c"]) if r["temp_c"] is not None else None,
                          "wind_kmh": float(r["wind_kmh"]) if r["wind_kmh"] is not None else None,
                          "rain_mm": float(r["rain_mm"]) if r["rain_mm"] is not None else None,
                          **({"humidity_pct": r["humidity"]} if r["humidity"] is not None else {}),
                          "likely_in_cloud": r["in_cloud"]} for r in rows],
            "note": "Measured station readings (not a forecast), read once a day by the site's updater. null = sensor gave no value.",
            "source": _source("ipma")}


def forecast_tomorrow(trail: str | None = None, spot: str | None = None, day: str = "tomorrow") -> dict:
    """Tomorrow's (or, with day='today', today's) cloud forecast for a summit spot (Pico do Areeiro, Achada do Teixeira, Rabaçal), from five weather
    models: morning (06–10) and daytime (10–17) cloud cover per model and whether they agree. Uncalibrated."""
    if trail:
        c = _need_trail(trail)
        reg = _q("SELECT region FROM kb.trail WHERE code = %s", (c,))[0]["region"]
        spot = FORECAST_SPOT.get(c) or FORECAST_SPOT.get(reg)
        if not spot:
            return {"forecast": None, "note": f"No summit forecast for {c}'s area in our data."}
    spot = spot or "pico-do-arieiro"
    tomorrow = (datetime.datetime.now(MADEIRA).date() + datetime.timedelta(days=0 if day == "today" else 1)).isoformat()
    rows = _q("SELECT * FROM kb.forecast WHERE spot = %s ORDER BY run_date DESC LIMIT 1", (spot,))
    if not rows:
        return {"forecast": None, "note": f"No forecast stored for {spot}."}
    h = rows[0]["hourly"]["hourly"]
    idx = {"morning": [i for i, t in enumerate(h["time"]) if t.startswith(tomorrow) and 6 <= int(t[11:13]) < 10],
           "day": [i for i, t in enumerate(h["time"]) if t.startswith(tomorrow) and 10 <= int(t[11:13]) < 17]}
    if not idx["morning"]:
        return {"forecast": None, "note": f"Levadinho has no cloud forecast for {FORECAST_NAMES.get(spot, spot)} on that day yet. "
                "Say so; the official Madeira forecast is IPMA's (https://www.ipma.pt). Don't point anywhere else."}
    models = sorted({k[len("cloud_cover_"):] for k in h if k.startswith("cloud_cover_") and not k.startswith("cloud_cover_low_")})
    out = {}
    for m in models:
        vals = h[f"cloud_cover_{m}"]
        out[m] = {p: (round(sum(vals[i] for i in ix if vals[i] is not None) / max(1, sum(vals[i] is not None for i in ix))))
                  if any(vals[i] is not None for i in ix) else None for p, ix in idx.items()}
    morning = [v["morning"] for v in out.values() if v["morning"] is not None]
    agree = (max(morning) - min(morning) <= 30) if morning else None
    return {"spot": FORECAST_NAMES.get(spot, spot), "date": tomorrow, "cloud_cover_pct_by_model": out,
            "models_agree_morning": agree,
            "note": "Model cloud cover at the spot's grid point; Levadinho has not yet calibrated it against webcam "
                    "frames, so present it as a rough guide, never a promise.",
            "source": _source(rows[0]["source_id"])}


def closures(since: str | None = None, lang: str = "en") -> dict:
    """Trails closed or partly open now (with IFCN's note), and every status change in the daily history since a
    date (YYYY-MM-DD; default 30 days ago)."""
    lang = _lang(lang)
    since = since or (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    now = _q("""SELECT t.code, t.name, s.status, s.note FROM kb.trail_status s JOIN kb.trail t USING (code)
                WHERE s.status <> 'OPEN' ORDER BY s.status, t.code""")
    changes = _q("""SELECT day, code, status, prev FROM (
                      SELECT day, code, status, source, lag(status) OVER (PARTITION BY code ORDER BY day) prev
                      FROM kb.status_day) x
                    WHERE prev IS NOT NULL AND prev <> status AND day >= %s ORDER BY day, code""", (since,))
    return {"not_open_now": [{"code": r["code"], "name": r["name"], "status": r["status"], "note": _pick(r["note"], lang)} for r in now],
            "changes": [{"date": r["day"].isoformat(), "code": r["code"], "from": r["prev"], "to": r["status"]} for r in changes],
            "note": "History before 2026-09-30 comes from Visit Madeira's index; from then on from IFCN's warnings list.",
            "source": _source("ifcn_warnings")}


def places(category: str | None = None, neighbourhood: str | None = None, near_lat: float | None = None,
           near_lon: float | None = None, limit: int = 10, lang: str = "en") -> dict:
    """Places in Funchal and around the island (viewpoint, sea_pool, museum, cable_car, poncha, bolo_de_mel, garden,
    landmark, restaurant_street…), by category, neighbourhood or distance from a point."""
    lang = _lang(lang)
    where, args = ["TRUE"], []
    if category:
        where.append("%s = ANY(category)"); args.append(category.lower())
    if neighbourhood:
        where.append("(neighbourhood ILIKE '%%' || %s || '%%' OR municipality ILIKE '%%' || %s || '%%')")
        args += [neighbourhood, neighbourhood]
    dist, order = "NULL::float", "name"
    if near_lat is not None and near_lon is not None:
        dist = "ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) / 1000"
        args = [near_lon, near_lat] + args
        order = "km"
    rows = _q(f"""SELECT id, name, category, neighbourhood, municipality, description, source_id, {dist} AS km
                  FROM kb.place WHERE {' AND '.join(where)} ORDER BY {order} LIMIT %s""", args + [max(1, min(limit, 40))])
    res = {"places": [{"id": r["id"], "name": r["name"], "category": r["category"], "neighbourhood": r["neighbourhood"],
                       "municipality": r["municipality"], "description": _pick(r["description"], lang),
                       **({"km_from_point": round(r["km"], 1)} if r["km"] is not None else {}),
                       "source": _source(r["source_id"])} for r in rows]}
    if not rows:
        res["note"] = "No places in our data for this query yet."
    return res


def place(id: str, lang: str = "en") -> dict:
    """Everything stored about one place (hours, price, phone, website, description, location)."""
    lang = _lang(lang)
    rows = _q("""SELECT *, ST_Y(geom::geometry) lat, ST_X(geom::geometry) lon FROM kb.place WHERE id = %s""", (id,))
    if not rows:
        raise ValueError(f"Unknown place id '{id}'.")
    r = rows[0]
    return {"id": r["id"], "name": r["name"], "category": r["category"], "neighbourhood": r["neighbourhood"],
            "municipality": r["municipality"], "location": {"lat": r["lat"], "lon": r["lon"]}, "hours": r["hours"],
            "price": r["price"], "phone": r["phone"], "website": r["website"], "description": _pick(r["description"], lang),
            "source": _source(r["source_id"])}


def notices(subject: str | None = None, lang: str = "en") -> dict:
    """Current and upcoming notices (closures, works, events, cruise days) for a trail code, place id or area."""
    lang = _lang(lang)
    where, args = ["(ends IS NULL OR ends >= now())"], []
    if subject:
        code = resolve_trail(subject)
        where.append("(subject = %s OR subject ILIKE '%%' || %s || '%%')"); args += [code or subject, subject]
    rows = _q(f"SELECT * FROM kb.notice WHERE {' AND '.join(where)} ORDER BY starts NULLS FIRST LIMIT 30", args)
    res = {"notices": [{"subject": r["subject"], "kind": r["kind"],
                        "starts": r["starts"].astimezone(MADEIRA).isoformat() if r["starts"] else None,
                        "ends": r["ends"].astimezone(MADEIRA).isoformat() if r["ends"] else None,
                        "text": _pick(r["text"], lang), "source": _source(r["source_id"])} for r in rows]}
    if not rows:
        res["note"] = "No notices in our data for this query. Trail closures are in trail_status / closures."
    return res


def search(text: str, lang: str = "en", limit: int = 5) -> dict:
    """Full-text search over Levadinho's pages (5 languages) and curated fact sheets: returns the best matching
    sections (whole, up to ~1,800 characters each) with their page and source. Use it when no other tool fits the question."""
    lang = _lang(lang)
    limit = max(1, min(limit, 10))

    def run(cfg_lang):
        return _q("""SELECT id, kind, subject, lang, title, url, source_id,
                            body snippet,
                            ts_rank_cd(tsv, q) rank
                     FROM kb.doc, websearch_to_tsquery(%s::regconfig, kb.unaccent_i(%s)) q
                     WHERE lang = %s AND tsv @@ q ORDER BY rank DESC LIMIT %s""",
                  (TS_CFG[cfg_lang], text, cfg_lang, limit))
    rows = run(lang)
    if not rows and lang != "en":
        rows = run("en")
    if not rows:  # websearch_to_tsquery ANDs every word: retry with any word
        words = [w for w in re.findall(r"\w{3,}", text)][:8]
        if words:
            rows = _q("""SELECT id, kind, subject, lang, title, url, source_id,
                                body snippet,
                                ts_rank_cd(tsv, q) rank
                         FROM kb.doc, to_tsquery(%s::regconfig, kb.unaccent_i(%s)) q
                         WHERE lang = %s AND tsv @@ q ORDER BY rank DESC LIMIT %s""",
                      (TS_CFG[lang], " | ".join(words), lang, limit))
    return {"results": [{"title": r["title"], "subject": r["subject"], "lang": r["lang"], "url": r["url"],
                         "text": re.sub(r"</?b>", "", r["snippet"]), "source": _source(r["source_id"])} for r in rows],
            **({} if rows else {"note": "Nothing found in Levadinho's knowledge for this query."})}


TOOLS = [trail_status, trail_facts, find_trails, fees_and_rules, bus, transport, weather_now, forecast_tomorrow,
         closures, places, place, notices, search]
