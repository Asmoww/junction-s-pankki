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

from . import eu, insights, live, money, style, verify
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
    if eu.active():  # EU mode: the open model we host in Finland does the same job
        return eu.json_call(system, user, schema, max_tokens)
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
        "one_offs": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["label", "amount", "date", "lookup"],
                     "properties": {"label": {"type": "string"}, "amount": {"type": ["number", "null"]}, "date": {"type": "string"},
                                    "lookup": {"type": ["string", "null"], "description": "Only when the user gave no amount: a short shop search for the item, e.g. 'pesukone 8 kg'"}}}},
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
              "'Pause/stop/no extras' = pause_extras. 'Eat out less' = cuts on Restaurants. A purchase = one_offs; if the user names "
              "something to buy but no amount, set amount null and lookup to a short shop search for it (the app reads live "
              "prices from shop pages); "
              "money coming in = income. Moving rent = move_bills Housing (only if that bill is before payday). If it can't "
              "be done (amount missing, no such bill), set unsupported to ONE short plain sentence (max 90 characters, "
              "no ISO dates, no technical words) in the label's language; otherwise null. "
              f"Write the label in {'Finnish' if lang == 'fi' else 'Swedish' if lang == 'sv' else 'English'}." + style.guide(lang))
    sc = _json_call(system, f"Context: {json.dumps(ctx)}\nWhat if: {text}", SCENARIO_SCHEMA)
    if isinstance(sc.get("unsupported"), str):
        sc["unsupported"] = sc["unsupported"].strip().strip("{}\"'").strip() or None
    # Amounts must come from the user's own words (verified the same way as coach answers).
    said = {float(x.replace(" ", "").replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", text)}
    sc["income"] = [o for o in sc["income"] if o.get("amount") is not None and round(abs(float(o["amount"])), 2) in said]
    # A purchase without an amount gets a live price confirmed on a shop page (Context.dev), or the app asks for it.
    keep, prices = [], []
    for o in sc["one_offs"]:
        if o.get("amount") is not None:
            if round(abs(float(o["amount"])), 2) in said:
                keep.append(o)
            continue
        r = None
        if o.get("lookup"):
            try:
                r = live.cached_purchase(o["lookup"], max_age_h=1)
            except (live.LiveUnavailable, ValueError) as e:
                log.info("no live price for %r: %s", o["lookup"], e)
        if r and r.get("confirmed"):
            best = r["confirmed"][0]  # the cheapest price confirmed on a shop's own page
            o["amount"] = best["price_eur"]
            prices.append({"item": r["item"], "price_eur": best["price_eur"], "shop": best["domain"], "url": best["url"],
                           "offers_confirmed": len(r["confirmed"]), "checked_at": r["checked_at"]})
            name = o.get("label") or r["item"]
            name = name if len(name) <= 18 else name[:18].rsplit(" ", 1)[0] + "…"
            sc["label"] = f"{name} {best['price_eur']:.0f} € · {best['domain']}"
            keep.append(o)
        else:
            sc["unsupported"] = NO_PRICE.get(lang, NO_PRICE["en"]).format(item=o.get("label") or o.get("lookup") or "")
    sc["one_offs"] = keep
    return {"parsed": sc, "live_prices": prices, **future(cid, sc)}


NO_PRICE = {"en": "I couldn't confirm a price for {item}. Add the amount, e.g. '{item} 150 €'.",
            "fi": "En saanut varmistettua hintaa: {item}. Lisää summa, esim. '{item} 150 €'.",
            "sv": "Jag kunde inte bekräfta ett pris för {item}. Lägg till beloppet, t.ex. '{item} 150 €'."}


FACTS_HELP = "Facts are computed from the customer's data; every number you write must appear in them."
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


# The AI chooses what to point at (kind + date); code fills in the value from the facts and the words from this table,
# so the labels are always correct in every language and on every model.
NOTE_PHRASES = {
    "en": {"biggest_day": "Biggest day {v} €", "big_day": "Big day {v} €", "no_spend_days": "{n} no-spend days",
           "payday_week": "Payday week +{p} %", "below_zero": "Below zero here", "payday": "Payday {v} €"},
    "fi": {"biggest_day": "Suurin menopäivä {v} €", "big_day": "Iso menopäivä {v} €", "no_spend_days": "{n} ostotonta päivää",
           "payday_week": "Palkkaviikko +{p} %", "below_zero": "Tili miinukselle", "payday": "Palkkapäivä {v} €"},
    "sv": {"biggest_day": "Största dagen {v} €", "big_day": "Stor dag {v} €", "no_spend_days": "{n} köpfria dagar",
           "payday_week": "Löneveckan +{p} %", "below_zero": "Kontot på minus", "payday": "Lönedag {v} €"},
}
NOTE_KINDS = list(NOTE_PHRASES["en"])


def _eur_whole(x: float, lang: str) -> str:
    s = f"{round(x):,}"
    return s if lang == "en" else s.replace(",", "\u00a0")


def _render_note(kind: str, d: str, f: dict, lang: str) -> dict | None:
    """One note as text, or None if the facts don't support it on that date."""
    ph = NOTE_PHRASES.get(lang, NOTE_PHRASES["en"])
    days = {x["date"]: x for x in f["biggest_spending_days"]}
    if kind in ("biggest_day", "big_day"):
        if d not in days:
            return None
        kind = "biggest_day" if f["biggest_spending_days"][0]["date"] == d else "big_day"
        return {"date": d, "kind": kind, "text": ph[kind].format(v=_eur_whole(days[d]["total_eur"], lang))}
    if kind == "no_spend_days":
        n = f["no_spend_days_since_payday"]
        return {"date": d, "kind": kind, "text": ph[kind].format(n=n)} if n >= 2 and d <= f["today"] else None
    if kind == "payday_week":
        p = f["extras_per_day_week_after_vs_before_payday_percent"]
        return {"date": d, "kind": kind, "text": ph[kind].format(p=round(p))} if p is not None and p >= 10 and d <= f["today"] else None
    if kind == "below_zero":
        return {"date": d, "kind": kind, "text": ph[kind]} if d == f["goes_below_zero_on"] else None
    if kind == "payday":
        return ({"date": d, "kind": kind, "text": ph[kind].format(v=_eur_whole(f["salary_eur"], lang))}
                if d == f["last_payday"] and f.get("salary_eur") else None)
    return None


def _fallback_notes(f: dict, lang: str = "en") -> list[dict]:
    picks = []
    if f["biggest_spending_days"]:
        picks.append(("biggest_day", f["biggest_spending_days"][0]["date"]))
    if f["goes_below_zero_on"]:
        picks.append(("below_zero", f["goes_below_zero_on"]))
    return [n for n in (_render_note(k, d, f, lang) for k, d in picks) if n]


NOTES_PICK_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["notes"],
    "properties": {"notes": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["date", "kind"],
        "properties": {"date": {"type": "string"}, "kind": {"type": "string", "enum": NOTE_KINDS}}}}},
}


def annotations(cid: str, lang: str = "en") -> dict:
    key = f"{cid}:{lang}{eu.cache_tag()}"
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if key in cache:
        return cache[key]
    f = line_facts(cid, lang)
    system = ("You choose 2-3 annotations for a customer's balance line in a banking app: the moments that best explain "
              "its shape. Kinds: biggest_day / big_day (a date from biggest_spending_days), no_spend_days (a past date, "
              "only if there are several), payday_week (a date in the week after last_payday, only if extras rise a lot "
              "after payday), below_zero (exactly goes_below_zero_on), payday (exactly last_payday). Prefer what a "
              "person would want explained: the big days, the payday-week effect, where it goes below zero. Spread the "
              "dates out; no two on the same date. Return kind and date only; the app writes the labels.")
    try:
        picks = _json_call(system, json.dumps(f, default=str), NOTES_PICK_SCHEMA)["notes"]
        ok, seen = [], set()
        for pk in picks:
            n = _render_note(pk.get("kind"), str(pk.get("date")), f, lang)
            if n and n["date"] not in seen and (n["kind"] == "big_day" or n["kind"] not in {x["kind"] for x in ok}):
                ok.append(n); seen.add(n["date"])
            if len(ok) == 3:
                break
        source = "ai"
    except Exception as e:  # API down or refused: deterministic notes, clearly marked
        log.warning("annotations fallback: %s", e)
        ok, source = _fallback_notes(f, lang), "rules"
    out = {"notes": ok or _fallback_notes(f, lang), "source": source if ok else "rules", "model": eu.label() if eu.active() else MODEL}
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        cache[key] = out
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1))
    return out


# ---------------------------------------------------------------- Notes on the longer ranges (3, 12, 24 months)
# Same split as the pay-month notes: code finds the moments, the AI picks which 2-3 explain the line best, and the
# labels come from this table, so every number on the graph is a code number.
LONG_PHRASES = {
    "en": {"lowest": "Lowest {v} €", "below_zero_spell": "{n} days below zero", "top_month": "Most spent {v} €",
           "best_month": "Best month +{v} €", "worst_month": "Toughest month −{v} €", "biggest_day": "Biggest day {v} €"},
    "fi": {"lowest": "Alimmillaan {v} €", "below_zero_spell": "{n} päivää miinuksella", "top_month": "Eniten menoja {v} €",
           "best_month": "Paras kuukausi +{v} €", "worst_month": "Tiukin kuukausi −{v} €", "biggest_day": "Suurin menopäivä {v} €"},
    "sv": {"lowest": "Lägst {v} €", "below_zero_spell": "{n} dagar på minus", "top_month": "Mest utgifter {v} €",
           "best_month": "Bästa månaden +{v} €", "worst_month": "Tuffaste månaden −{v} €", "biggest_day": "Största dagen {v} €"},
}
LONG_KINDS = list(LONG_PHRASES["en"])


def long_facts(cid: str, months: int) -> dict:
    """The moments worth explaining on a 3/12/24-month balance line, each with its date and value (all from code)."""
    h = insights.balance_history(cid, months)
    start = date.fromisoformat(h["period"]["start"])
    eod = _q("SELECT tx_date d, arg_max(balance, seq) b FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? "
             "GROUP BY 1 ORDER BY 1", [cid, start, TODAY])
    have = {r["d"]: float(r["b"]) for r in eod}
    bal, d, spell, best_spell = float(eod[0]["b"]), start, None, None
    while d <= TODAY:                       # longest run of days below zero
        bal = have.get(d, bal)
        if bal < 0:
            spell = (spell[0], spell[1] + 1) if spell else (d, 1)
            if not best_spell or spell[1] > best_spell[1]:
                best_spell = spell
        else:
            spell = None
        d += timedelta(days=1)
    day_ = _q("SELECT tx_date d, -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND kind = 'spend' "
              "GROUP BY 1 ORDER BY t DESC LIMIT 1", [cid, start, TODAY])
    pm = [m for m in h["per_month"] if m["out_eur"] or m["in_eur"]]
    mid = lambda m: f"{m['month']}-15"  # noqa: E731  a month's note sits mid-month
    m = {}
    m["lowest"] = {"date": h["lowest"]["date"], "v": h["lowest"]["balance_eur"]}
    if best_spell and best_spell[1] >= 2:
        m["below_zero_spell"] = {"date": best_spell[0].isoformat(), "n": best_spell[1]}
    if len(pm) >= 2:
        top = max(pm, key=lambda x: x["out_eur"])
        nets = [(x, x["in_eur"] - x["out_eur"]) for x in pm]
        best, worst = max(nets, key=lambda t: t[1]), min(nets, key=lambda t: t[1])
        m["top_month"] = {"date": mid(top), "v": top["out_eur"], "month": top["month"]}
        if best[1] > 0:
            m["best_month"] = {"date": mid(best[0]), "v": round(best[1], 2), "month": best[0]["month"]}
        if worst[1] < 0:
            m["worst_month"] = {"date": mid(worst[0]), "v": round(-worst[1], 2), "month": worst[0]["month"]}
    if day_:
        m["biggest_day"] = {"date": str(day_[0]["d"]), "v": float(day_[0]["t"])}
    return {"months": months, "start": h["period"]["start"], "end": TODAY.isoformat(), "change_eur": h["change_eur"],
            "days_below_zero": h["days_below_zero"], "moments": m}


def _render_long(kind: str, f: dict, lang: str) -> dict | None:
    x = f["moments"].get(kind)
    if not x:
        return None
    ph = LONG_PHRASES.get(lang, LONG_PHRASES["en"])[kind]
    text = ph.format(n=x.get("n"), v=_eur_whole(abs(x.get("v") or 0), lang))
    if kind == "lowest" and x["v"] < 0:
        text = text.replace(" " + _eur_whole(abs(x["v"]), lang), " −" + _eur_whole(abs(x["v"]), lang))
    return {"date": x["date"], "kind": kind, "text": text, **({"month": x["month"]} if "month" in x else {})}


LONG_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["kinds"],
               "properties": {"kinds": {"type": "array", "items": {"type": "string", "enum": LONG_KINDS}}}}


def long_annotations(cid: str, months: int, lang: str = "en") -> dict:
    lang = lang if lang in LONG_PHRASES else "en"
    key = f"long:{cid}:{months}:{lang}{eu.cache_tag()}"
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if key in cache:
        return cache[key]
    f = long_facts(cid, months)
    fallback = [k for k in ("below_zero_spell", "lowest", "top_month") if k in f["moments"]][:3]
    system = ("You choose 2-3 annotations for a customer's balance line over the last months in a banking app: the "
              "moments that best explain its shape to them. Kinds: lowest (the lowest balance), below_zero_spell (the "
              "longest run of days below zero), top_month (the month with the most spending), best_month (most money "
              "left over), worst_month (the biggest shortfall), biggest_day (the biggest spending day). Only kinds "
              "present in moments. Prefer what explains the line (the low points and why), avoid two notes on the "
              "same month, and return kinds only; the app writes the labels from the data.")
    try:
        kinds = _json_call(system, json.dumps(f, default=str), LONG_SCHEMA, max_tokens=200)["kinds"]
        source = "ai"
    except Exception as e:  # noqa: BLE001
        log.warning("long annotations fallback: %s", e)
        kinds, source = fallback, "rules"
    out, months_used = [], set()
    for k in list(dict.fromkeys(kinds)) or fallback:
        n = _render_long(k, f, lang)
        if n and n["date"][:7] not in months_used:
            out.append(n); months_used.add(n["date"][:7])
        if len(out) == 3:
            break
    if not out:
        out, source = [n for n in (_render_long(k, f, lang) for k in fallback) if n], "rules"
    res = {"notes": out, "source": source, "model": eu.label() if eu.active() else MODEL}
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        cache[key] = res
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1))
    return res
