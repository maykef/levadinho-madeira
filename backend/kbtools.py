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


ALIASES = {  # names the fuzzy match gets wrong or that aren't a trail's own name
    "levada do norte": "PR17",  # its ticketed stretch (the rest is non-classified and free)
}


def resolve_trail(text):
    """'pr 6.1', 'PR6,1', 'risco', 'Levada do Risco' → 'PR6.1' (or None)."""
    if not text:
        return None
    for alias, code in ALIASES.items():
        if alias in text.lower():
            return code
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


def areeiro_sunrise(day):
    """Sunrise at Pico do Areeiro (32.7355 N, 16.9283 W) on `day`, Madeira time, NOAA formula (standard refraction):
    matches our sunrise page's computed monthly table within 2 min. The summit, with a clear east horizon, sees the
    sun about 6 minutes earlier."""
    import math
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1.25)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                   - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lat = math.radians(32.7355)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(lat) * math.cos(decl))
                                - math.tan(lat) * math.tan(decl)))
    utc = datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.UTC) \
        + datetime.timedelta(minutes=720 - 4 * (-16.9283 + ha) - eq)
    return utc.astimezone(MADEIRA)


def _y(month):
    """The year of that month's next (or current) occurrence."""
    today = datetime.datetime.now(MADEIRA).date()
    return today.year + (month < today.month)


def sunrise_now():
    """Today's and tomorrow's sunrise at Pico do Areeiro (the visitor asks about these, not the 1st of the month)."""
    today = datetime.datetime.now(MADEIRA).date()
    out = {}
    for key, d in (("today", today), ("tomorrow", today + datetime.timedelta(days=1))):
        t = areeiro_sunrise(d)
        slot = t.replace(second=0, microsecond=0) + datetime.timedelta(minutes=(30 - t.minute % 30) % 30 or 0)
        if slot <= t:
            slot += datetime.timedelta(minutes=30)
        out[key] = {"weekday": d.strftime("%A"), "sunrise": t.strftime("%H:%M"),
                    "summit_clear_horizon": (t - datetime.timedelta(minutes=6)).strftime("%H:%M"),
                    # slots start every 30 minutes; the model got "08:00 or 08:30" for an 08:17 sunrise (24 Oct)
                    "first_slot_after_sunrise": slot.strftime("%H:%M")}
    return out


def trail_facts(code: str, lang: str = "en") -> dict:
    """Facts about one trail: distance, time, difficulty, altitude, start/end, fee, tunnels/torch/exposure,
    trailhead coordinates, today's status, our page and the official page, plus curated notes."""
    lang = _lang(lang)
    c = _need_trail(code)
    t = _q("""SELECT t.*, ST_Y(trailhead::geometry) lat, ST_X(trailhead::geometry) lon, s.status, s.note
              FROM kb.trail t LEFT JOIN kb.trail_status s USING (code) WHERE code = %s""", (c,))[0]
    # bus timetables live in bus(), but the 'nobus' sentences carry the car-park and shuttle facts (Rabaçal ER105…)
    notes = _q("""SELECT topic, text, source_id FROM kb.fact WHERE subject = %s AND confirmed
                  AND (topic <> 'bus' OR id LIKE 'bus:%%:nobus:%%') ORDER BY id""", (c,))
    return {
        "code": t["code"], "name": t["name"], "status": t["status"], "status_note": _pick(t["note"], lang),
        "distance": t["distance_txt"], "duration": t["duration"], "difficulty": t["difficulty"],
        "altitude_m": [t["alt_min_m"], t["alt_max_m"]] if t["alt_min_m"] else None,
        "route_type": t["route_type"], "start": t["start_name"], "end": t["end_name"], "region": t["region"],
        "fee_eur": float(t["fee_eur"]) if t["fee_eur"] is not None else None,
        "fee_note": None if t["fee_eur"] is not None else "No IFCN fee for this trail.",
        # PR1's fee is not one number: hand the model the full tariff so a cost question gets all of it
        **({"fees": [{"label": _pick(f["label"], lang), "eur": float(f["amount_eur"])}
                     for f in _q("SELECT label, amount_eur FROM kb.fee WHERE applies_to = 'PR1' ORDER BY amount_eur DESC")]}
           if c == "PR1" else {}),
        # sunrise on the 1st of each month at Pico do Areeiro, Madeira time ±2 min (our sunrise page's computed
        # table) — a structured field because the model misread the prose note and invented December times
        **({"sunrise_1st_of_month": {"Jan": "08:10", "Feb": "08:03", "Mar": "07:36", "Apr": "07:56",
                                     "May": "07:21", "Jun": "07:01", "Jul": "07:03", "Aug": "07:21",
                                     "Sep": "07:42", "Oct": "08:02", "Nov": "07:25", "Dec": "07:52"},
            "sunrise_today_tomorrow": sunrise_now(),
            "sunrise_note": "For today or tomorrow give sunrise_today_tomorrow (computed for that day). For another "
                            "month COPY the month's time from sunrise_1st_of_month, never estimate one. "
                            "Mid-October is about 08:12 and late October 08:20 (clocks go back on the last "
                            "Sunday of October, hence November 07:25). "
                            "Latest sunrises: December–January (~07:52–08:10), so even the 07:30 slot is "
                            "before sunrise then; only late May–July (sunrise ~07:00) needs the 07:00 slot. "
                            "Which slot: to watch the sunrise from the viewpoint first, book the first slot that "
                            "starts after sunrise (the slots are every 30 minutes); a slot before sunrise means "
                            "starting the walk in the dark with a headlamp. From August to April the 07:00 and "
                            "07:30 slots are before sunrise. "
                            "The slot is only for walking onto PR1: the viewpoint by the car park is outside "
                            "the classified trail, so just watching the sunrise should not need a ticket "
                            "(no explicit official statement — say so)."}
           if c == "PR1" else {}),
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
    far = []
    if near_lat is not None and near_lon is not None:   # "nearby" means nearby: trailheads within NEAR_KM only
        far = [r for r in rows if r["km"] is not None and r["km"] > NEAR_KM]
        rows = [r for r in rows if r["km"] is None or r["km"] <= NEAR_KM]
    return {**({"note": f"Only trails whose start is within {NEAR_KM} km are listed."} if far else {}),
            "trails": [{"code": r["code"], "name": r["name"], "status": r["status"],
                        **({"note": _pick(r["note"], lang)} if r["status"] != "OPEN" and r["note"] else {}),
                        "region": r["region"], "distance": r["distance_txt"], "duration": r["duration"],
                        "difficulty": r["difficulty"], "exposure": r["exposure"], "tunnels": r["tunnels"],
                        "fee_eur": float(r["fee_eur"]) if r["fee_eur"] is not None else None,
                        **({"km_from_point": round(r["km"], 1)} if r["km"] is not None else {}),
                        "page": _page(r["page_url"], lang)} for r in rows],
            "source": {"facts": _source("visitmadeira"), "status": _source("ifcn_warnings"),
                       "exposure": _source("ifcn_panels")}}


NEAR_KM = 15

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
            raise ValueError("day: YYYY-MM-DD, today, tomorrow, a weekday name, mon_fri, sat or sun_hol") from None
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
        key = (r["leg"] or "line", r["operator"], line, r["from_stop"], r["to_stop"], r["days"])
        marks = [MARKS.get(m, m) + (f" at {r['change_at']}" if m == "T" and r["change_at"] else "") for m in r["marks"]]
        groups.setdefault(key, []).append(r["dep"].strftime("%H:%M") + (f"→{r['arr'].strftime('%H:%M')}" if r["arr"] else "")
                                          + (f" ({', '.join(marks)})" if marks else ""))
    order = list(DAY_NAMES)
    return [f"{leg} · {op} {line} {a} → {b} · {DAY_NAMES[d]}: " + ", ".join(deps)
            for (leg, op, line, a, b, d), deps in sorted(groups.items(), key=lambda kv: (kv[0][0] != "there", kv[0][3], order.index(kv[0][5])))]


def bus(trail: str | None = None, from_stop: str | None = None, to_stop: str | None = None, day: str | None = None,
        lang: str = "en") -> dict:
    """Printed bus trips — call this for EVERY public-transport question, not only trails: it also holds the
    island's town-to-town lines (Rodoeste west, CAM east/north, Horários do Funchal interurban: Funchal, Machico,
    Faial, Porto da Cruz, Santana, Porto Moniz, Calheta, Paul do Mar, Ponta do Pargo, São Vicente, Monte, Curral
    das Freiras…). Use trail='PR8', or from_stop/to_stop (partial names are fine).
    day: YYYY-MM-DD, today, tomorrow, a weekday, mon_fri, sat or sun_hol (public holidays run the sun_hol timetable).
    Lists every printed trip; also the notes our pages give (no bus at the start, take a taxi from Santana…).
    An empty trips list means our sheets show no bus for that pair: say so and suggest a taxi."""
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
    # the same physical trip can be in both a curated sheet ("Santana network") and a transcribed line (801):
    # keep one row per (from, to, dep, days, leg), preferring the one with the printed line number
    seen = {}
    for r in rows:
        k = (r["from_stop"], r["to_stop"], r["dep"], r["days"])
        if k not in seen or (not (seen[k]["line"] or "")[:1].isdigit() and (r["line"] or "")[:1].isdigit()):
            seen[k] = r
    rows = list(seen.values())
    if not rows and not code:
        guess = resolve_trail(to_stop or "") or resolve_trail(from_stop or "")
        if guess:  # "São Lourenço" is PR8, whose stop is Baía d'Abra
            return {"note": f"No bus stop named '{to_stop or from_stop}' in our data; it is trail {guess}. Its buses:",
                    **bus(trail=guess, day=day, lang=lang)}
        # a place with no timed column of its own (e.g. Lombo Galego) appears only in the sheets'
        # observations ("Via Lº Galego", "ends at Lombo Galego"): offer those trips, without a time there
        place = to_stop or from_stop
        w2, a2 = ["EXISTS (SELECT 1 FROM unnest(marks) m WHERE m ILIKE '%%' || %s || '%%')"], [place]
        if from_stop and to_stop:
            other = from_stop if place == to_stop else to_stop
            w2.append("(from_stop ILIKE '%%' || %s || '%%' OR to_stop ILIKE '%%' || %s || '%%')")
            a2 += [other, other]
        if dtype:
            w2.append("days = ANY(%s)"); a2.append(list(DAYS_FOR[dtype]))
        obs_rows = _q(f"""SELECT operator, line, new_line, from_stop, to_stop, dep, arr, days, marks, change_at, leg, source_id
                          FROM kb.bus_trip WHERE {' AND '.join(w2)}
                          ORDER BY from_stop, days, dep""", a2)
        if obs_rows:
            seen, uniq = set(), []
            for r in obs_rows:
                k = (r["line"], r["from_stop"], r["dep"], r["days"])
                if k not in seen:
                    seen.add(k); uniq.append(r)
            return {"note": f"No stop named '{place}' has printed times, but these trips serve it per the "
                            f"timetable's observations (no exact time there; book serviço-a-pedido trips by "
                            f"16:00 the previous working day):",
                    "trips": [{"operator": r["operator"], "line": r["line"], "from": r["from_stop"],
                               "to": r["to_stop"], "dep": r["dep"].strftime("%H:%M"),
                               "arr": r["arr"].strftime("%H:%M") if r["arr"] else None, "days": r["days"],
                               "obs": [m for m in r["marks"]][:3]} for r in uniq[:12]],
                    "caveat": "Times as printed on the operators' timetables; intermediate stops are approximate.",
                    "source": [_source(s) for s in sorted({r["source_id"] for r in obs_rows})]}
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
            # one rank, one row: Táxis Funchal and the island-wide "Táxis Madeira" share +351 291 764 476
            if r["id"] not in seen and tuple(r["phone"] or ()) not in seen:
                seen.add(r["id"]); seen.add(tuple(r["phone"] or ()))
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
    res["note"] = ("Give the ranks serving the pick-up place first (call them and the destination's, compare quotes). "
                   "For what the ride costs call taxi_prices; never quote a fare it didn't return.")
    return res


TAXI_ROUTES = os.environ.get("TAXI_ROUTES") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                            "bot", "taxi_routes.json")


def _plain(s):
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFKD", (s or "").lower()) if not unicodedata.combining(ch))


def _share(r, people):
    people = int(people)
    if people > 10:
        return f"{people} people need more than one vehicle: ask when booking"
    eur = r["car_eur"] if people <= 4 or not r.get("van_eur") else r["van_eur"]
    if people > 4 and not r.get("van_eur"):
        return f"{people} people need a van or two cars: ask the price when booking"
    return f"{'car' if people <= 4 else 'van'} €{eur} ÷ {people} = about €{eur / people:.2f} each".replace(".00 each", " each")


def taxi_prices(pickup: str | None = None, destination: str | None = None, people: int | None = None) -> dict:
    """What a taxi costs on the routes a local driver has priced (owner, 2026-10-24): Funchal ↔ Pico do Areeiro,
    Funchal ↔ Ribeiro Frio, the PR1 package (hotel → Pico do Areeiro, collected at Achada do Teixeira at a set time)
    and the Ribeiro Frio → Pico do Areeiro → Achada do Teixeira → Funchal day (Balcões + PR1). Call it whenever the
    visitor asks what a taxi, a ride or a taxi plan costs. Prices are per vehicle and INDICATIVE: car up to 4 people,
    van 5–10 (+20%); the fare is agreed when booking. people = the group size if the visitor gave it (adds the share
    per person). A route without a price → the metered-fare wording."""
    import json
    try:
        cfg = json.load(open(TAXI_ROUTES, encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {"routes": []}
    p, d = _plain(pickup), _plain(destination)

    def hit(keys, text):
        return any(_plain(k) in text for k in keys)
    rows = [r for r in cfg["routes"] if (not p or hit(r["from"], p)) and (not d or hit(r["to"], d))]
    exact = bool(rows) and bool(p or d)
    if not exact:  # no route matched: hand over every priced route and let the model pick the visitor's trip
        rows = [r for r in cfg["routes"] if r.get("car_eur")]
    routes = [{"route": r["label"], "car_up_to_4_eur": r.get("car_eur"),
               **({"van_5_to_10_eur": r["van_eur"]} if r.get("van_eur") else {}),
               **({"note": r["note"]} if r.get("note") else {}),
               "price": "indicative" if r.get("car_eur") else "no price yet: metered, ask for a quote",
               **({"for_your_group": _share(r, people)} if people and r.get("car_eur") else {})} for r in rows]
    res = {"routes": routes, "matched_the_trip": exact,
           "rules": ["Prices are per vehicle, not per person; when the visitor gave the group size, give for_your_group.",
                     "Always say the price is indicative and that the fare is agreed when booking (most are a local driver's prices; a route's note says when it is a hiker's report instead).",
                     "Pick-ups at Achada do Teixeira are done by the Santana taxis; for the numbers call transport.",
                     "Achada do Teixeira → Pico do Areeiro: a shared ride with other hikers usually costs about €15–20 per person."],
           "source": {"name": "Indicative prices: a local taxi driver, and hikers' reports where noted", "url": None}}
    if not exact:
        res["note"] = "No priced route matches this trip exactly: use one of these only if it IS the visitor's trip; otherwise taxis are metered, ask for a quote."
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


FC_WORDS = {  # forecast_tomorrow's text, per language (owner, 2026-10-24: the tool says it, the model quotes it)
    "en": {"head": "Cloud forecast for {spot}, next {h} hours", "days": ["today", "tomorrow", "the day after"],
           "parts": {"morning": "morning (06–10)", "day": "daytime (10–17)"}, "sky": ["clear", "partly cloudy", "cloudy"], "votes": "{n} of {m} models, middle value {p}% cloud", "next": "Next forecast at {t} {when}.",
           "when": ["today", "tomorrow"], "none": "No cloud forecast for {spot} for the next hours."},
    "pt": {"head": "Previsão de nuvens para {spot}, próximas {h} horas", "days": ["hoje", "amanhã", "depois de amanhã"],
           "parts": {"morning": "manhã (06–10)", "day": "dia (10–17)"}, "sky": ["limpo", "parcialmente nublado", "nublado"], "votes": "{n} de {m} modelos, valor central {p}% de nuvens", "next": "Próxima previsão às {t} de {when}.",
           "when": ["hoje", "amanhã"], "none": "Sem previsão de nuvens para {spot} nas próximas horas."},
    "fr": {"head": "Prévision de nuages pour {spot}, {h} prochaines heures", "days": ["aujourd'hui", "demain", "après-demain"],
           "parts": {"morning": "matin (06–10)", "day": "journée (10–17)"}, "sky": ["dégagé", "partiellement nuageux", "nuageux"], "votes": "{n} modèles sur {m}, valeur médiane {p} % de nuages", "next": "Prochaine prévision à {t} {when}.",
           "when": ["aujourd'hui", "demain"], "none": "Pas de prévision de nuages pour {spot} pour les prochaines heures."},
    "de": {"head": "Wolkenprognose für {spot}, nächste {h} Stunden", "days": ["heute", "morgen", "übermorgen"],
           "parts": {"morning": "früh (06–10)", "day": "tagsüber (10–17)"}, "sky": ["klar", "teils bewölkt", "bewölkt"], "votes": "{n} von {m} Modellen, Mittelwert {p} % Wolken", "next": "Nächste Prognose {when} um {t}.",
           "when": ["heute", "morgen"], "none": "Keine Wolkenprognose für {spot} für die nächsten Stunden."},
    "pl": {"head": "Prognoza zachmurzenia dla {spot}, najbliższe {h} godz.", "days": ["dziś", "jutro", "pojutrze"],
           "parts": {"morning": "rano (06–10)", "day": "w dzień (10–17)"}, "sky": ["bezchmurnie", "częściowe zachmurzenie", "pochmurno"], "votes": "{n} z {m} modeli, wartość środkowa {p}% chmur", "next": "Następna prognoza {when} o {t}.",
           "when": ["dziś", "jutro"], "none": "Brak prognozy zachmurzenia dla {spot} na najbliższe godziny."},
}


def forecast_tomorrow(trail: str | None = None, spot: str | None = None, day: str = "tomorrow", lang: str = "en") -> dict:
    """Cloud forecast for a summit spot (Pico do Areeiro, Achada do Teixeira, Rabaçal) for the next hours, from five
    weather models, as ready text: morning (06–10) and daytime (10–17), the sky most models give (clear / partly cloudy / cloudy), how many back it and the middle value,
    plus when the next forecast is made (three a day: 06:07, 12:07, 20:07). Quote the text as it is. Uncalibrated."""
    if trail:
        c = _need_trail(trail)
        reg = _q("SELECT region FROM kb.trail WHERE code = %s", (c,))[0]["region"]
        spot = FORECAST_SPOT.get(c) or FORECAST_SPOT.get(reg)
        if not spot:
            return {"forecast": None, "note": f"No summit forecast for {c}'s area in our data."}
    if spot and spot not in FORECAST_NAMES:  # the model passes names ("Pico do Areeiro", "Rabaçal"), not slugs
        s = _plain(spot)
        spot = ("achada-do-teixeira" if "achada" in s or "ruivo" in s else "rabacal-madeira" if "rabacal" in s
                else "pico-do-arieiro" if "are" in s or "arie" in s else None)
        if not spot:
            return {"forecast": None, "note": "Levadinho's cloud forecast covers only Pico do Areeiro, Achada do Teixeira and Rabaçal."}
    spot = spot or "pico-do-arieiro"
    w = FC_WORDS[_lang(lang)]
    name = FORECAST_NAMES.get(spot, spot)
    now = datetime.datetime.now(MADEIRA).replace(tzinfo=None)
    t = next((f"{hh:02d}:07" for hh in (6, 12, 20) if (now.hour, now.minute) < (hh, 7)), None)  # runs at 06:07, 12:07, 20:07
    nxt = w["next"].format(t=t or "06:07", when=w["when"][0 if t else 1])
    rows = _q("SELECT * FROM kb.forecast WHERE spot = %s ORDER BY run_date DESC LIMIT 1", (spot,))
    if not rows:
        return {"forecast": w["none"].format(spot=name), "next_forecast": nxt, "note": "Quote both lines as they are."}
    h = rows[0]["hourly"]["hourly"]
    times = [datetime.datetime.fromisoformat(t) for t in h["time"]]
    models = sorted({k[len("cloud_cover_"):] for k in h if k.startswith("cloud_cover_") and not k.startswith("cloud_cover_low_")})
    lines, last = [], None
    for d in range(3):
        date = now.date() + datetime.timedelta(days=d)
        for part, (h0, h1) in (("morning", (6, 10)), ("day", (10, 17))):
            ix = [i for i, t in enumerate(times) if t.date() == date and h0 <= t.hour < h1 and t >= now.replace(minute=0)]
            if not ix:
                continue
            means = [round(sum(v[i] for i in ix if v[i] is not None) / n) for m in models
                     for v in [h[f"cloud_cover_{m}"]] for n in [sum(v[i] is not None for i in ix)] if n]
            if not means:
                continue
            # the reading the models agree on most: clear < 30 %, partly cloudy 30–69 %, cloudy ≥ 70 % (owner, 2026-10-24:
            # a 0–92 % range "makes no sense"); then how many of the five back it and the middle (median) value
            cat = [0 if v < 30 else 1 if v < 70 else 2 for v in means]
            best = max(range(3), key=lambda c: (cat.count(c), -abs(c - 1)))
            mid = sorted(means)[len(means) // 2]
            lines.append(f"{w['days'][d]}, {w['parts'][part]}: {w['sky'][best]} "
                         f"({w['votes'].format(n=cat.count(best), m=len(means), p=mid)})")
            last = times[ix[-1]]
    if not lines:
        return {"forecast": w["none"].format(spot=name), "next_forecast": nxt,
                "note": "There is NO forecast for the coming hours: quote both lines as they are and say nothing about "
                        "cloud, sun or clear sky later on (a weather_now reading is about now only). The official Madeira "
                        "forecast is IPMA's (https://www.ipma.pt)."}
    hours = max(1, round((last - now).total_seconds() / 3600) + 1)
    return {"forecast": w["head"].format(spot=name, h=hours) + ": " + "; ".join(lines) + ".", "next_forecast": nxt,
            "note": "Quote forecast and next_forecast as they are, in this order; add nothing. Five weather models, not yet "
                    "calibrated against our webcams: a rough guide, never a promise.",
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
    """Current and upcoming notices (closures, works, events, cruise days) for a trail code, place id or area.
    Cruise rows are the port's schedule, not the visitor's booking: never assume a listed ship is theirs."""
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


WEBCAM_DIR = os.environ.get("WEBCAM_DIR", "/mnt/tank/levadinho_webcams")
CAM_BASE = os.environ.get("CAM_BASE", "https://microscopy-rig-system.tail53cc58.ts.net/levadinho/cam")
WEBCAMS = {  # NetMadeira cameras we grab (seo_research/funchal/webcams/grab.py) and what each one shows (checked 2026-10-03)
    "rabacal": {"folder": "nm_rabacal-madeira", "name": "Rabaçal car park (ER105, Paul da Serra)",
                "shows": "the Rabaçal car park on the ER105 and the road: how full it is, and the cloud",
                "trails": ["PR6", "PR6.1", "PR6.2"], "places": ["rabaçal", "rabacal", "25 fontes", "risco", "paul da serra"],
                "live": "https://www.netmadeira.com/webcams/show/netmadeira/rabacal-madeira"},
    "achada": {"folder": "nm_achada-do-teixeira", "name": "Achada do Teixeira car park",
               "shows": "the Achada do Teixeira car park (start of PR1.2 to Pico Ruivo, where PR1 ends): how full it is, and the cloud",
               "trails": ["PR1.2", "PR1"], "places": ["achada do teixeira", "pico ruivo"],
               "live": "https://www.netmadeira.com/webcams/show/netmadeira/achada-do-teixeira"},
    "areeiro": {"folder": "nm_pico-do-arieiro", "name": "Pico do Areeiro",
                "shows": "the view from Pico do Areeiro over the valley (not the car park): whether the summit is above or in the cloud",
                "trails": ["PR1"], "places": ["pico do areeiro", "pico do arieiro", "areeiro", "arieiro"],
                "live": "https://www.netmadeira.com/webcams/show/netmadeira/pico-do-arieiro"},
}


def latest_frame(cam_id):
    """(path, taken datetime) of the newest grabbed frame of one camera, or (None, None)."""
    folder = os.path.join(WEBCAM_DIR, WEBCAMS[cam_id]["folder"])
    days = sorted((d for d in os.listdir(folder) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)), reverse=True) if os.path.isdir(folder) else []
    for d in days[:2]:
        frames = sorted((f for f in os.listdir(os.path.join(folder, d)) if f.endswith(".jpg")),
                        key=lambda f: os.path.getmtime(os.path.join(folder, d, f)), reverse=True)
        if frames:
            path = os.path.join(folder, d, frames[0])
            return path, datetime.datetime.fromtimestamp(os.path.getmtime(path), MADEIRA)
    return None, None


def webcam(trail: str | None = None, place: str | None = None) -> dict:
    """The latest picture from the webcam at a trailhead or car park (Rabaçal, Achada do Teixeira, Pico do Areeiro):
    use it for 'is the car park full?', 'is there parking now?', 'is it cloudy up there now?'. Returns the picture's
    URL, when it was taken and what the camera shows; no camera for that place → says so."""
    want = []

    def by_place(p):
        p = (p or "").lower()
        return [k for k, c in WEBCAMS.items() if len(p) >= 4 and any(x in p or p in x for x in c["places"])]
    if place:   # the place the visitor named comes first ("Rabaçal car park" asked from another trail's page)
        want = by_place(place)
    if trail and not want:
        code = resolve_trail(trail)
        want = [k for k, c in WEBCAMS.items() if code and code in c["trails"]]
        if not want and code:   # a trail starting or ending at a camera's place
            r = _q("SELECT start_name, end_name FROM kb.trail WHERE code = %s", (code,))
            if r:
                want = by_place(r[0]["start_name"]) or by_place(r[0]["end_name"])
        if not want and not place:
            want = by_place(trail)
    if not want:
        return {"webcams": [], "note": "We have no webcam for that place. Cameras: Rabaçal car park, Achada do Teixeira car park, Pico do Areeiro."}
    now = datetime.datetime.now(MADEIRA)
    out = []
    for k in want[:1]:
        c = WEBCAMS[k]
        path, taken = latest_frame(k)
        item = {"camera": c["name"], "shows": c["shows"], "live_view": c["live"], "source": _source("netmadeira")}
        if path:
            age = int((now - taken).total_seconds() // 60)
            item.update(image_url=f"{CAM_BASE}/{k}.jpg", taken=taken.strftime("%H:%M"), minutes_ago=age,
                        **({"note": "This picture is more than 2 hours old."} if age > 120 else {}))
        else:
            item["note"] = "No recent picture stored; the live view link works."
        out.append(item)
    return {"webcams": out}


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
    # the no-rule topics (owner, 2026-10-22): a trail name in the query outranks the unregulated sheet, so pin it
    if re.search(r"\b(dogs?|pets?|bikes?|bicycle|cycling|cycle|rower|v[ée]lo|fahrrad|hund|pies|chien|c[ãa]o|"
                 r"drones?|camp\w*|zelt\w*|biwak\w*|picnic|piquenique|barbecue|grill)\b", text, re.I):
        pinned = _q("SELECT id, kind, subject, lang, title, url, source_id, body snippet, 1 rank "
                    "FROM kb.doc WHERE id = 'facts:en:scope:unregulated'")
        rows = pinned + [r for r in rows if r["id"] != "facts:en:scope:unregulated"][:limit - 1]
    return {"results": [{"title": r["title"], "subject": r["subject"], "lang": r["lang"], "url": r["url"],
                         "text": re.sub(r"</?b>", "", r["snippet"]), "source": _source(r["source_id"])} for r in rows],
            **({} if rows else {"note": "Nothing found in Levadinho's knowledge for this query."})}


def page_doc(subject: str, lang: str = "en") -> dict:
    """The whole text of one of our pages (kb.doc, section by section) — not a model tool: brain.py gives it to the
    model when the visitor is chatting on that page (owner, 2026-10-24: the page's own answer first)."""
    lang = _lang(lang)
    rows = _q("SELECT title, url, body FROM kb.doc WHERE kind = 'page' AND subject = %s AND lang = %s "
              "ORDER BY split_part(id, ':', 5)::int", (subject, lang))
    rows = [r for r in rows if not re.match(r"(sources|fontes|sources|quellen|źródła)$", (r["title"] or "").strip(), re.I)]
    sections = [{"title": r["title"], "text": r["body"]} for r in rows]
    if rows and subject in ("guide:sunrise", "guide:weather", "guide:oneway", "guide:pedrarija", "guide:parking"):
        # the page's table gives the 1st of each month; the visitor means today (24 Oct: "sunrise today 07:56")
        sr = sunrise_now()
        sections.insert(0, {"title": "TODAY'S SUNRISE at Pico do Areeiro (computed for today and tomorrow, Madeira time; "
                                     "the page's monthly table further down is only for the 1st of each month)",
                         "text": "; ".join(f"{k} ({v['weekday']}): sunrise {v['sunrise']}, from the summit with a "
                                           f"clear east horizon {v['summit_clear_horizon']}; the first SIMplifica slot "
                                           f"after sunrise is {v['first_slot_after_sunrise']}" for k, v in sr.items())
                                 + ". For another month or part of a month (computed the same way): "
                                 + "; ".join(f"{datetime.date(2026, m, 1):%B} 1st {areeiro_sunrise(datetime.date(_y(m), m, 1)):%H:%M}, "
                                             f"15th {areeiro_sunrise(datetime.date(_y(m), m, 15)):%H:%M}" for m in range(1, 13))
                                 + ". "
                                   "To watch the sunrise from the viewpoint before you start, book the first SIMplifica "
                                   "slot after sunrise (above); an earlier slot means walking the ridge in the dark."})
    return {"page": rows[0]["url"] if rows else None, "sections": sections}


TOOLS = [trail_status, trail_facts, find_trails, fees_and_rules, bus, transport, weather_now, forecast_tomorrow,
         closures, places, place, notices, webcam, search]


PLAN_TEXT = {  # day_plan's text, per language (owner, 2026-10-24); {…} filled from the bus timetables
    "portela_back": {
        "en": ["Check the bus times at the Portela stop.",
               "Otherwise call Táxis Machico (+351 291 962 189 / +351 291 962 480): a taxi down to Machico costs about €15, then the bus from Machico to Funchal: {mach}.",
               "A taxi all the way to Funchal is about €50.", "Prices are indicative."],
        "pt": ["Verifique os horários do autocarro na paragem da Portela.",
               "Caso contrário, ligue para os Táxis Machico (+351 291 962 189 / +351 291 962 480): um táxi até Machico custa cerca de 15 €, e depois o autocarro de Machico para o Funchal: {mach}.",
               "Um táxi direto até ao Funchal custa cerca de 50 €.", "Os preços são indicativos."],
        "fr": ["Vérifiez les horaires de bus à l'arrêt de Portela.",
               "Sinon, appelez Táxis Machico (+351 291 962 189 / +351 291 962 480) : un taxi jusqu'à Machico coûte environ 15 €, puis le bus de Machico à Funchal : {mach}.",
               "Un taxi jusqu'à Funchal coûte environ 50 €.", "Les prix sont indicatifs."],
        "de": ["Prüfen Sie die Busfahrzeiten an der Haltestelle Portela.",
               "Sonst rufen Sie Táxis Machico an (+351 291 962 189 / +351 291 962 480): Ein Taxi hinunter nach Machico kostet etwa 15 €, dann der Bus von Machico nach Funchal: {mach}.",
               "Ein Taxi direkt nach Funchal kostet etwa 50 €.", "Die Preise sind Richtwerte."],
        "pl": ["Sprawdź rozkład autobusów na przystanku Portela.",
               "W przeciwnym razie zadzwoń do Táxis Machico (+351 291 962 189 / +351 291 962 480): taksówka w dół do Machico kosztuje około 15 €, potem autobus z Machico do Funchal: {mach}.",
               "Taksówka prosto do Funchal kosztuje około 50 €.", "Ceny są orientacyjne."]},
    "pr11_pr10": {
        "en": ["Take the {dep} bus from Funchal, Almirante Reis bay 7, to Ribeiro Frio (line {line}, arriving {arr}; €2.65 on the bus).",
               "Walk PR11 Balcões there and back (3 km, about 1 h 30) and have a hot drink in Ribeiro Frio on your way back.",
               "Start PR10 Levada do Furado towards Portela at around 9–10 (11 km, about 4 h).",
               "Before you set off, book Táxis Machico (+351 291 962 189 / +351 291 962 480) to pick you up at the Portela viewpoint and take you down to Machico (about €15).",
               "From Machico, the bus to Funchal: {mach}.", "Book both trails on SIMplifica. Prices are indicative."],
        "pt": ["Apanhe o autocarro das {dep} no Funchal, Almirante Reis, doca 7, para o Ribeiro Frio (linha {line}, chega às {arr}; 2,65 € pagos no autocarro).",
               "Faça a PR11 Vereda dos Balcões, ida e volta (3 km, cerca de 1 h 30), e tome uma bebida quente no Ribeiro Frio no regresso.",
               "Comece a PR10 Levada do Furado em direção à Portela por volta das 9–10 h (11 km, cerca de 4 h).",
               "Antes de sair, reserve os Táxis Machico (+351 291 962 189 / +351 291 962 480) para o irem buscar ao miradouro da Portela e o levarem até Machico (cerca de 15 €).",
               "De Machico, o autocarro para o Funchal: {mach}.", "Reserve os dois percursos no SIMplifica. Os preços são indicativos."],
        "fr": ["Prenez le bus de {dep} à Funchal, Almirante Reis quai 7, pour Ribeiro Frio (ligne {line}, arrivée {arr} ; 2,65 € dans le bus).",
               "Faites le PR11 Balcões aller-retour (3 km, environ 1 h 30) et prenez une boisson chaude à Ribeiro Frio au retour.",
               "Partez sur le PR10 Levada do Furado vers Portela vers 9–10 h (11 km, environ 4 h).",
               "Avant de partir, réservez Táxis Machico (+351 291 962 189 / +351 291 962 480) pour venir vous chercher au belvédère de Portela et vous descendre à Machico (environ 15 €).",
               "De Machico, le bus pour Funchal : {mach}.", "Réservez les deux sentiers sur SIMplifica. Les prix sont indicatifs."],
        "de": ["Nehmen Sie den Bus um {dep} in Funchal, Almirante Reis Bucht 7, nach Ribeiro Frio (Linie {line}, Ankunft {arr}; 2,65 € im Bus).",
               "Gehen Sie PR11 Balcões hin und zurück (3 km, etwa 1 h 30) und trinken Sie auf dem Rückweg in Ribeiro Frio etwas Heißes.",
               "Starten Sie PR10 Levada do Furado gegen 9–10 Uhr Richtung Portela (11 km, etwa 4 h).",
               "Buchen Sie vor dem Start Táxis Machico (+351 291 962 189 / +351 291 962 480), das Sie am Aussichtspunkt Portela abholt und nach Machico bringt (etwa 15 €).",
               "Ab Machico der Bus nach Funchal: {mach}.", "Buchen Sie beide Wege auf SIMplifica. Die Preise sind Richtwerte."],
        "pl": ["Jedź autobusem o {dep} z Funchal, Almirante Reis stanowisko 7, do Ribeiro Frio (linia {line}, przyjazd {arr}; 2,65 € w autobusie).",
               "Przejdź PR11 Balcões tam i z powrotem (3 km, ok. 1 h 30) i w drodze powrotnej napij się czegoś ciepłego w Ribeiro Frio.",
               "Ruszaj na PR10 Levada do Furado w stronę Portela około 9–10 (11 km, ok. 4 h).",
               "Przed wyjściem zarezerwuj Táxis Machico (+351 291 962 189 / +351 291 962 480), żeby odebrali cię z punktu widokowego Portela i zawieźli do Machico (ok. 15 €).",
               "Z Machico autobus do Funchal: {mach}.", "Zarezerwuj oba szlaki w SIMplifica. Ceny są orientacyjne."]},
}


def day_plan(plan: str, day: str | None = None, lang: str = "en") -> dict:
    """A ready-made answer to quote word for word, with that day's bus times filled in (owner's plans).
    plan: portela_back = getting back to Funchal from Portela (end of PR10 Levada do Furado, start of PR5);
    pr11_pr10 = Balcões (PR11) and Levada do Furado (PR10) on the same day without a car.
    day: the day the visitor means (today, tomorrow, a weekday, sat, sun_hol…); today if not given."""
    if plan not in PLAN_TEXT:
        return {"error": f"plan must be one of {sorted(PLAN_TEXT)}"}
    day = day or "today"
    lines = PLAN_TEXT[plan][_lang(lang)]
    mach = sorted({t["dep"] for t in bus(from_stop="Machico", to_stop="Funchal", day=day)["trips"] if t["dep"] >= "13:00"})
    fill = {"mach": ", ".join(mach) or "—"}
    if plan == "pr11_pr10":
        up = sorted(bus(from_stop="Funchal", to_stop="Ribeiro Frio", day=day)["trips"], key=lambda t: t["dep"])
        if not up:
            return {"error": "no bus from Funchal to Ribeiro Frio that day in our data"}
        fill.update(dep=up[0]["dep"], arr=up[0]["arr"] or "?", line=up[0]["line"])
    text = "\n".join((f"{n}) " if plan == "pr11_pr10" and n <= 5 or plan == "portela_back" and n <= 3 else "") + s.format(**fill)
                     for n, s in enumerate(lines, 1))
    return {"text": text, "note": "Reply with this text exactly as it is, nothing before or after it.",
            "source": {"name": "Bus timetables (SIGA / Horários do Funchal); Táxis Machico from IFCN's PR10 and PR5 panels; "
                               "the taxi prices are a hiker's report", "url": None}}
