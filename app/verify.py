"""Verified numbers: every euro amount and percentage in a coach answer is matched against the tool results.

Status per number: "derived" (exact sum or difference of two numbers from one tool result), "yours" (the user's own
number), "suggestion" (a percentage offered in a question, not a claim), "verified" (equals a tool value at the shown precision), "rounded" (a tool value rounded to
tens/hundreds, e.g. "about 1,000 €" for 997 €), "unverified" (no source: flagged in the UI and counted in traps).

With explain=True (the coach chat) a number that is not from the data can also be:
"assumption" (a number the coach put into calculate or a tool argument, e.g. a 20 % savings rate or a 7 % return),
"calculated" (a calculate result that used at least one such assumption), or "rule" (a percentage the coach marked as
a rule of thumb in its hidden notes block, accepted only in a sentence that makes no claim about the user's money and
presents no statistic). A calculate result whose inputs all come from the data stays "verified". Notes the coach
writes are attached as "note" but never change a status; notes with other numbers or data claims are dropped.
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
_NOTES = re.compile(r"\s*<number-notes>(.*?)(?:</number-notes>|$)", re.DOTALL | re.IGNORECASE)
_DATA_CLAIM = re.compile(r"\b(you (spent|paid|earned|saved|have|had|got)|your (balance|spending|account|transactions|biggest|data)"
                         r"|from your (account|data|transactions)|käytit|tililläsi|du (spenderade|betalade|har))\b", re.IGNORECASE)
_STATISTIC = re.compile(r"\b(most|many|average|on average|typical(ly)?|studies|research|survey|statistic\w*|people|households|"
                        r"finns|useimmat|keskimäärin|ihmiset|suomalaiset|tutkimu\w*|de flesta|i genomsnitt|människor|studier)\b",
                        re.IGNORECASE)
_PCT_UNITS = ("%", "prosenttia", "procent")


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
    """Remove the coach's hidden notes block. Lines: '<number with unit>|note|<why>' or '<number>|rule|<why>'."""
    m = _NOTES.search(text)
    if not m:
        return text, []
    notes = []
    for line in m.group(1).strip().splitlines():
        parts = [p.strip() for p in line.strip().lstrip("-• ").split("|", 2)]
        if len(parts) != 3 or not parts[2]:
            continue
        hit = _matches(parts[0])
        if not hit:
            continue
        try:
            val = _parse(hit[0][1])[0]
        except ValueError:
            continue
        notes.append({"value": val, "pct": hit[0][2] in _PCT_UNITS, "kind": parts[1].lower(), "note": parts[2][:200]})
    return (text[:m.start()] + text[m.end():]).strip(), notes


def _sentence(answer: str, start: int) -> str:
    """The sentence around position start (a decimal point like 2,412.60 is not a sentence end)."""
    cuts = [m.end() for m in re.finditer(r"[.!?](?=\s|$)|\n", answer)]
    a = max([c for c in cuts if c <= start], default=0)
    b = min([c for c in cuts if c > start], default=len(answer))
    return answer[a:b]


def _hit(val: float, dec: int, pool):
    """First (status, source) in pool equal to val at its precision, or rounded to 10/50/100."""
    tol = 0.5 * 10 ** -dec + 1e-6
    for v, p in pool:
        if abs(round(v, dec) - val) < 1e-6 or abs(v - val) <= tol:
            return "exact", p
    if dec == 0 and val >= 10:
        for v, p in pool:
            for step in (10, 50, 100):
                if val % step == 0 and abs(v - val) <= step / 2 and abs(v - val) <= 0.06 * max(v, 1):
                    return "rounded", p
    return None, None


def _operands(expr: str) -> list[float]:
    vals = []
    for raw in re.findall(r"\d+(?:\.\d+)?", expr.replace(",", "")):
        v = float(raw)
        vals.append(v)
        if 0 < v < 1:
            vals.append(round(v * 100, 6))  # 0.2 -> 20 %
    return vals


def _ref(src) -> dict:
    """Pointer from a number to the tool result behind it: trace index + path inside the result (customer.* has none)."""
    return {"ti": src.ti, "path": src.path} if isinstance(src, _Src) and src.ti is not None else {}


def check(answer: str, trace: list[dict], user_texts: list[str], lang: str = "en",
          context: dict | None = None, explain: bool = False, notes: list[dict] | None = None) -> list[dict]:
    """context: values the coach was given up front (e.g. the customer's balance).
    explain: coach chat mode (assumption / calculated / rule statuses, notes); off for captions, which must be data only."""
    sources = [(abs(float(v)), f"customer.{k}") for k, v in (context or {}).items() if isinstance(v, (int, float))]
    per_tool, calcs, inputs = [], [], []
    for ti, t in enumerate(trace):
        if t.get("error"):
            continue
        if explain and t["tool"] == "calculate":
            calcs.append(t)
            continue
        vals = [(v, _Src(f"{t['tool']}.{p}", ti, p)) for v, p in _collect(t["result"])]
        sources += vals
        per_tool.append([(v, p) for v, p in vals if v >= 1 and " (as %)" not in p][:80])
        if explain:
            inputs += [(v, f"{t['tool']}.{p}") for v, p in _collect(t.get("input") or {})]
    data_sources = list(sources)
    yours = []
    for u in user_texts:  # numbers the user said themselves ("cut by 20 %", "€500") are theirs, not claims
        for _, num, _ in _matches(u):
            try:
                yours.append((_parse(num)[0], "your question"))
            except ValueError:
                pass
        if explain:
            yours += [(v, "your question") for v in _word_numbers(u)]
    sources += yours
    calc_data, calc_assumed, assumed, calc_parts = [], [], list(inputs), {}
    for t in calcs:  # a calculate result is data only if every input is data; otherwise it rests on an assumption
        expr, res = str(t["input"].get("expression", "")), t["result"].get("result")
        ops = _operands(expr)
        own = [o for o in ops if o not in (0, 1, 100) and _hit(o, 2, data_sources)[0] is None]
        src = f"{expr} = {res}" + (f" ({t['input'].get('what')})" if t["input"].get("what") else "")
        if isinstance(res, (int, float)):
            (calc_assumed if own else calc_data).append((abs(float(res)), src))
            if not own:  # all inputs are data: keep them so the app can name each part
                hits = [(o, _hit(o, 2, data_sources)[1]) for o in _operands(expr) if o not in (0, 1, 100) and o >= 1]
                calc_parts[src] = [{"value": o, **_ref(h)} for o, h in hits if h is not None]
        assumed += [(o, f"calculate: {expr}") for o in own]
    sources += calc_data
    found = []
    for full, num, unit in _matches(answer):
        try:
            val, dec = _parse(num)
        except ValueError:
            continue
        status, src, rounded_from, parts = "unverified", None, None, None
        tol = 0.5 * 10 ** -dec + 1e-6
        for v, p in sources:
            if abs(round(v, dec) - val) < 1e-6 or abs(v - val) <= tol:
                status, src = "verified", p
                break
        if status == "unverified" and dec == 0 and val >= 10:
            for v, p in sources:
                for step in (10, 50, 100):
                    if val % step == 0 and abs(v - val) <= step / 2 and abs(v - val) <= 0.06 * max(v, 1):
                        status, src, rounded_from = "rounded", p, v
                        break
                if src:
                    break
        if status == "unverified" and dec == 2:
            # Exact sum or difference of two numbers from the SAME tool result (e.g. groceries + surprise buffer).
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
        if unit in ("%", "prosenttia", "procent") and (status == "unverified" or src == "your question"):
            # A percentage inside a closing question ("Want to see a 30 % cut?") is an offer, not a claim, even when
            # it happens to equal a number the user typed.
            at = answer.find(full) + len(full)
            end = answer.find("\n", at)
            sentence = answer[at: end if end >= 0 else len(answer)]
            if "?" in sentence.split(".")[0]:
                status, src = "suggestion", None
        if src == "your question":
            status = "yours"
        if explain and status == "unverified":
            for pool, st in ((calc_assumed, "calculated"), (assumed, "assumption")):
                kind, p = _hit(val, dec, pool)
                if kind:
                    status, src = st, p
                    break
        entry = {"text": full, "value": val, "status": status, "source": src}
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
            at = answer.find(full)
            for n in notes or []:
                if abs(n["value"] - val) > 1e-6 or n["pct"] != pct:
                    continue
                note = n["note"]
                others = [x for x in _matches(note) if abs(_parse(x[1])[0] - val) > 1e-6]
                green = status in ("verified", "rounded", "derived")
                if others or (not green and status != "calculated" and _DATA_CLAIM.search(note)):
                    break  # a note may only explain its own number, never add numbers or facts about the user
                if n["kind"] == "rule" and status == "unverified" and pct:
                    sent = _sentence(answer, at)
                    if not _DATA_CLAIM.search(sent) and not _STATISTIC.search(sent):
                        status = entry["status"] = "rule"
                entry["note"] = note
                break
        found.append(entry)
    return found
