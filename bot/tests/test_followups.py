"""Offline tests for the wake-on-demand follow-ups: privacy export/erase of the queue, the local chat with
the model down, the analytics scrub sweep and web-* campaigns, the facts file, and IFCN wording in brain.
No model, no Docker, no WhatsApp, no Postgres (psycopg and analytics._exec are fakes); the SQLite store
is a scratch file.

  python bot/tests/test_followups.py
"""
import json
import os
import queue
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BOT = os.path.dirname(HERE)
sys.path.insert(0, BOT)
SCRATCH = tempfile.mkdtemp()
os.environ["LEVADINHO_DB"] = os.path.join(SCRATCH, "test.db")
os.environ["DB_URL"] = ""                                         # nothing reaches the live Postgres
os.environ["LLM_URL"] = "http://127.0.0.1:9/v1/chat/completions"  # nothing listens there
os.environ["LLM_ON_DEMAND"] = "1"
os.environ["SCRUB_SWEEP_S"] = os.environ["SCRUB_RETRY_S"] = "3600"  # keep the background worker idle
for k in ("WA_TOKEN", "WA_PHONE_NUMBER_ID", "WA_APP_SECRET", "WA_VERIFY_TOKEN"):
    os.environ[k] = "test"

import llm_control  # noqa: E402

model = {"up": False}
llm_control.is_up = lambda timeout=2.0: model["up"]

import analytics  # noqa: E402
import brain  # noqa: E402
import chat  # noqa: E402
import privacy_request as pr  # noqa: E402
import store  # noqa: E402

assert store.DB.startswith(SCRATCH), "store must be the scratch database"
STATUS = {
    "status": "PARTIAL", "date": "2026-09-30", "manual_note": "",
    "note": {"pt": "Transitável: Areeiro–Pedra Rija.", "en": "Open: Areeiro–Pedra Rija."},
    "weather": {"ok": True, "temp_c": 14.2, "humidity": 100, "in_cloud": True, "wind_kmh": 10},
    "source": {"name": "IFCN", "url": "https://ifcn.madeira.gov.pt/…", "updated": "14/09/2026"},
    "trails": [{"code": "PR1.2", "name": "Vereda do Pico Ruivo", "status": "OPEN", "note": {"pt": "Aberto só de manhã."}},
               {"code": "PR11", "name": "Vereda dos Balcões", "status": "OPEN",
                "note": {"pt": "Condicionado.", "en": "Restricted."}},
               {"code": "PR9", "name": "Levada do Caldeirão Verde", "status": "CLOSED", "note": {}}],
}
brain.live_status = lambda: STATUS


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        raise SystemExit(1)


# ---------------------------------------------------------------- 1. privacy_request
class FakeCursor:
    def __init__(self, log):
        self.log, self.description = log, []

    def execute(self, sql, params=()):
        self.log.append(sql.split()[0])
        return self

    def fetchall(self):
        return []

    def fetchone(self):
        return (0,)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self):
        self.log = []

    def cursor(self):
        return FakeCursor(self.log)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_privacy_queue():
    u = "351920000001"
    store.reset(u)
    store.set_user(u, lang="en", state="ready", consent="yes")
    store.note_inbound(u)
    store.queue_pending(u, "wake", {"message": {"from": u, "type": "text", "text": {"body": "Is PR1 open?"}},
                                    "new_visitor": False, "notice": {"type": "text", "body": brain.WAKING["en"]}})
    store.queue_pending("351920000999", "busy", {"message": {"type": "text", "text": {"body": "someone else"}}})
    ws = pr.working_store(u)
    check(len(ws["queued_messages"]) == 1 and ws["queued_messages"][0]["message"]["text"]["body"] == "Is PR1 open?"
          and ws["queued_messages"][0]["notice_sent"] == brain.WAKING["en"], "access: this visitor's queue only")
    check(ws["last_incoming_message_at"] and ws["last_incoming_message_at"].startswith("20"), "access: last_inbound")
    conn = FakeConn()
    pr.psycopg.connect = lambda url: conn
    pr.HERE = SCRATCH  # export lands in the scratch dir
    pr.access(u, "vid")
    out = [f for f in os.listdir(os.path.join(SCRATCH, "privacy_exports"))][0]
    data = json.load(open(os.path.join(SCRATCH, "privacy_exports", out)))
    check(data["working_store"]["queued_messages"][0]["reason"] == "wake"
          and data["working_store"]["last_incoming_message_at"], "access export JSON has queue + last inbound")
    pr.input = lambda prompt: "yes"
    import builtins
    real_input, builtins.input = builtins.input, (lambda prompt="": "yes")
    try:
        pr.erase(u, "vid")
    finally:
        builtins.input = real_input
    check(not store.pending_for(u) and store.last_inbound(u) is None and store.get_user(u) is None,
          "erase: queue, last_inbound and user gone")
    check(len(store.pending_for("351920000999")) == 1, "erase: other visitors' queue untouched")
    check(conn.log.count("DELETE") == 4, "erase: analytics tables deleted (fake Postgres)")


# ---------------------------------------------------------------- 2. chat.py with the model down
def fake_llm(messages, max_tokens=700, schema=None, temperature=0.3):
    if not model["up"]:
        raise brain.LLMDown()
    text = messages[-1]["content"]
    if schema:
        return json.dumps({"is_question": "?" in text, "language": brain.guess_lang(text) or "en",
                           "intent": "status", "topic": "pr1 open", "trail_code": "PR1"})
    return f"ANSWER to: {text}"


def test_chat_model_down():
    brain.llm = fake_llm
    store.reset(chat.USER)
    model["up"] = False
    out = chat.send("Ist der PR1 heute offen?")
    check(len(out) == 1 and out[0]["type"] == "buttons" and store.get_user(chat.USER)["lang"] == "de",
          "chat: question with the model down → notice in German, no model needed, no crash")
    check(not store.pending_all() or all(r["user"] != chat.USER for r in store.pending_all()),
          "chat: nothing queued")
    store.reset(chat.USER)
    model["up"] = True
    out = chat.send("Is PR1 open today?")
    check(out[0]["type"] == "buttons", "chat: question before Accept → notice")
    model["up"] = False
    out = chat.send("/yes")
    check(len(out) == 1 and "[model down" in out[0]["body"] and brain.WAKING["en"] in out[0]["body"],
          "chat: Accept while down → the waiting question shown as deferred")
    model["up"] = True
    out = chat.send("And the weather?")
    check(out == [{"type": "text", "body": "ANSWER to: And the weather?"}], "chat: model up → normal answer")


# ---------------------------------------------------------------- 3a. scrub sweep
class FakePG:
    """conversation_turn rows, seen through analytics._exec."""
    def __init__(self, rows):
        self.rows = {r["turn_id"]: r for r in rows}
        self.selects = 0
        self.down = False

    def exec(self, sql, params=(), fetch=False):
        if self.down:
            return None
        s = " ".join(sql.split())
        if s.startswith("SELECT turn_id, text_scrubbed FROM conversation_turn"):
            self.selects += 1
            import re
            hits = [r for r in sorted(self.rows.values(), key=lambda r: r["turn_id"])
                    if r["scrub_method"] == "rules" and re.search(r"[A-Za-zÀ-ž]{2}", r["text"] or "")
                    and ((r["dir"] == "in" and r["kind"] == "text") or (r["dir"] == "out" and r["model"]))]
            return [(r["turn_id"], r["text"]) for r in hits[:params[0]]]
        if s.startswith("UPDATE conversation_turn SET text_scrubbed"):
            clean, tid = params
            self.rows[tid].update(text=clean, scrub_method="rules+llm")
            return None
        if s.startswith("UPDATE conversation_turn SET scrub_method='rules+llm-rejected'"):
            self.rows[params[0]]["scrub_method"] = "rules+llm-rejected"
            return None
        raise AssertionError(s)


def row(tid, text, d="in", kind="text", model_name=None, method="rules"):
    return {"turn_id": tid, "text": text, "dir": d, "kind": kind, "model": model_name, "scrub_method": method}


def test_scrub_sweep():
    pg = FakePG([row(1, "Hi, I'm Anna, is PR1 open?"), row(2, "WAKING notice", d="out"),
                 row(3, "Yes Anna, it is open.", d="out", model_name="levadinho"),
                 row(4, "en", kind="language_choice"), row(5, "Done already", method="rules+llm"),
                 row(6, "Bad one")])
    calls = []

    def scrub(text):
        calls.append(text)
        if not model["up"]:
            raise ConnectionError("refused")
        return None if text == "Bad one" else text.replace("Anna", "[NAME]")

    analytics._exec, analytics.scrub_llm, analytics.DB_URL = pg.exec, scrub, "postgresql://fake"
    analytics._scrub_q = queue.Queue()
    analytics._sweep.update(at=time.time(), backlog=False)
    model["up"] = False
    analytics._scrub_q.put((1, pg.rows[1]["text"]))
    analytics._scrub_step(timeout=0)
    check(calls == [] and analytics._sweep["backlog"], "model asleep: live scrub skipped (no call), backlog noted")
    check(pg.rows[1]["scrub_method"] == "rules", "model asleep: row stays rules-only")
    check(not analytics._sweep_due(), "sweep not due yet (retry interval)")
    analytics._sweep["at"] = time.time() - analytics.SCRUB_RETRY_S - 1
    check(analytics._sweep_due(), "backlog → sweep due after SCRUB_RETRY_S")
    analytics._scrub_step(timeout=0)
    check(calls == [] and pg.selects == 0, "sweep with the model asleep: no query, no model call (never wakes it)")
    model["up"] = True
    analytics._sweep["at"] = 0
    analytics._scrub_step(timeout=0)
    check(pg.rows[1]["text"] == "Hi, I'm [NAME], is PR1 open?" and pg.rows[1]["scrub_method"] == "rules+llm",
          "model up: incoming question re-scrubbed")
    check(pg.rows[3]["scrub_method"] == "rules+llm" and "[NAME]" in pg.rows[3]["text"], "model's answer re-scrubbed")
    check(pg.rows[2]["scrub_method"] == "rules" and pg.rows[4]["scrub_method"] == "rules",
          "notices and picker choices are not sent to the model")
    check(pg.rows[6]["scrub_method"] == "rules+llm-rejected", "guard-rejected row marked, not retried forever")
    check(not analytics._sweep["backlog"], "backlog cleared")
    n = len(calls)
    analytics._sweep["at"] = 0
    analytics.sweep()
    check(len(calls) == n, "second sweep: nothing left to do")
    # model goes down in the middle of a sweep
    pg.rows.update({7: row(7, "Anna again"), 8: row(8, "and Anna")})
    real = scrub

    def dies(text):
        model["up"] = False
        return real(text)
    analytics.scrub_llm = dies
    analytics._sweep["at"] = 0
    done = analytics.sweep()
    check(done == 0 and pg.rows[7]["scrub_method"] == "rules" and analytics._sweep["backlog"],
          "model dies mid-sweep: stops, rows kept for later")
    # batches
    model["up"] = True
    analytics.scrub_llm = scrub
    for i in range(10, 40):
        pg.rows[i] = row(i, f"Question {i} from Anna")
    analytics.sweep(limit=5)
    check(analytics._sweep["backlog"], "full batch → more to do soon (retry interval)")
    pg.down = True
    check(analytics.sweep() == 0, "database down: sweep is a no-op")
    analytics.DB_URL = ""


# ---------------------------------------------------------------- 3b. web campaigns
def test_web_campaigns():
    sqls = []
    state = {"down": False}

    def fake_exec(sql, params=(), fetch=False):
        sqls.append((" ".join(sql.split()), params))
        if state["down"]:
            return None
        return [] if fetch else None
    analytics._exec, analytics.DB_URL = fake_exec, "postgresql://fake"
    analytics._campaigns_known.clear()
    analytics.event("whatsapp", "qr_scanned", vid="v", campaign="web-pr1")
    ins = [s for s in sqls if s[0].startswith("INSERT INTO campaign")]
    check(len(ins) == 1 and ins[0][1] == ("web-pr1",) and "NULL, 'website page link'" in ins[0][0]
          and "ON CONFLICT (campaign_id) DO NOTHING" in ins[0][0], "web-pr1: campaign row inserted if missing")
    sqls.clear()
    analytics.turn("351", "in", "text", None, campaign="web-pr1")
    analytics.event("whatsapp", "x", vid="v", campaign="web-pr1")
    check(not any(s[0].startswith("INSERT INTO campaign") for s in sqls), "web-pr1: only once per process")
    sqls.clear()
    analytics.event("whatsapp", "x", vid="v", campaign="areeiro")
    analytics.event("whatsapp", "x", vid="v", campaign=None)
    analytics.event("whatsapp", "x", vid="v", campaign="web-BAD tag;")
    check(not any(s[0].startswith("INSERT INTO campaign") for s in sqls), "QR tags, None and malformed tags ignored")
    state["down"] = True
    analytics.event("whatsapp", "x", vid="v", campaign="web-fees")
    check("web-fees" not in analytics._campaigns_known, "database down: fail-soft, retried later")
    state["down"] = False
    sqls.clear()
    analytics.event("whatsapp", "x", vid="v", campaign="web-fees")
    check(any(s[0].startswith("INSERT INTO campaign") for s in sqls) and "web-fees" in analytics._campaigns_known,
          "web-fees inserted once the database is back")
    analytics.DB_URL = ""


# ---------------------------------------------------------------- 4. facts file
def test_facts():
    f = open(os.path.join(BOT, "pr1_facts.md"), encoding="utf-8").read()
    for s in ("€250 to €2,500", "Portaria 801/2025 art. 10", "24/2022/M", "art. 13", "**€7**", "**€9**",
              "**€22.50**", "**€52.50**", "PR1 is never included", "06:00", "06:45", "12:15", "19:00",
              "€3.00 per trip", "291 705 555", "+351 291 572 540", "**1 May 2026**", "26 June 2026",
              "14–17 and 21–22", "NEVER give\na date", "No bus serves Achada do Teixeira",
              "without a ticket", "Not confirmed"):
        check(s in f, f"facts: {s}")
    for s in ("ATUALIZADO", "according to IFCN's list, updated", "fines reported up to €250", "NO public bus at Achada do Teixeira or at Pico do Areeiro",
              "Watching sunrise from the Pico do Areeiro viewpoint is free", "Contact the SIMplifica call centre"):
        check(s not in f, f"facts: stale claim gone: {s}")
    check(brain.FACTS == f, "brain loads the facts file")


# ---------------------------------------------------------------- 5. brain IFCN wording
def test_brain_ifcn():
    b = brain.status_block()
    check("14/09/2026" not in b and "updated" not in b and "warnings list" in b, "status_block: IFCN source, no date")
    check("every morning" not in b and "Visit Madeira" not in b, "status_block: no 'every morning' claim")
    check("PR1.2 | Vereda do Pico Ruivo | OPEN (Aberto só de manhã.)" in b, "trail note: pt fallback")
    check("PR11 | Vereda dos Balcões | OPEN (Restricted.)" in b, "trail note: en preferred")
    check("PR9 | Levada do Caldeirão Verde | CLOSED |" in b, "trail without a note")
    s2 = dict(STATUS, trails=[{"code": "PR1", "name": "Vereda do Areeiro", "status": "PARTIAL"}] + STATUS["trails"])
    brain.live_status = lambda: s2
    check("PR1 | Vereda do Areeiro | PARTIAL (Open: Areeiro–Pedra Rija.)" in brain.status_block(),
          "PR1 note: English, from the top-level note")
    brain.live_status = lambda: STATUS
    # every trail is covered: the table has facts, the question picks the right pages
    check("6.1 km" in brain.status_block() or "PR1 |" not in brain.status_block(), "table carries official facts")
    for q, code in [("Is PR6.1 open?", "PR6.1"), ("Balcões by bus?", "PR11"), ("Ist die Levada das 25 Fontes offen?", "PR6"),
                    ("Czy Pico Ruivo jest otwarte?", "PR1.2"), ("levada do caldeirão verde - um caminho para todos", "PR9.1")]:
        check(code in brain.pick_context("t-ctx", q, {})[0], f"pick_context: {q} → {code}")
    check("tunnels" in brain.pick_context("t-ctx", "Do I need a torch for Caldeirão Verde?", {})[1], "torch → tunnels guide")
    check(brain.pick_context("t-ctx", "Which levadas can I do without a car?", {})[1] == ["bus"], "no car → bus guide")
    r = "From Ribeiro Frio, PR10 Levada do Furado is open. Book here: https://simplifica.madeira.gov.pt/services/78-82-259"
    check(brain.site_links(r, ["PR11"], "en").endswith("🥾 PR10 Levada do Furado on our site: https://levadinho-madeira.com/levada-do-furado/"),
          "site link: the trail the reply talks about")
    check(brain.site_links("See https://levadinho-madeira.com/balcoes/", ["PR11"], "pt") == "", "site link: not twice")
    check("no nosso site: https://levadinho-madeira.com/balcoes/" in brain.site_links("Sim.", ["PR11"], "pt"),
          "site link: the question's trail when the reply names none")
    check(brain.pick_context("t-ctx", "Is Levada dos Tornos open?", {"trail_code": "PR14"})[0] == [],
          "classifier's trail guess ignored (Tornos is not PR14)")
    check(brain._en("plain") == "plain" and brain._en({"fr": "x"}) == "x" and brain._en(None) == "", "_en fallbacks")
    STATUS["source"] = {}
    check("date" not in brain.status_block().split("\n")[0].replace("Never give any date", ""), "no source.updated: no date talk")
    STATUS["source"] = {"name": "IFCN", "updated": "14/09/2026"}
    check("say it's from this morning" not in brain.SYSTEM and "never say it was checked this morning" in brain.SYSTEM.lower() and "IFCN's official warnings list" in brain.SYSTEM
          and "NEVER give a date" in brain.SYSTEM and "14/09/2026" not in brain.SYSTEM, "SYSTEM: cite IFCN, never a date")
    for lang, s in brain.LOC_FAR.items():
        check("{updated}" not in s and "IFCN" in s, f"LOC_FAR[{lang}] cites IFCN, no date")
    u = "351920000002"
    store.reset(u)
    store.set_user(u, lang="pt", state="ready", consent="yes")
    out = brain.handle_location(u, 32.65, -16.91)  # Funchal: far from PR1
    check("14/09/2026" not in out[0]["body"] and "IFCN" in out[0]["body"] and "parcialmente aberto" in out[0]["body"],
          f"far location reply (pt): {out[0]['body'][:120]}")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            print(f"\n== {name}")
            fn()
    print("\nALL PASSED")
