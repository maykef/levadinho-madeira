"""Code-level discipline for model answers (owner, 2026-10-10: "fix the indiscipline").

The prompt already had these rules and the local model broke them in real chats (4-8 Oct). So every model reply
passes through check() before it is sent:
  1. no private company names: a sentence naming one is dropped (known names + "X Transfers / Tours / Hikes…" +
     "X Madeira" that isn't an official body);
  2. no "I'm an independent guide" self-introduction, unless the visitor asked who runs Levadinho;
  3. a cruise passenger never gets "ask your hotel reception";
  4. bus times only as printed: model sentences with a bus word and a time are replaced by the timetable lines;
  5. a trail the visitor named gets its live status first if the reply doesn't state it;
  6. known typos ("metrotrímetro").
Each change is logged in the returned list, kept in the analytics record (what the model said vs. what we sent).
"""
import re

import answers

ALLOWED_MADEIRA = {"visit", "taxis", "táxis", "radio", "rádio", "governo", "região", "regiao", "ilha", "da", "de", "do",
                   "in", "on", "of", "to", "for", "around", "across", "about", "explore", "welcome", "enjoy", "the",
                   "palace"}   # Monte Palace Madeira, the garden in our places list (12 Nov: dropped as a company)
COMPANIES = re.compile(r"\b(beyond madeira|doit madeira|do it madeira|gettohikes|get to hikes|madeira transfers?|"
                       r"happy transfers?|pico transfers|picotransfers|madeira explorers|lido tours|walkme\w*|"
                       r"madeirahiking|madeira hiking|viator|getyourguide|get your guide|civitatis|klook|uber|"
                       r"madeira adventure kingdom|madeira island tours|hike madeira|true spirit|terras de aventura|madeira\.best|madeira best)\b", re.I)
# 18 Nov real chat: "Some operators listed in Visit Madeira's official directories include: - madeira.best: …"
OPERATOR_LIST = re.compile(r"\b(operators?|companies|empresas|opérateurs|op[ée]rateurs|anbieter|unternehmen|firmy|przewoźni\w*)\b"
                           r"[^.\n]{0,80}\b(include|includes|listed|such as|incluem|como|comme|incluent|wie|zum beispiel|takie jak|np\.)",
                           re.I)
WEB_NAME = re.compile(r"\b(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)*)\.(best|com|pt|net|org|eu|de|fr|uk|io|travel|tours)\b", re.I)
OK_DOMAINS = re.compile(r"madeira\.gov|simplifica|visitmadeira|levadinho|ipma|horariosdofunchal|rodoeste|sam\.pt|cam\.pt|"
                        r"taxismadeira|aitram|funchal\.pt|apram|ana\.pt|aeroportomadeira|netmadeira|portaldoclima", re.I)
BRAND = re.compile(r"\b([A-Z][\w'&-]+(?:\s[A-Z][\w'&-]+)*)\s(Transfers?|Tours?|Hikes|Hiking|Excursions|Adventures?|"
                   r"Experiences|Trips|Travel|Shuttles?)\b")
X_MADEIRA = re.compile(r"\b([A-Z][\w'-]+)\s+Madeira\b")
WHO = re.compile(r"who (are|runs|is behind)|quem (é|e|és|es|gere)|qui (êtes|etes|gère|gere)|wer (bist|sind|steckt)|"
                 r"kim (jesteś|jestes)|kto prowadzi", re.I)
SELF_GUIDE = re.compile(r"\b(independent guide|guia independente|guide indépendant|guide independant|"
                        r"unabhängige[rn]? (guide|führer|reiseführer)|niezależny przewodnik)\b", re.I)
RECEPTION = re.compile(r"\b(hotel reception|reception of your hotel|receção do (seu )?hotel|recepção do (seu )?hotel|"
                       r"réception (de votre |de l')?h[oô]tel|hotelrezeption|rezeption (ihres|deines) hotels|recepcj\w* hotel\w*)\b", re.I)
BUS_WORD = re.compile(r"\b(bus|buses|autocarro|autocarros|autobus|autobusy|autobusem|navette|busse|linha|line)\b", re.I)
HHMM = re.compile(r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b")
TYPOS = [(re.compile(r"metrotr[ií]metro", re.I), "taxímetro"), (re.compile(r"\btaximetro\b", re.I), "taxímetro")]
# "for real-time availability check the IFCN panel / call the taxi rank" (10 Oct, Rabaçal car park): made-up advice
WORKAROUND = re.compile(r"(real[- ]time|availability|disponibilidade|en temps réel|verfügbarkeit|dostępnoś)\w*.{0,80}"
                        r"(panel|painel|panneau|tafel|tablic|call|ligue|appelez|rufen|zadzwoń)|"
                        r"(panel|painel|panneau|call|ligue|appelez|rufen|zadzwoń).{0,80}(real[- ]time|availability|disponibilidade)", re.I)
RETELL = re.compile(r"\b(open|closed|restricted|one[- ]way|both (ways|directions)|direction|status|ifcn|aberto|encerrad\w*|"
                    r"sentido|ambos|estado|ouvert|fermé|sens unique|statut|geöffnet|gesperrt|richtung|status|otwart\w*|"
                    r"zamkni\w*|kierun\w*)\b", re.I)
# "want the contact for a transfer company…?" (10 Oct): an offer to name a private company
COMPANY_OFFER = re.compile(r"(transfer|tour|shuttle|guide|guia|transfert|reiseführer|przewodnik)\w*\s+(company|companies|empresa|"
                           r"société|agence|unternehmen|firm\w*|operator\w*)", re.I)
NOT_TRAIL = re.compile(r"\b(cafe|caf[eé]s?|restaurant\w*|bar|shop|loja|market|mercado|museum|museu|cable|telef\w*|lido|toilet\w*|"
                       r"wc|car ?park|parking|parque|estacionamento|parkplatz|parking|supermarket|pharmacy|farmacia)\b", re.I)
# topics no official source regulates (owner, 2026-10-22: the model kept inventing a cycling ban at temp 0,
# even with the kb sheet in context): if the visitor asked about one and the reply asserts a prohibition,
# the whole reply becomes the honest no-rule sentence
NO_RULE_TOPIC = re.compile(r"\b(bike\w*|bicycl\w*|cycl\w*|mountain ?bik\w*|rower\w*|fahrr[aä]d\w*|radfahren|v[eé]los?|"
                           r"bicicleta|"  # dogs (on PR1) and drones have a rule since 2026-10-26 (Levadinho's guide)
                           r"camp\w*|zelt\w*|biwak\w*|acampar|namiot\w*|picnic\w*|piquenique|barbecue|grill\w*)\b", re.I)
PROHIBIT = re.compile(r"\b(not (allowed|permitted)|forbidden|prohibited|banned|nicht (erlaubt|gestattet)|verboten|"
                      r"interdit\w*|pas autoris\w*|n[aã]o ([eé] )?(permitid\w*|autorizad\w*)|proibid\w*|"
                      r"zakazan\w*|zabronion\w*|niedozwolon\w*)\b", re.I)
NO_RULE_ANSWER = {
    "en": "Our official sources (IFCN, SIMplifica, the Portarias) have no rule about that on the levadas, so I "
          "can't say whether it is allowed. You can ask hello@levadinho-madeira.com.",
    "pt": "As nossas fontes oficiais (IFCN, SIMplifica, as Portarias) não têm nenhuma regra sobre isso nas "
          "levadas, por isso não posso dizer se é permitido. Pode perguntar a hello@levadinho-madeira.com.",
    "fr": "Nos sources officielles (IFCN, SIMplifica, les Portarias) n'ont aucune règle à ce sujet sur les "
          "levadas, je ne peux donc pas dire si c'est autorisé. Vous pouvez écrire à hello@levadinho-madeira.com.",
    "de": "Unsere offiziellen Quellen (IFCN, SIMplifica, die Portarias) enthalten dazu keine Regel für die "
          "Levadas, daher kann ich nicht sagen, ob es erlaubt ist. Sie können hello@levadinho-madeira.com fragen.",
    "pl": "Nasze oficjalne źródła (IFCN, SIMplifica, Portarie) nie zawierają żadnej reguły na ten temat na "
          "levadach, więc nie mogę powiedzieć, czy to dozwolone. Można zapytać hello@levadinho-madeira.com.",
}
MONTE = re.compile(r"\bmonte\b", re.I)
# a cruise passenger, any language and word form ("porto de cruzeiros" slipped past answers.CRUISE_RE, 24 Oct)
SHIP_STEM = re.compile(r"cruis|cruzeir|croisi|paquebot|kreuzfahrt|schiff|statk|wycieczkow|navio|\bship", re.I)
TAXI_ASKED = re.compile(r"\b(taxi|táxi|taxis|táxis|taksówk\w*|uber|bolt)\b", re.I)
MONTH = re.compile(r"(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember|"
                   r"stycz|lut|mar|kwie|maj|czerw|lip|sierp|wrze|paźdz|pazdz|listop|grud)", re.I)
SENT = re.compile(r"(?<=[.!?])\s+|\n")


ABBREV = re.compile(r"(?:\b(?:z|B|e\.g|i\.e|ex|p|np|bzw|usw|ca|vgl|etc|approx|aprox|env|tzn|m\.in|ok)\.|\(\s*\w{1,3}\.)$", re.I)


ONE_DAY = re.compile(r"\b(today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekend|weekday|"
                     r"hoje|amanha|segunda|terca|quarta|quinta|sexta|sabado|domingo|fim de semana|aujourd|demain|lundi|"
                     r"mardi|mercredi|jeudi|vendredi|samedi|dimanche|heute|morgen|montag|dienstag|mittwoch|donnerstag|"
                     r"freitag|samstag|sonntag|wochenende|dzis|jutro|poniedzial\w*|wtor\w*|srod\w*|czwart\w*|piat\w*|sobot\w*|"
                     r"niedziel\w*|weekend)\b", re.I)


def _sentences(text):
    """Split keeping line breaks: [(sentence, separator)]. A full stop that ends an abbreviation ("z. B.", "e.g.",
    "p. ex.", "np.") doesn't end the sentence (24 Oct: "(z. B. Beyond Madeira…)" was cut after "z. B." and the
    company half dropped, leaving "(z. B." in the reply)."""
    out, start = [], 0
    for m in SENT.finditer(text):
        if m.group(0) != "\n" and "\n" not in m.group(0) and ABBREV.search(text[start:m.start()]):
            continue
        # a German/Polish date's ordinal dot ("den 02. November", "2. listopada") doesn't end the sentence (1 Nov test:
        # "Am Montag, den 02." was left alone when the times after it were dropped)
        if m.group(0) != "\n" and "\n" not in m.group(0) and re.search(r"\b\d{1,2}\.$", text[start:m.start()]) \
                and MONTH.match(text[m.end():]):
            continue
        out.append((text[start:m.start()], m.group(0)))
        start = m.end()
    out.append((text[start:], ""))
    return out


def _drop(text, pred):
    kept, dropped = [], []
    for s, sep in _sentences(text):
        if s.strip() and pred(s):
            dropped.append(s.strip())
            continue
        kept.append(s + sep)
    return re.sub(r"\n{3,}", "\n\n", "".join(kept)).strip(), dropped


# 18 Nov real chats: "When will PR1 reopen?" -> "I don't have information about when it will reopen" (owner: never)
REOPEN_ASK = re.compile(r"re-?open|open again|reabr|volt\w* a abrir|rouvr|wieder (offen|geöffnet|öffn)|öffnen .*wieder|"
                        r"ponownie otwar|zostan\w* otwart|kiedy\b.*otwar", re.I)
NO_INFO = re.compile(r"\b(I|we) (don'?t|do not|cannot|can'?t) (have|give)\b[^.\n]{0,50}\b(date|information|info|forecast|timeline)|"
                     r"\bn[aã]o (tenho|temos|há)\b[^.\n]{0,40}\b(informa|data|previs)|"
                     r"\b(je n'ai|nous n'avons) (pas|aucune?)\b[^.\n]{0,40}\b(date|information|pr[ée]vision)|"
                     r"\b(ich habe|wir haben) keine\b[^.\n]{0,40}\b(datum|information|angabe|prognose)|"
                     r"\bnie (mam|mamy)\b[^.\n]{0,40}\b(informacj|dat|prognoz)", re.I)
REOPEN_LINE = {
    "en": "Whether a closed trail reopens is IFCN's decision, announced on its trail-warnings list: we can't predict it, so book flexibly.",
    "pt": "A reabertura de um percurso encerrado é decisão do IFCN, anunciada na sua lista de avisos: não a podemos prever, por isso reserve com flexibilidade.",
    "fr": "La réouverture d'un sentier fermé est une décision de l'IFCN, annoncée sur sa liste d'avis : nous ne pouvons pas la prévoir, réservez donc avec souplesse.",
    "de": "Ob ein gesperrter Weg wieder öffnet, entscheidet das IFCN auf seiner Hinweisliste: Wir können das nicht vorhersagen, buchen Sie also flexibel.",
    "pl": "O ponownym otwarciu zamkniętego szlaku decyduje IFCN na swojej liście ostrzeżeń: nie możemy tego przewidzieć, więc rezerwuj elastycznie.",
}
# 14 Nov real chat: "And tomorrow" -> "PR1.3 is closed tomorrow according to IFCN" (IFCN's list gives today only)
TOMORROW_ASK = re.compile(r"tomorrow|amanh[aã]|demain|morgen|jutr", re.I)
TOMORROW_W = re.compile(r"\b(tomorrow|amanh[aã]|demain|morgen|jutr\w*)\b", re.I)
STATUS_W = re.compile(r"\b(closed|open|encerrad\w*|fechad\w*|abert\w*|ferm[ée]e?s?|ouvert\w*|gesperrt|geschlossen|geöffnet|offen|"
                      r"zamkni\w*|otwart\w*)\b", re.I)
SKY_W = re.compile(r"cloud|nuv|nubl|nuag|wolk|bewölk|chmur|rain|chuv|pluie|regen|deszcz|wind|vent|sun|sol|soleil|sonne|słoń", re.I)
NO_TOMORROW = {
    "en": "IFCN's list gives today's status only, not tomorrow's: check it again tomorrow morning.",
    "pt": "A lista do IFCN indica apenas o estado de hoje, não o de amanhã: confirme-a de novo amanhã de manhã.",
    "fr": "La liste de l'IFCN ne donne que l'état du jour, pas celui de demain : revérifiez-la demain matin.",
    "de": "Die IFCN-Liste zeigt nur den heutigen Status, nicht den von morgen: Prüfen Sie sie morgen früh erneut.",
    "pl": "Lista IFCN podaje tylko dzisiejszy stan, nie jutrzejszy: sprawdź ją ponownie jutro rano.",
}


def _names_company(s):
    if COMPANIES.search(s) or BRAND.search(s) or COMPANY_OFFER.search(s) or OPERATOR_LIST.search(s):
        return True
    if any(not OK_DOMAINS.search(m.group(0)) for m in WEB_NAME.finditer(s) if "@" not in s[max(0, m.start() - 1):m.start()]):
        return True
    return any(m.group(1).lower() not in ALLOWED_MADEIRA for m in X_MADEIRA.finditer(s))


STAY_ASK = re.compile(r"accommodation|where (should|could|to|do) (we |i )?(stay|base)|alojamento|onde (ficar|nos hospedar)|"
                      r"unterkunft|übernachten|hébergement|où (loger|dormir|séjourner)|nocleg|gdzie (się )?(zatrzymać|nocować)", re.I)
STAY_TIP = re.compile(r"booking (platform|site|website)|platforms?\b|plataforma|tourism office|tourist office|posto de turismo|"
                      r"office de tourisme|touristeninformation|informacj\w* turystyczn|airbnb|booking\.com|expedia|"
                      r"agenc(y|ies)|agência|agence|reisebüro|biur\w* podróży|hotel website", re.I)
STAY_ANSWER = {"en": "Levadinho doesn't advise on where to stay.", "pt": "O Levadinho não dá conselhos sobre alojamento.",
               "fr": "Levadinho ne donne pas de conseils d'hébergement.", "de": "Levadinho gibt keine Empfehlungen zu Unterkünften.",
               "pl": "Levadinho nie doradza w sprawie noclegów."}


_TOOL_NAMES = "|".join(sorted({f.__name__ for f in answers.kbtools.TOOLS} | {"taxi_prices", "day_plan", "weather_forecast"},
                               key=len, reverse=True))
# 11 Nov real chat: "For contact numbers, call the transport tool." The model's own plumbing never reaches a visitor.
TOOL_LEAK = re.compile(r"\b(" + _TOOL_NAMES + r")\s*\(|\b(" + "|".join(n for n in _TOOL_NAMES.split("|") if "_" in n)
                       + r")\b|how_to_answer|reply_exactly|\b(call|use|chame|chamar|use a|usar|appele[zr]?|utilise[zr]?|aufrufen|"
                       r"verwende\w*|nutze\w*|wywołaj|użyj)\b.{0,30}\b(tool|tools|ferramenta\w*|outil\w*|werkzeug\w*|"
                       r"narzędzi\w*)\b|\b(" + _TOOL_NAMES + r")\s+(tool|ferramenta|outil|werkzeug|narzędzi\w*)\b|"
                       r"\b(tool|werkzeug|outil|narzędzi\w*)\s+[«\"']?(" + _TOOL_NAMES + r")\b",
                       re.I)


def check(reply, user_text, lang, trails, context=""):
    """Returns (reply, changes)."""
    changes = []
    out = reply
    for rx, rep in TYPOS:
        out, n = rx.subn(rep, out)
        if n:
            changes.append(f"typo fixed x{n}")
    out, d = _drop(out, lambda s: bool(TOOL_LEAK.search(s)))
    changes += [f"tool wording dropped: {x[:80]}" for x in d]
    out, d = _drop(out, _names_company)
    changes += [f"company sentence dropped: {x[:80]}" for x in d]
    if not WHO.search(user_text):
        out, d = _drop(out, lambda s: bool(SELF_GUIDE.search(s)))
        if d:
            changes.append("self-introduction as independent guide removed")
    if MONTE.search(user_text) and not TAXI_ASKED.search(user_text):   # owner: Monte = cable car up, bus down; never taxis
        out, d = _drop(out, lambda s: bool(TAXI_ASKED.search(s)))
        changes += [f"taxi sentence dropped (Monte): {x[:80]}" for x in d]
        if d and not re.search(r"[A-Za-zÀ-ž]{3}", out):   # nothing left: the cable car fact from the store
            try:
                out = answers.kbtools.place("cablecar")["description"]
            except Exception:
                pass
    if REOPEN_ASK.search(user_text):
        out, d = _drop(out, lambda s: bool(NO_INFO.search(s)))
        if d:
            changes += [f"'no information' about reopening dropped: {x[:80]}" for x in d]
            if not re.search(r"IFCN[^.\n]{0,60}(decis|décision|entscheid|decyduj)|(decis|décision|entscheid|decyduj)[^.\n]{0,60}IFCN", out, re.I):
                out = out.rstrip() + "\n\n" + REOPEN_LINE.get(lang, REOPEN_LINE["en"])
    if TOMORROW_ASK.search(user_text):
        out, d = _drop(out, lambda s: bool(TOMORROW_W.search(s) and STATUS_W.search(s) and not SKY_W.search(s)))
        if d:
            changes += [f"status for tomorrow dropped: {x[:80]}" for x in d]
            for code in trails[:1]:
                line = answers.status_line(code, lang)
                if line and line[:40] not in out:
                    out = line + "\n\n" + out
            out = out.rstrip() + "\n\n" + NO_TOMORROW.get(lang, NO_TOMORROW["en"])
    out, d = _drop(out, lambda s: bool(WORKAROUND.search(s)))
    changes += [f"invented workaround dropped: {x[:80]}" for x in d]
    if STAY_ASK.search(user_text):   # owner: never point to accommodation / booking sites (8 Nov test: "check booking platforms")
        out, d = _drop(out, lambda s: bool(STAY_TIP.search(s)))
        changes += [f"accommodation tip dropped: {x[:80]}" for x in d]
        if d and not re.search(r"[A-Za-zÀ-ž]{3}", out):
            out = STAY_ANSWER.get(lang, STAY_ANSWER["en"])
    if NO_RULE_TOPIC.search(user_text) and any(PROHIBIT.search(s) and NO_RULE_TOPIC.search(s) for s, _ in _sentences(out)):
        out = NO_RULE_ANSWER.get(lang, NO_RULE_ANSWER["en"])
        changes.append("invented prohibition replaced with the no-rule answer")
    full = answers.fold(user_text + " " + context)
    if answers.CRUISE_RE.search(full):
        out, d = _drop(out, lambda s: bool(RECEPTION.search(s)))
        if d:
            changes.append("hotel reception removed (cruise passenger)")
    # Bus times only as printed (owner rule). Work out which direction the reply is about; if it leaves out printed
    # departures (10 Oct: São Lourenço weekdays dropped) or gives a time we don't have, that direction's printed
    # timetable replaces the model's time lines. The other direction is never added unasked.
    legs = []
    # never for a cruise passenger: the printed timetable is the 06:00 bus, before ships dock (24 Oct, live)
    for code in (trails[:1] if not SHIP_STEM.search(full) else []):
        for leg in ("there", "back"):
            tt = answers._bus(code, leg)
            if tt:
                pairs = re.findall(r"(\d{2}:\d{2})→(\d{2}:\d{2})", tt)
                legs.append((code, leg, tt, {a for a, _ in pairs}, {x for p in pairs for x in p}))
    said = {f"{int(h):02d}:{m}" for h, m in HHMM.findall(out)}
    if legs and len(said) >= 2:
        # the directions the reply is about: most of their departure times appear in it
        covered = [l for l in legs if l[3] and len(said & l[3]) / len(l[3]) >= 0.5] or \
                  [l for l in [max(legs, key=lambda l: len(said & l[3]))] if len(said & l[3]) >= 3]
        known = set().union(*(l[4] for l in legs))
        # a day was asked ("amanhã", "on Sunday"): that day's trips are a correct subset, so only an invented time
        # brings the full table back (1 Nov test: "Há autocarro para o PR8 amanhã?" got every day type, in English)
        one_day = bool(ONE_DAY.search(answers.fold(user_text)))
        if covered and ((not one_day and any(l[3] - said for l in covered)) or said - known):
            out, d = _drop(out, lambda s: bool(HHMM.search(s)) and (BUS_WORD.search(s) or len(HHMM.findall(s)) >= 3
                                                                   or len(re.sub(r"[\d:→,\s*\-–()|]", "", s)) < 25))
            out = re.sub(r"\n?\*[^*\n]{3,40}:\*\s*(?=\n|$)", "", out)     # day headings left without times
            tables = []
            for code, leg, tt, _deps, _every in covered:
                head = (answers.T["there_bus"] if leg == "there" else answers.T["back_bus"])[lang].format(tt="")
                tables.append(head.rstrip(": ") + ":\n" + "\n".join("• " + x.strip() for x in tt.split(" | ")))
                changes.append(f"timetable replaced with the printed one: {code} {leg}")
            table = "\n\n".join(tables)
            parts = out.rsplit("\n\n", 1)
            if len(parts) == 2 and parts[1].strip().endswith("?"):   # keep a closing question last
                out = parts[0] + "\n\n" + table + "\n\n" + parts[1]
            else:
                out += "\n\n" + table
    heads = []
    CLOSED_WORDS = re.compile(r"\b(closed|clos|fechad\w*|encerrad\w*|ferm[ée]e?s?|geschlossen|gesperrt|zamkni\w*)\b", re.I)
    # "is the café / market / cable car open?" is not a question about a trail's status
    asked_status = bool(answers.STATUS_RE.search(answers.fold(user_text))) and not NOT_TRAIL.search(answers.fold(user_text))
    # a trail's state, not the sky: "partly cloudy", "parcialmente nublado", "partiellement nuageux"… stay (25 Oct)
    partial_rx = re.compile(r"\b(partly|partially|partial|parcialmente|partiellement|partiel|teilweise|częściowo|czesciowo)\b"
                            r"(?!\s+(cloud|nublad|nuag|bewölk|bewolk|pochmur|zachmurz|słonecz|sunny|ensolarad|ensoleill))", re.I)
    try:
        blanket = ((answers._status_data().get("alert") or {}).get("blanket")) == "closed"
    except Exception:  # noqa: BLE001
        blanket = False
    for code in trails[:2]:
        t = answers._trail(code)
        if not t:
            continue
        if t["status"] == "PARTIAL":   # owner: never "partly open" — the full description instead
            out, d = _drop(out, lambda s: bool(partial_rx.search(s)))
            if d:
                changes.append(f"'partly open' wording replaced: {code}")
            if asked_status:
                # the official description is the answer: drop the model's own retelling of directions / status
                out, d2 = _drop(out, lambda s: bool(RETELL.search(s)))
                if d2:
                    changes.append(f"status retelling dropped: {code}")
                heads.append(answers.status_line(code, lang))
            elif d:  # 20 Oct: the dropped sentence was the status ("PR1 tomorrow at 9h?"): put the official one back
                out, _ = _drop(out, lambda s: bool(RETELL.search(s)))
                heads.append(answers.status_line(code, lang))
            continue
        # owner, 2026-10-10: answer only what was asked — the status goes first only when the question is about it,
        # or the trail is CLOSED (safety); never pasted in front of a parking or bus answer
        words = [answers.ST[t["status"]][lang].lower()]
        if blanket:
            # storm mode (owner, 2026-11-08 test): the storm lead / the web chat's opening already says every trail is
            # closed; a CLOSED block per trail on top said it two or three times. Only a status question whose reply
            # doesn't say it gets one line, for one trail.
            if asked_status and not heads and not CLOSED_WORDS.search(out):
                heads.append(answers.status_line(code, lang))
            continue
        if (asked_status or t["status"] == "CLOSED") and not any(w in out.lower() for w in words):
            heads.append(answers.status_line(code, lang))
    if heads:
        changes.append("status added: " + ", ".join(trails[:2]))
        out = "\n\n".join(heads) + "\n\n" + out
    if not out.strip():
        out = "\n\n".join(answers.status_line(c, lang) for c in trails[:2]) or reply
        changes.append("reply emptied by the guard: status only")
    return out.strip(), changes
