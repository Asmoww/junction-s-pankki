"""The future on the ribbon: a deterministic scenario engine, plus two small AI jobs on top of it.

- simulate(): balance day by day to next payday under a scenario (pause/cut extras, move a bill, one-off spend or
  income). Pure code; every number on the graph comes from here.
- parse_whatif(): Claude turns "concert tickets 150 € on Friday" into a scenario (JSON schema), code computes it.
- annotations(): Claude reads computed facts about the line and writes 2-3 short notes pinned to dates. Numbers are
  checked against the facts (verify.check); unverified notes are dropped. Cached per customer and language.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import date, timedelta
from pathlib import Path

import anthropic

from . import insights, money, verify
from .money import TODAY, _month_start, _q, _r

log = logging.getLogger("future")
MODEL = os.environ.get("COACH_MODEL", "claude-sonnet-5-5")
EXTRA_CATS = ["Restaurants", "Entertainment", "Lifestyle", "Travel", "Transportation", "Groceries", "Home & Tech", "Health"]
CACHE = Path(__file__).resolve().parent.parent / "state" / "annotations.json"
_lock = threading.Lock()


def components(cid: str) -> dict:
    """Everything the simulation needs, from the same sources as safe-to-spend and the forecast."""
    sts = money.get_safe_to_spend(cid)
    fc = insights.payday_forecast(cid)
    days = sts["days_until_payday"]
    since = TODAY - timedelta(days=89)
    cats = {r["category"]: float(r["t"]) / 90 for r in _q(
        "SELECT category, -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date >= ? AND basket = 3 GROUP BY 1",
        [cid, since])}
    return {"balance": money.customer(cid)["balance"], "days": days,
            "payday": TODAY + timedelta(days=days),
            "essentials_day": -sts["steps"][3]["eur"] / days, "surprises_day": -sts["steps"][4]["eur"] / days,
            "extras_day": cats, "bills": fc["bills_ahead"]}


def simulate(cid: str, scenario: dict | None = None, comp: dict | None = None) -> dict:
    s = scenario or {}
    c = comp or components(cid)
    days, payday = c["days"], c["payday"]
    extras = dict(c["extras_day"])
    if s.get("pause_extras"):
        extras = {k: 0.0 for k in extras}
    for cut in s.get("cuts", []):
        if cut.get("category") in extras:
            extras[cut["category"]] *= max(0.0, 1 - float(cut.get("percent", 0)) / 100)
    moved = {m["bill"]: date.fromisoformat(m["date"]) for m in s.get("move_bills", []) if m.get("date")}
    events: dict[date, float] = {}
    for b in c["bills"]:
        when = moved.get(b["bill"], date.fromisoformat(b["date"]))
        if when <= payday:  # moved past payday = not paid in this pay month
            events[when] = events.get(when, 0) - b["eur"]
    for o in s.get("one_offs", []):
        d = min(max(date.fromisoformat(o["date"]), TODAY + timedelta(days=1)), payday)
        events[d] = events.get(d, 0) - abs(float(o["amount"]))
    for o in s.get("income", []):
        d = min(max(date.fromisoformat(o["date"]), TODAY + timedelta(days=1)), payday)
        events[d] = events.get(d, 0) + abs(float(o["amount"]))
    daily = c["essentials_day"] + c["surprises_day"] + sum(extras.values())
    bal, path, out = c["balance"], [], None
    for i in range(1, days + 1):
        d = TODAY + timedelta(days=i)
        bal += -daily + events.get(d, 0)
        path.append({"date": d.isoformat(), "balance_eur": _r(bal)})
        if bal < 0 and out is None:
            out = d
    return {"path": path, "end_eur": _r(bal), "runs_out": out.isoformat() if out else None,
            "extras_until_payday_eur": _r(sum(extras.values()) * days)}


def future(cid: str, scenario: dict | None = None) -> dict:
    """Base line, the no-extras edge of the band, and the scenario line if one is given."""
    comp = components(cid)
    base = simulate(cid, None, comp)
    noext = simulate(cid, {"pause_extras": True}, comp)
    out = {"base": base, "no_extras": noext, "next_payday": comp["payday"].isoformat(),
           "bills": comp["bills"], "extras_by_category_until_payday": {
               k: _r(v * comp["days"]) for k, v in sorted(comp["extras_day"].items(), key=lambda kv: -kv[1]) if v > 0}}
    if scenario:
        out["scenario"] = simulate(cid, scenario, comp)
        out["scenario"]["delta_at_payday_eur"] = _r(out["scenario"]["end_eur"] - base["end_eur"])
    return out


def _client():
    return anthropic.Anthropic()


def _json_call(system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict:
    resp = _client().messages.create(
        model=MODEL, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": user}],
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}})
    if resp.stop_reason == "refusal":
        raise ValueError("refused")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


SCENARIO_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["label", "pause_extras", "cuts", "move_bills", "one_offs", "income", "unsupported"],
    "properties": {
        "label": {"type": "string", "description": "Very short chip label in the user's language, max 28 characters."},
        "pause_extras": {"type": "boolean"},
        "cuts": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["category", "percent"],
                 "properties": {"category": {"type": "string", "enum": EXTRA_CATS}, "percent": {"type": "number"}}}},
        "move_bills": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["bill", "date"],
                       "properties": {"bill": {"type": "string", "enum": ["Housing", "Utilities"]}, "date": {"type": "string"}}}},
        "one_offs": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["label", "amount", "date"],
                     "properties": {"label": {"type": "string"}, "amount": {"type": "number"}, "date": {"type": "string"}}}},
        "income": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["label", "amount", "date"],
                   "properties": {"label": {"type": "string"}, "amount": {"type": "number"}, "date": {"type": "string"}}}},
        "unsupported": {"type": ["string", "null"], "description": "One short plain sentence if it can't be done, else null."},
    },
}


def parse_whatif(cid: str, text: str, lang: str = "en") -> dict:
    """Natural language what-if → scenario (AI) → forecast (code)."""
    comp = components(cid)
    ctx = {"today": TODAY.isoformat(), "weekday_today": TODAY.strftime("%A"), "next_payday": comp["payday"].isoformat(),
           "bills_before_payday": comp["bills"],
           "everyday_extras_until_payday_by_category_eur": {k: _r(v * comp["days"]) for k, v in comp["extras_day"].items() if v > 0}}
    system = ("You turn a bank customer's what-if question into a scenario for a forecast engine. Use only what the "
              "user said; never invent amounts. Dates are ISO, from tomorrow to next payday; moving a bill to after "
              "payday means the day after next payday. "
              "'Pause/stop/no extras' = pause_extras. 'Eat out less' = cuts on Restaurants. A purchase = one_offs; "
              "money coming in = income. Moving rent = move_bills Housing (only if that bill is before payday). If it can't "
              "be done (amount missing, no such bill), set unsupported to ONE short plain sentence (max 90 characters, "
              "no ISO dates, no technical words) in the label's language; otherwise null. "
              f"Write the label in {'Finnish' if lang == 'fi' else 'Swedish' if lang == 'sv' else 'English'}.")
    sc = _json_call(system, f"Context: {json.dumps(ctx)}\nWhat if: {text}", SCENARIO_SCHEMA)
    if isinstance(sc.get("unsupported"), str):
        sc["unsupported"] = sc["unsupported"].strip().strip("{}\"'").strip() or None
    # Amounts must come from the user's own words (verified the same way as coach answers).
    said = {float(x.replace(" ", "").replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", text)}
    for k in ("one_offs", "income"):
        sc[k] = [o for o in sc[k] if round(abs(float(o["amount"])), 2) in said]
    return {"parsed": sc, **future(cid, sc)}


FACTS_HELP = "Facts are computed from the customer's data; every number you write must appear in them."
NOTES_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["notes"],
    "properties": {"notes": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["date", "text"],
        "properties": {"date": {"type": "string"}, "text": {"type": "string", "description": "Max 30 characters."}}}}},
}


BILL_NAMES = {"Housing": {"en": "Rent", "fi": "Vuokra", "sv": "Hyra"}, "Utilities": {"en": "Bills", "fi": "Laskut", "sv": "Räkningar"}}


def line_facts(cid: str, lang: str = "en") -> dict:
    rib = insights.ribbon(cid)
    start = date.fromisoformat(rib["last_payday"])
    days = _q("""SELECT tx_date d, round(-sum(amount), 2) t, list(sub ORDER BY amount) subs FROM tx
                 WHERE customer_id = ? AND tx_date > ? AND tx_date <= ? AND kind = 'spend' GROUP BY 1 ORDER BY t DESC LIMIT 3""",
              [cid, start, TODAY])
    nospend = (TODAY - start).days - _q("SELECT count(DISTINCT tx_date) n FROM tx WHERE customer_id = ? AND tx_date > ? "
                                        "AND tx_date <= ? AND kind = 'spend'", [cid, start, TODAY])[0]["n"]
    pp = insights.payday_pattern(cid)
    return {"today": TODAY.isoformat(), "last_payday": rib["last_payday"], "salary_eur": rib["salary_eur"],
            "biggest_spending_days": [{"date": str(d["d"]), "total_eur": d["t"], "what": d["subs"][:2]} for d in days],
            "no_spend_days_since_payday": nospend,
            "extras_per_day_week_after_vs_before_payday_percent": pp["payday_week_change_percent"],
            "bills_ahead": [{**b, "name": BILL_NAMES.get(b["bill"], {}).get(lang, b["bill"])} for b in rib["bills_ahead"]],
            "goes_below_zero_on": rib["runs_out_around"],
            "balance_at_payday_usual_pace_eur": rib["balance_at_payday_eur"], "next_payday": rib["next_payday"]}


def _fallback_notes(f: dict) -> list[dict]:
    notes = []
    if f["biggest_spending_days"]:
        b = f["biggest_spending_days"][0]
        notes.append({"date": b["date"], "text": f"Biggest day: {round(b['total_eur'])} €"})
    if f["goes_below_zero_on"]:
        notes.append({"date": f["goes_below_zero_on"], "text": "Below zero from here"})
    return notes


def annotations(cid: str, lang: str = "en") -> dict:
    key = f"{cid}:{lang}"
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if key in cache:
        return cache[key]
    f = line_facts(cid, lang)
    lname = {"fi": "Finnish", "sv": "Swedish"}.get(lang, "English")
    system = (f"You annotate a customer's balance line in a banking app with 2-3 short notes in {lname}, each pinned to a "
              "date in the facts. Point at what explains the shape: big spending days, the payday-week effect, a bill "
              f"that pushes the balance below zero, no-spend streaks. Max 30 characters each, plain words, no blame. "
              f"Round amounts to whole euros and write them like 205 €. Call bills by their 'name'. Don't repeat a bill's "
              f"name and amount on its own: the graph already labels bills; say what it does instead. {FACTS_HELP}")
    try:
        notes = _json_call(system, json.dumps(f, default=str), NOTES_SCHEMA)["notes"]
        trace = [{"tool": "facts", "error": False, "result": f}]
        ok = []
        valid_dates = {f["last_payday"], f["today"], f["next_payday"]} | {d["date"] for d in f["biggest_spending_days"]} | \
                      {b["date"] for b in f["bills_ahead"]} | ({f["goes_below_zero_on"]} if f["goes_below_zero_on"] else set())
        for n in notes[:3]:
            nums = verify.check(n["text"], trace, [], lang)
            if n["date"] in valid_dates and all(x["status"] != "unverified" for x in nums):
                ok.append(n)
        source = "ai"
    except Exception as e:  # API down or refused: deterministic notes, clearly marked
        log.warning("annotations fallback: %s", e)
        ok, source = _fallback_notes(f), "rules"
    out = {"notes": ok or _fallback_notes(f), "source": source if ok else "rules", "model": MODEL}
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        cache[key] = out
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1))
    return out
