"""Verified numbers: every euro amount and percentage in a coach answer is matched against the tool results.

Status per number: "derived" (exact arithmetic on matched numbers: a sum or difference of two numbers from one tool
result or from this answer, a total of the amounts listed just above, or a tool value per 2/3/4/6/12 months), "yours" (the user's own
number), "suggestion" (a percentage offered in a question, not a claim), "verified" (equals a tool value at the shown precision), "rounded" (a tool value rounded to
tens/hundreds, e.g. "about 1,000 €" for 997 €), "unverified" (no source: flagged in the UI and counted in traps).
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


def check(answer: str, trace: list[dict], user_texts: list[str], lang: str = "en",
          context: dict | None = None, earlier: list[str] | None = None) -> list[dict]:
    """context: values the coach was given up front (e.g. the customer's balance)."""
    sources = [(abs(float(v)), f"customer.{k}") for k, v in (context or {}).items() if isinstance(v, (int, float))]
    per_tool = []
    for t in trace:
        if not t.get("error"):
            vals = [(v, f"{t['tool']}.{p}") for v, p in _collect(t["result"])]
            sources += vals
            per_tool.append([(v, p) for v, p in vals if v >= 1 and " (as %)" not in p][:80])
    for u in user_texts:  # numbers the user said themselves ("cut by 20 %", "save 200 euros", "$4000") are theirs
        for m in re.finditer(_NUM, u):
            try:
                sources.append((_parse(m.group(0))[0], "your question"))
            except ValueError:
                pass
    for e in earlier or []:  # the coach's own earlier answers in this chat (they were checked when first shown)
        for _, num, _ in _matches(e):
            try:
                sources.append((_parse(num)[0], "earlier in this chat"))
            except ValueError:
                pass
    found = []
    for full, num, unit in _matches(answer):
        try:
            val, dec = _parse(num)
        except ValueError:
            continue
        status, src = "unverified", None
        tol = 0.5 * 10 ** -dec + 1e-6
        for v, p in sources:
            if abs(round(v, dec) - val) < 1e-6 or abs(v - val) <= tol:
                status, src = "verified", p
                break
        if status == "unverified" and dec == 0 and val >= 10:
            for v, p in sources:
                for step in (10, 50, 100):
                    if val % step == 0 and abs(v - val) <= step / 2 and abs(v - val) <= 0.06 * max(v, 1):
                        status, src = "rounded", p
                        break
                if src:
                    break
        if status == "unverified" and dec == 2:
            # Exact sum or difference of two numbers from the SAME tool result (e.g. groceries + surprise buffer).
            # Only cent-exact matches, so an invented number almost never passes by chance.
            for tool_vals in per_tool:
                hit = next(((a, b, op) for i, (a, pa) in enumerate(tool_vals) for (b, pb) in tool_vals[i + 1:]
                            for op, v in (("+", a + b), ("−", abs(a - b))) if abs(round(v, 2) - val) < 1e-6), None)
                if hit:
                    a, b, op = hit
                    status, src = "derived", f"{max(a, b) if op == '−' else a:.2f} {op} {min(a, b) if op == '−' else b:.2f}"
                    break
        if status == "unverified" and unit in ("%", "prosenttia", "procent"):
            # A percentage inside a closing question ("Want to see a 30 % cut?") is an offer, not a claim.
            at = answer.find(full) + len(full)
            end = answer.find("\n", at)
            sentence = answer[at: end if end >= 0 else len(answer)]
            if "?" in sentence.split(".")[0]:
                status = "suggestion"
        if src == "your question":
            status = "yours"
        elif src == "earlier in this chat":
            status = "earlier"
        found.append({"text": full, "value": val, "status": status, "source": src, "decimals": dec})
    _derive_more(found, sources)
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
