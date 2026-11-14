"""Sort with the AI: the customer decides which basket their unclear spending belongs to.

Code finds the genuinely unclear items in the customer's own last 12 months: big one-time buys that could be a broken
thing being replaced (a surprise must-pay) or a want (an extra), and habits like parking or taxis that can be a
must (the commute) or a convenience. Claude picks the most useful few, asks about each in plain words and explains the
basket idea; it never writes numbers (the card shows them from code). The answers override the data's basket in every
tool (money.set_basket_answers), and Claude sums up what changed, with every number checked against the result.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from . import future, insights, live, money, verify
from .money import TODAY, _month_start, _q, _r
from .taxonomy import BASKETS

log = logging.getLogger("sorter")
STATE = Path(__file__).resolve().parent.parent / "state"
ANSWERS = STATE / "basket_answers.json"
QUESTIONS = STATE / "sort_questions.json"
_lock = threading.Lock()

HABITS = ("Parking", "Taxis", "Kiosks & convenience stores", "Fast food & cafes", "Fuel", "Fuel (automated)",
          "Other transportation", "Pharmacy", "Public transport")
BIG_BUY_CATEGORIES = ("Home & Tech", "Lifestyle")
BIG_BUY_EUR = 150


def _read(p: Path) -> dict:
    with _lock:
        return json.loads(p.read_text()) if p.exists() else {}


def _write(p: Path, d: dict) -> None:
    with _lock:
        STATE.mkdir(exist_ok=True)
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False))


def load_all() -> None:
    """At startup: put every saved answer back into the data layer."""
    for cid, a in _read(ANSWERS).items():
        money.set_basket_answers(cid, {int(k): v for k, v in a.get("tx", {}).items()}, a.get("sub", {}))


def candidates(cid: str) -> list[dict]:
    """The unclear items, from code. Ids: 't<seq>' for one transaction, 's:<merchant type>' for a habit."""
    start = _month_start(TODAY, 11)
    out = []
    for r in _q(f"""SELECT seq, tx_date d, ts, sub, -amount a, data_basket b FROM tx
                    WHERE customer_id = ? AND tx_date >= ? AND kind = 'spend' AND -amount >= ?
                    AND category IN {BIG_BUY_CATEGORIES} ORDER BY a DESC LIMIT 6""", [cid, start, BIG_BUY_EUR]):
        out.append({"id": f"t{r['seq']}", "kind": "one_purchase", "merchant_type": r["sub"], "amount_eur": _r(r["a"]),
                    "date": str(r["d"]), "weekday": r["d"].strftime("%A"),
                    "hour": r["ts"].hour if r["ts"] else None, "data_basket": r["b"]})
    for r in _q(f"""SELECT sub, count(*) n, -sum(amount) t, median(-amount) typ, any_value(data_basket) b,
                           avg(CASE WHEN dayofweek(tx_date) BETWEEN 1 AND 5 THEN 1 ELSE 0 END) wk,
                           median(hour(ts)) h
                    FROM tx WHERE customer_id = ? AND tx_date >= ? AND kind = 'spend' AND sub IN {HABITS}
                    GROUP BY 1 HAVING count(*) >= 6 ORDER BY t DESC LIMIT 6""", [cid, start]):
        out.append({"id": f"s:{r['sub']}", "kind": "habit", "merchant_type": r["sub"], "times": r["n"],
                    "total_eur": _r(r["t"]), "typical_eur": _r(r["typ"]), "share_on_weekdays": round(r["wk"], 2),
                    "typical_hour": int(r["h"]) if r["h"] is not None else None, "data_basket": r["b"]})
    return out


Q_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["questions"], "properties": {"questions": {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
                               "required": ["id", "question", "answer_1", "answer_2", "answer_3", "lesson"],
                               "properties": {k: {"type": "string"} for k in
                                              ("id", "question", "answer_1", "answer_2", "answer_3", "lesson")}}}}}


def _no_digits(*texts: str) -> bool:
    return all(isinstance(t, str) and t.strip() and not any(c.isdigit() for c in t) for t in texts)


def questions(cid: str, lang: str = "en") -> dict:
    """The cards: code facts (merchant type, amount, date, times) + Claude's question, three answers and a lesson."""
    key = f"{cid}:{lang}"
    cache = _read(QUESTIONS)
    pool = {c["id"]: c for c in candidates(cid)}
    if key not in cache:
        lname = {"fi": "Finnish", "sv": "Swedish"}.get(lang, "English")
        system = (
            f"You help a bank customer sort their own spending into three baskets, in {lname}. Basket 1: mandatory and "
            "regular (rent, bills, groceries, the commute). Basket 2: mandatory but irregular (a broken washing machine, "
            "the dentist). Basket 3: everyday spending that slips through your fingers (coffees, taxis, treats). "
            "From the items, pick the 5 whose basket is most genuinely unclear and that teach the most (mix one-time "
            "purchases and habits; use weekday and hour as hints, e.g. weekday mornings suggest a commute). For each: a "
            "short friendly question (max 90 characters) that helps the person decide; answer_1/2/3 are short answers "
            "(max 32 characters) that mean basket 1, 2 and 3 for this item; lesson is one line (max 90 characters) on "
            "why the difference matters for their money. The card already shows the amount, date and merchant type: "
            "write NO digits anywhere. Never judge. Use the item ids exactly.")
        try:
            got = future._json_call(system, json.dumps(list(pool.values())), Q_SCHEMA, max_tokens=2000)["questions"]
            qs = [q for q in got if q["id"] in pool and
                  _no_digits(q["question"], q["answer_1"], q["answer_2"], q["answer_3"], q["lesson"])][:6]
        except Exception as e:  # noqa: BLE001
            log.warning("sort questions failed: %s", e)
            qs = []
        if not qs:
            return {"cards": [], "source": "none"}
        cache[key] = qs
        _write(QUESTIONS, cache)
    saved = _read(ANSWERS).get(cid, {})
    hsl = live.registry().get("hsl_30day_ab", {})
    alt = ({"label": "hsl_30day_ab", "price_eur": hsl["value"], "source_url": hsl["source_url"]}
           if hsl.get("status") == "confirmed" else None)  # live public price next to a commuting habit
    cards = []
    for q in cache[key]:
        c = pool.get(q["id"])
        if not c:
            continue
        cur = (saved.get("tx", {}).get(q["id"][1:]) if q["id"].startswith("t") else saved.get("sub", {}).get(q["id"][2:]))
        cards.append({**c, "question": q["question"], "answers": {"1": q["answer_1"], "2": q["answer_2"], "3": q["answer_3"]},
                      "lesson": q["lesson"], "your_answer": cur,
                      "live_alternative": alt if c["merchant_type"] in ("Parking", "Taxis") else None})
    return {"cards": cards, "source": "ai"}


def _snapshot(cid: str) -> dict:
    b = money.get_three_baskets(cid, "last_12_months")
    sts = money.get_safe_to_spend(cid)
    r = insights.ribbon(cid)
    return {"baskets_eur": {str(x["basket"]): x["total_eur"] for x in b["baskets"]},
            "safe_until_payday_eur": sts["safe_until_payday_eur"], "safe_this_week_eur": sts["safe_this_week_eur"],
            "balance_at_payday_eur": r["balance_at_payday_eur"]}


def _forget_ai_caches(cid: str) -> None:
    for p in (future.CACHE, STATE / "wrapped.json"):
        d = _read(p)
        if any(k.startswith(cid + ":") for k in d):
            _write(p, {k: v for k, v in d.items() if not k.startswith(cid + ":")})


TAKEAWAY_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["takeaway"],
                   "properties": {"takeaway": {"type": "string"}}}


def answer(cid: str, answers: dict[str, int], lang: str = "en") -> dict:
    """Save the customer's answers (merged with earlier ones), apply them everywhere, say what changed."""
    pool = {c["id"]: c for c in candidates(cid)}
    all_ans = _read(ANSWERS)
    mine = all_ans.get(cid, {"tx": {}, "sub": {}})
    before = _snapshot(cid)
    moved = []
    for i, b in answers.items():
        if i not in pool or int(b) not in (1, 2, 3):
            raise money.ToolError(f"unknown item or basket: {i}")
        c, b = pool[i], int(b)
        if i.startswith("t"):
            mine["tx"][i[1:]] = b
        else:
            mine["sub"][i[2:]] = b
        if b != c["data_basket"]:
            moved.append({"merchant_type": c["merchant_type"], "from_basket": c["data_basket"], "to_basket": b,
                          "eur": c.get("amount_eur", c.get("total_eur"))})
    all_ans[cid] = mine
    _write(ANSWERS, all_ans)
    money.set_basket_answers(cid, {int(k): v for k, v in mine["tx"].items()}, mine["sub"])
    after = _snapshot(cid)
    _forget_ai_caches(cid)
    change = {b: _r(after["baskets_eur"][b] - before["baskets_eur"][b]) for b in before["baskets_eur"]}
    out = {"before": before, "after": after, "change_eur": change, "moved": moved, "takeaway": None,
           "basket_names": {str(k): v["name"] for k, v in BASKETS.items()}}
    facts = {k: v for k, v in out.items() if k != "takeaway"}
    lname = {"fi": "Finnish", "sv": "Swedish"}.get(lang, "English")
    system = (f"In {lname}, write ONE short sentence (max 130 characters) for a bank customer who just sorted some of "
              "their spending into the three baskets (1 fixed must-pays, 2 surprise must-pays, 3 everyday extras). Say "
              "what it means, e.g. if a habit is really a must-pay, there is less room for extras than it looked. At most "
              "one number, from the facts, rounded to whole euros like 1,437 €. If nothing moved, say their sorting "
              "matches ours. Warm, never judging.")
    trace = [{"tool": "sorted", "error": False, "result": facts}]
    try:
        t = future._json_call(system, json.dumps(facts), TAKEAWAY_SCHEMA, max_tokens=400)["takeaway"]
        if len(t) <= 170 and all(n["status"] not in ("unverified",) for n in verify.check(t, trace, [], lang)):
            out["takeaway"] = t
    except Exception as e:  # noqa: BLE001
        log.warning("sort takeaway failed: %s", e)
    return out


def reset(cid: str) -> dict:
    all_ans = _read(ANSWERS)
    all_ans.pop(cid, None)
    _write(ANSWERS, all_ans)
    money.set_basket_answers(cid, {}, {})
    _forget_ai_caches(cid)
    return {"reset": True}
