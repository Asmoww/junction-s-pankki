"""Charts and dated events for the coach. Code computes every point; the model only picks the chart and
explains the returned summary.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import future, insights, money
from .money import TODAY, _month_start, _q, _r

KINDS = ["monthly_spend", "category_trend", "income_vs_spend", "month_runway"]


def _months(n: int) -> list[str]:
    return [_month_start(TODAY, i).strftime("%Y-%m") for i in range(n - 1, -1, -1)]


def _trend(vals: list[float]) -> float | None:
    """Least-squares slope in € per month over the given months."""
    n = len(vals)
    if n < 3:
        return None
    mx, my = (n - 1) / 2, sum(vals) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return _r(sum((i - mx) * (v - my) for i, v in enumerate(vals)) / den)


def show_chart(cid: str, kind: str, months: int = 12, category: str | None = None, subcategory: str | None = None,
               basket: int | None = None) -> dict:
    if kind not in KINDS:
        raise money.ToolError(f"kind must be one of {KINDS}")
    months = max(3, min(int(months or 12), 24))
    ms = _months(months)
    start = _month_start(TODAY, months - 1)
    if kind == "month_runway":
        r = insights.ribbon(cid)
        return {"kind": kind, "title": "Balance this pay month and the forecast to payday",
                "period": {"start": r["last_payday"], "end": r["next_payday"], "today": TODAY.isoformat()},
                "past": [{"x": p["date"], "v": p["balance_eur"]} for p in r["past"]],
                "future": [{"x": p["date"], "v": p["balance_eur"]} for p in r["future"]],
                "balance_now_eur": r["past"][-1]["balance_eur"], "balance_at_payday_eur": r["balance_at_payday_eur"],
                "goes_below_zero_on": r["runs_out_around"]}
    if kind == "category_trend" and not (category or subcategory or basket):
        raise money.ToolError("category_trend needs a category, subcategory or basket")
    where, params = money._filters(category, subcategory, basket)
    spend = {r["m"]: float(r["t"]) for r in _q(
        f"SELECT strftime(tx_date, '%Y-%m') m, -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date >= ? AND {where} GROUP BY 1",
        [cid, start] + params)}
    rows = _q(f"SELECT count(*) n FROM tx WHERE customer_id = ? AND tx_date >= ? AND {where}", [cid, start] + params)[0]["n"]
    sv = [_r(spend.get(m, 0)) for m in ms]
    series = [{"label": "Spending", "points": [{"x": m, "v": v} for m, v in zip(ms, sv)]}]
    out = {"kind": kind, "period": {"start": start.isoformat(), "end": TODAY.isoformat(), "months": months},
           "filter": {"category": category, "subcategory": subcategory, "basket": basket}, "rows_used": rows}
    if kind == "income_vs_spend":
        inc = {r["m"]: float(r["t"]) for r in _q(
            "SELECT strftime(tx_date, '%Y-%m') m, sum(amount) t FROM tx WHERE customer_id = ? AND tx_date >= ? AND kind = 'income' GROUP BY 1",
            [cid, start])}
        iv = [_r(inc.get(m, 0)) for m in ms]
        series.insert(0, {"label": "Income", "points": [{"x": m, "v": v} for m, v in zip(ms, iv)]})
        out["income_total_eur"], out["spending_total_eur"] = _r(sum(iv)), _r(sum(sv))
        out["income_minus_spending_eur"] = _r(sum(iv) - sum(sv))
    hi = max(range(len(sv)), key=lambda i: sv[i])
    lo = min(range(len(sv)), key=lambda i: sv[i])
    out.update({"title": {"monthly_spend": "Spending per month", "category_trend": f"{subcategory or category or f'Basket {basket}'} per month",
                          "income_vs_spend": "Income and spending per month"}[kind],
                "series": series, "spending_trend_eur_per_month": _trend(sv), "total_eur": _r(sum(sv)),
                "highest_month": {"month": ms[hi], "eur": sv[hi]}, "lowest_month": {"month": ms[lo], "eur": sv[lo]},
                "average_per_month_eur": _r(sum(sv) / len(sv))})
    return out


def forecast_with_events(cid: str, events: list[dict], pause_extras: bool = False) -> dict:
    """Costs or income the user tells us about, placed on their own dates. One model gives both figures: the week is its
    share of the until-payday money (income included); a cost after the next 7 days lowers safe-until-payday only."""
    sts = money.get_safe_to_spend(cid)
    payday = date.fromisoformat(sts["next_payday"]) if sts["next_payday"] else TODAY + timedelta(days=30)
    week_end = TODAY + timedelta(days=7)
    clean, sc = [], {"one_offs": [], "income": [], "pause_extras": bool(pause_extras)}
    for e in events[:10]:
        try:
            d = date.fromisoformat(str(e["date"]))
            amt = abs(float(e["amount"]))
        except (KeyError, ValueError, TypeError):
            raise money.ToolError("each event needs label, amount and an ISO date")
        if d <= TODAY:
            raise money.ToolError("event dates must be after today (2026-09-30)")
        kind = "income" if e.get("kind") == "income" else "spend"
        (sc["income"] if kind == "income" else sc["one_offs"]).append({"label": str(e.get("label", ""))[:40], "amount": amt, "date": d.isoformat()})
        clean.append({"label": str(e.get("label", ""))[:40], "amount_eur": _r(amt), "date": d.isoformat(), "kind": kind,
                      "in_next_7_days": d <= week_end, "before_payday": d <= payday})
    spend_before = sum(e["amount_eur"] for e in clean if e["kind"] == "spend" and e["before_payday"])
    inc_before = sum(e["amount_eur"] for e in clean if e["kind"] == "income" and e["before_payday"])
    spend_week = sum(e["amount_eur"] for e in clean if e["kind"] == "spend" and e["in_next_7_days"])
    until_after = sts["safe_until_payday_eur"] - spend_before + inc_before
    # Same rule as get_safe_to_spend: the week gets its share of the money that must last until payday. Income
    # joins that money (an extra 5,000 € raises the week too); costs inside the week count in full; costs after it
    # only cap the figure.
    days = sts["days_until_payday"] or 30
    pool = sts["safe_until_payday_eur"] + inc_before
    share = max(pool, 0) / days * min(7, days) if inc_before else sts["safe_this_week_eur"]
    week_after = max(0.0, min(share - spend_week, until_after))
    f = future.future(cid, sc)
    return {"events": clean, "next_payday": sts["next_payday"],
            "safe_until_payday_before_eur": sts["safe_until_payday_eur"], "safe_until_payday_after_eur": _r(until_after),
            "safe_this_week_before_eur": sts["safe_this_week_eur"], "safe_this_week_after_eur": _r(week_after),
            "costs_in_next_7_days_eur": _r(spend_week),
            "balance_at_payday_before_eur": f["base"]["end_eur"], "balance_at_payday_after_eur": f["scenario"]["end_eur"],
            "goes_below_zero_on_after": f["scenario"]["runs_out"],
            "rule": ("This week's figure is its share of what must last until payday. Income before payday raises both "
                     "figures; costs in the next 7 days count fully this week; later costs lower safe-until-payday only."),
            "_future": f}
