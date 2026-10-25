"""Tools-only answers (phase 3 of the knowledge-store work): the model gets no facts in its prompt, only tools
on Levadinho's knowledge store (backend/kbtools.py, schema kb in levadinho-db), and answers from what they
return, or says it doesn't know.

brain.answer() uses this when BOT_TOOLS=1; otherwise the prompt-stuffed answer stays. Needs vLLM started with
--enable-auto-tool-choice --tool-call-parser qwen3_coder (start.sh / llm_control.py).
"""
import inspect
import json
import logging
import os
import re
import sys
import time
import types
import typing
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
import kbtools  # noqa: E402

log = logging.getLogger("levadinho.tools")
MAX_ROUNDS = 5
MAX_RESULT_CHARS = 12000

# Every public MCP tool (owner, 2026-10-10: every fact in the knowledge store, every answer from it).
BOT_TOOLS = list(kbtools.TOOLS) + [kbtools.taxi_prices, kbtools.day_plan]  # bot only, not on the public MCP server
BY_NAME = {f.__name__: f for f in BOT_TOOLS}
JSON_TYPE = {str: "string", int: "integer", float: "number", bool: "boolean"}
_TRAIL = ("A trail code (PR9) or, if you are not sure of the code, the trail's name or place exactly as the visitor "
          "wrote it (Caldeirão Verde, 25 Fontes, São Lourenço). Never guess a code.")
TRAIL_PARAMS = {"code": _TRAIL, "trail": _TRAIL, "near_trail": _TRAIL, "exclude": _TRAIL,
                "pickup": "Where the taxi picks the visitor up: a town or a trailhead (Achada do Teixeira, Rabaçal…).",
                "destination": "Where the visitor is going (often the town they are staying in).",
                "place": "The place exactly as the visitor wrote it (Rabaçal, Achada do Teixeira, Monte…)."}


def _schema(fn):
    """OpenAI-style tool definition from the function's signature and docstring. `lang` is filled in by us."""
    props, required = {}, []
    hints = typing.get_type_hints(fn)
    for name, p in inspect.signature(fn).parameters.items():
        if name == "lang":
            continue
        t = hints.get(name, str)
        if isinstance(t, types.UnionType) or typing.get_origin(t) is typing.Union:
            t = next(a for a in typing.get_args(t) if a is not type(None))
        props[name] = {"type": JSON_TYPE.get(t, "string")}
        if name in TRAIL_PARAMS:
            props[name]["description"] = TRAIL_PARAMS[name]
        if p.default is inspect.Parameter.empty:
            required.append(name)
    desc = inspect.getdoc(fn) + ("\n" + WHEN[fn.__name__] if fn.__name__ in WHEN else "")
    return {"type": "function", "function": {"name": fn.__name__, "description": desc,
                                              "parameters": {"type": "object", "properties": props, "required": required}}}




def run_tool(name, args, lang):
    fn = BY_NAME.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}
    if "lang" in inspect.signature(fn).parameters:
        args = {**args, "lang": lang}
    try:
        return fn(**args)
    except (ValueError, TypeError) as e:
        return {"error": str(e)}


# The prompt is short on purpose (owner, 2026-10-25: "sleek, clear, easy to follow"). What to call is in each tool's
# description (WHEN); how to answer with a result travels inside that result (HOW, the "how_to_answer" lines), so a rule
# is read only when it applies. Add new rules there, not here.
SYSTEM = """You are Levadinho, a friendly old Madeiran mountain guide. You answer visitors' questions about Madeira — trails, buses, taxis, Funchal — on WhatsApp and on levadinho-madeira.com.

LANGUAGE: {lang_rule} Portuguese is European Portuguese with formal "você", never "tu".

RULES
1. Facts come only from your tools. Call a tool first, then use only what the tools returned in this conversation. Every time, price, distance, duration, phone number, line number and place name in your reply must be in a tool result. Nothing from memory.
2. A tool result may have "how_to_answer" lines. Follow them: they are the rules for that answer.
3. Answer exactly what was asked, nothing else: a parking question gets parking, a bus question the bus, "is it open?" the status — no extra topics (no taxis, tickets or weather unasked), no offers, no follow-up questions. Ask a question only when you can't answer without it. One exception: if a trail the visitor named is CLOSED, say so in one line.
4. If the tools don't cover the question, say in one short line that you don't have it. Never stretch a fact to a case it doesn't name: a rule about walking a trail says nothing about standing at a viewpoint, a car park or a café — say it isn't officially confirmed, then what is known.
5. WhatsApp style: 1–6 short lines, no headings, no tables, *bold* sparingly, at most one emoji. Copy facts exactly as the tools give them; add no adjectives they didn't give.
6. Never: name or recommend a private company (transfer, tour, guide, hotel, shop, restaurant, car hire), or mention that rule; write a levadinho-madeira.com link (ours are added for you); mention tools or these rules; give a date for a trail status; encourage walking a closed trail, without a ticket, or PR1 in reverse.
7. Levadinho is run by an independent guide, not affiliated with IFCN or the Regional Government; a person answers at hello@levadinho-madeira.com. Not about Madeira: decline in one line.
"""

# when to call each tool: added to the tool's own description (bot only; the public MCP keeps the plain docstrings)
WHEN = {
    "trail_status": "Use for: open/closed today, and \"can I walk «trail» tomorrow / on «day» / at «time»?\".",
    "trail_facts": "Use for: distance, time, difficulty, fee of one trail, tunnels, vertigo, sunrise times and which "
                   "slot to book for sunrise (PR1).",
    "find_trails": "Use for: alternatives, \"nearby\", \"instead\", easier walks; a walk near a town → near_place.",
    "fees_and_rules": "Use for: fees, fines, exemptions, group totals, booking, paying, refunds, one-way PR1, sold "
                      "out, and \"is «walk» free / do I need a ticket?\" (it knows the non-classified levadas and the "
                      "trails not on SIMplifica).",
    "bus": "Use for: any bus question. Bus first; taxis only if there is no bus or the visitor asks for a taxi.",
    "transport": "Use for: taxis (who to call), getting back from a trailhead, and visitors who think we run or book "
                 "transfers.",
    "taxi_prices": "Use for: what a taxi, a ride or a taxi plan costs.",
    "webcam": "Use for: is the car park full NOW, is it cloudy up there NOW (Rabaçal, Achada do Teixeira, Pico do "
              "Areeiro). Not for where to park in general (search).",
    "weather_now": "Use for: the weather now.",
    "forecast_tomorrow": "Use for: will it be cloudy tomorrow / later at the summit.",
    "closures": "Use for: what closed or reopened.",
    "places": "Use for: Funchal and Monte only — cable cars, market, museums, gardens, lidos, toboggan, opening hours "
              "(then place(id) for one place).",
    "notices": "Use for: events in Funchal (\"funchal\") and cruise ships in port (\"funchal-port\").",
    "search": "Use for: anything else, in the visitor's language — parking, what's at a trailhead (café, toilets), "
              "dogs, drones, what to bring, one or two days in Madeira, things to do, cruise-day plans.",
    "day_plan": "Use ONLY when the visitor asks for one of these exact plans: Balcões AND PR1 on the same day "
                "(pr11_pr1); Balcões AND Levada do Furado on the same day (pr11_pr10); getting back from Portela "
                "(portela_back). Never for a general \"which walk?\" question. Never answer Balcões + PR1 with pr11_pr10.",
}

PR1_TICKETS = ("PR1 has two SIMplifica tickets: €4.50 for Areeiro ↔ Pedra Rija (both ways) and €10.50 for the full "
               "one-way route to Pico Ruivo, ending at Achada do Teixeira.")
PR1_TIME = ("PR1 is open every day unless the status says otherwise; there is no weekday or hours rule, and one-way never "
            "means closed. A start at «time» is fine if a SIMplifica slot for that time is free; for the full route add "
            "the finish: start + about 4 h (PR1 about 3 h + 45–60 min down PR1.2) = at Achada do Teixeira around "
            "«time + 4 h», written as HH:MM (e.g. 15:00 → 19:00).")


def _how(name, args, result, lang):
    """The answer rules for this result (bot only). Each line is used only when it applies."""
    h = []
    blob = json.dumps(result, ensure_ascii=False, default=str)
    code = (result.get("code") if isinstance(result, dict) else None) or ""
    if name == "trail_status":
        h.append("Say it is according to IFCN's official warnings list. If the trail is partly open, say which part is "
                 "open, as the note says, in the visitor's language. No date.")
        if code == "PR1" or '"PR1"' in blob[:200]:
            h += [PR1_TIME, PR1_TICKETS + " Give both when they ask about walking PR1."]
        if '"CLOSED"' in blob:
            h.append("Walking or entering a CLOSED trail is an administrative offence, like walking without a ticket "
                     "(fines €250–€2,500): say so if they ask whether they can still go.")
    elif name == "trail_facts":
        if code == "PR1":
            h += [PR1_TICKETS + " Give every price for the trail.", PR1_TIME,
                  "Sunrise: answer from the computed sunrise notes, never from the slot list alone."]
        h.append("No road and no taxi reaches Pico Ruivo: the nearest road and taxi pick-up is Achada do Teixeira, "
                 "2.8 km down PR1.2." if code in ("PR1", "PR1.2") else "")
    elif name == "fees_and_rules":
        h += ["Group totals: count every person; only children 12 and under are free (a 13-year-old pays); exempt "
              "people still go on the booking. Write ONE multiplication for everyone who pays, e.g. \"2 adults + the "
              "13-year-old = 3 × €4.50 = €13.50; the 9-year-old is free but goes on the booking\".",
              "\"Do I still need a ticket if…?\": yes — walking a classified trail without one is an administrative "
              "offence, fines €250–€2,500. Say it.",
              "\"Which walks are free?\": name both groups — the non-classified levadas AND PR3, PR3.1, PR4, PR23 "
              "(run by others: not on SIMplifica, no IFCN fee).",
              "Paying: SIMplifica takes Multibanco, credit card (Visa, Mastercard) and MB WAY; Multibanco and MB WAY "
              "need a Portuguese bank account, so visitors pay by card. Taxis are never booked on SIMplifica.",
              "A topic with no rule here (dogs, drones, bikes, camping…): say no official source covers it; never "
              "say allowed or not allowed.",
              "Standing at a viewpoint, a car park or a café (e.g. the sunrise at Pico do Areeiro without a ticket): "
              "these rules are about walking the trail, so say no official source confirms it either way, then that "
              "walking onto the trail needs a ticket."]
    elif name == "bus":
        h += ["Give every departure returned, with line and stops, for the day they mean; with no day given, every day "
              "type returned. Never add a day type or a trip the result doesn't have. Give the fare when it is there.",
              "A bus serves a place only if a returned trip goes to or from it."]
    elif name == "transport":
        h += ["Visitors who think we run or book transfers: \"I'm an independent guide — I don't run or book transfers "
              "or taxis. Your hotel reception can arrange a transfer, or you can book a taxi for a set time yourself\", "
              "then the numbers. Never name a transfer company.",
              "Taxi after the full PR1: book a set pick-up time at Achada do Teixeira before you start (the walk ends "
              "there); count about 4 hours from the start (PR1 about 3 h + 45–60 min down). In the daytime taxis "
              "usually wait there; for an early, late or off-season finish, book ahead.",
              "Taxis are paid in cash, so carry enough. Taxis are booked by phone, never on SIMplifica.",
              "Never state a fare here: what a ride costs comes from taxi_prices."]
    elif name == "taxi_prices":
        h += ["A route with a price: \"About €«car» by car (up to 4 people), €«van» by van (5–10) — an indicative price; "
              "the fare is agreed when you book.\" With the group size, add for_your_group. Portuguese: car = "
              "\"carro\", van = \"carrinha\".",
              "No price for their trip: taxis are metered at the official tariff — ask for a quote when booking. "
              "(PT \"cobram pelo taxímetro\", FR \"au compteur\", DE \"nach Taxameter\", PL \"według taksometru\".)",
              "The shared ride back from Achada do Teixeira to Pico do Areeiro: about €15–20 per person; for «n» people "
              "about €«15×n»–«20×n» in total. A question about that shared ride gets only this, not a car price.",
              "If the visitor's own sum is right, start with \"Yes\"."]
    elif name == "weather_now":
        h.append("Say when it was measured (\"measured at\" + observed_time), never \"right now\".")
    elif name == "webcam":
        h.append("The picture is sent after your reply: say in one line which camera it is and when the picture was "
                 "taken (e.g. \"Here's the Rabaçal car park, picture from 17:26\"). Never describe the picture.")
    elif name in ("places", "place") and re.search(r"cable|monte|telef", blob[:4000], re.I):
        h.append("Monte: the cable car from the Old Town (Zona Velha) is the way up; the bus is the way down after the "
                 "cable car stops. Never answer Monte with taxis.")
    elif name == "notices" and "cruise" in blob:
        h.append("A ship in this list is the port's schedule: never assume it is the visitor's ship.")
    elif name == "search":
        h.append("Use only the sections about what was asked; a plan or schedule is given as the page has it.")
    return [x for x in h if x]


TOOLS = [_schema(f) for f in BOT_TOOLS]


def looping(reply):
    """A degenerate generation: the same line or sentence three times or more, making up most of the reply. A bus
    timetable repeats its notes ("Só no Período Escolar") on many lines and is not one (24 Oct)."""
    sents = [x.strip().lower() for x in re.split(r"(?<=[.!?])\s+|\n+", reply) if len(x.strip()) >= 20]
    rep = sum(len(x) * sents.count(x) for x in set(sents) if sents.count(x) >= 3)
    return rep > 0.5 * max(1, len(reply))


def unloop(messages, reply):
    """A looping reply (24 Oct, PL, live: the visitor's question repeated over and over) is asked for once more,
    with a repetition penalty."""
    if not looping(reply):
        return reply
    log.warning("looping reply, asked again: %r", reply[:200])
    m = _call(messages + [{"role": "assistant", "content": reply},
                          {"role": "user", "content": "(That reply repeated itself. Answer the question once, in 1–5 "
                                                      "short lines, from the tool results above.)"}],
              use_tools=False, extra={"repetition_penalty": 1.15})
    return (m.get("content") or "").strip()


def _call(messages, max_tokens=900, use_tools=True, choice="auto", extra=None):
    import brain  # llm settings and the wake-on-demand check live there
    if brain.llm_control.ON_DEMAND and not brain.llm_control.is_up():
        raise brain.LLMDown()
    body = {"model": brain.LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}
    if use_tools:
        body.update(tools=TOOLS, tool_choice=choice)
    body.update(extra or {})
    req = urllib.request.Request(brain.LLM_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]
    except (ConnectionError, urllib.error.URLError) as e:
        if brain.llm_control.ON_DEMAND and isinstance(getattr(e, "reason", e), ConnectionError):
            brain.llm_control.mark_down()
            raise brain.LLMDown() from e
        raise


_NAMES = None


def fix_trail_names(reply):
    """Deterministic guard: 'Levada das 25 Fontes (PR1.2)' → 'Vereda do Pico Ruivo (PR1.2)'. A trail name written next
    to another trail's code is replaced by the code's real name (the code is what the tools returned)."""
    global _NAMES
    if _NAMES is None:
        _NAMES = {r["code"]: r["name"] for r in kbtools._q("SELECT code, name FROM kb.trail")}
    by_name = sorted(((n, c) for c, n in _NAMES.items()), key=lambda x: -len(x[0]))
    for name, code in by_name:
        for m in re.finditer(re.escape(name) + r"(\*?\s*\(\s*)(PR\d{1,2}(?:\.\d)?)(?=\s*\))", reply):
            other = m.group(2)
            if other != code and other in _NAMES:
                log.warning("trail name fixed: %s (%s) → %s", name, other, _NAMES[other])
                reply = reply.replace(m.group(0), _NAMES[other] + m.group(1) + other)
    return reply


PREFETCH = 0  # search results given with the question (RAG); 0 since 2026-10-10: they pushed unasked topics into answers


def answer(history, text, lang, lang_rule, page_hint="", search_text=None, page=None):
    """Returns (reply, trace). trace = the tool calls made, for the analytics record and the regression.
    search_text = the visitor's own words (text may carry our bracketed hints).
    page = kbtools.page_doc() of the page the visitor is chatting on: given to the model as its first tool result,
    so the page's own answer comes first (owner, 2026-10-24: on the cruise-port page "how do I get to town?" got
    taxis from transport() while the page says it is a flat 30-40 minute walk)."""
    messages = [{"role": "system", "content": SYSTEM.format(lang_rule=lang_rule) + page_hint}] + history \
        + [{"role": "user", "content": text}]
    trace = []
    if page and page.get("sections"):
        args = {"page": page["page"]}
        trace.append({"tool": "page", "args": args, "ms": 0, "error": None, "prefetch": True})
        messages += [{"role": "assistant", "content": "", "tool_calls": [{"id": "prefetch-page", "type": "function",
                      "function": {"name": "search", "arguments": json.dumps({"text": "page " + page["page"]})}}]},
                     {"role": "tool", "tool_call_id": "prefetch-page",
                      "content": json.dumps({"results": [{"title": s["title"], "url": page["page"], "text": s["text"]}
                                                         for s in page["sections"]]},
                                            ensure_ascii=False)[:MAX_RESULT_CHARS]}]
    if PREFETCH:
        args = {"text": search_text or text, "limit": PREFETCH}
        t = time.time()
        found = run_tool("search", args, lang)
        trace.append({"tool": "search", "args": args, "ms": int((time.time() - t) * 1000), "error": found.get("error"),
                      "prefetch": True})
        messages += [{"role": "assistant", "content": "", "tool_calls": [{"id": "prefetch-search", "type": "function",
                      "function": {"name": "search", "arguments": json.dumps(args, ensure_ascii=False)}}]},
                     {"role": "tool", "tool_call_id": "prefetch-search",
                      "content": json.dumps(found, ensure_ascii=False, default=str)[:MAX_RESULT_CHARS]}]
    for n in range(MAX_ROUNDS):
        # round 1 must call a tool: with "auto" the model answers from memory and invents facts (tested 2026-10-07)
        # with the page given, round 1 still calls a tool: when the page doesn't answer (the café's hours on the
        # sunrise page, 24 Oct) the model otherwise said "I don't know" without looking
        m = _call(messages, choice="required" if n == 0 else "auto")
        calls = m.get("tool_calls") or []
        if not calls:
            reply = fix_trail_names(unloop(messages, (m.get("content") or "").strip()))
            return fact_check(messages, reply, text, history, lang, trace), trace
        messages.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            t = time.time()
            result = run_tool(name, args, lang)
            how = _how(name, args, result, lang) if isinstance(result, dict) and not result.get("error") else []
            if how:
                result = {**result, "how_to_answer": how}
            out = json.dumps(result, ensure_ascii=False, default=str)
            if len(out) > MAX_RESULT_CHARS:
                out = out[:MAX_RESULT_CHARS] + "…(cut)"
            trace.append({"tool": name, "args": args, "ms": int((time.time() - t) * 1000), "error": result.get("error")})
            if name == "bus":  # brain.bus_footer adds the follow-up offer and a taxi after a timetable
                trace[-1]["trips"] = len(result.get("trips") or [])
                trace[-1]["trip_rows"] = result.get("trips") or []
            if name == "forecast_tomorrow" and result.get("forecast") and len(calls) == 1:
                # the forecast goes out as the tool wrote it (owner, 2026-10-24: "simply cite what the tool says"); the
                # model's paraphrase turned a clear summit into "no sea of clouds expected"
                trace[-1]["verbatim"] = True
                return result["forecast"] + "\n" + result.get("next_forecast", ""), trace
            if result.get("reply_exactly") and len(calls) == 1 and not any(
                    t.get("tool") not in ("page", name) for t in trace[:-1]):
                # nothing in our data for it: a fixed sentence from the tool, never the model's own words (owner, 25 Oct)
                return result["reply_exactly"], trace
            if name == "day_plan" and result.get("text"):
                # the owner's fixed plans go out word for word: the model's copy dropped a phone digit (24 Oct)
                return result["text"], trace
            if name == "webcam":  # the picture goes out after the reply (brain.answer_tools)
                imgs = [w["image_url"] for w in result.get("webcams", []) if w.get("image_url")]
                if imgs:
                    trace[-1]["image_url"] = imgs[0]
            messages.append({"role": "tool", "tool_call_id": c.get("id"), "content": out})
    # out of rounds: one last call without tools so the model has to answer from what it has
    messages.append({"role": "user", "content": "(Answer now from the tool results above; say you don't know what they don't cover.)"})
    m = _call(messages, use_tools=False)
    reply = fix_trail_names(unloop(messages, re.sub(r"<tool_call>.*", "", m.get("content") or "", flags=re.S).strip()))
    return fact_check(messages, reply, text, history, lang, trace), trace


def fact_check(messages, reply, text, history, lang, trace):
    """Step 1 of 25 Oct (grounding.py): hard facts not in this turn's tool results are asked again once, then cut;
    nothing left → the fixed no-data sentence, written in code."""
    import grounding
    tools = [m.get("content") or "" for m in messages if m.get("role") == "tool"]
    said = "\n".join([m.get("content") or "" for m in history if m.get("role") == "user"] + [text])
    ev = grounding.Evidence(tools, said)
    bad = grounding.unsupported(reply, ev)
    if not bad:
        return reply
    log.warning("fact check: unsupported %s in %r", bad, reply[:160])
    first = list(bad)
    m = _call(messages + [{"role": "assistant", "content": reply},
                          {"role": "user", "content": "(Your reply states things no tool result gives: " + "; ".join(bad)
                           + ". Write the reply again using only what the tool results say, and leave out what they "
                             "don't cover.)"}], use_tools=False)
    again = fix_trail_names((m.get("content") or "").strip())
    bad = grounding.unsupported(again, ev) if again else bad
    reply = again if again else reply
    if bad:
        reply = grounding.cut(reply, bad)
    if not grounding.substantive(reply):
        reply = grounding.NO_DATA.get(lang, grounding.NO_DATA["en"])
    trace.append({"tool": "fact_check", "args": {"unsupported": first, "still": bad}, "ms": 0, "error": None})
    return reply
