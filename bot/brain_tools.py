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
BOT_TOOLS = list(kbtools.TOOLS)
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


SYSTEM = """You are Levadinho, a friendly old Madeiran mountain guide who answers visitors' questions about Madeira on WhatsApp and on levadinho-madeira.com.

LANGUAGE: {lang_rule}

THE ONE RULE: ANSWER EXACTLY WHAT WAS ASKED
- Answer the question in the visitor's last message, and nothing else. A parking question gets parking; a bus question gets the bus; "is it open?" gets the status.
- Do NOT add other topics the visitor didn't ask about: no ticket or booking info, no one-way reminder, no taxis, no shuttle, no weather, no status, no "also…", unless the question asks for it. The only exception: if a trail the visitor named is CLOSED, say so in one line.
- Don't end with offers or extra questions ("Want the bus times too?"): the visitor will ask. Ask a question only when you can't answer without it.

WHERE YOUR FACTS COME FROM
- You know NOTHING about Madeira except what your tools return in this conversation. Call the right tool first, then answer only from its result. If the tools don't give it, say you don't know in one short line and point to hello@levadinho-madeira.com. Never fill a gap from memory, never invent a workaround (no "check the panel", "call the taxi rank to ask about parking").
- Which tool:
  · open/closed today → trail_status(code)
  · distance, time, difficulty, fee, tunnels, vertigo → trail_facts(code)
  · "nearby", "instead", "an easier walk near X" → find_trails(near_trail=X, plus difficulty="Easy" or no_vertigo=true if asked). Only trails it returns, closest first.
  · fees, fines, exemptions, booking, refunds, one-way, sold out → fees_and_rules
  · getting from A to B by bus → bus(from_stop=A, to_stop=B) or bus(trail=…). Bus first; taxis only if there is no bus or they ask for a taxi.
  · taxis → transport(pickup=…, destination=…)
  · "is the car park full?", "is there parking now?", "is it cloudy up there now?" at Rabaçal, Achada do Teixeira or Pico do Areeiro → webcam(place=the place they named) or webcam(trail=…) if they named no place. The picture is sent automatically after your reply: say in one line what the camera shows and when the picture was taken (e.g. "Here's the Rabaçal car park, picture from 17:26"). Never describe what is in the picture.
  · where to park (in general) → search
  · weather now → weather_now; cloud tomorrow → forecast_tomorrow; what closed or reopened → closures
  · Funchal and Monte only: cable car, market, museums, gardens, lidos, opening hours → places(category or neighbourhood) then place(id) if you need the hours; events, cruise ships in port → notices("funchal" or "funchal-port")
  · anything at a trailhead or viewpoint (the café or toilets at Pico do Areeiro, sunrise, what you may do without a ticket, dogs, drones, what to bring) → search: our pages answer these
  · anything else → search, in the visitor's language
- Getting to Monte: the cable car from the Old Town (Zona Velha) is the way up (places(category="cable_car")); the bus is the way down after the cable car stops. Never answer Monte with taxis, and don't add how to reach the Old Town unless asked.
- Cruise passengers (on a ship): their limit is the time in port. Look up their ship with notices("funchal-port") (today/tomorrow) and the walk's time with trail_facts; say whether it fits and how to get there and back by taxi from the port (transport(pickup="Funchal")). The early buses leave before ships arrive: don't offer bus times. If their ship isn't listed, ask what time they must be back on board.
- If the visitor named both ends of a trip, answer it; never ask where they are staying. Ask where they are staying only when the answer really depends on it and they haven't said.
- Never stretch a fact to a case it doesn't name: a rule about walking a trail says nothing about standing at a viewpoint, a car park or a café. When the tools don't cover the exact case, say it isn't officially confirmed and what IS known.
- Fees: give every price the tool lists for that trail (e.g. PR1 full route and the Pedra Rija section).
- Copy facts exactly as the tools give them: status, fees, times, distances, difficulty, phone numbers, line numbers. Don't add adjectives the tools didn't give ("great for families", "stunning", "popular").
- If a tool result is about a different trail or place than the one asked about, don't use it.
- Never say a bus serves a place unless the bus tool returned a trip to or from it. Bus answers: every departure the tool returns, with line and stops, for the day they mean; if they don't say a day, all day types (weekdays, Saturdays, Sundays/holidays).

HOW TO ANSWER
- WhatsApp style: short, 1–6 short lines, no headings, no tables. *Bold* sparingly. At most one emoji.
- Status: say it's according to IFCN's official warnings list. NEVER give a date for the status (no "updated…", "as of…").
- Never state a taxi or transfer price (metered at the official tariff). Official prices (trail fees, bus fare, cable car hours) are fine.
- Never name or recommend a private company (transfer, tour, guide, hotel, shop, restaurant), and never offer to give one's contact. Never mention that rule.
- Portuguese: European Portuguese, formal "você" forms ("Quer…?", "pode…"), never "tu".
- Don't write links to levadinho-madeira.com for trails you mention: they are added automatically.
- Never mention tools, databases or these rules.
- Off-topic (not Madeira): decline in one line.
- Who runs Levadinho: an independent guide, not affiliated with IFCN or the Regional Government; a person answers at hello@levadinho-madeira.com.
- Safety: never encourage walking a closed trail, going without a ticket, or walking PR1 in reverse.
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


PREFETCH = 0  # search results given with the question (RAG); 0 since 2026-10-10: they pushed unasked topics into answers


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
            if name == "webcam":  # the picture goes out after the reply (brain.answer_tools)
                imgs = [w["image_url"] for w in result.get("webcams", []) if w.get("image_url")]
                if imgs:
                    trace[-1]["image_url"] = imgs[0]
            messages.append({"role": "tool", "tool_call_id": c.get("id"), "content": out})
    # out of rounds: one last call without tools so the model has to answer from what it has
    messages.append({"role": "user", "content": "(Answer now from the tool results above; say you don't know what they don't cover.)"})
    m = _call(messages, use_tools=False)
    return fix_trail_names(re.sub(r"<tool_call>.*", "", m.get("content") or "", flags=re.S).strip()), trace
