"""Play your next two weeks: the customer's likely days until payday as cards, with the three baskets as the rules.

- Fixed must-pays (basket 1: rent, bills, groceries) can't be skipped; rent can be moved to after payday.
- The surprise buffer (basket 2) can't be skipped either: surprises come whether you plan for them or not.
- Everyday extras (basket 3) are the choices: keep or skip each one.

Code predicts the cards from the customer's own last 90 days (how often each habit happens, its usual price and
usual weekday) and computes every balance. Claude does two small jobs on top: before the game it suggests which
cards to skip and why (no numbers; code computes where that plan lands), and after it sums up the choices (numbers
checked against the result). The line is the forecast engine's no-extras line minus the extras kept, so keeping
everything ends exactly where the usual forecast does.
"""
from __future__ import annotations

import json
from urllib.parse import urlparse
import logging
import statistics
import threading
from datetime import timedelta
from pathlib import Path

from . import eu, future, insights, live, money, style, verify
from .money import TODAY, _q, _r

log = logging.getLogger("play")
CACHE = Path(__file__).resolve().parent.parent / "state" / "play_tips.json"
_lock = threading.Lock()
MAX_CARDS = 8
TRANSPORT = ("Parking", "Taxis")  # habits a public-transport ticket can replace


def _hourly(cid: str) -> float | None:
    sal = [r["a"] for r in _q("SELECT amount a FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date > ?",
                              [cid, TODAY - timedelta(days=365)])]
    return statistics.median(sal) / 160 if sal else None


def deal(cid: str) -> dict:
    """The cards and the lines, all from code."""
    comp = future.components(cid)
    days, payday = comp["days"], comp["payday"]
    noext = future.simulate(cid, {"pause_extras": True}, comp)
    base = future.simulate(cid, None, comp)
    pace = sum(comp["extras_day"].values()) * days
    since = TODAY - timedelta(days=90)
    habits = _q("""WITH d AS (SELECT tx_date, sub, -sum(amount) a FROM tx WHERE customer_id = ? AND tx_date > ? AND basket = 3
                               GROUP BY 1, 2)
                   SELECT sub, count(*) n, median(a) typ FROM d GROUP BY 1 ORDER BY sum(a) DESC""", [cid, since])
    wk = {}
    for r in _q("""SELECT sub, dayofweek(tx_date) w, count(*) n FROM tx WHERE customer_id = ? AND basket = 3 AND tx_date > ?
                   GROUP BY 1, 2""", [cid, TODAY - timedelta(days=365)]):
        wk.setdefault(r["sub"], {})[r["w"]] = r["n"]
    horizon = [TODAY + timedelta(days=i) for i in range(1, days + 1)]
    hour = _hourly(cid)
    extras = []
    for h in habits:
        expected = h["n"] / 90 * days
        n = round(expected) if expected >= 1 else (1 if expected >= 0.45 else 0)
        if not n:
            continue
        pref = wk.get(h["sub"], {})
        dates = sorted(horizon, key=lambda d: (-pref.get(d.isoweekday() % 7, 0), d))[:n]
        for d in sorted(dates):
            extras.append({"merchant_type": h["sub"], "date": d.isoformat(), "amount_eur": _r(h["typ"]),
                           "times_in_90_days": h["n"]})
    extras = sorted(sorted(extras, key=lambda c: -c["amount_eur"])[:MAX_CARDS], key=lambda c: c["date"])
    rest = _r(pace - sum(c["amount_eur"] for c in extras))
    cards = [{"id": "ess", "kind": "fixed", "basket": 1, "label": "groceries", "amount_eur": _r(comp["essentials_day"] * days),
              "date": None},
             {"id": "sur", "kind": "buffer", "basket": 2, "label": "surprises", "amount_eur": _r(comp["surprises_day"] * days),
              "date": None}]
    bills = sorted(comp["bills"], key=lambda b: b["date"])
    for b in bills:
        cards.append({"id": f"bill:{b['bill']}", "kind": "fixed", "basket": 1, "label": b["bill"], "amount_eur": _r(b["eur"]),
                      "date": b["date"], "movable": b["bill"] == "Housing" and b["date"] < payday.isoformat()})
    for i, c in enumerate(extras):
        cards.append({"id": f"x{i}", "kind": "extra", "basket": 3, "label": c["merchant_type"], **c,
                      "hours_of_work": round(c["amount_eur"] / hour, 1) if hour else None})
    if rest >= 10:
        cards.append({"id": "rest", "kind": "extra", "basket": 3, "label": "everything_else", "amount_eur": rest, "date": None,
                      "hours_of_work": round(rest / hour, 1) if hour else None})
    # dated cards in date order; the two whole-period cards first, everything-else last
    cards.sort(key=lambda c: (c["id"] not in ("ess", "sur"), c["id"] == "rest", c["date"] or ""))
    # Swap: a live, official ticket price (Context.dev, hsl.fi) can replace the parking and taxi cards
    swap, hsl = None, live.registry().get("hsl_30day_ab", {})
    replaces = [c["id"] for c in cards if c["kind"] == "extra" and c["label"] in TRANSPORT]
    if replaces and hsl.get("status") == "confirmed":
        swap = {"label": "hsl_30day_ab", "price_eur": hsl["value"], "source_url": hsl["source_url"], "fetched_at": hsl.get("fetched_at"),
                "valid_from": hsl.get("source_date"), "replaces": replaces, "replaced_eur": _r(sum(c["amount_eur"] for c in cards if c["id"] in replaces)),
                "covers_until": (TODAY + timedelta(days=30)).isoformat(),
                "hours_of_work": round(hsl["value"] / hour, 1) if hour else None}
    return {"days": days, "today": TODAY.isoformat(), "next_payday": payday.isoformat(), "balance_eur": comp["balance"],
            "no_extras_path": noext["path"], "keep_all_end_eur": base["end_eur"], "skip_all_end_eur": noext["end_eur"],
            "cards": cards, "swap": swap, "monthly_gap_eur": _monthly_gap(cid)}


def _monthly_gap(cid: str) -> float | None:
    """The structural gap: how much a typical month runs short (12-month average of income minus spending). The game
    can get someone to payday by timing; this says honestly whether the months themselves add up."""
    f = insights.money_health(cid)["facts"]
    gap = (f.get("spend_month") or 0) - (f.get("income_month") or 0)
    return _r(gap) if gap > 0 else None


def outcome(cid: str, kept: list[str], move_rent: bool, d: dict | None = None, swap: bool = False) -> dict:
    """Where the chosen plan lands, recomputed by the forecast engine."""
    d = d or deal(cid)
    byid = {c["id"]: c for c in d["cards"]}
    sc = {"pause_extras": True, "one_offs": [], "move_bills": []}
    sw = d.get("swap") if swap else None
    if sw:  # the ticket is bought tomorrow; the parking and taxi cards it replaces are gone
        kept = [k for k in kept if k not in sw["replaces"]]
        sc["one_offs"].append({"label": "ticket", "amount": sw["price_eur"], "date": (TODAY + timedelta(days=1)).isoformat()})
    for k in kept:
        c = byid.get(k)
        if not c or c["kind"] != "extra":
            continue
        if c["id"] == "rest":  # spread over the days, like the usual pace
            per = c["amount_eur"] / d["days"]
            sc["one_offs"] += [{"label": "rest", "amount": per, "date": (TODAY + timedelta(days=i)).isoformat()}
                               for i in range(1, d["days"] + 1)]
        else:
            sc["one_offs"].append({"label": c["label"], "amount": c["amount_eur"], "date": c["date"]})
    if move_rent:
        sc["move_bills"].append({"bill": "Housing", "date": (TODAY + timedelta(days=d["days"] + 1)).isoformat()})
    r = future.simulate(cid, sc)
    kept_eur = sum(byid[k]["amount_eur"] for k in kept if k in byid and byid[k]["kind"] == "extra")
    skipped = [c for c in d["cards"] if c["kind"] == "extra" and c["id"] not in kept and not (sw and c["id"] in sw["replaces"])]
    return {"end_eur": r["end_eur"], "goes_below_zero_on": r["runs_out"], "extras_kept_eur": _r(kept_eur),
            "extras_skipped_eur": _r(sum(c["amount_eur"] for c in skipped)),
            "skipped": [{"what": c["label"], "date": c["date"], "eur": c["amount_eur"]} for c in skipped],
            "rent_moved_after_payday": move_rent, "keep_all_end_eur": d["keep_all_end_eur"], "next_payday": d["next_payday"],
            "months_still_short_by_eur": d.get("monthly_gap_eur"),
            "swapped_to_ticket": ({"ticket_eur": sw["price_eur"], "replaced_parking_and_taxis_eur": sw["replaced_eur"],
                                   "source": urlparse(sw["source_url"]).netloc.removeprefix("www.")} if sw else None),
            "scenario": sc}


TIP_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["skip", "move_rent", "swap", "tip"],
              "properties": {"skip": {"type": "array", "items": {"type": "string"}}, "move_rent": {"type": "boolean"}, "swap": {"type": "boolean"},
                             "tip": {"type": "string"}}}


def tip(cid: str, lang: str = "en") -> dict | None:
    """Claude suggests a plan (which extras to skip, whether to move rent) with one line of why; code checks where it
    lands. Cached per customer and language."""
    key = f"{cid}:{lang}{eu.cache_tag()}"
    with _lock:
        cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    d = deal(cid)
    if key not in cache:
        lname = {"fi": "Finnish", "sv": "Swedish"}.get(lang, "English")
        system = (f"You coach a bank customer, in {lname}, before they plan their days until payday. Cards of kind 'extra' "
                  "can be skipped; rent can be moved to after payday if 'movable'; fixed and buffer cards stay. If 'swap' is given, a "
                  "public-transport ticket can replace the parking and taxi cards (set swap true if that helps). Suggest the "
                  "smallest plan that reaches payday at or above zero, keeping the extras that look most valued (frequent "
                  "habits) where possible. If skipping extras can't get there, say so and suggest moving rent. Return the "
                  "ids to skip, move_rent, and tip: one friendly line (max 110 characters) with NO digits, explaining the "
                  "idea (e.g. timing beats coffee). The tip must match the plan: if move_rent is true, say rent moves to "
                  "after payday; never suggest paying rent early." + style.guide(lang))
        facts = {k: d[k] for k in ("keep_all_end_eur", "skip_all_end_eur", "next_payday")}
        facts["cards"] = [{k: c.get(k) for k in ("id", "kind", "label", "date", "amount_eur", "movable")} for c in d["cards"]]
        facts["swap"] = ({k: d["swap"][k] for k in ("price_eur", "replaces", "replaced_eur", "covers_until")} if d["swap"] else None)
        try:
            t = future._json_call(system, json.dumps(facts), TIP_SCHEMA, max_tokens=600)
        except Exception as e:  # noqa: BLE001
            log.warning("play tip failed: %s", e)
            return None
        t["tip"] = style.proofread({"tip": t["tip"]}, lang).get("tip", t["tip"])
        if any(ch.isdigit() for ch in t["tip"]) or len(t["tip"]) > 160:
            return None
        cache[key] = t
        with _lock:
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps({**(json.loads(CACHE.read_text()) if CACHE.exists() else {}), key: t},
                                        indent=1, ensure_ascii=False))
    t = cache[key]
    ids = {c["id"] for c in d["cards"] if c["kind"] == "extra"}
    skip = [i for i in t["skip"] if i in ids]
    sw = bool(t.get("swap")) and bool(d["swap"])
    o = outcome(cid, [i for i in ids if i not in skip], t["move_rent"], d, sw)
    return {"skip": skip, "move_rent": t["move_rent"], "swap": sw, "tip": t["tip"], "end_eur": o["end_eur"]}


SUM_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["summary"],
              "properties": {"summary": {"type": "string"}}}


def finish(cid: str, kept: list[str], move_rent: bool, lang: str = "en", swap: bool = False) -> dict:
    o = outcome(cid, kept, move_rent, swap=swap)
    lname = {"fi": "Finnish", "sv": "Swedish"}.get(lang, "English")
    system = (f"In {lname}, write ONE short sentence (max 140 characters) summing up a customer's plan until payday: what "
              "they skipped, swapped or moved and where they land. If rent was moved, say it needs the landlord's OK. If they land below zero, be kind and name the one lever that "
              "would help most. At most two numbers, from the facts, rounded to whole euros like 87 €. Never judge." + style.guide(lang))
    facts = {k: v for k, v in o.items() if k != "scenario"}
    trace = [{"tool": "plan", "error": False, "result": facts}]
    o["summary"] = None
    try:
        s = future._json_call(system, json.dumps(facts), SUM_SCHEMA, max_tokens=300)["summary"]
        s = style.proofread({"s": s}, lang).get("s", s)
        if len(s) <= 180 and all(n["status"] != "unverified" for n in verify.check(s, trace, [], lang)):
            o["summary"] = s
    except Exception as e:  # noqa: BLE001
        log.warning("play summary failed: %s", e)
    return o
