"""Verified numbers: every euro amount and percentage in a coach answer is matched against the tool results.

Status per number: "suggestion" (a percentage offered in a question, not a claim), "verified" (equals a tool value at the shown precision), "rounded" (a tool value rounded to
tens/hundreds, e.g. "about 1,000 €" for 997 €), "unverified" (no source: flagged in the UI and counted in traps).
"""
from __future__ import annotations

import re

# 1,234.50 € | 1 234,50 € | 20 % | 20% | 1234 EUR | 47,10 euroa
_NUM = r"(\d{1,3}(?:[,   ]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_RE = re.compile(_NUM + r"\s?(€|EUR\b|euroa\b|euro\b|%|prosenttia\b|procent\b)", re.IGNORECASE)


def _parse(raw: str, lang: str) -> tuple[float, int]:
    s = raw.replace(" ", " ").replace(" ", " ")
    if lang in ("fi", "sv"):
        s = s.replace(" ", "").replace(".", "").replace(",", ".")
    else:
        s = s.replace(" ", "")
        if re.search(r",\d{3}(?!\d)", s):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
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
          context: dict | None = None) -> list[dict]:
    """context: values the coach was given up front (e.g. the customer's balance)."""
    sources = [(abs(float(v)), f"customer.{k}") for k, v in (context or {}).items() if isinstance(v, (int, float))]
    for t in trace:
        if not t.get("error"):
            sources += [(v, f"{t['tool']}.{p}") for v, p in _collect(t["result"])]
    for u in user_texts:  # numbers the user said themselves ("cut by 20 %") are fine to repeat
        for m in _RE.finditer(u):
            try:
                sources.append((_parse(m.group(1), "en")[0], "your question"))
            except ValueError:
                pass
    found = []
    for m in _RE.finditer(answer):
        try:
            val, dec = _parse(m.group(1), lang)
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
        if status == "unverified" and m.group(2) in ("%", "prosenttia", "procent"):
            # A percentage inside a closing question ("Want to see a 30 % cut?") is an offer, not a claim.
            end = answer.find("\n", m.end())
            sentence = answer[m.end(): end if end >= 0 else len(answer)]
            if "?" in sentence.split(".")[0]:
                status = "suggestion"
        found.append({"text": m.group(0), "value": val, "status": status, "source": src})
    return found
