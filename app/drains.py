"""Monthly drains: what leaves the account every month without a decision.

Three kinds, from the customer's last 12 months:
- bills: rent and utility payments (they recur by definition), with how much they grew vs a year ago;
- subscriptions: a merchant charging a steady amount in most months (the synthetic data has none; real S-Bank data
  would find streaming, gyms, apps here);
- habits that work like a subscription: everyday extras (basket 3) present in nearly every month, e.g. restaurants
  12 of 12 months. Nobody signed up for them, but they drain like one.
Every number is computed here; the coach and the UI only show and explain it.
"""
from __future__ import annotations

import statistics
from datetime import timedelta

from .money import TODAY, _month_start, _q, _r

BILL_TYPES = {"housing_payment": "Housing", "utilities_payment": "Utilities"}
HABIT_MIN_MONTHS = 6      # present in at least half of the last 12 months
# Habits people recognise group several merchant types ("eating out" = restaurants, cafes, bars…)
FAMILIES = {"Restaurants": "eating_out", "Fast food & cafes": "eating_out", "Bars & pubs": "eating_out",
            "Other restaurants": "eating_out", "Kiosks & convenience stores": "kiosks", "Taxis": "taxis_parking",
            "Parking": "taxis_parking"}
HABIT_MIN_EUR_MONTH = 10


def _hourly(cid: str) -> float | None:
    sal = [r["a"] for r in _q("SELECT amount a FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date > ?",
                              [cid, TODAY - timedelta(days=365)])]
    return statistics.median(sal) / 160 if sal else None


def drains(cid: str) -> dict:
    start = _month_start(TODAY, 11)
    hour = _hourly(cid)
    hours = (lambda eur: round(eur / hour, 1) if hour else None)
    out = {"period": {"start": start.isoformat(), "end": TODAY.isoformat(), "months": 12}, "bills": [], "subscriptions": [], "habits": []}

    for tt, name in BILL_TYPES.items():
        r = _q("""SELECT count(DISTINCT strftime(tx_date, '%Y-%m')) m, count(*) n, -sum(amount) t FROM tx
                  WHERE customer_id = ? AND transaction_type = ? AND tx_date >= ?""", [cid, tt, start])[0]
        if r["m"]:
            out["bills"].append({"bill": name, "months_present": r["m"], "payments": r["n"], "eur_month": _r(r["t"] / 12),
                                 "eur_year": _r(r["t"])})

    # A merchant charging a steady amount in most months (coefficient of variation under 15 %)
    for r in _q("""WITH m AS (SELECT merchant_id, any_value(sub) sub, strftime(tx_date, '%Y-%m') mo, -sum(amount) a FROM tx
                              WHERE customer_id = ? AND tx_date >= ? AND kind = 'spend' AND merchant_id IS NOT NULL GROUP BY 1, 3)
                   SELECT merchant_id, any_value(sub) sub, count(*) m, avg(a) avg_a, stddev_samp(a) sd FROM m GROUP BY 1
                   HAVING count(*) >= 6""", [cid, start]):
        if r["avg_a"] and (r["sd"] or 0) / r["avg_a"] < 0.15:
            out["subscriptions"].append({"merchant_type": r["sub"], "merchant": r["merchant_id"], "months_present": r["m"],
                                         "eur_month": _r(r["avg_a"]), "eur_year": _r(r["avg_a"] * 12), "hours_of_work_month": hours(r["avg_a"])})

    fam = {}
    for r in _q("""SELECT sub, strftime(tx_date, '%Y-%m') mo, count(*) n, -sum(amount) t FROM tx
                   WHERE customer_id = ? AND tx_date >= ? AND basket = 3 GROUP BY 1, 2""", [cid, start]):
        key = FAMILIES.get(r["sub"], r["sub"])
        f = fam.setdefault(key, {"months": set(), "n": 0, "t": 0.0, "subs": set()})
        f["months"].add(r["mo"]); f["n"] += r["n"]; f["t"] += r["t"]; f["subs"].add(r["sub"])
    for key, f in sorted(fam.items(), key=lambda kv: -kv[1]["t"]):
        if len(f["months"]) >= HABIT_MIN_MONTHS and f["t"] / 12 >= HABIT_MIN_EUR_MONTH:
            subs = sorted(f["subs"])
            out["habits"].append({"habit": key, "merchant_types": subs, "months_present": len(f["months"]),
                                  "times_month": round(f["n"] / 12, 1), "eur_month": _r(f["t"] / 12), "eur_year": _r(f["t"]),
                                  "hours_of_work_month": hours(f["t"] / 12)})
    out["habits"] = out["habits"][:5]

    tot = lambda xs: _r(sum(x["eur_month"] for x in xs))
    out["totals_eur_month"] = {"bills": tot(out["bills"]), "subscriptions": tot(out["subscriptions"]), "habits": tot(out["habits"])}
    out["drain_eur_month"] = _r(out["totals_eur_month"]["subscriptions"] + out["totals_eur_month"]["habits"])
    out["drain_eur_year"] = _r(out["drain_eur_month"] * 12)
    out["drain_hours_of_work_month"] = hours(out["drain_eur_month"])
    out["note"] = ("Habits are everyday extras present in at least 6 of the last 12 months: nobody signed up for them, but "
                   "they leave the account like a subscription. Bills are listed separately; they are must-pays.")
    return out
