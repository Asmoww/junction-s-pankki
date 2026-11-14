"""Scenario planner (Plan): months ahead, not just to payday.

What it does
- profile(): the customer's own starting point, built from their last 12 months: income by source, fixed must-pays
  (basket 1), surprise must-pays (basket 2, lumpy), everyday extras (basket 3) by category, savings transfers.
- assumptions(): every input the plan uses, each with its value, unit, where it came from ("your data: median of the
  last 12 months", "your edit", "scenario"), and the range the user may move it in. Nothing hidden.
- suggest(): scenarios picked from the analysis of this customer's own habits and income (not a fixed menu), each
  with the reason in plain words and its effect.
- run(): Monte Carlo over the customer's own months. Each simulated month re-draws one real past month's surprise
  must-pays, extras mix and other income, so lumpy months and irregular income show up as a range (bad / typical /
  good), not one false-precise line. Baseline and scenario use the same draws, so the difference is the lever's
  effect, not noise.

Money tools stay deterministic (fixed seed); the AI may pick and explain scenarios but never computes them.
The core (`run`, `suggest`, `assumptions`) is pure: it takes a profile dict and is unit-tested without the database.
"""
from __future__ import annotations

import math
import random
import statistics

DEFAULT_HORIZON = 12
SIMS = 400
SEED = 20261114

# Levers a scenario may set. Every one is shown to the user with its bounds.
LEVERS = {
    "horizon_months": {"label": "Months ahead", "unit": "months", "min": 3, "max": 36, "step": 1},
    "salary_change_pct": {"label": "Salary change", "unit": "%", "min": -50, "max": 50, "step": 1},
    "other_income_kept_pct": {"label": "Other income that continues", "unit": "%", "min": 0, "max": 100, "step": 5},
    "fixed_change_eur": {"label": "Change in fixed must-pays (rent, bills)", "unit": "€/month", "min": -1500, "max": 1500, "step": 10},
    "surprise_scale_pct": {"label": "Surprise must-pays compared with your past", "unit": "%", "min": 0, "max": 300, "step": 10},
    "extras_cut_pct": {"label": "Cut in everyday extras (all)", "unit": "%", "min": 0, "max": 100, "step": 5},
    "category_cuts_pct": {"label": "Cut per extras category", "unit": "% per category", "min": 0, "max": 100, "step": 5},
    "save_on_payday_eur": {"label": "Moved to savings on payday", "unit": "€/month", "min": 0, "max": 5000, "step": 10},
    "one_offs": {"label": "One-off costs or income", "unit": "list of {month, amount_eur, label}", "min": None, "max": None, "step": None},
}


def _pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _r(x: float) -> float:
    return round(float(x), 2)


# ---------- assumptions ----------

def assumptions(profile: dict, levers: dict | None = None) -> list[dict]:
    """Every input with its source and allowed range. `levers` = what the user or scenario changed."""
    lv = levers or {}
    m = profile["months"]
    n = len(m)
    sal = statistics.median([x["salary"] for x in m])
    oth = statistics.fmean([x["other_income"] for x in m])
    fixed = statistics.median([x["fixed"] for x in m])
    sur = statistics.fmean([x["surprise"] for x in m])
    ext = statistics.median([sum(x["extras"].values()) for x in m])
    src = f"your data: last {n} months"
    rows = [
        {"key": "start_balance_eur", "label": "Account balance now", "value": _r(profile["balance"]), "unit": "€",
         "source": "your account today", "editable": False},
        {"key": "savings_moved_start_eur", "label": "Money the plan has moved to savings", "value": 0.0, "unit": "€",
         "source": "starts at 0; your current savings are inside the account balance", "editable": False},
        {"key": "salary_eur", "label": "Salary per month", "value": _r(sal), "unit": "€/month", "source": f"{src}, median", "editable": False},
        {"key": "other_income_eur", "label": "Other income per month (irregular)", "value": _r(oth), "unit": "€/month",
         "source": f"{src}, average; months drawn from your real ones", "editable": False},
        {"key": "fixed_eur", "label": "Fixed must-pays (rent, bills, groceries)", "value": _r(fixed), "unit": "€/month",
         "source": f"{src}, median", "editable": False},
        {"key": "surprise_eur", "label": "Surprise must-pays (health, repairs)", "value": _r(sur), "unit": "€/month on average",
         "source": f"{src}; each simulated month re-draws one of your real months, so big months happen", "editable": False},
        {"key": "moved_out_eur", "label": "Already moved to savings, investments or another bank",
         "value": _r(statistics.median([x.get("moved_out", 0.0) for x in m])), "unit": "€/month",
         "source": f"{src}, median; counted as savings, not spending", "editable": False},
        {"key": "extras_eur", "label": "Everyday extras", "value": _r(ext), "unit": "€/month", "source": f"{src}, median", "editable": False},
        {"key": "method", "label": "How the range is made", "value": SIMS, "unit": "simulated futures",
         "source": "bad / typical / good = 10th / 50th / 90th percentile; same draws for baseline and scenario", "editable": False},
    ]
    for k, meta in LEVERS.items():
        default = {"horizon_months": DEFAULT_HORIZON, "other_income_kept_pct": 100, "surprise_scale_pct": 100,
                   "category_cuts_pct": {}, "one_offs": []}.get(k, 0)
        val = lv.get(k, default)
        rows.append({"key": k, "label": meta["label"], "value": val, "unit": meta["unit"],
                     "source": "your edit" if k in lv else "default (no change)", "editable": True,
                     "min": meta["min"], "max": meta["max"], "step": meta["step"]})
    return rows


def _clean(levers: dict | None, profile: dict) -> dict:
    """Clamp levers to their bounds; drop unknown keys and categories (so a typo can't silently do nothing)."""
    out, notes = {}, []
    for k, v in (levers or {}).items():
        if k not in LEVERS:
            notes.append(f"ignored unknown setting {k!r}")
            continue
        meta = LEVERS[k]
        if k == "category_cuts_pct":
            cats = profile["extras_categories"]
            good = {c: max(0.0, min(100.0, float(p))) for c, p in (v or {}).items() if c in cats}
            notes += [f"no extras category {c!r} in your data" for c in (v or {}) if c not in cats]
            out[k] = good
        elif k == "one_offs":
            out[k] = [{"month": max(1, int(o["month"])), "amount_eur": float(o["amount_eur"]),
                       "label": str(o.get("label", "one-off"))[:40]} for o in (v or [])]
        else:
            x = float(v)
            cx = max(meta["min"], min(meta["max"], x))
            if cx != x:
                notes.append(f"{meta['label']} limited to {cx:g} {meta['unit']}")
            out[k] = cx
    return {"levers": out, "notes": notes}


# ---------- simulation ----------

def _simulate(profile: dict, lv: dict, draws: list[list[int]]) -> dict:
    m = profile["months"]
    horizon = int(lv.get("horizon_months", DEFAULT_HORIZON))
    sal0 = statistics.median([x["salary"] for x in m])
    fixed0 = statistics.median([x["fixed"] for x in m])
    sal = sal0 * (1 + lv.get("salary_change_pct", 0) / 100)
    keep = lv.get("other_income_kept_pct", 100) / 100
    scale = lv.get("surprise_scale_pct", 100) / 100
    cut_all = lv.get("extras_cut_pct", 0) / 100
    cuts = {c: p / 100 for c, p in lv.get("category_cuts_pct", {}).items()}
    save = lv.get("save_on_payday_eur", 0.0)
    oneoff = {}
    for o in lv.get("one_offs", []):
        oneoff[o["month"]] = oneoff.get(o["month"], 0.0) + o["amount_eur"]
    paths, pots, below = [], [], 0
    for d in draws:
        bal, pot, low, path = profile["balance"], 0.0, profile["balance"], []
        for i in range(horizon):
            h = m[d[i]]
            extras = sum(v * (1 - max(cut_all, cuts.get(c, 0.0))) for c, v in h["extras"].items())
            out = (fixed0 + lv.get("fixed_change_eur", 0.0)) + h["surprise"] * scale + extras
            inc = sal + h["other_income"] * keep
            bal += inc - out + oneoff.get(i + 1, 0.0)
            habit = h.get("moved_out", 0.0)            # what you already move to savings / another bank that month
            bal -= habit
            pot += habit
            moved = min(save, max(bal, 0.0))           # you can't move money you don't have
            bal -= moved
            pot += moved
            low = min(low, bal)
            path.append(bal)
        paths.append(path)
        pots.append(pot)
        below += low < 0
    end = [p[-1] for p in paths]
    total = [p[-1] + q for p, q in zip(paths, pots)]
    band = [{"month": i + 1, "bad": _r(_pct([p[i] for p in paths], 0.1)), "typical": _r(_pct([p[i] for p in paths], 0.5)),
             "good": _r(_pct([p[i] for p in paths], 0.9))} for i in range(horizon)]
    return {"horizon_months": horizon, "account_band": band,
            "account_end": {"bad": _r(_pct(end, 0.1)), "typical": _r(_pct(end, 0.5)), "good": _r(_pct(end, 0.9))},
            "savings_end_typical_eur": _r(statistics.median(pots)),
            "_pots": pots,
            "total_end": {"bad": _r(_pct(total, 0.1)), "typical": _r(_pct(total, 0.5)), "good": _r(_pct(total, 0.9))},
            "chance_below_zero": round(float(below) / len(draws), 3),
            "monthly_income_eur": _r(sal), "_end": end, "_total": total}


def run(profile: dict, levers: dict | None = None, sims: int = SIMS, seed: int = SEED) -> dict:
    """Baseline and scenario on the same random draws of the customer's own months."""
    if len(profile["months"]) < 6:
        return {"status": "too_little_history", "months_seen": len(profile["months"])}
    c = _clean(levers, profile)
    lv = c["levers"]
    horizon = int(lv.get("horizon_months", DEFAULT_HORIZON))
    rng = random.Random(seed)
    n = len(profile["months"])
    draws = [[rng.randrange(n) for _ in range(horizon)] for _ in range(sims)]
    base = _simulate(profile, {"horizon_months": horizon}, draws)
    sc = _simulate(profile, lv, draws)
    diff_total = [s - b for s, b in zip(sc["_total"], base["_total"])]
    diff_pot = [s - b for s, b in zip(sc["_pots"], base["_pots"])]
    for x in (base, sc):
        x.pop("_end"), x.pop("_total"), x.pop("_pots")
    return {"status": "ok", "baseline": base, "scenario": sc,
            "effect_on_total_money": {"typical": _r(statistics.median(diff_total)),
                                      "range": [_r(_pct(diff_total, 0.1)), _r(_pct(diff_total, 0.9))]},
            "effect_on_savings": {"typical": _r(statistics.median(diff_pot))},
            "effect_on_chance_below_zero": round(sc["chance_below_zero"] - base["chance_below_zero"], 3),
            "assumptions": assumptions(profile, lv), "notes": c["notes"],
            "reading": ("Account = money in your account; savings = what the plan moved aside; total = both. "
                        "Bad / typical / good: 1 in 10 futures ends below 'bad', 1 in 10 above 'good'.")}


# ---------- suggestions from the customer's own habits and income ----------

def suggest(profile: dict, safe_to_save_eur: float | None = None, k: int = 4) -> list[dict]:
    """Scenarios worth trying for this person, each with the reason from their data and its effect."""
    m = profile["months"]
    if len(m) < 6:
        return []
    inc = [x["salary"] + x["other_income"] for x in m]
    spend = [x["fixed"] + x["surprise"] + sum(x["extras"].values()) for x in m]
    gap = statistics.median([s - i for s, i in zip(spend, inc)])
    cats = profile["extras_categories"]
    cat_avg = {c: statistics.fmean([x["extras"].get(c, 0.0) for x in m]) for c in cats}
    top = sorted(cat_avg, key=cat_avg.get, reverse=True)
    oth_share = sum(x["other_income"] for x in m) / max(sum(inc), 1)
    surs = [x["surprise"] for x in m]
    cands = []
    if gap > 0 and top:
        pick = top[:3]
        base_ = sum(cat_avg[c] for c in pick)
        need = math.ceil(gap / max(base_, 1) * 100 / 5) * 5
        pct = min(need, 50)
        share = min(100, round(pct / 100 * base_ / gap * 100))
        names = ", ".join(pick[:-1]) + (" and " if len(pick) > 1 else "") + pick[-1]
        title = (f"Close the monthly gap: {names} down {pct} %" if need <= 50 else
                 f"Halve {names}: closes about {share} % of the monthly gap")
        cands.append(({"category_cuts_pct": {c: pct for c in pick}}, "close_gap", title,
                      f"In a typical month about {gap:,.0f} € more goes out than comes in; these are your biggest extras.", 0))
    if top:
        cands.append(({"category_cuts_pct": {top[0]: 20}}, "cut_top",
                      f"Spend 20 % less on {top[0]}", f"{top[0]} is your biggest everyday extra, about {cat_avg[top[0]]:,.0f} € a month.", 2))
    # Safe-to-save counts what you already move out; suggest only the extra, so nobody is told to save twice.
    already = statistics.median([x.get("moved_out", 0.0) for x in m])
    extra = math.floor(max((safe_to_save_eur or 0) - already, 0) / 10) * 10
    if extra >= 20:
        more = " more" if already >= 10 else ""
        cands.append(({"save_on_payday_eur": extra}, "save_on_payday",
                      f"Move {extra:,.0f} €{more} to savings every payday",
                      ("Safe to save says about " + f"{safe_to_save_eur:,.0f} € a month would have fitted in at least 3 of "
                       f"your last 4 pay months" + (f"; you already move about {already:,.0f} €." if already >= 10 else ".")), 1))
    if oth_share >= 0.08:
        cands.append(({"other_income_kept_pct": 0}, "income_stops",
                      "What if your other income stopped?", f"About {oth_share:.0%} of your income is not salary and comes irregularly.", 1))
    big = max(surs) if surs else 0.0
    if big >= 200 and statistics.fmean(surs) > 0 and statistics.pstdev(surs) / statistics.fmean(surs) > 0.8:
        cands.append(({"one_offs": [{"month": 3, "amount_eur": -big, "label": "a month like your biggest surprise"}]},
                      "surprise", f"A {big:,.0f} € surprise in three months",
                      "Your surprise must-pays come in lumps; this repeats your biggest month.", 1))
    housing = statistics.median([x["housing"] for x in m])
    if housing >= 100:
        cands.append(({"fixed_change_eur": round(0.05 * housing, -1)}, "rent_up",
                      "Rent or housing costs rise 5 %", "Housing is your largest fixed cost.", 3))
    out = []
    for lv, key, title, why, prio in cands:
        r = run(profile, lv)
        if r.get("status") != "ok":
            continue
        moves_only = key == "save_on_payday"
        out.append({"key": key, "title": title, "why": why, "levers": lv,
                    "effect_kind": "moved to savings" if moves_only else "change in your total money",
                    "effect_typical_eur": r["effect_on_savings"]["typical"] if moves_only else r["effect_on_total_money"]["typical"],
                    "effect_range_eur": None if moves_only else r["effect_on_total_money"]["range"],
                    "chance_below_zero": {"now": r["baseline"]["chance_below_zero"], "with_this": r["scenario"]["chance_below_zero"]},
                    "horizon_months": r["scenario"]["horizon_months"], "_prio": prio})
    # Most relevant first: priority from the person's situation, then size of effect.
    out.sort(key=lambda x: (x["_prio"], -abs(x["effect_typical_eur"] or 0)))
    for x in out:
        x.pop("_prio")
    return out[:k]


# ---------- data (app only) ----------

def profile_from_data(cid: str, months: int = 12) -> dict:
    """Last `months` full months of the customer's own data, in the shape run()/suggest() need."""
    from . import money
    from .money import TODAY, _month_start, _q as q

    s, e = _month_start(TODAY, months), _month_start(TODAY)
    rows = q("""SELECT strftime(tx_date, '%Y-%m') m,
                  sum(amount) FILTER (WHERE category = 'Salary') salary,
                  sum(amount) FILTER (WHERE kind = 'income' AND category <> 'Salary') other_income,
                  -sum(amount) FILTER (WHERE basket = 1) fixed,
                  -sum(amount) FILTER (WHERE basket = 1 AND category = 'Housing') housing,
                  -sum(amount) FILTER (WHERE basket = 2 OR one_off) surprise,
                  -sum(amount) FILTER (WHERE category IN ('Salary Sweep', 'Invest Deposit', 'Invest Withdraw')) moved_out
                FROM tx WHERE customer_id = ? AND tx_date >= ? AND tx_date < ? GROUP BY 1 ORDER BY 1""", [cid, s, e])
    ext = q("""SELECT strftime(tx_date, '%Y-%m') m, category c, -sum(amount) t FROM tx
               WHERE customer_id = ? AND basket = 3 AND NOT one_off AND tx_date >= ? AND tx_date < ? GROUP BY 1, 2""", [cid, s, e])
    by = {}
    for r in ext:
        by.setdefault(r["m"], {})[r["c"]] = float(r["t"] or 0.0)
    mo = [{"month": r["m"], "salary": float(r["salary"] or 0), "other_income": float(r["other_income"] or 0),
           "fixed": float(r["fixed"] or 0), "housing": float(r["housing"] or 0), "surprise": float(r["surprise"] or 0),
           "moved_out": float(r["moved_out"] or 0), "extras": by.get(r["m"], {})} for r in rows]
    cats = sorted({c for x in mo for c in x["extras"]})
    for x in mo:
        for c in cats:
            x["extras"].setdefault(c, 0.0)
    c = money.customer(cid)
    return {"customer_id": cid, "balance": float(c["balance"]), "months": mo, "extras_categories": cats, "as_of": TODAY.isoformat()}


def plan(cid: str, levers: dict | None = None) -> dict:
    """API/coach entry: starting point, suggested scenarios, and the run for the given levers (or the baseline)."""
    from . import saving

    p = profile_from_data(cid)
    sts = saving.get_safe_to_save(cid)
    out = run(p, levers)
    out["suggestions"] = suggest(p, sts.get("safe_to_save_on_payday_eur") or None)
    out["as_of"] = p["as_of"]
    return out
