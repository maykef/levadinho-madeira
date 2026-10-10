"""Access and erasure requests (GDPR Art. 15 and 17) for one WhatsApp number.

Nothing in the analytics database holds a phone number: the visitor's rows are found by
recomputing visitor_id = HMAC(bot/.visitor_key, phone). So a request needs the number the
person used, with the country code.

  python bot/privacy_request.py access +351912345678   # writes a JSON export of everything held
  python bot/privacy_request.py erase  +351912345678   # shows the counts, asks, then deletes

Erase removes: the analytics rows (event, conversation_turn, location_fix, visitor), the
working store (language, consent, last 24 h of chat, guide links, messages queued while the model
was asleep and the time of the last incoming message: store.erase) and the raw guide log files
of that person's guide links (tracklog/). Anonymous rows (no visitor id) cannot be linked to
anyone and are not touched. The nightly database backups roll off after 30 days
(db/backup.sh), which is how the erasure reaches them; the policy promises 30 days.
Runbook: db/PRIVACY_REQUESTS.md.
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
for line in open(os.path.join(HERE, ".env")):
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v)

import psycopg  # noqa: E402

import analytics  # noqa: E402
import store  # noqa: E402

TABLES = ("event", "conversation_turn", "location_fix")  # deleted before visitor (foreign keys)


def rows(cur, sql, params):
    cur.execute(sql, params)
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def tokens_for(phone):
    return [t for (t,) in store._db.execute("SELECT token FROM guide_tokens WHERE user=?", (phone,))]


def tracklog_files(phone):
    base = os.path.join(HERE, "tracklog")
    toks = set(tokens_for(phone))
    return [os.path.join(base, r, f) for r in (os.listdir(base) if os.path.isdir(base) else [])
            for f in os.listdir(os.path.join(base, r)) if f.removesuffix(".jsonl") in toks]


def working_store(phone):
    """What the working store (store.py, SQLite) holds about this number."""
    last = store.last_inbound(phone)
    return {"user": store.get_user(phone), "recent_chat": store.history(phone),
            "guide_links": len(tokens_for(phone)),
            # wake-on-demand: messages waiting for the model, and WhatsApp's 24-hour window
            "queued_messages": [{"at": datetime.fromtimestamp(r["at"], timezone.utc).isoformat(),
                                 "reason": r["reason"], "message": r["payload"].get("message"),
                                 "notice_sent": (r["payload"].get("notice") or {}).get("body")}
                                for r in store.pending_for(phone)],
            "last_incoming_message_at": datetime.fromtimestamp(last, timezone.utc).isoformat() if last else None}


def access(phone, vid):
    with psycopg.connect(os.environ["DB_URL"]) as c, c.cursor() as cur:
        data = {"visitor": rows(cur, "SELECT * FROM visitor WHERE visitor_id=%s", (vid,)),
                "conversation": rows(cur, "SELECT occurred_at, direction, msg_kind, text_scrubbed, lang, intent, topic "
                                          "FROM conversation_turn WHERE visitor_id=%s ORDER BY occurred_at", (vid,)),
                "events": rows(cur, "SELECT occurred_at, channel, event_type, route_id, stop_id, lang, "
                                    "ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lon, attributes "
                                    "FROM event WHERE visitor_id=%s ORDER BY occurred_at", (vid,)),
                "locations": rows(cur, "SELECT occurred_at, source, ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lon, "
                                       "accuracy_m, altitude_m, speed_ms, heading_deg FROM location_fix "
                                       "WHERE visitor_id=%s ORDER BY occurred_at", (vid,))}
    data["working_store"] = working_store(phone)
    out = os.path.join(HERE, "privacy_exports", f"access-{vid[:8]}-{datetime.now(timezone.utc):%Y%m%d}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, default=str)
    print(f"{len(data['conversation'])} messages, {len(data['events'])} events, {len(data['locations'])} positions")
    print(f"Export: {out}  (send it to the person, then delete it; privacy_exports/ is git-ignored)")


def erase(phone, vid):
    files = tracklog_files(phone)
    with psycopg.connect(os.environ["DB_URL"]) as c, c.cursor() as cur:
        counts = {t: cur.execute(f"SELECT count(*) FROM {t} WHERE visitor_id=%s", (vid,)).fetchone()[0] for t in TABLES}
        counts["visitor"] = cur.execute("SELECT count(*) FROM visitor WHERE visitor_id=%s", (vid,)).fetchone()[0]
        ws = working_store(phone)
        print(f"visitor {vid}: {counts}; working store: {ws['user']}, {len(ws['queued_messages'])} queued "
              f"message(s), last incoming {ws['last_incoming_message_at']}; guide log files: {len(files)}")
        if input("Delete all of this? Type yes: ").strip() != "yes":
            print("Nothing deleted.")
            return
        for t in TABLES + ("visitor",):
            cur.execute(f"DELETE FROM {t} WHERE visitor_id=%s", (vid,))
    for f in files:
        os.remove(f)
    print("Deleted. Working store:", store.erase(phone))
    print("Reply to the person that it's done. Backups roll off within 30 days.")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("access", "erase"):
        sys.exit(__doc__)
    phone = sys.argv[2] if sys.argv[2].startswith("web:") else "".join(ch for ch in sys.argv[2] if ch.isdigit())  # Meta sends digits only; the chat on our pages is web:<code>
    vid = analytics.visitor_id_for(phone)
    if not vid:
        sys.exit("bot/.visitor_key is missing: without it no visitor can be found.")
    {"access": access, "erase": erase}[sys.argv[1]](phone, vid)
