"""Tiny SQLite store: each visitor's language/state and their recent conversation."""
import os
import sqlite3
import time

DB = os.environ.get("LEVADINHO_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "levadinho.db"))
HISTORY_TURNS = 8          # previous exchanges sent back to the model
HISTORY_TTL = 24 * 3600    # forget a conversation after a day of silence

_db = sqlite3.connect(DB, check_same_thread=False)
_db.executescript("""
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, lang TEXT, state TEXT, updated REAL);
CREATE TABLE IF NOT EXISTS turns (user TEXT, at REAL, question TEXT, answer TEXT);
CREATE TABLE IF NOT EXISTS seen (msg_id TEXT PRIMARY KEY, at REAL);
CREATE TABLE IF NOT EXISTS guide_tokens (token TEXT PRIMARY KEY, user TEXT, route TEXT, at REAL);
""")
GUIDE_TOKEN_TTL = 30 * 24 * 3600  # a guide link keeps working for a month (offline packs, repeat walks)


def get_user(uid):
    row = _db.execute("SELECT lang, state FROM users WHERE id=?", (uid,)).fetchone()
    return {"lang": row[0], "state": row[1]} if row else None


def set_user(uid, **fields):
    cur = get_user(uid) or {"lang": None, "state": None}
    cur.update(fields)
    _db.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?)", (uid, cur["lang"], cur["state"], time.time()))
    _db.commit()


def history(uid):
    rows = _db.execute("SELECT question, answer FROM turns WHERE user=? AND at>? ORDER BY at DESC LIMIT ?",
                       (uid, time.time() - HISTORY_TTL, HISTORY_TURNS)).fetchall()
    msgs = []
    for q, a in reversed(rows):
        msgs += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
    return msgs


def add_turn(uid, question, answer):
    _db.execute("INSERT INTO turns VALUES (?,?,?,?)", (uid, time.time(), question, answer))
    # The privacy policy promises conversations are kept 24 h — delete, don't just ignore.
    _db.execute("DELETE FROM turns WHERE at<?", (time.time() - HISTORY_TTL,))
    _db.commit()


def first_time(msg_id):
    """True the first time we see a WhatsApp message id (Meta retries deliveries)."""
    try:
        _db.execute("INSERT INTO seen VALUES (?,?)", (msg_id, time.time()))
        _db.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def new_guide_token(uid, route):
    """A random token for a visitor's guide link. Nothing in it derives from the phone number."""
    import secrets
    token = secrets.token_urlsafe(12)
    _db.execute("INSERT INTO guide_tokens VALUES (?,?,?,?)", (token, uid, route, time.time()))
    _db.commit()
    return token


def guide_token_ok(token, route):
    row = _db.execute("SELECT at FROM guide_tokens WHERE token=? AND route=?", (token or "", route)).fetchone()
    return bool(row) and time.time() - row[0] < GUIDE_TOKEN_TTL


def reset(uid):
    _db.execute("DELETE FROM users WHERE id=?", (uid,))
    _db.execute("DELETE FROM turns WHERE user=?", (uid,))
    _db.commit()
