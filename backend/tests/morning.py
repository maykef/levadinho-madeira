"""Every morning (owner, 2026-10-25): put the bot through its two test sets and keep the score, so a change that
breaks an answer shows up the next morning instead of in a visitor's chat.

  1. the regression set (backend/tests/regression_questions.json, via regression.py tools)
  2. the training question set (seo_research/finetune/questions/*.jsonl, local only): each question's expected tool
     calls (or an accepted alternative), its must / must_not patterns

Runs against the live model on a copy of the bot's chat store (no visitor's history is touched, nothing is recorded
in the analytics database). Writes reports/data/bot_tests/<date>.json and one line per run in summary.log; exit 1
when a test that passed on the previous run now fails, so the Data collection tab shows a red dot. Skips (exit 0) when
the model is down. Collect job: bot_morning_test.
"""
import datetime
import glob
import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "reports", "data", "bot_tests")
QUESTIONS = sorted(glob.glob(os.path.join(ROOT, "seo_research", "finetune", "questions", "*.jsonl")))
# the page a question is asked on, as the bot sees it (the #web-… tag of the page's WhatsApp link / web chat)
PAGE_SOURCE = {"/pr1-sunrise-transport/": "web-sunrise"}


def training(rows):
    import brain
    import store
    out = []
    for r in rows:
        user = "test:" + "".join(random.choices(string.ascii_lowercase, k=12))
        source = (r.get("real") or {}).get("tag") or PAGE_SOURCE.get(r.get("page"), "")
        store.set_user(user, lang=r["lang"], state="ready", consent="yes", source=source)
        body, got, t = "", [], time.time()
        try:
            for turn in r["turns"]:
                meta = {"events": []}
                body = " ".join(o.get("body") or "" for o in brain.handle(user, turn, meta=meta))
                got = [x["tool"] for x in meta.get("tools", [])]
        except Exception as e:  # one broken question never stops the run
            body = f"ERROR {e!r}"
        want = {c["tool"] for c in r["calls"][-1]}
        alts = [{c["tool"] for c in a} for a in (r.get("alt_calls") or [])]
        tools_ok = not want or want <= set(got) or any(a <= set(got) for a in alts)
        miss = [m for m in r.get("must", []) if not re.search(m, body)]
        bad = [m for m in r.get("must_not", []) if re.search(m, body)]
        out.append({"id": r["id"], "q": r["turns"][-1], "ok": tools_ok and not miss and not bad, "tools": got,
                    "tools_ok": tools_ok, "missing": miss, "forbidden": bad, "answer": body,
                    "secs": round(time.time() - t, 1)})
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    day = datetime.date.today().isoformat()
    sys.path.insert(0, os.path.join(ROOT, "bot"))
    db = os.path.join(OUT, "probe.db")
    shutil.copy(os.path.join(ROOT, "bot", "levadinho.db"), db)
    os.environ.update(BOT_TOOLS="1", LEVADINHO_DB=db)
    import llm_control
    if not llm_control.is_up():
        print("skipped: model down")
        return 0
    reg_file = os.path.join(OUT, f"{day}_regression.json")
    subprocess.run([sys.executable, os.path.join(ROOT, "backend", "tests", "regression.py"), "tools", reg_file],
                   cwd=ROOT, env=os.environ, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        reg = json.load(open(reg_file))
        reg = reg if isinstance(reg, list) else reg.get("results", [])
    except (OSError, ValueError):
        reg = []
    rows = [json.loads(l) for f in QUESTIONS for l in open(f, encoding="utf-8") if l.strip()]
    train = training(rows)
    res = {"date": day, "regression": [{"id": x["id"], "ok": x.get("ok")} for x in reg], "training": train}
    prev = sorted(f for f in glob.glob(os.path.join(OUT, "????-??-??.json")) if not f.endswith(f"{day}.json"))
    json.dump(res, open(os.path.join(OUT, f"{day}.json"), "w"), ensure_ascii=False, indent=1)
    passed = {("r", x["id"]) for x in res["regression"] if x["ok"]} | {("t", x["id"]) for x in train if x["ok"]}
    broke = []
    if prev:
        p = json.load(open(prev[-1]))
        before = {("r", x["id"]) for x in p["regression"] if x["ok"]} | {("t", x["id"]) for x in p["training"] if x["ok"]}
        broke = sorted(i for _, i in before - passed)
    reg_ok = sum(1 for x in res["regression"] if x["ok"])
    tr_ok = sum(1 for x in train if x["ok"])
    line = (f"{day} regression {reg_ok}/{len(res['regression'])} · training {tr_ok}/{len(train)}"
            + (f" · newly failing: {', '.join(broke)}" if broke else ""))
    with open(os.path.join(OUT, "summary.log"), "a") as f:
        f.write(line + "\n")
    print(line)
    print(f"ROWS {len(res['regression']) + len(train)}")
    return 1 if broke else 0


if __name__ == "__main__":
    sys.exit(main())
