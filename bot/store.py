"""Tiny SQLite store: each visitor's language/state, their recent conversation, and messages waiting
for the model while it wakes up (wake-on-demand, see llm_control.py)."""
import json
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
-- wake-on-demand (llm_control.py): messages waiting for the model, each visitor's last incoming message
-- (WhatsApp's 24-hour customer-service window), and small flags
CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, at REAL, reason TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS last_inbound (user TEXT PRIMARY KEY, at REAL);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
""")
# consent: the privacy notice — None (not answered), "yes" (accepted) or "no" (declined: no service).
# (consent_asked is a leftover column from the first consent design; unused.)
for col in ("consent TEXT", "consent_asked REAL"):
    try:
        _db.execute(f"ALTER TABLE users ADD COLUMN {col}")
    except sqlite3.OperationalError:
        pass  # already there
GUIDE_TOKEN_TTL = 30 * 24 * 3600  # a guide link keeps working for a month (offline packs, repeat walks)
USER_FIELDS = ("lang", "state", "consent")


def get_user(uid):
    row = _db.execute(f"SELECT {', '.join(USER_FIELDS)} FROM users WHERE id=?", (uid,)).fetchone()
    return dict(zip(USER_FIELDS, row)) if row else None


def set_user(uid, **fields):
    cur = get_user(uid) or dict.fromkeys(USER_FIELDS)
    cur.update(fields)
    _db.execute(f"INSERT OR REPLACE INTO users (id, {', '.join(USER_FIELDS)}, updated) VALUES (?,?,?,?,?)",
                (uid, *(cur[f] for f in USER_FIELDS), time.time()))
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


def guide_token_user(token):
    row = _db.execute("SELECT user FROM guide_tokens WHERE token=?", (token or "",)).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------- wake-on-demand queue
def note_inbound(uid):
    """The visitor just wrote to us: WhatsApp's 24-hour window for our replies starts again."""
    _db.execute("INSERT OR REPLACE INTO last_inbound VALUES (?,?)", (uid, time.time()))
    _db.commit()


def last_inbound(uid):
    row = _db.execute("SELECT at FROM last_inbound WHERE user=?", (uid,)).fetchone()
    return row[0] if row else None


def queue_pending(uid, reason, payload):
    """A message that waits for the model. reason: "wake" (model loading) or "busy" (GPU in use:
    a callback once it frees). payload: JSON-able dict (the WhatsApp message and how to record it)."""
    _db.execute("INSERT INTO pending (user, at, reason, payload) VALUES (?,?,?,?)",
                (uid, time.time(), reason, json.dumps(payload, ensure_ascii=False)))
    _db.commit()


def has_pending(uid=None):
    q, p = ("SELECT 1 FROM pending WHERE user=? LIMIT 1", (uid,)) if uid else ("SELECT 1 FROM pending LIMIT 1", ())
    return _db.execute(q, p).fetchone() is not None


def pending_all():
    """Oldest first → [{"id", "user", "at", "reason", "payload"}]."""
    rows = _db.execute("SELECT id, user, at, reason, payload FROM pending ORDER BY id").fetchall()
    return [{"id": i, "user": u, "at": at, "reason": r, "payload": json.loads(p)} for i, u, at, r, p in rows]


def drop_pending(pid):
    _db.execute("DELETE FROM pending WHERE id=?", (pid,))
    _db.commit()


def get_flag(k):
    row = _db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return row[0] if row else None


def set_flag(k, v):
    if v is None:
        _db.execute("DELETE FROM kv WHERE k=?", (k,))
    else:
        _db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (k, v))
    _db.commit()


def reset(uid):
    for table, col in (("users", "id"), ("turns", "user"), ("pending", "user"), ("last_inbound", "user")):
        _db.execute(f"DELETE FROM {table} WHERE {col}=?", (uid,))
    _db.commit()


def erase(uid):
    """Everything held about a phone number here (erasure request). Returns rows deleted per table."""
    n = {}
    for table, col in (("users", "id"), ("turns", "user"), ("guide_tokens", "user"), ("pending", "user"),
                       ("last_inbound", "user")):
        n[table] = _db.execute(f"DELETE FROM {table} WHERE {col}=?", (uid,)).rowcount
    _db.commit()
    return n
