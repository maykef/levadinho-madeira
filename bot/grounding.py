"""The fact check (owner, 2026-10-25): every hard fact in a reply must come from what the tools returned in that turn,
or from the visitor's own words. A reply that states something no tool gave is asked again once; whatever is still
unsupported is cut; if nothing is left, the reply is a fixed sentence written here, never by the model (owner: "if you
tell the bot we don't know, it will make it up").

What counts as a hard fact (each kind is checked against the same kind in the evidence):
  times      07:30, 9h15, 18h            → a time printed in a tool result (bus trips, webcam picture time…) or the
                                           visitor's time + 3–5 h (the PR1 finish arithmetic)
  money      €4.50, 22,50 €, 35 euros    → an amount in a result, or one multiplied by a group size (2–20) or shared
                                           among 2–10 people
  phones     +351 291 572 540            → the same digits in a result
  durations  45 minutes, 1 h 30, 2 Std   → only when the sentence is about driving ("drive", "de carro", "mit dem
                                           Auto"…): a driving time must be in a result sentence that also talks
                                           about driving. Walking times are checked by the trail tools themselves.
  km         6.2 km                      → a number in a result
  names      Ponta do Pargo, Igreja de…  → a Portuguese-style place name (two capitalised words joined by do/da/
                                           dos/das/de, or after Igreja/Museu/Praia/Miradouro/Piscinas…) must appear in
                                           a result or the visitor's words
What it can't see: a claim with no number or name ("you don't need a 4x4"). Those stay with rules 1 and 4.
"""
import re
import unicodedata

NUM = r"\d+(?:[.,]\d+)?"
TIME_RE = re.compile(r"(?<![\d.,:])([01]?\d|2[0-3])\s?(?:[:h]\s?([0-5]\d)|h(?![a-z]))(?![\d])", re.I)
MONEY_RE = re.compile(rf"€\s?({NUM})|({NUM})\s?(?:€|eur\b|euros?\b|euro\b)", re.I)
PHONE_RE = re.compile(r"(?:\+?351[\s.]?)?(?:2\d{2}|9\d{2}|800)[\s.]?\d{3}[\s.]?\d{3}")
KM_RE = re.compile(rf"({NUM})\s?km\b", re.I)
DUR_RE = re.compile(rf"({NUM})\s?(?:-|–|to|a|à|bis|do)?\s?(?:{NUM}\s?)?(min\w*|h\b|hours?|horas?|heures?|stunden?|std\b|godz\w*)", re.I)
DRIVE_RE = re.compile(r"\b(driv\w*|by car|car ride|de carro|conduzir|condução|en voiture|conduire|route en|mit dem auto|"
                      r"autofahrt|fahrt\w*|samochodem|autem|jazd\w*|dojazd\w*)\b", re.I)
NAME_RE = re.compile(r"\b((?:Igreja|Capela|Museu|Praia|Miradouro|Piscinas?|Forte|Quinta|Ponta|Porto|Pico|Lagoa|Ribeira|"
                     r"Achada|Fajã|Cabo|Ilhéu|[A-ZÀ-Ý][a-zà-ÿ]{2,})\s(?:(?:do|da|dos|das|de|d')\s?)"
                     r"[A-ZÀ-Ý][\wà-ÿ]+(?:\s(?:do|da|dos|das|de)\s[A-ZÀ-Ý][\wà-ÿ]+)*)")
# group sizes written as words ("we are two", "somos três", "nous sommes quatre", "wir sind zu dritt", "jest nas dwoje")
WORD_NUM = {w: n for n, ws in {
    2: "two couple dois duas deux zwei zweit zu zweit dwa dwie dwoje dwoch para",
    3: "three tres trois drei dritt trzy troje",
    4: "four quatro quatre vier viert cztery czworo",
    5: "five cinco cinq funf funft piec piecioro",
    6: "six seis sechs sechst szesc",
    7: "seven sete sept sieben siedem",
    8: "eight oito huit acht osiem",
    9: "nine nove neuf neun dziewiec",
    10: "ten dez dix zehn dziesiec"}.items() for w in ws.split()}
NO_DATA = {
    "en": "I don't have that in my sources. A person answers at hello@levadinho-madeira.com.",
    "pt": "Não tenho essa informação nas minhas fontes. Uma pessoa responde em hello@levadinho-madeira.com.",
    "fr": "Je n'ai pas cette information dans mes sources. Une personne répond à hello@levadinho-madeira.com.",
    "de": "Dazu habe ich nichts in meinen Quellen. Ein Mensch antwortet unter hello@levadinho-madeira.com.",
    "pl": "Nie mam tej informacji w moich źródłach. Człowiek odpowie pod adresem hello@levadinho-madeira.com.",
}


def _fold(t):
    return "".join(c for c in unicodedata.normalize("NFKD", (t or "").lower()) if not unicodedata.combining(c))


def _num(x):
    return round(float(x.replace(",", ".")), 2)


AMPM_RE = re.compile(r"(?<![\d:])(1[0-2]|0?[1-9])(?::([0-5]\d))?\s?(am|pm|a\.m\.|p\.m\.)", re.I)
# a driving time written without a digit: "about an hour", "half an hour", "uma hora", "eine Stunde"…
WORD_DUR = re.compile(r"\b(an hour|half an hour|a few minutes|uma hora|meia hora|une heure|une demi-heure|"
                      r"eine stunde|eine halbe stunde|godzin[eęy]|p[oó]ł godziny)\b", re.I)


def _times(text):
    out = {(int(h), int(m or 0)) for h, m in TIME_RE.findall(text or "")}
    for h, m, ap in AMPM_RE.findall(text or ""):
        h = int(h) % 12 + (12 if ap.lower().startswith("p") else 0)
        out.add((h, int(m or 0)))
    return out


def _money(text):
    return {_num(a or b) for a, b in MONEY_RE.findall(text or "")}


def _phones(text):
    return {re.sub(r"\D", "", p)[-9:] for p in PHONE_RE.findall(text or "")}


def _numbers(text):
    return {_num(n) for n in re.findall(NUM, text or "")}


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


class Evidence:
    """Everything the reply may rest on: the tool results of this turn (their JSON text, money in *_eur fields
    included), the visitor's message and our own notes added to it."""

    def __init__(self, tool_texts, question):
        self.text = "\n".join(tool_texts) + "\n" + (question or "")
        self.fold = _fold(self.text)
        self.times = _times(self.text)
        self.money = _money(self.text) | {_num(v) for v in re.findall(rf'_eur"?\s*:\s*({NUM})', self.text)} \
            | {_num(v) for v in re.findall(rf'"eur"?\s*:\s*({NUM})', self.text)}
        self.phones = _phones(self.text)
        self.numbers = _numbers(self.text)
        # text right around a driving word: a driving time must be written there (JSON has no sentences)
        self.drive_sents = [self.fold[max(0, m.start() - 90):m.end() + 90] for m in DRIVE_RE.finditer(self.fold)]
        # group sizes the visitor gave ("2 of us", "4 adults and a 13-year-old" → 2, 4, 1, 5…): money may be
        # multiplied or shared by these, or by a factor the reply itself writes ("5 × €4.50")
        words = [WORD_NUM[w] for w in re.findall(r"[a-zà-ÿ]+", _fold(question)) if w in WORD_NUM]
        small = sorted([n for n in _numbers(question) if n == int(n) and 1 <= n <= 20] + words)
        self.groups = set(int(n) for n in small) | ({int(sum(small))} if small else set())
        q_times = _times(question)
        for h, m in q_times:  # the PR1 finish: start + about 4 h (3–5 h), to the half hour
            for add in (3, 4, 5):
                for mm in (m, 0, 30):
                    self.times.add(((h + add) % 24, mm))

    def money_ok(self, v, factors=()):
        if v in self.money:
            return True
        ks = (self.groups | set(factors)) - {0, 1}
        return any(abs(a * k - v) < 0.06 or abs(a / k - v) < 0.06 for a in self.money if a for k in ks)


def unsupported(reply, ev):
    """The hard facts in `reply` that the evidence doesn't support, as short strings."""
    out = []
    for h, m in _times(reply):
        if (h, m) not in ev.times:
            out.append(f"{h:02d}:{m:02d}")
    factors = {int(_num(k)) for k in re.findall(rf"({NUM})\s?[×x*]\s?€?|[×x*]\s?({NUM})", reply) for k in k if k}
    for v in _money(reply):
        if not ev.money_ok(v, factors):
            out.append(f"€{v:g}")
    for p in _phones(reply):
        if p not in ev.phones:
            out.append("phone " + p)
    for d in re.findall(r"\b20\d\d-\d\d-\d\d\b", reply):  # no dates in replies (owner rule)
        out.append(d)
    for v in {_num(k) for k in KM_RE.findall(reply)}:
        if v not in ev.numbers:
            out.append(f"{v:g} km")
    for s in _sentences(reply):
        if DRIVE_RE.search(s):
            for n, unit in DUR_RE.findall(s):
                if not any(re.search(rf"(?<![\d.,]){re.escape(n)}\s?(?:-|–|to|a|bis)?\s?(?:{NUM}\s?)?{re.escape(unit[:3].lower())}",
                                     d) for d in ev.drive_sents):
                    out.append(f"driving time {n} {unit}")
            for w in WORD_DUR.findall(s):
                if not any(_fold(w) in d for d in ev.drive_sents):
                    out.append(f"driving time {w}")
    for name in {m.group(1) for m in NAME_RE.finditer(reply)}:
        if _fold(name) not in ev.fold:
            out.append(name)
    return list(dict.fromkeys(out))


def cut(reply, bad):
    """The reply without the sentences that carry an unsupported fact."""
    keep = []
    for line in reply.split("\n"):
        parts = [s for s in re.split(r"(?<=[.!?])\s+", line)]
        parts = [s for s in parts if not any(b.lower() in s.lower() or _hit(b, s) for b in bad)]
        keep.append(" ".join(parts))
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(keep)).strip()
    return out


def _hit(b, s):
    if re.fullmatch(r"\d\d:\d\d", b):
        h, m = int(b[:2]), int(b[3:])
        return (h, m) in _times(s)
    if b.startswith("€"):
        return _num(b[1:]) in _money(s)
    if b.startswith("phone "):
        return b[6:] in _phones(s)
    if b.endswith(" km"):
        return _num(b[:-3]) in {_num(k) for k in KM_RE.findall(s)}
    if b.startswith("driving time "):
        return bool(DRIVE_RE.search(s)) and b[len("driving time "):].split()[0].lower() in s.lower()
    return False


def substantive(text):
    """Something left worth sending: more than a greeting or an emoji."""
    return len(re.findall(r"[A-Za-zÀ-ž]{3,}", text or "")) >= 6
