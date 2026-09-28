"""Analytics store: every interaction, kept pseudonymously in Postgres (levadinho-db).

The bot's operational store (store.py, SQLite) holds phone numbers for 24 h so it can reply.
This module is the permanent record, and it never stores a phone number or an IP address:
  - visitor_id = HMAC-SHA256(secret key, phone); the key lives in bot/.visitor_key, apart
    from the data. The same visitor gets the same id every day; for an access/erasure
    request, recompute it from the phone number (visitor_id_for).
  - conversation text is scrubbed: patterns first (phones, emails, links, codes), then the
    local model replaces people's names, in a background thread so replies aren't delayed.
Fail-soft: if the database is down, the bot keeps working and the event is skipped (logged).

  python bot/analytics.py init       # apply db/schema.sql, sync routes/stops/campaigns
  python bot/analytics.py backfill   # import guide test logs from bot/tracklog/
"""
import hashlib
import hmac
import json
import logging
import os
import queue
import re
import threading
import time
import urllib.request
from datetime import datetime, timezone

import phonenumbers
import psycopg
from psycopg.types.json import Jsonb

import geo

HERE = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger("levadinho.analytics")
DB_URL = os.environ.get("DB_URL", "")
LLM_URL = os.environ.get("LLM_URL", "http://127.0.0.1:8001/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "levadinho")
_KEY = open(os.path.join(HERE, ".visitor_key")).read().strip().encode() if os.path.exists(os.path.join(HERE, ".visitor_key")) else None

_lock = threading.Lock()
_conn = None


def _db():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DB_URL, autocommit=True, connect_timeout=3)
    return _conn


def _exec(sql, params=(), fetch=False):
    """Run one statement; never raise into the bot."""
    if not DB_URL:
        return None
    try:
        with _lock:
            cur = _db().execute(sql, params)
            return cur.fetchall() if fetch else None
    except Exception:
        log.exception("analytics write failed")
        global _conn
        _conn = None
        return None


# ---------------------------------------------------------------- identity
def visitor_id_for(phone):
    """Pseudonymous, stable id for a WhatsApp number (digits only, as Meta sends it)."""
    if not _KEY or not phone:
        return None
    return hmac.new(_KEY, re.sub(r"\D", "", phone).encode(), hashlib.sha256).hexdigest()[:32]


def country_for(phone):
    try:
        return phonenumbers.region_code_for_number(phonenumbers.parse("+" + re.sub(r"\D", "", phone)))
    except Exception:
        return None


def touch_visitor(phone, lang=None):
    vid = visitor_id_for(phone)
    if vid:
        _exec("""INSERT INTO visitor (visitor_id, country, lang) VALUES (%s, %s, %s)
                 ON CONFLICT (visitor_id) DO UPDATE SET last_seen = now(),
                   lang = COALESCE(EXCLUDED.lang, visitor.lang)""", (vid, country_for(phone), lang))
    return vid


def visitor_known(phone):
    vid = visitor_id_for(phone)
    return bool(vid and _exec("SELECT 1 FROM visitor WHERE visitor_id=%s", (vid,), fetch=True))


def set_consent(vid, status, version):
    """Proof of consent (GDPR Art. 7(1)): what the visitor agreed to, and when."""
    if vid:
        _exec("UPDATE visitor SET consent=%s, consent_version=%s, consent_at=now() WHERE visitor_id=%s",
              (status, version, vid))


def _point(lat, lon):
    return f"SRID=4326;POINT({float(lon)} {float(lat)})" if lat is not None and lon is not None else None


def _ts(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc) if ms else datetime.now(timezone.utc)


# ---------------------------------------------------------------- writes
def event(channel, event_type, phone=None, vid=None, occurred=None, session=None, route=None, stop=None,
          campaign=None, lang=None, lat=None, lon=None, **attrs):
    vid = vid or visitor_id_for(phone)
    _exec("""INSERT INTO event (occurred_at, channel, event_type, visitor_id, session_id, route_id, stop_id,
                                campaign_id, lang, country, geom, attributes)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,(SELECT country FROM visitor WHERE visitor_id=%s),%s,%s)""",
          (occurred or datetime.now(timezone.utc), channel, event_type, vid, session, route, stop, campaign, lang,
           vid, _point(lat, lon), Jsonb(attrs)))


def fix(source, lat, lon, phone=None, vid=None, occurred=None, session=None, route=None, acc=None, alt=None,
        alt_acc=None, speed=None, heading=None, screen=None, online=None):
    vid = vid or visitor_id_for(phone)
    _exec("""INSERT INTO location_fix (occurred_at, visitor_id, session_id, route_id, source, geom, accuracy_m,
                                       altitude_m, altitude_accuracy_m, speed_ms, heading_deg, screen, online)
             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (occurred or datetime.now(timezone.utc), vid, session, route, source, _point(lat, lon), acc, alt, alt_acc,
           speed, heading, screen, online))


# ---------------------------------------------------------------- conversation turns + scrubbing
_PATTERNS = [
    (re.compile(r"https?://\S+|www\.\S+", re.I), "[LINK]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    # 9+ digits: phone numbers, not dates (2026-10-19 has 8) or prices
    (re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)"),
     lambda m: "[PHONE]" if len(re.sub(r"\D", "", m.group())) >= 9 else m.group()),
    (re.compile(r"\b(?=[A-Z0-9-]*\d)(?=[A-Z0-9-]*[A-Z])[A-Z0-9-]{6,}\b"), "[CODE]"),  # booking / ticket references
]


def scrub_rules(text):
    for rx, tag in _PATTERNS:
        text = rx.sub(tag, text)
    return text


SCRUB_PROMPT = (
    "You anonymise messages sent to a hiking assistant. Replace every PERSON's name with [NAME] and any other detail "
    "that identifies a private person (home or hotel address, room number, ID or passport number, licence plate) "
    "with [PRIVATE]. Do NOT change place names (trails, peaks, towns, hotels as places), dates, times, prices or "
    "anything else. 'Levadinho' is the assistant's own name, not a person: keep it. Keep existing tags like [PHONE]. "
    "Output only the rewritten message, nothing else.")


def scrub_llm(text):
    body = {"model": LLM_MODEL, "temperature": 0, "max_tokens": max(64, len(text) // 2 + 64),
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": SCRUB_PROMPT}, {"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)["choices"][0]["message"]["content"].strip()
    # guard: the model must not invent or drop much; otherwise keep the rules-only version
    return out if 0.5 * len(text) <= len(out) <= 1.5 * len(text) + 20 else None


_scrub_q = queue.Queue()


def _scrub_worker():
    while True:
        turn_id, text = _scrub_q.get()
        try:
            clean = scrub_llm(text)
            if clean is not None:
                _exec("UPDATE conversation_turn SET text_scrubbed=%s, scrub_method='rules+llm' WHERE turn_id=%s",
                      (clean, turn_id))
        except Exception:
            log.warning("LLM scrub failed for turn %s; rules-only text kept", turn_id)


threading.Thread(target=_scrub_worker, daemon=True).start()


def turn(phone, direction, kind, text=None, lang=None, is_question=None, intent=None, topic=None, trail=None,
         campaign=None, latency_ms=None, model=None, llm_scrub=True):
    vid = visitor_id_for(phone)
    clean = scrub_rules(text) if text else None
    rows = _exec("""INSERT INTO conversation_turn (visitor_id, direction, msg_kind, text_scrubbed, scrub_method, lang,
                      is_question, intent, topic, trail_code, campaign_id, latency_ms, model)
                    VALUES (%s,%s,%s,%s,'rules',%s,%s,%s,%s,%s,%s,%s,%s) RETURNING turn_id""",
                 (vid, direction, kind, clean, lang, is_question, intent, topic, trail, campaign, latency_ms, model),
                 fetch=True)
    if rows and clean and llm_scrub and re.search(r"[A-Za-zÀ-ž]{2}", clean):
        _scrub_q.put((rows[0][0], clean))


# ---------------------------------------------------------------- guide log → database
GUIDE_EVENTS = {
    "start": "guide_started", "stop_fired": "stop_fired", "stop_fired_dr": "stop_fired_estimate",
    "stop_missed": "stop_missed", "clip_play": "clip_played", "clip_end": "clip_ended", "clip_fail": "clip_failed",
    "manual_play": "clip_manual", "pocket_on": "pocket_mode", "pocket_off": "pocket_mode", "vis": "screen_state",
    "wake_on": "wake_lock", "wake_off": "wake_lock", "wake_fail": "wake_lock", "offline_ok": "offline_pack",
    "offline_fail": "offline_pack", "gps_err": "gps_error", "poll_err": "gps_error", "hb": "heartbeat",
    "consent": "consent_given",
}


def guide_events(phone, token, route, events):
    """The guide page's batch (see guide.js log()) → location_fix rows and event rows."""
    vid = touch_visitor(phone) if phone else None
    for e in events:
        ev, t = e.get("ev"), e.get("t")
        when = _ts(t)
        if ev in ("fix", "poll_fix"):
            if e.get("lat") is None:
                continue
            fix("guide_gps" if ev == "fix" else "guide_poll", e["lat"], e["lon"], vid=vid, occurred=when,
                session=token, route=route, acc=e.get("acc"), alt=e.get("alt"), alt_acc=e.get("altAcc"),
                speed=e.get("speed"), heading=e.get("heading"), screen=e.get("vis"), online=e.get("online"))
            continue
        etype = GUIDE_EVENTS.get(ev, "guide_other")
        attrs = {k: v for k, v in e.items() if k not in ("ev", "t", "id", "srv", "lang")}
        attrs["ev"] = ev
        if ev in ("pocket_on", "pocket_off"):
            attrs["on"] = ev == "pocket_on"
        elif ev in ("wake_on", "wake_off", "wake_fail"):
            attrs["state"] = ev.split("_")[1]
        elif ev == "vis":
            attrs["state"] = e.get("vis")
        elif ev in ("offline_ok", "offline_fail"):
            attrs["ok"] = ev == "offline_ok"
        elif ev == "poll_err":
            attrs["poll"] = True
        event("guide", etype, vid=vid, occurred=when, session=token, route=route, stop=e.get("id"),
              lang=e.get("lang"), **attrs)


# ---------------------------------------------------------------- lookups
def sync_routes(campaigns=None):
    for r in geo.load_routes():
        line = "SRID=4326;LINESTRING(" + ",".join(f"{lon} {lat}" for lat, lon in r["line"]) + ")"
        _exec("""INSERT INTO route (route_id, title, is_private, length_m, line, updated_at)
                 VALUES (%s,%s,%s,%s,%s,now())
                 ON CONFLICT (route_id) DO UPDATE SET title=EXCLUDED.title, is_private=EXCLUDED.is_private,
                   length_m=EXCLUDED.length_m, line=EXCLUDED.line, updated_at=now()""",
              (r["id"], Jsonb(r["title"]), r["private"], r.get("length_m"), line))
        for s in r["stops"]:
            _exec("""INSERT INTO stop (route_id, stop_id, seq, name, at_m, radius_m, geom) VALUES (%s,%s,%s,%s,%s,%s,%s)
                     ON CONFLICT (route_id, stop_id) DO UPDATE SET seq=EXCLUDED.seq, name=EXCLUDED.name,
                       at_m=EXCLUDED.at_m, radius_m=EXCLUDED.radius_m, geom=EXCLUDED.geom""",
                  (r["id"], s["id"], s["n"], Jsonb(s["name"]), s["at_m"], s["radius"], _point(s["lat"], s["lon"])))
    for tag, rid in (campaigns or {}).items():
        _exec("""INSERT INTO campaign (campaign_id, route_id) VALUES (%s,%s)
                 ON CONFLICT (campaign_id) DO UPDATE SET route_id=EXCLUDED.route_id""", (tag, rid))


def init():
    with open(os.path.join(HERE, "db", "schema.sql"), encoding="utf-8") as f:
        sql = f.read()
    with psycopg.connect(DB_URL, autocommit=True) as c:
        c.execute(sql)
    import brain  # campaigns live with the bot's flow
    sync_routes(brain.CAMPAIGNS)


def backfill():
    """Import the guide test logs (bot/tracklog/<route>/<token>.jsonl) once."""
    import store
    base = os.path.join(HERE, "tracklog")
    for route in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        for fn in sorted(os.listdir(os.path.join(base, route))):
            token = fn.removesuffix(".jsonl")
            if _exec("SELECT 1 FROM event WHERE session_id=%s LIMIT 1", (token,), fetch=True) or \
               _exec("SELECT 1 FROM location_fix WHERE session_id=%s LIMIT 1", (token,), fetch=True):
                continue
            phone = store.guide_token_user(token)
            if not phone or phone.startswith("test-") or not phone.isdigit():
                continue  # desk tests
            events = [json.loads(l) for l in open(os.path.join(base, route, fn), encoding="utf-8")]
            guide_events(phone, token, route, events)
            print(f"{route}/{token}: {len(events)} events")


if __name__ == "__main__":
    import sys
    env = os.path.join(HERE, ".env")
    for line in open(env):
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)
    DB_URL = os.environ["DB_URL"]
    logging.basicConfig(level=logging.INFO)
    {"init": init, "backfill": backfill}[sys.argv[1]]()
    time.sleep(0.2)
