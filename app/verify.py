"""Verified numbers: every euro amount and percentage in a coach answer is matched against the tool results.

Status per number: "derived" (exact arithmetic on matched numbers: a sum or difference of two numbers from one tool
result or from this answer, a total of the amounts listed just above, or a tool value per 2/3/4/6/12 months), "yours" (the user's own
number), "suggestion" (a percentage offered in a question, not a claim), "verified" (equals a tool value at the shown precision), "rounded" (a tool value rounded to
tens/hundreds, e.g. "about 1,000 €" for 997 €), "unverified" (no source: flagged in the UI and counted in traps).

With explain=True (the coach chat) a number that is not from the data can also be:
"assumption" (a number the coach put into calculate or a tool argument, e.g. a 20 % savings rate or a 7 % return),
"calculated" (a calculate result that used at least one such assumption), or "rule" (a percentage the coach marked as
a rule of thumb in its hidden notes block, accepted only in a sentence that makes no claim about the user's money and
presents no statistic, and says it is a rule of thumb). A calculate result whose amounts all come from the data stays
"verified". In this mode a € only matches a euro field and a % a percentage field, so a count of days or payments can
never make an invented amount green. Notes the coach writes are attached as "note" but never change a status; notes
with other numbers, statistics or claims about the user are dropped.
"""
from __future__ import annotations

import re

# 1,234.50 € | 1 234,50 € | 20 % | 20% | 1234 EUR | 47,10 euroa
_NUM = r"(\d{1,3}(?:[,   ]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_RE = re.compile(_NUM + r"\s?(€|EUR\b|euroa\b|euro\b|%|prosenttia\b|procent\b)", re.IGNORECASE)
_RE_PRE = re.compile(r"(€|EUR)\s?" + _NUM, re.IGNORECASE)  # "€500", "EUR 1,234.50"


def _matches(text: str):
    """(full text, number string, unit) for '500 €' and '€500' forms, in order of appearance."""
    out = [(m.start(), m.group(0), m.group(1), m.group(2)) for m in _RE.finditer(text)]
    taken = [(m.start(), m.end()) for m in _RE.finditer(text)]
    for m in _RE_PRE.finditer(text):
        if not any(a <= m.start() < b for a, b in taken):
            out.append((m.start(), m.group(0), m.group(2), "€"))
    return [o[1:] for o in sorted(out)]


def _parse(raw: str, lang: str = "") -> tuple[float, int]:
    """Language-independent: spaces are thousands; with both ',' and '.', the last one is the decimal mark;
    a single ',' or '.' followed by exactly three digits is a thousands separator, otherwise a decimal mark."""
    s = raw.replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        if re.search(rf"\{sep}\d{{3}}$", s) and s.count(sep) >= 1 and not re.search(rf"\{sep}\d{{1,2}}$", s):
            s = s.replace(sep, "")
        else:
            s = s.replace(sep, ".")
    decimals = len(s.split(".")[1]) if "." in s else 0
    return float(s), decimals


def _collect(obj, path="", out=None):
    out = [] if out is None else out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        v = float(obj)
        out.append((abs(v), path))
        if 0 < abs(v) <= 2 and ("share" in path or "percent" not in path):
            out.append((abs(v) * 100, path + " (as %)"))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _collect(v, f"{path}.{k}" if path else k, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _collect(v, f"{path}[{i}]", out)
    return out


_MILLION = re.compile(r"(?:(\d+(?:[.,]\d+)?)\s*)?\b(million(?:aire|s)?|miljoon\w*|miljonä\w*|miljon\w*)\b", re.IGNORECASE)
# The coach's hidden notes block: every block is removed, also inside a code fence, with "_" or " " in the tag, or cut
# off before its closing tag (a truncated answer).
_NOTES = re.compile(r"(?:```[a-z]*[ \t]*\n?)?[ \t]*<\s*number[-_ ]notes\s*>(.*?)(?:<\s*/\s*number[-_ ]notes\s*>[ \t]*\n?(?:```)?|\Z)",
                    re.DOTALL | re.IGNORECASE)
_STRAY = re.compile(r"<\s*/?\s*number[-_ ]notes\s*>", re.IGNORECASE)
# A claim about the user's own money (EN, FI, SV): such a sentence can't hold a rule of thumb, and a note can't say it.
_DATA_CLAIM = re.compile(
    r"\b(you(?:'re| are| have| had| spend| spent| pay| paid| earn| earned| save| saved| got| use| used| owe)\b"
    r"|your \w+(?: \w+)? (?:is|was|are|were|went|came|costs?|rose|fell)\b|from your (?:account|data|transactions)"
    r"|käytit|käytät|maksat|maksoit|ansaitset|ansaitsit|säästät|säästit|tililläsi|tililtäsi|saldosi|vuokrasi|tulosi|menosi|kulusi|olet"
    r"|du (?:har|hade|spenderar|spenderade|betalar|betalade|tjänar|tjänade|sparar|sparade|är)\b|(?:din|ditt|dina) \w+ (?:är|var|kostar)\b)",
    re.IGNORECASE)
_NOTE_CLAIM = re.compile(r"\b(your (balance|spending|account|transactions|biggest|data|rent|income|salary|pay|bills?|extras?)"
                         r"|sinun|tilisi|dina? (saldo|utgifter|konto|inkomst|lön|hyra))\b", re.IGNORECASE)
_STATISTIC = re.compile(r"\b(most|many|average|on average|typical(ly)?|studies|research|survey|statistic\w*|people|households|"
                        r"finns|experts?|useimmat|keskimäärin|ihmiset|suomalaiset|tutkimu\w*|asiantuntij\w*|de flesta|i genomsnitt|"
                        r"människor|studier|experter)\b", re.IGNORECASE)
# A rule of thumb must say so: without one of these words a percentage is a claim, not general advice.
_RULE_WORD = re.compile(r"rule of thumb|common rule|general rule|guideline|nyrkkisääntö|yleinen (?:sääntö|ohje)|tumregel|"
                        r"allmän regel|riktlinje", re.IGNORECASE)
_PCT_UNITS = ("%", "prosenttia", "procent")
# Plain unit conversions inside calculate (months, weeks, days, a whole): neither data nor an assumption.
_NEUTRAL = {0, 1, 2, 3, 4, 6, 7, 12, 24, 30, 31, 52, 100, 365}
# Which tool fields are euro amounts and which are percentages; counts, days and months are neither.
_EUR_KEY = re.compile(r"(eur|amount|balance|salary|total|price|cost|income|spend|value|deepest|median)(\b|_|$)|_month$", re.IGNORECASE)
_PCT_KEY = re.compile(r"(percent|share|rate|pct|\(as %\))", re.IGNORECASE)


_COUNT_KEY = re.compile(r"^(transactions|payments|n|count|n_\w+|\w*_count|months\w*|\w*_months|days\w*|\w*_days|times\w*|"
                        r"\w*hours\w*|paydays|age|year|weekday|key|seq|rank|score|points|customers)$", re.IGNORECASE)


def _kind_of(path: str) -> str:
    """'eur', 'pct' or 'other' for a source path such as get_spending.breakdown[2].total_eur or
    get_cashflow.spending_eur.Everyday extras (a euro amount under a euro parent)."""
    p = str(path)
    segs = [x for x in re.split(r"[.\[\]]", p.replace(" (as %)", "")) if x and not x.isdigit()]
    last = segs[-1] if segs else ""
    if " (as %)" in p or _PCT_KEY.search(last):
        return "pct"
    if _COUNT_KEY.match(last):
        return "other"
    if p.startswith("customer.balance") or any(_EUR_KEY.search(x) for x in segs[1:] or segs):
        return "eur"
    return "other"


class _User(str):
    """'your question', remembering what kind of number the user typed: 'pct' (20 %), 'eur' (500 €, $4000, a million),
    'other' (a bare 4000) or 'time' (20 years). A duration is never an amount: "20 years" must not make "20 %" theirs."""
    def __new__(cls, kind: str):
        o = super().__new__(cls, "your question")
        o.kind = kind
        return o


_AFTER_PCT = re.compile(r"\s?(%|prosent\w*|procent\w*|percent\b)", re.IGNORECASE)
_AFTER_EUR = re.compile(r"\s?(€|eur\b|euro\w*|e\b)", re.IGNORECASE)
_AFTER_TIME = re.compile(r"\s?(-?\s?)(years?|yrs?|months?|weeks?|days?|v\b|vuo\w*|kuuka\w*|kk\b|viik\w*|päiv\w*|år\w*|månad\w*|veck\w*|dag\w*)",
                         re.IGNORECASE)


def _user_numbers(text: str) -> list[tuple[float, "_User"]]:
    """Every number the user typed, with its kind (see _User)."""
    out = []
    for m in re.finditer(_NUM, text):
        try:
            v = _parse(m.group(0))[0]
        except ValueError:
            continue
        after, before = text[m.end():m.end() + 14], text[max(0, m.start() - 4):m.start()]
        if _AFTER_PCT.match(after):
            kind = "pct"
        elif _AFTER_TIME.match(after):
            kind = "time"
        elif _AFTER_EUR.match(after) or re.search(r"(€|\$|eur)\s?$", before, re.IGNORECASE):
            kind = "eur"
        else:
            kind = "other"
        out.append((v, _User(kind)))
    return out


class _Src(str):
    """A source label ("get_spending.total_eur") that also remembers its trace entry and path, so the app can describe
    the number in plain words (category, period, payments) and list the payments behind it."""
    def __new__(cls, label: str, ti: int | None = None, path: str = ""):
        o = super().__new__(cls, label)
        o.ti, o.path = ti, path
        return o


def _word_numbers(text: str) -> list[float]:
    """'millionaire', 'a million', '2 million', 'miljoona', 'miljon' -> euro amounts the user named in words."""
    out = []
    for m in _MILLION.finditer(text):
        try:
            k = _parse(m.group(1))[0] if m.group(1) else 1.0
        except ValueError:
            k = 1.0
        out.append(k * 1_000_000)
    return out


def split_notes(text: str) -> tuple[str, list[dict]]:
    """Remove the coach's hidden notes blocks. Lines: '<number with unit>|note|<why>' or '<number>|rule|<why>'."""
    blocks = [m.group(1) for m in _NOTES.finditer(text)]
    if not blocks and not _STRAY.search(text):
        return text, []
    clean = _STRAY.sub("", _NOTES.sub("", text)).strip()
    notes = []
    for line in "\n".join(blocks).splitlines():
        parts = [p.strip() for p in line.strip().lstrip("-• ").split("|", 2)]
        if len(parts) != 3 or not parts[2]:
            continue
        hit = _matches(parts[0])
        if not hit:
            continue
        try:
            val = _parse(hit[-1][1])[0]
        except ValueError:
            continue
        own = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", parts[0])]  # "10-20 %" is one number field
        notes.append({"value": val, "own": own, "pct": hit[-1][2] in _PCT_UNITS, "kind": parts[1].lower(), "note": parts[2][:200]})
    return clean, notes


def _sentence(answer: str, start: int) -> str:
    """The sentence around position start (a decimal point like 2,412.60 is not a sentence end)."""
    cuts = [m.end() for m in re.finditer(r"[.!?](?=\s|$)|\n", answer)]
    a = max([c for c in cuts if c <= start], default=0)
    b = min([c for c in cuts if c > start], default=len(answer))
    return answer[a:b]


def _hit(val: float, dec: int, pool, rounding: bool = True):
    """First (status, source) in pool equal to val at its precision, or rounded to 10/50/100."""
    tol = 0.5 * 10 ** -dec + 1e-6
    for v, p in pool:
        if abs(round(v, dec) - val) < 1e-6 or abs(v - val) <= tol:
            return "exact", p
    if rounding and dec == 0 and val >= 10:
        for v, p in pool:
            for step in (10, 50, 100):
                if val % step == 0 and abs(v - val) <= step / 2 and abs(v - val) <= 0.06 * max(v, 1):
                    return "rounded", p
    return None, None


def _operands(expr: str) -> list[float]:
    vals = []
    for raw in re.findall(r"\d+(?:\.\d+)?", expr):
        v = float(raw)
        vals.append(v)
        if 0 < v < 1:
            vals.append(round(v * 100, 6))  # 0.2 -> 20 %
    return vals


def _ref(src) -> dict:
    """Pointer from a number to the tool result behind it: trace index + path inside the result (customer.* has none)."""
    return {"ti": src.ti, "path": src.path} if isinstance(src, _Src) and src.ti is not None else {}


def _note_ok(note: str, val: float, green: bool, own: list[float] | None = None) -> bool:
    """A note may only explain its own number: no other numbers, no statistic, no claim about the user's money."""
    allowed = [val, *(own or [])]
    for raw in re.findall(r"\d+(?:[.,]\d+)?", note):
        try:
            if all(abs(_parse(raw)[0] - a) > 1e-6 for a in allowed):
                return False
        except ValueError:
            return False
    return green or not (_DATA_CLAIM.search(note) or _NOTE_CLAIM.search(note) or _STATISTIC.search(note))


def check(answer: str, trace: list[dict], user_texts: list[str], lang: str = "en",
          context: dict | None = None, earlier: list[str] | None = None, explain: bool = False,
          notes: list[dict] | None = None) -> list[dict]:
    """context: values the coach was given up front (e.g. the customer's balance). earlier: the coach's own earlier
    answers in this chat. explain: coach chat mode, where a € only matches a euro field and a % only a percentage
    field, calculate inputs decide whether a result is data, and assumption / calculated / rule statuses and notes are
    added. Off for captions (Wrapped, Sort, Play), which keep the strict data-only check unchanged."""
    sources = [(abs(float(v)), _Src(f"customer.{k}")) for k, v in (context or {}).items() if isinstance(v, (int, float))]
    per_tool, calcs, inputs = [], [], []
    for ti, t in enumerate(trace):
        if t.get("error"):
            continue
        if explain and t["tool"] == "calculate":
            calcs.append(t)
            continue
        vals = [(v, _Src(f"{t['tool']}.{p}", ti, p)) for v, p in _collect(t["result"])]
        sources += vals
        per_tool.append([(v, p) for v, p in vals if v >= 1 and " (as %)" not in p and (not explain or _kind_of(p) == "eur")][:80])
        if explain:
            inputs += [(v, f"{t['tool']}.{p}") for v, p in _collect(t.get("input") or {})]
    data_sources = list(sources)
    eur_data = [(v, p) for v, p in data_sources if _kind_of(p) == "eur"]
    for u in user_texts:  # numbers the user said themselves ("cut by 20 %", "save 200 euros", "$4000") are theirs
        sources += [(v, k) for v, k in _user_numbers(u) if k.kind != "time"]
        if explain:
            sources += [(v, _User("eur")) for v in _word_numbers(u)]
    for e in earlier or []:  # the coach's own earlier answers in this chat (they were checked when first shown)
        for _, num, _ in _matches(e):
            try:
                sources.append((_parse(num)[0], "earlier in this chat"))
            except ValueError:
                pass
    calc_data, calc_assumed, assumed, calc_parts = [], [], list(inputs), {}
    for t in calcs:  # a calculate result is data only if every amount it used is a euro amount from the data
        expr, res = str(t["input"].get("expression", "")), (t["result"] or {}).get("result")
        ops, own = _operands(expr), []
        for raw in re.findall(r"\d+(?:\.\d+)?", expr):
            o = float(raw)
            if 0 < o < 1:                      # a rate such as 0.2 is always the coach's choice (also as 20 %)
                own += [o, round(o * 100, 6)]
            elif o not in _NEUTRAL and _hit(o, 2, eur_data, rounding=False)[0] is None:
                own.append(o)
        src = f"{expr} = {res}" + (f" ({t['input'].get('what')})" if t["input"].get("what") else "")
        has_data = any(_hit(float(r), 2, eur_data, rounding=False)[0] for r in re.findall(r"\d+(?:\.\d+)?", expr)
                       if float(r) not in _NEUTRAL and float(r) >= 1)
        if not has_data:  # only unit conversions (6 × 100): nothing in it comes from the data
            own = own or [float(r) for r in re.findall(r"\d+(?:\.\d+)?", expr) if float(r) not in (0, 1)]
        if isinstance(res, (int, float)):
            (calc_assumed if own else calc_data).append((abs(float(res)), src))
            if not own:  # all amounts are data: keep them so the app can name each part
                hits = [(o, _hit(o, 2, eur_data, rounding=False)[1]) for o in ops if o not in _NEUTRAL and o >= 1]
                calc_parts[src] = [{"value": o, **_ref(h)} for o, h in hits if h is not None]
        assumed += [(o, f"calculate: {expr}") for o in own]
    calc_data_srcs = {s for _, s in calc_data}
    sources += calc_data

    def pool_for(unit: str):
        """Explain mode: € only from euro fields, % only from percentage fields; the user's, earlier and calculated
        numbers match either."""
        if not explain:
            return sources
        want = "pct" if unit in _PCT_UNITS else "eur"
        # The user's numbers keep their unit too: 20 % only from a typed "20 %", € from "500 €" or a bare "500".
        return [(v, p) for v, p in sources
                if (_kind_of(p) == want if isinstance(p, _Src)
                    else p.kind == want or (p.kind == "other" and want == "eur") if isinstance(p, _User) else True)]

    found, cursor = [], 0
    for full, num, unit in _matches(answer):
        try:
            val, dec = _parse(num)
        except ValueError:
            continue
        at = answer.find(full, cursor)
        at = at if at >= 0 else answer.find(full)
        cursor = at + len(full)
        pool = pool_for(unit)
        status, src, rounded_from, parts = "unverified", None, None, None
        tol = 0.5 * 10 ** -dec + 1e-6
        for v, p in pool:
            if abs(round(v, dec) - val) < 1e-6 or abs(v - val) <= tol:
                status, src = "verified", p
                break
        if status == "unverified" and dec == 0 and val >= 10 and not (explain and unit in _PCT_UNITS):
            for v, p in pool:
                for step in (10, 50, 100):
                    if val % step == 0 and abs(v - val) <= step / 2 and abs(v - val) <= 0.06 * max(v, 1):
                        status, src, rounded_from = "rounded", p, v
                        break
                if src:
                    break
        if status == "unverified" and dec == 2 and unit not in _PCT_UNITS:
            # Exact sum or difference of two amounts from the SAME tool result (e.g. groceries + surprise buffer).
            # Only cent-exact matches, so an invented number almost never passes by chance.
            for tool_vals in per_tool:
                hit = next(((a, pa, b, pb, op) for i, (a, pa) in enumerate(tool_vals) for (b, pb) in tool_vals[i + 1:]
                            for op, v in (("+", a + b), ("−", abs(a - b))) if abs(round(v, 2) - val) < 1e-6), None)
                if hit:
                    a, pa, b, pb, op = hit
                    if op == "−" and b > a:
                        a, pa, b, pb = b, pb, a, pa
                    status, src = "derived", _Src(f"{a:.2f} {op} {b:.2f}", pa.ti, "")
                    parts = [{"value": a, "op": "", **_ref(pa)}, {"value": b, "op": op, **_ref(pb)}]
                    break
        if unit in _PCT_UNITS and (status == "unverified" or src == "your question"):
            # A percentage inside a closing question ("Want to see a 30 % cut?") is an offer, not a claim, even when
            # it equals a number the user typed.
            end = answer.find("\n", cursor)
            if "?" in answer[cursor: end if end >= 0 else len(answer)].split(".")[0]:
                status, src = "suggestion", None
        if src == "your question":
            status = "yours"
        elif src == "earlier in this chat":
            status = "earlier"
        if explain and status == "verified" and src in calc_data_srcs:
            parts = None  # a calculation on data stays green; its parts come from calc_parts below
        if explain and status == "unverified":
            for pl, st in ((calc_assumed, "calculated"), (assumed, "assumption")):
                kind, p = _hit(val, dec, pl, rounding=False)
                if kind:
                    status, src = st, p
                    break
        entry = {"text": full, "value": val, "status": status, "source": src, "decimals": dec}
        if explain:
            entry["unit"] = "%" if unit in _PCT_UNITS else "€"
        if explain and status in ("verified", "rounded", "derived"):
            entry.update(_ref(src))
            if rounded_from is not None:
                entry["rounded_from"] = round(rounded_from, 2)
            if parts:
                entry["parts"] = parts
            elif src in calc_parts:
                entry["parts"], entry["expression"] = calc_parts[src], str(src)
        if explain:
            pct = unit in _PCT_UNITS
            for n in notes or []:
                if abs(n["value"] - val) > 1e-6 or n["pct"] != pct:
                    continue
                green = status in ("verified", "rounded", "derived")
                if not _note_ok(n["note"], val, green, n.get("own")):
                    break  # a note may only explain its own number, never add numbers or facts
                if n["kind"] == "rule" and status == "unverified" and pct:
                    sent = _sentence(answer, at)
                    if _RULE_WORD.search(sent) and not _DATA_CLAIM.search(sent) and not _STATISTIC.search(sent):
                        status = entry["status"] = "rule"
                entry["note"] = n["note"]
                break
            if pct and status == "unverified" and "note" not in entry:
                # No note (the open model often leaves the block out): the sentence alone must call it a rule of thumb
                sent = _sentence(answer, at)
                if _RULE_WORD.search(sent) and not _DATA_CLAIM.search(sent) and not _STATISTIC.search(sent):
                    status = entry["status"] = "rule"
        found.append(entry)
    _derive_more(found, eur_data + [(v, p) for v, p in sources if not isinstance(p, _Src)] if explain else sources)
    return found


_PERIODS = (2, 3, 4, 6, 12)


def _derive_more(found: list[dict], sources: list[tuple[float, str]]) -> None:
    """Exact arithmetic the model showed in its own answer, cent-exact only: a sum or difference of two amounts already
    matched in this answer, the total of the 3-4 matched amounts listed just before it, or a tool value per period
    (/ or × 2, 3, 4, 6, 12 months). Repeats so a total can then be used in a later difference."""
    eq = lambda a, b: abs(round(a, 2) - b) < 0.006
    for _ in range(3):
        changed = False
        for i, f in enumerate(found):
            if f["status"] != "unverified" or f["decimals"] != 2 or f["value"] < 1:
                continue
            val, hit = f["value"], None
            known = [g["value"] for g in found if g is not f and g["status"] not in ("unverified", "suggestion")]
            for x, a in enumerate(known):
                b = next((b for b in known[x + 1:] if eq(a + b, val) or eq(abs(a - b), val)), None)
                if b is not None:
                    hit = f"{max(a, b):.2f} {'+' if eq(a + b, val) else '−'} {min(a, b):.2f} (in this answer)"
                    break
            if not hit:
                prev = [g["value"] for g in found[:i] if g["status"] not in ("unverified", "suggestion")]
                k = next((k for k in (3, 4) if len(prev) >= k and eq(sum(prev[-k:]), val)), None)
                hit = f"total of the {k} amounts above" if k else None
            if not hit:
                for v, p in sources:
                    k = next((k for k in _PERIODS if v >= 1 and (eq(v / k, val) or eq(v * k, val))), None) if v >= 1 else None
                    if k:
                        hit = f"{p} {'/' if eq(v / k, val) else '×'} {k}"
                        break
            if hit:
                f["status"], f["source"], changed = "derived", hit, True
        if not changed:
            break
