"""Insights built on the money tools: surprise pot, payday pattern, payday forecast, spender type, benchmarks,
basket game, full-picture (PSD2) signal and the home-screen cards. Deterministic; the coach only explains them.
"""
from __future__ import annotations

import json
import random
from datetime import timedelta
from pathlib import Path

from . import money
from .money import TODAY, _month_start, _period_info, _q, _r
from .taxonomy import BASKETS

BENCH = json.loads((Path(__file__).resolve().parent / "bench_statfin.json").read_text())
# Our categories -> Statistics Finland COICOP groups that measure roughly the same thing.
BENCH_MAP = [
    ("Groceries", "category = 'Groceries'", "01"),
    ("Restaurants & cafes", "category = 'Restaurants'", "111"),
    ("Transport", "category = 'Transportation'", "07"),
    ("Recreation & culture", "category = 'Entertainment'", "09"),
    ("Health", "category = 'Health'", "06"),
    ("Clothing", "sub IN ('Clothing', 'Fashion')", "03"),
]


def surprise_pot(cid: str) -> dict:
    """Basket 2 month by month over the whole history, and what a fixed monthly pot would have done."""
    rows = _q("""SELECT strftime(tx_date, '%Y-%m') m, -sum(amount) FILTER (WHERE basket = 2) t FROM tx
                 WHERE customer_id = ? GROUP BY 1 ORDER BY 1""", [cid])
    months = [{"month": r["m"], "eur": _r(r["t"])} for r in rows]
    vals = [m["eur"] for m in months] or [0]
    last12 = vals[-12:]
    pot = _r(sum(last12) / len(last12))
    balance, low = 0.0, 0.0
    for v in vals[-12:]:
        balance += pot - v
        low = min(low, balance)
    nonzero = sum(1 for v in vals if v > 0)
    return {"based_on": _period_info(_month_start(TODAY, len(vals) - 1), TODAY),
            "months": months,
            "average_per_month_last_12_eur": pot, "total_last_12_eur": _r(sum(last12)),
            "months_with_surprises": nonzero, "months_total": len(vals),
            "smallest_month_eur": _r(min(vals)), "biggest_month_eur": _r(max(vals)),
            "suggested_monthly_pot_eur": pot,
            "pot_low_point_last_12_eur": _r(low),
            "lesson": ("Surprise costs are irregular month to month but steady over a year. Setting aside the yearly "
                       "average every month turns them into a planned cost.")}


def payday_pattern(cid: str, months: int = 6) -> dict:
    """Extras per day in the week after payday vs the week before, and weekend vs weekday."""
    s = _month_start(TODAY, months - 1)
    r = _q("""WITH p AS (SELECT tx_date sd FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date >= ?),
              x AS (SELECT t.amount, t.tx_date - p.sd dd FROM tx t JOIN p ON t.tx_date BETWEEN p.sd - 7 AND p.sd + 6
                    WHERE t.customer_id = ? AND t.basket = 3)
              SELECT -sum(amount) FILTER (WHERE dd >= 0) / 7 / (SELECT count(*) FROM p) after_day,
                     -sum(amount) FILTER (WHERE dd < 0) / 7 / (SELECT count(*) FROM p) before_day,
                     (SELECT count(*) FROM p) paydays FROM x""", [cid, s, cid])[0]
    w = _q("""SELECT -sum(amount) FILTER (WHERE dayofweek(tx_date) IN (0, 6)) we,
                     -sum(amount) FILTER (WHERE dayofweek(tx_date) NOT IN (0, 6)) wd,
                     count(DISTINCT tx_date) FILTER (WHERE dayofweek(tx_date) IN (0, 6)) dummy
              FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND basket = 3""", [cid, s, TODAY])[0]
    days = (TODAY - s).days + 1
    weekend_days = sum(1 for i in range(days) if (s + timedelta(days=i)).weekday() >= 5)
    after, before = float(r["after_day"] or 0), float(r["before_day"] or 0)
    we = float(w["we"] or 0) / max(weekend_days, 1)
    wd = float(w["wd"] or 0) / max(days - weekend_days, 1)
    return {"based_on": _period_info(s, TODAY), "paydays": r["paydays"],
            "extras_per_day_week_after_payday_eur": _r(after), "extras_per_day_week_before_payday_eur": _r(before),
            "payday_week_change_percent": round((after / before - 1) * 100) if before else None,
            "extras_per_weekend_day_eur": _r(we), "extras_per_weekday_eur": _r(wd),
            "weekend_change_percent": round((we / wd - 1) * 100) if wd else None,
            "dataset_typical": "Across all customers: +30 % in the week after payday, weekend days +45 %."}


def payday_forecast(cid: str) -> dict:
    """Balance at next payday if the usual pace continues (bills + essentials + surprises + usual extras)."""
    sts = money.get_safe_to_spend(cid)
    days = sts["days_until_payday"]
    usual_extras = sts["your_usual_extras_per_week_eur"] / 7 * days
    bal = money.customer(cid)["balance"]
    planned = -sum(s["eur"] for s in sts["steps"][2:])  # bills, essentials, surprise buffer
    end = bal - planned - usual_extras
    short_day = None
    if end < 0:
        per_day = (planned + usual_extras) / days
        short_day = (TODAY + timedelta(days=int(bal // per_day) + 1)).isoformat() if per_day > 0 else None
    return {"as_of": TODAY.isoformat(), "next_payday": sts["next_payday"], "days_until_payday": days,
            "balance_now_eur": _r(bal), "expected_costs_until_payday_eur": _r(planned),
            "short_at_usual_pace_eur": _r(max(-end, 0)),
            "short_even_with_no_extras_eur": _r(max(-(bal - planned), 0)),
            "usual_extras_until_payday_eur": _r(usual_extras), "balance_at_payday_at_usual_pace_eur": _r(end),
            "runs_out_around": short_day,
            "note": "Assumes bills, essentials and extras continue at your usual 90-day pace."}


def benchmark(cid: str) -> dict:
    """Monthly spending per area vs Statistics Finland 2022 for the same age group."""
    age = money.customer(cid)["age"]
    band = next((b for b in ["17-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84"]
                 if int(b[:2]) <= age <= int(b[3:])), "85-")
    s = _month_start(TODAY, 5)
    out = []
    for label, cond, code in BENCH_MAP:
        mine = _q(f"SELECT -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND kind = 'spend' "
                  f"AND NOT one_off AND {cond}", [cid, s, TODAY])[0]["t"] or 0
        out.append({"area": label, "you_per_month_eur": _r(mine / 6),
                    "finland_same_age_per_month_eur": BENCH["by_age"][band][code],
                    "finland_group": BENCH["groups"][code]})
    return {"based_on": _period_info(s, TODAY), "age_group": band, "areas": out, "source": BENCH["source"],
            "caveats": ["National figures are 2022, per consumption unit (adult-equivalent), all payment methods.",
                        "This account may not hold all your spending; the bank data is synthetic.",
                        "Use as a reference point, not a target."]}


def spender_type(cid: str) -> dict:
    """A friendly archetype from measured signals. Never a judgement; every signal is shown."""
    prof = money.get_spender_profile(cid)
    pp = payday_pattern(cid)
    cf = money.get_cashflow(cid, "last_6_months")
    inc = max(cf["income_eur"]["total"], 1)
    moved_away = cf["moved_to_own_savings_or_investments_eur"]["salary_sweep_to_other_account"] / inc
    saving = (cf["income_eur"]["total"] - cf["spending_eur"]["total"]) / inc  # share of income not spent
    x3 = prof["you"]["extras_share_of_spending"]
    peer = prof["peers_same_age_group"]["median_extras_share"]
    signals = {"extras_share": x3, "peer_extras_share": peer, "payday_week_change_percent": pp["payday_week_change_percent"],
               "weekend_change_percent": pp["weekend_change_percent"],
               "transactions_while_overdrawn": prof["habits"]["transactions_while_overdrawn"],
               "share_of_income_not_spent": round(saving, 2),
               "share_of_income_moved_to_other_bank": round(moved_away, 2),
               "spending_vs_income": prof["you"]["spending_vs_income"]}
    if moved_away >= 0.5:
        t = ("Money mover", "Most of your income moves on right after payday. This account sees only a slice of your life.")
    elif signals["transactions_while_overdrawn"] >= 5 and prof["you"]["spending_vs_income"] > 1:
        t = ("Tight-rope walker", "Your spending runs a bit above your income, and the account dips below zero now and then.")
    elif saving >= 0.2:
        t = ("Quiet saver", "A good part of your income stays unspent every month, and everyday extras are modest.")
    elif (pp["payday_week_change_percent"] or 0) >= 40:
        t = ("Payday celebrator", "Extras jump right after payday and slow down as the month goes on.")
    elif (pp["weekend_change_percent"] or 0) >= 60:
        t = ("Weekend spender", "Your extras cluster on weekends.")
    elif x3 > peer + 0.05:
        t = ("Experience seeker", "A bigger share of your money goes to extras than for people your age.")
    else:
        t = ("Steady planner", "Your spending is balanced and close to people your age.")
    return {"type": t[0], "summary": t[1], "signals": signals, "based_on": prof["based_on"],
            "note": "A playful label from your own numbers. Everyone's type changes over time."}


def full_picture(cid: str) -> dict:
    """PSD2 signal: how much of the salary leaves for an account in another bank."""
    cf = money.get_cashflow(cid, "last_month")
    out = cf["moved_to_own_savings_or_investments_eur"]["salary_sweep_to_other_account"]
    inc = cf["income_eur"]["total"]
    return {"period": cf["period"], "salary_eur": cf["income_eur"]["salary"], "moved_to_other_bank_eur": out,
            "share_of_income": round(out / inc, 2) if inc else 0, "spent_from_this_account_eur": cf["spending_eur"]["total"],
            "visible": out < 0.3 * inc if inc else True}


def basket_game(cid: str, n: int = 6, seed: int | None = None) -> dict:
    """n recent transactions, at least one per basket, for the 'sort into baskets' game."""
    rows = _q("""SELECT ts, category, sub, -amount amount, basket, one_off FROM tx WHERE customer_id = ?
                 AND tx_date >= ? AND basket IS NOT NULL""", [cid, _month_start(TODAY, 2)])
    rnd = random.Random(seed)
    pick = []
    for b in (1, 2, 3):
        pool = [r for r in rows if r["basket"] == b]
        if pool:
            pick.append(rnd.choice(pool))
    rest = [r for r in rows if r not in pick]
    pick += rnd.sample(rest, min(n - len(pick), len(rest)))
    rnd.shuffle(pick)
    why = {1: "It comes back every month and you can't really skip it.",
           2: "You can't skip it, but you can't predict the month it hits.",
           3: "A choice: nice to have, and easy to adjust."}
    items = []
    for r in pick:
        reason = why[r["basket"]]
        if r["one_off"]:
            reason = "A big one-off purchase: rare, hard to plan for month by month."
        elif r["category"] == "Groceries" and r["basket"] == 3:
            reason = "Kiosk and convenience shopping is usually a top-up choice, not the weekly groceries."
        items.append({"date": r["ts"].strftime("%Y-%m-%d"), "merchant_type": r["sub"], "category": r["category"],
                      "amount_eur": _r(r["amount"]), "basket": r["basket"], "basket_name": BASKETS[r["basket"]]["name"],
                      "why": reason})
    return {"items": items}


def cards(cid: str) -> list[dict]:
    """Proactive home-screen cards, most urgent first. Text is templated from the numbers above."""
    out = []
    fc = payday_forecast(cid)
    if fc["balance_at_payday_at_usual_pace_eur"] < 0:
        out.append({"kind": "warning", "id": "forecast",
                    "title": "Heads up before payday",
                    "body": f"At your usual pace you'll be about {abs(fc['balance_at_payday_at_usual_pace_eur']):,.0f} € "
                            f"short before payday on {fc['next_payday']}.",
                    "numbers": fc, "ask": "How can I get to payday without going overdrawn?"})
    fp = full_picture(cid)
    if not fp["visible"]:
        out.append({"kind": "psd2", "id": "psd2", "title": "You see only part of your money here",
                    "body": f"{fp['moved_to_other_bank_eur']:,.0f} € of your {fp['salary_eur']:,.0f} € salary moved to "
                            f"another bank last month. Connect it to get advice on the full picture.",
                    "numbers": fp, "ask": None})
    pp = payday_pattern(cid)
    if (pp["payday_week_change_percent"] or 0) >= 20:
        out.append({"kind": "insight", "id": "payday",
                    "title": "Payday week effect",
                    "body": f"In the week after payday you spend {pp['payday_week_change_percent']} % more per day on "
                            f"extras than in the week before (last 6 months).",
                    "numbers": pp, "ask": "Why do I spend more after payday, and what can I do about it?"})
    pot = surprise_pot(cid)
    if pot["average_per_month_last_12_eur"] >= 50:
        out.append({"kind": "pot", "id": "pot", "title": "Your surprises aren't surprises",
                    "body": f"Surprise costs ranged from {pot['smallest_month_eur']:,.0f} € to "
                            f"{pot['biggest_month_eur']:,.0f} € a month, but averaged "
                            f"{pot['average_per_month_last_12_eur']:,.0f} € over the last 12 months.",
                    "numbers": pot, "ask": "How would a surprise pot work for me?"})
    return out
