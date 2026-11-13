"""Regression run of the bot's answers on backend/tests/regression_questions.json.

  python3 backend/tests/regression.py baseline OUT.json   # the current bot (bot/brain.py, prompt-stuffed)
  python3 backend/tests/regression.py tools OUT.json      # the tools-only bot (BOT_TOOLS=1, bot/brain_tools.py)
  python3 backend/tests/regression.py score OUT.json      # re-score a saved run
  REGRESSION_QUESTIONS=backend/tests/heldout_questions.json …   # another question set

Each question goes to a fresh test visitor (no history, or the "before" turns replayed first) with "Staying in: Funchal" already known, through
brain.classify + brain.respond, as on WhatsApp after the privacy notice. LEVADINHO_DB is pointed at a scratch
file so nothing reaches the live bot store; brain writes no analytics (app.py does). Needs the model up.
"""
import json
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
QFILE = os.environ.get("REGRESSION_QUESTIONS", os.path.join(HERE, "regression_questions.json"))
QUESTIONS = json.load(open(QFILE, encoding="utf-8"))["questions"]


def live_status():
    try:
        return json.load(open(os.path.join(ROOT, "status.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def trail_status(st, code):
    return next((t.get("status") for t in st.get("trails") or [] if t.get("code") == code), None)


def lead_heads(st):
    """Bold heads of the closure / warnings banners the bot puts before its answer (brain.storm_lead), all languages."""
    a = st.get("alert") or {}
    return [x["head"] for k in ("partial", "ahead_text") for x in ((a.get(k) or {}).get("text", a.get(k)) or {}).values()
            if isinstance(x, dict) and x.get("head")]


def without_lead(answer, heads):
    """The answer minus the leading banner paragraphs (owner, 2026-11-13: the many-trails-closed banner names
    'PR1 … (Pico do Areeiro)', which failed must_not checks on answers that were right)."""
    paras = answer.split("\n\n")
    while paras and (paras[0].startswith(("⚠️ *", "🌧️ *")) or any(h in paras[0] for h in heads)):
        paras.pop(0)
    return "\n\n".join(paras)


def score(results):
    passed = 0
    current = {q["id"]: q for q in QUESTIONS}  # always score against today's checks
    st = live_status()
    heads = lead_heads(st)
    for r in results:
        r.update({k: current[r["id"]].get(k, []) for k in ("must", "must_not")} if r["id"] in current else {})
        # a question written for an open / partly open trail: its "when_closed" checks apply while the trail was
        # CLOSED at run time (owner, 2026-11-13: PR1 closed, the "Pedra Rija" checks failed right answers)
        wc = (current.get(r["id"]) or {}).get("when_closed")
        if wc and (r.get("trail_status_at_run") or trail_status(st, wc["trail"])) == "CLOSED":
            r["must"], r["must_not"] = wc.get("must", []), wc.get("must_not", [])
        a = without_lead(r["answer"] or "", heads)   # the bot's own answer, both ways
        miss = [p for p in r.get("must", []) if not re.search(p, a, re.I)]
        bad = [p for p in r.get("must_not", []) if re.search(p, a, re.I)]
        r["ok"] = not miss and not bad and not r.get("error")
        r["missing"], r["forbidden"] = miss, bad
        passed += r["ok"]
        print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['id']:20s} {r.get('latency_s', 0):5.1f}s"
              + (f"  missing {miss}" if miss else "") + (f"  forbidden {bad}" if bad else "")
              + (f"  error {r['error']}" if r.get("error") else ""))
    print(f"\n{passed}/{len(results)} pass")
    return results


def baseline(out, mode="baseline"):
    if mode == "tools":
        os.environ["BOT_TOOLS"] = "1"
    os.environ["LEVADINHO_DB"] = os.path.join(tempfile.mkdtemp(prefix="lvd-regress-"), "store.db")
    sys.path.insert(0, os.path.join(ROOT, "bot"))
    import brain
    import store
    results = []
    for n, q in enumerate(QUESTIONS):
        user = f"regress-{n}"
        store.reset(user)
        store.set_user(user, lang=q["lang"], consent="yes", state="ready", base=q.get("base", "Funchal"), source=q.get("source"))
        t = time.time()
        r = dict(q)
        if q.get("when_closed"):
            r["trail_status_at_run"] = trail_status(live_status(), q["when_closed"]["trail"])
        try:
            for turn in q.get("before", []):  # a follow-up: the earlier turns of the real chat, on the same visitor
                brain.respond(user, turn, q["lang"], {"events": []}, brain.classify(turn))
            c = brain.classify(q["q"])
            r["classified"] = c
            meta = {"events": []}
            r["answer"] = brain.respond(user, q["q"], q["lang"], meta, c)
            r["tools"] = meta.get("tools")
            r["image_url"] = meta.get("image_url")
        except Exception as e:  # noqa: BLE001
            r["answer"], r["error"] = None, f"{type(e).__name__}: {e}"
        r["latency_s"] = round(time.time() - t, 1)
        results.append(r)
        print(f"[{n + 1}/{len(QUESTIONS)}] {q['id']} {r['latency_s']}s", flush=True)
    score(results)
    json.dump({"run": mode, "at": time.strftime("%F %T"), "results": results},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", out)


if __name__ == "__main__":
    mode, path = sys.argv[1], sys.argv[2]
    if mode in ("baseline", "tools"):
        baseline(path, mode)
    else:
        d = json.load(open(path, encoding="utf-8"))
        score(d["results"])
