"""Money Wrapped: your money year as story slides. Code computes every fact; Claude writes one short caption per
slide from those facts (numbers verified, cached per customer and language). Share text never contains amounts.
"""
from __future__ import annotations

import json
import logging
import statistics
import threading
from datetime import date, timedelta
from pathlib import Path

from . import future, insights, money, verify
from .money import TODAY, _month_start, _q, _r
from .taxonomy import BASKETS

log = logging.getLogger("wrapped")
CACHE = Path(__file__).resolve().parent.parent / "state" / "wrapped.json"
_lock = threading.Lock()
EAT_OUT = ("Restaurants", "Fast food & cafes", "Bars & pubs", "Other restaurants")


def _period():
    return _month_start(TODAY, 11), TODAY


def twins(cid: str, salary: float, age: int, start, end) -> dict | None:
    """People like you (same age decade, similar pay), split by whether they ever went below zero. Groups only."""
    lo_age = (age // 10) * 10
    for spread in (0.12, 0.2, 0.3):
        rows = _q(f"""WITH s AS (SELECT customer_id, median(amount) sal FROM tx WHERE category = 'Salary' AND tx_date BETWEEN ? AND ? GROUP BY 1),
              p AS (SELECT customer_id, -sum(amount) FILTER (WHERE basket = 3) / 12 extras,
                           count(*) FILTER (WHERE sub IN {EAT_OUT}) / 12.0 eat_n, -sum(amount) FILTER (WHERE sub IN {EAT_OUT}) / 12 eat_eur,
                           count(DISTINCT tx_date) FILTER (WHERE balance < 0) neg_days
                    FROM tx WHERE tx_date BETWEEN ? AND ? GROUP BY 1)
              SELECT (neg_days = 0) never_neg, count(*) n, median(extras) extras, median(eat_n) eat_n, median(eat_eur) eat_eur
              FROM p JOIN s USING (customer_id) JOIN cust c USING (customer_id)
              WHERE c.age BETWEEN ? AND ? AND sal BETWEEN ? AND ? AND customer_id < 'CUST05001' AND customer_id <> ?
              GROUP BY 1""", [start, end, start, end, lo_age, lo_age + 9, salary * (1 - spread), salary * (1 + spread), cid])
        g = {r["never_neg"]: r for r in rows}
        if True in g and False in g and g[True]["n"] >= 20 and g[False]["n"] >= 20:
            t, f = g[True], g[False]
            return {"age_group": f"{lo_age}-{lo_age + 9}", "salary_range_eur": [_r(salary * (1 - spread)), _r(salary * (1 + spread))],
                    "never_below_zero": {"people": t["n"], "extras_per_month_eur": _r(t["extras"]), "eat_out_visits_per_month": round(t["eat_n"], 1),
                                         "eat_out_eur_per_month": _r(t["eat_eur"])},
                    "went_below_zero": {"people": f["n"], "extras_per_month_eur": _r(f["extras"]), "eat_out_visits_per_month": round(f["eat_n"], 1),
                                        "eat_out_eur_per_month": _r(f["eat_eur"])},
                    "difference_extras_per_month_eur": _r(f["extras"] - t["extras"])}
    return None


def _with_you(t: dict | None, cf: dict, eat: dict, neg_days: int) -> dict | None:
    """Compare the person with the twins who never went below zero (what the slide shows), not group vs group."""
    if not t:
        return None
    you = cf["spending_eur"][BASKETS[3]["name"]] / 12
    them = t["never_below_zero"]
    return {"age_group": t["age_group"], "twins_who_never_went_below_zero": them["people"],
            "your_extras_per_month_eur": _r(you), "their_extras_per_month_eur": them["extras_per_month_eur"],
            "you_minus_them_extras_per_month_eur": _r(you - them["extras_per_month_eur"]),
            "your_eat_out_visits_per_month": round(eat["n"] / 12, 1), "their_eat_out_visits_per_month": them["eat_out_visits_per_month"],
            "your_eat_out_eur_per_month": _r((eat["t"] or 0) / 12), "their_eat_out_eur_per_month": them["eat_out_eur_per_month"],
            "your_days_below_zero": neg_days}


def facts(cid: str) -> dict:
    start, end = _period()
    c = money.customer(cid)
    sal = [r["a"] for r in _q("SELECT amount a FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date BETWEEN ? AND ?", [cid, start, end])]
    salary = statistics.median(sal) if sal else None
    hour = salary / 160 if salary else None
    cf = money.get_cashflow(cid, start=start.isoformat(), end=end.isoformat())
    eat = _q(f"SELECT count(*) n, -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND sub IN {EAT_OUT}", [cid, start, end])[0]
    # The guess game: the four extras (basket 3) that cost the most, biggest first
    top = _q("""SELECT sub, count(*) n, -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND basket = 3
                GROUP BY 1 ORDER BY t DESC LIMIT 4""", [cid, start, end])
    # net = income + (negative spending amounts): what was left from the month's money
    months = _q("""SELECT strftime(tx_date, '%Y-%m') m, coalesce(sum(amount) FILTER (WHERE kind = 'income'), 0) + coalesce(sum(amount) FILTER (WHERE kind = 'spend'), 0) net,
                          min(balance) low FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? GROUP BY 1 ORDER BY 1""", [cid, start, end])
    best = max(months, key=lambda r: r["net"]) if months else None
    tough = min(months, key=lambda r: r["low"]) if months else None
    spend_days = {r["d"] for r in _q("SELECT DISTINCT tx_date d FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND kind = 'spend'", [cid, start, end])}
    total_days = (end - start).days + 1
    streak = run = 0
    for i in range(total_days):
        run = 0 if (start + timedelta(days=i)) in spend_days else run + 1
        streak = max(streak, run)
    neg_days = _q("SELECT count(DISTINCT tx_date) n FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND balance < 0",
                  [cid, start, end])[0]["n"]
    pp = insights.payday_pattern(cid, months=12)
    health = insights.money_health(cid)
    from .personas import PERSONAS
    persona_name = next((p["name"] for p in PERSONAS if p["id"] == cid), None)
    out = {
        "name": persona_name, "period": {"start": start.isoformat(), "end": end.isoformat()},
        "money_in_eur": cf["income_eur"]["total"], "money_out_eur": cf["spending_eur"]["total"],
        "moved_to_savings_eur": _r(cf["moved_to_own_savings_or_investments_eur"]["investment_deposits"] +
                                   cf["moved_to_own_savings_or_investments_eur"]["salary_sweep_to_other_account"]),
        "baskets_eur": {str(k): cf["spending_eur"][BASKETS[k]["name"]] for k in (1, 2, 3)},
        "eat_out": {"visits": eat["n"], "total_eur": _r(eat["t"]), "hours_of_work": round(eat["t"] / hour) if hour and eat["t"] else None},
        "top_extras": [{"merchant_type": r["sub"], "times": r["n"], "total_eur": _r(r["t"])} for r in top],
        "months": [{"month": r["m"], "left_over_eur": _r(r["net"])} for r in months],
        "best_month": {"month": best["m"], "left_over_eur": _r(best["net"])} if best else None,
        "toughest_month": {"month": tough["m"], "lowest_balance_eur": _r(tough["low"])} if tough else None,
        "no_spend_days": total_days - len(spend_days), "longest_no_spend_streak_days": streak,
        "payday_week_change_percent": pp["payday_week_change_percent"],
        "hourly_pay_eur": _r(hour) if hour else None,
        "twins": _with_you(twins(cid, salary, c["age"], start, end) if salary else None, cf, eat, neg_days),
        "rahakunto": {"score": health["score"], "tier": health["tier"], "parts": health["parts"]},
        "spender_type": insights.spender_type(cid)["type"],
        "next_step": ({**health["steps"][0], "points": round(health["steps"][0]["points"])} if health["steps"] else None),
        # one character per day from the period start: "1" = no spending that day (drawn as a calendar, not sent to the AI)
        "_calendar": "".join("0" if (start + timedelta(days=i)) in spend_days else "1" for i in range(total_days)),
    }
    return out


CAPTIONS_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["captions"],
                   "properties": {"captions": {"type": "object", "additionalProperties": False,
                                               "required": ["year", "guess", "baskets", "habit", "months", "no_spend", "payday", "twins", "next"],
                                               "properties": {k: {"type": "string"} for k in
                                                              ["year", "guess", "baskets", "habit", "months", "no_spend", "payday", "twins", "next"]}}}}


def captions(cid: str, lang: str = "en") -> dict:
    key = f"{cid}:{lang}"
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if key in cache:
        return cache[key]
    f = {k: v for k, v in facts(cid).items() if not k.startswith("_")}
    lname = {"fi": "Finnish", "sv": "Swedish"}.get(lang, "English")
    system = (f"You write captions for a 'money year' story (like Spotify Wrapped) in a Finnish bank's app, in {lname}. One "
              "caption per slide, max 50 characters, warm and a little playful, never shaming, never comparing the person "
              "to anyone except the 'twins' group in the facts. Each slide already shows its numbers as a chart, so write "
              "NO digits at all: say what it means or give a light nudge. 'guess' is about the first entry of top_extras "
              "(shown after the person guesses; you don't know if they guessed right, so never say whether they did). 'habit' is about eating out costing hours of work: a gentle nudge to notice it, not praise. 'next' is one encouraging line about next_step.")
    trace = [{"tool": "facts", "error": False, "result": f}]
    ok = lambda v: isinstance(v, str) and len(v) <= 60 and not any(ch.isdigit() for ch in v) and all(n["status"] != "unverified" for n in verify.check(v, trace, [], lang))
    try:
        caps = {}
        for _ in range(2):  # a caption that fails the length or number check gets one more try
            resp = future._json_call(system, json.dumps(f, default=str), CAPTIONS_SCHEMA, max_tokens=1200)["captions"]
            for k, v in resp.items():
                if not caps.get(k) and ok(v):
                    caps[k] = v
            if all(caps.get(k) for k in CAPTIONS_SCHEMA["properties"]["captions"]["required"]):
                break
        caps = {k: caps.get(k) for k in CAPTIONS_SCHEMA["properties"]["captions"]["required"]}
        source = "ai"
    except Exception as e:  # noqa: BLE001
        log.warning("wrapped captions fallback: %s", e)
        caps, source = {}, "none"
    out = {"captions": caps, "source": source}
    if source != "ai":  # don't cache a failure: the next open tries again
        return out
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        cache[key] = out
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    return out


def wrapped(cid: str, lang: str = "en") -> dict:
    return {"facts": facts(cid), **captions(cid, lang)}
