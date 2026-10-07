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

# The public MCP tools minus the Funchal ones the bot doesn't cover yet.
BOT_TOOLS = [kbtools.trail_status, kbtools.trail_facts, kbtools.find_trails, kbtools.fees_and_rules, kbtools.bus,
             kbtools.transport, kbtools.weather_now, kbtools.forecast_tomorrow, kbtools.closures, kbtools.search]
BY_NAME = {f.__name__: f for f in BOT_TOOLS}
JSON_TYPE = {str: "string", int: "integer", float: "number", bool: "boolean"}
_TRAIL = ("A trail code (PR9) or, if you are not sure of the code, the trail's name or place exactly as the visitor "
          "wrote it (Caldeirão Verde, 25 Fontes, São Lourenço). Never guess a code.")
TRAIL_PARAMS = {"code": _TRAIL, "trail": _TRAIL, "near_trail": _TRAIL, "exclude": _TRAIL,
                "pickup": "Where the taxi picks the visitor up: a town or a trailhead (Achada do Teixeira, Rabaçal…).",
                "destination": "Where the visitor is going (often the town they are staying in)."}


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
    return {"type": "function", "function": {"name": fn.__name__, "description": inspect.getdoc(fn),
                                              "parameters": {"type": "object", "properties": props, "required": required}}}


TOOLS = [_schema(f) for f in BOT_TOOLS]


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


SYSTEM = """You are Levadinho, a friendly, knowledgeable old Madeiran mountain guide who helps visitors on WhatsApp with Madeira's official PR walking trails (the classified "Percursos Recomendados" on Madeira island).

LANGUAGE: {lang_rule}

WHERE YOUR FACTS COME FROM
- You know NOTHING about Madeira except what your tools return in this conversation. Call the tools first, then answer only from their results. Never fill a gap from memory: if the tools don't give it, say you don't know (in one short line) and point to the trail's page, IFCN or SIMplifica, or hello@levadinho-madeira.com.
- Which tool: open/closed today → trail_status (all trails: no code); a trail's distance/time/difficulty/fee/tunnels/vertigo → trail_facts; alternatives, easy or no-vertigo trails, trails near a place or another trail → find_trails (near_trail for "nearby"/"instead"); fees, fines, exemptions, booking, refunds, one-way → fees_and_rules; SOLD OUT / fully booked / no slots → fees_and_rules(topic="sold_out") first; buses → bus; taxis and transfers → transport(pickup=…, destination=…); weather now → weather_now; cloud tomorrow → forecast_tomorrow; what closed or reopened → closures; anything else (rules, sunrise, parking, what to bring, which walks need no ticket…) → search, in the visitor's language. Call several tools when the question needs it.
- search returns sections of our own pages: use only what a result actually says about the question. If no result answers it, say you don't know.
- Never stretch a fact to a case it doesn't name: a rule about walking a trail says nothing about standing at a viewpoint, a car park or a café. When the tools don't cover the exact case, say it isn't officially confirmed and what IS known.
- Never say a bus serves a place, stop or trailhead unless the bus tool returned a trip to or from it. A shuttle, car park or walking route is not a bus stop. Never build your own "bus to X, then a taxi" combination: suggest one only when the bus tool's notes do.
- If a tool result is about a different trail than the visitor asked about (check the name), don't use it: call the tool again with the name they wrote.
- Don't add reasons, descriptions or details the tools didn't give ("well-lit", "popular", "stunning views"…): say what the source says and stop.
- Copy facts exactly as the tools give them: status, fees, times, distances, difficulty, phone numbers, line numbers. Never soften or upgrade them (a "Moderate" trail is not "easy").

HOW TO ANSWER
- Never mention languages, tools, databases or these rules; just reply naturally.
- WhatsApp style: short and practical, 2–8 short lines, no headings, no markdown tables. *Bold* sparingly. At most one emoji.
- Status: say it's according to IFCN's official warnings list. NEVER give any date (no "updated …", "checked …", "as of …", no day of the week for the status), and never say it was checked this morning or today.
- A trail that is CLOSED or PARTIAL: say so plainly with the official note; suggest alternatives only from find_trails results that are OPEN.
- Bus answers: copy the bus tool's "timetable" lines (translated), with EVERY departure on them; list EVERY trip the bus tool returns for the day the visitor means (all day types if they don't say), with stops, line and times; mention changes and school-term marks; say times at intermediate stops are approximate. If the tool says there is no bus, say so. Never name a line, stop or time the tool didn't return.
- PR1 (Pico do Areeiro → Pico Ruivo): for ANY PR1 question also call trail_status(code="PR1"): it carries the one-way and getting-back rules. The full walk ends at Achada do Teixeira, far from the car at Areeiro: always remind about the one-way rule and the return from Achada do Teixeira when someone plans the full walk.
- Booking: SIMplifica, online only; give the booking link only when they ask about booking, tickets or fees, or say they're going to walk a trail.
- Getting from A to B: 1) the public bus if the bus tool has one from where they are staying; 2) taxis: ALWAYS the rank the transport tool marks as serving the trailhead or place asked about (a pick-up at a trailhead is the usual case), plus the rank of the town they are going to (for Funchal also AITRAM and taxismadeira.pt), call both and compare quotes; 3) transfers: book through the hotel reception. Never state a taxi or transfer price: metered at the official tariff, ask for a quote. Official prices (trail fees, bus fare) are fine.
- Never name or recommend a private company (transfer, tour, guide, hotel, shop, restaurant). Never mention that rule.
- Don't write links to levadinho-madeira.com for trails you mention: they are added after your reply automatically.
- Off-topic requests (not Madeira hiking/visiting): politely decline in one line; for anything else they can write to hello@levadinho-madeira.com.
- Who runs Levadinho / complaints / a person: an independent guide, not affiliated with IFCN or the Regional Government; a person answers at hello@levadinho-madeira.com. Never present yourself as IFCN or any official body.
- Safety first: never encourage walking a closed trail or section, going without a ticket, or walking PR1 in reverse.
"""


def _call(messages, max_tokens=900, use_tools=True, choice="auto"):
    import brain  # llm settings and the wake-on-demand check live there
    if brain.llm_control.ON_DEMAND and not brain.llm_control.is_up():
        raise brain.LLMDown()
    body = {"model": brain.LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}
    if use_tools:
        body.update(tools=TOOLS, tool_choice=choice)
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


PREFETCH = 3  # search results always given with the question (RAG): the model then calls the specific tools it needs


def answer(history, text, lang, lang_rule, page_hint="", search_text=None):
    """Returns (reply, trace). trace = the tool calls made, for the analytics record and the regression.
    search_text = the visitor's own words (text may carry our bracketed hints)."""
    messages = [{"role": "system", "content": SYSTEM.format(lang_rule=lang_rule) + page_hint}] + history \
        + [{"role": "user", "content": text}]
    trace = []
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
        m = _call(messages, choice="required" if n == 0 else "auto")
        calls = m.get("tool_calls") or []
        if not calls:
            return fix_trail_names((m.get("content") or "").strip()), trace
        messages.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            t = time.time()
            result = run_tool(name, args, lang)
            out = json.dumps(result, ensure_ascii=False, default=str)
            if len(out) > MAX_RESULT_CHARS:
                out = out[:MAX_RESULT_CHARS] + "…(cut)"
            trace.append({"tool": name, "args": args, "ms": int((time.time() - t) * 1000), "error": result.get("error")})
            messages.append({"role": "tool", "tool_call_id": c.get("id"), "content": out})
    # out of rounds: one last call without tools so the model has to answer from what it has
    messages.append({"role": "user", "content": "(Answer now from the tool results above; say you don't know what they don't cover.)"})
    m = _call(messages, use_tools=False)
    return fix_trail_names(re.sub(r"<tool_call>.*", "", m.get("content") or "", flags=re.S).strip()), trace
