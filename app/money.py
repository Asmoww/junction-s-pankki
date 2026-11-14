"""Money tools: deterministic queries over data/tx.parquet. Every number the coach or the UI shows comes from here.

All functions take a customer_id and return plain JSON-able dicts with amounts in EUR (spending as positive numbers)
and the exact period used, so answers can always say what they are based on.
"""
from __future__ import annotations

import calendar
import statistics
import threading
from datetime import date, timedelta
from pathlib import Path

import duckdb

from .taxonomy import BASKETS, MCC_LABELS, NO_MCC_SUB, SPEND_CATEGORIES

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TODAY = date(2026, 9, 30)  # the dataset ends here; the demo lives on this day

SUBCATEGORIES = sorted(set(MCC_LABELS.values()) | set(NO_MCC_SUB.values())
                       | {f"Other {c.lower()}" for c in SPEND_CATEGORIES if c not in NO_MCC_SUB})
PERIODS = ["this_month", "last_month", "last_3_months", "last_6_months", "last_12_months", "this_year", "last_year",
           "all"]

_lock = threading.Lock()
_con = duckdb.connect()
_con.execute("SET memory_limit='300MB'; SET threads=2")
# The customer's own basket answers ("this was a broken washing machine, not a want") override the data's basket,
# either for one transaction (seq) or for every transaction of a merchant type (sub). Every tool reads tx, so the
# answers flow into baskets, safe-to-spend, forecasts and the coach.
_con.execute("CREATE TABLE ov_tx (customer_id VARCHAR, seq BIGINT, basket INTEGER, PRIMARY KEY (customer_id, seq))")
_con.execute("CREATE TABLE ov_sub (customer_id VARCHAR, sub VARCHAR, basket INTEGER, PRIMARY KEY (customer_id, sub))")
# Scalar subqueries, not LEFT JOINs: with joins in this view DuckDB 2.0.0 ignored LIMIT in queries on tx.
_con.execute(f"""CREATE VIEW tx AS SELECT p.* REPLACE (CASE WHEN p.basket IS NULL THEN NULL ELSE coalesce(
                    (SELECT o.basket FROM ov_tx o WHERE o.customer_id = p.customer_id AND o.seq = p.seq),
                    (SELECT o.basket FROM ov_sub o WHERE o.customer_id = p.customer_id AND o.sub = p.sub),
                    p.basket) END AS basket),
                    p.basket AS data_basket
             FROM '{DATA / 'tx.parquet'}' p""")
_con.execute(f"CREATE TABLE cust AS SELECT * FROM '{DATA / 'customers.parquet'}'")
# Per customer and month: spending per basket (one-offs kept separate) and income. Used for peers and baselines.
CM_SQL = """
SELECT customer_id, date_trunc('month', tx_date)::DATE AS month,
       -sum(amount) FILTER (WHERE basket = 1) AS b1,
       -sum(amount) FILTER (WHERE basket = 2 AND NOT one_off) AS b2,
       -sum(amount) FILTER (WHERE basket = 3) AS b3,
       -sum(amount) FILTER (WHERE one_off) AS oneoff,
       sum(amount) FILTER (WHERE kind = 'income') AS income
FROM tx {where} GROUP BY ALL
"""
_con.execute("CREATE TABLE cm AS " + CM_SQL.format(where=""))


def set_basket_answers(cid: str, tx: dict[int, int], subs: dict[str, int]) -> None:
    """Replace one customer's basket answers and refresh their monthly rows. Empty dicts = back to the data's baskets."""
    with _lock:
        c = _con.cursor()
        c.execute("DELETE FROM ov_tx WHERE customer_id = ?", [cid])
        c.execute("DELETE FROM ov_sub WHERE customer_id = ?", [cid])
        for seq, b in tx.items():
            c.execute("INSERT INTO ov_tx VALUES (?, ?, ?)", [cid, int(seq), int(b)])
        for sub, b in subs.items():
            c.execute("INSERT INTO ov_sub VALUES (?, ?, ?)", [cid, sub, int(b)])
        c.execute("DELETE FROM cm WHERE customer_id = ?", [cid])
        c.execute("INSERT INTO cm " + CM_SQL.format(where="WHERE customer_id = ?"), [cid])


class ToolError(ValueError):
    """Bad tool input; the message is shown to the model so it can correct itself."""


def _q(sql: str, params: list | None = None) -> list[dict]:
    with _lock:
        cur = _con.cursor()
        res = cur.execute(sql, params or [])
        cols = [d[0] for d in res.description]
        return [dict(zip(cols, row)) for row in res.fetchall()]


def _r(x) -> float:
    return round(float(x or 0), 2)


def _month_start(d: date, back: int = 0) -> date:
    y, m = d.year, d.month - back
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, 1)


def resolve_period(period: str | None = None, start: str | None = None, end: str | None = None) -> tuple[date, date]:
    """Inclusive date range. Custom start/end win over a named period."""
    if start or end:
        try:
            s = date.fromisoformat(start) if start else date(2024, 10, 1)
            e = date.fromisoformat(end) if end else TODAY
        except ValueError as ex:
            raise ToolError(f"Dates must be YYYY-MM-DD: {ex}")
        if s > e:
            raise ToolError("start is after end")
        return s, min(e, TODAY)
    p = period or "last_3_months"
    this = _month_start(TODAY)
    ranges = {
        "this_month": (this, TODAY),
        "last_month": (_month_start(TODAY, 1), this - timedelta(days=1)),
        "last_3_months": (_month_start(TODAY, 2), TODAY),
        "last_6_months": (_month_start(TODAY, 5), TODAY),
        "last_12_months": (_month_start(TODAY, 11), TODAY),
        "this_year": (date(TODAY.year, 1, 1), TODAY),
        "last_year": (date(TODAY.year - 1, 1, 1), date(TODAY.year - 1, 12, 31)),
        "all": (date(2024, 10, 1), TODAY),
    }
    if p not in ranges:
        raise ToolError(f"Unknown period {p!r}. Use one of {PERIODS} or start/end dates.")
    return ranges[p]


DATA_START = date(2024, 10, 1)


def _months_between(s: date, e: date) -> int:
    return max((e.year - s.year) * 12 + e.month - s.month + 1, 0)


def _period_info(s: date, e: date) -> dict:
    """months = calendar months asked for; months_with_data = those inside the data (2024-10 .. today).
    Averages divide by months_with_data, never by months the data doesn't cover (outside test 14 Nov:
    Jan-Dec 2024 divided Oct-Dec spending by 12)."""
    months = _months_between(s, e)
    covered = _months_between(max(s, DATA_START), min(e, TODAY)) if e >= DATA_START else 0
    info = {"start": s.isoformat(), "end": e.isoformat(), "months": months, "months_with_data": covered,
            "data_covers": "2024-10-01 to 2026-09-30", "today": TODAY.isoformat()}
    if covered < months:
        info["coverage_note"] = (f"Only {covered} of the {months} months asked for are in the data (it starts "
                                 f"2024-10-01). Months before that are unavailable, not zero; averages use the "
                                 f"{covered} covered months.")
    return info


def _per_month(total: float | None, info: dict) -> float | None:
    return _r((total or 0) / info["months_with_data"]) if info["months_with_data"] else None


def _filters(category=None, subcategory=None, basket=None) -> tuple[str, list]:
    where, params = ["kind = 'spend'"], []
    if category:
        if category not in SPEND_CATEGORIES:
            raise ToolError(f"Unknown category {category!r}. Use one of {SPEND_CATEGORIES}.")
        where.append("category = ?"), params.append(category)
    if subcategory:
        if subcategory not in SUBCATEGORIES:
            raise ToolError(f"Unknown subcategory {subcategory!r}. Use one of {SUBCATEGORIES}.")
        where.append("sub = ?"), params.append(subcategory)
    if basket:
        if basket not in BASKETS:
            raise ToolError("basket must be 1, 2 or 3")
        where.append("basket = ?"), params.append(basket)
    return " AND ".join(where), params


def customer(cid: str) -> dict:
    rows = _q("SELECT customer_id, age, postal_code FROM cust WHERE customer_id = ?", [cid])
    if not rows:
        raise ToolError(f"Unknown customer {cid}")
    bal = _q("SELECT balance FROM tx WHERE customer_id = ? ORDER BY seq DESC LIMIT 1", [cid])
    return {**rows[0], "balance": _r(bal[0]["balance"]) if bal else 0.0, "as_of": TODAY.isoformat()}


def get_spending(cid: str, period: str | None = None, start: str | None = None, end: str | None = None,
                 category: str | None = None, subcategory: str | None = None, basket: int | None = None,
                 group_by: str = "none") -> dict:
    """Money out (spending only, transfers to own savings excluded) for a period, optionally filtered and grouped."""
    s, e = resolve_period(period, start, end)
    where, params = _filters(category, subcategory, basket)
    base = [cid, s, e] + params
    tot = _q(f"SELECT -sum(amount) total, count(*) n, count(*) FILTER (WHERE one_off) n_oneoff, "
             f"-sum(amount) FILTER (WHERE one_off) oneoff_total "
             f"FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND {where}", base)[0]
    out = {"period": _period_info(s, e),
           "filter": {"category": category, "subcategory": subcategory, "basket": basket},
           "total_eur": _r(tot["total"]), "transactions": tot["n"],
           "average_per_month_eur": _per_month(tot["total"], _period_info(s, e)),
           "one_off_large_purchases": {"count": tot["n_oneoff"], "total_eur": _r(tot["oneoff_total"])}}
    if subcategory and subcategory in MCC_LABELS.values():
        # Purchases without a merchant code cannot be split into sub-categories; say how much that is.
        cat = _q("SELECT category FROM tx WHERE sub = ? LIMIT 1", [subcategory])
        if cat:
            unk = _q("SELECT -sum(amount) t, count(*) n FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? "
                     "AND category = ? AND mcc IS NULL AND kind = 'spend'", [cid, s, e, cat[0]["category"]])[0]
            if unk["n"]:
                out["not_classifiable"] = {
                    "note": f"{unk['n']} {cat[0]['category']} purchases ({_r(unk['t'])} EUR) have no merchant type, "
                            f"so some {subcategory} may be among them.",
                    "count": unk["n"], "total_eur": _r(unk["t"])}
    groups = {"category": "category", "subcategory": "sub", "basket": "basket",
              "month": "strftime(tx_date, '%Y-%m')", "weekday": "dayname(tx_date)"}
    if group_by != "none":
        if group_by not in groups:
            raise ToolError(f"group_by must be one of {['none', *groups]}")
        g = groups[group_by]
        order = "1" if group_by == "month" else "total DESC"
        rows = _q(f"SELECT {g} AS key, -sum(amount) total, count(*) n FROM tx WHERE customer_id = ? "
                  f"AND tx_date BETWEEN ? AND ? AND {where} GROUP BY 1 ORDER BY {order} LIMIT 30", base)
        out["breakdown"] = [{"key": (BASKETS[r["key"]]["name"] if group_by == "basket" else str(r["key"])),
                             "total_eur": _r(r["total"]), "transactions": r["n"]} for r in rows]
        if group_by == "month":  # every month in the period with data, 0 where nothing was spent (averages stay right)
            have = {b["key"]: b for b in out["breakdown"]}
            m, last = max(s, DATA_START).replace(day=1), min(e, TODAY)
            months = []
            while m <= last:
                k = m.strftime("%Y-%m")
                months.append(have.get(k, {"key": k, "total_eur": 0.0, "transactions": 0}))
                m = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
            out["breakdown"] = months
    return out


def list_transactions(cid: str, period: str | None = None, start: str | None = None, end: str | None = None,
                      category: str | None = None, subcategory: str | None = None, basket: int | None = None,
                      sort: str = "latest", limit: int = 10) -> dict:
    s, e = resolve_period(period, start, end)
    where, params = _filters(category, subcategory, basket)
    order = {"latest": "seq DESC", "largest": "amount ASC"}.get(sort)
    if not order:
        raise ToolError("sort must be latest or largest")
    limit = max(1, min(int(limit), 25))
    rows = _q(f"SELECT ts, category, sub, -amount amount, basket, one_off FROM tx WHERE customer_id = ? "
              f"AND tx_date BETWEEN ? AND ? AND {where} ORDER BY {order} LIMIT {limit}", [cid, s, e] + params)
    return {"period": _period_info(s, e), "note": "Merchant names are not in the data; merchant type is shown.",
            "transactions": [{"time": r["ts"].strftime("%Y-%m-%d %H:%M"), "category": r["category"],
                              "merchant_type": r["sub"], "amount_eur": _r(r["amount"]),
                              "basket": BASKETS[r["basket"]]["name"], "one_off": r["one_off"]} for r in rows]}


def get_cashflow(cid: str, period: str | None = None, start: str | None = None, end: str | None = None) -> dict:
    """Money in, money out by basket, and transfers to own savings/investments."""
    s, e = resolve_period(period, start, end)
    r = _q("""SELECT sum(amount) FILTER (WHERE category = 'Salary') salary,
                     sum(amount) FILTER (WHERE category = 'Other Income') other_income,
                     -sum(amount) FILTER (WHERE basket = 1) b1, -sum(amount) FILTER (WHERE basket = 2) b2,
                     -sum(amount) FILTER (WHERE basket = 3) b3,
                     -sum(amount) FILTER (WHERE category = 'Salary Sweep') sweep,
                     -sum(amount) FILTER (WHERE category = 'Invest Deposit') invest_in,
                     sum(amount) FILTER (WHERE category = 'Invest Withdraw') invest_out,
                     arg_min(balance - amount, seq) bal_start, arg_max(balance, seq) bal_end
              FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ?""", [cid, s, e])[0]
    income = _r((r["salary"] or 0) + (r["other_income"] or 0))
    spending = _r((r["b1"] or 0) + (r["b2"] or 0) + (r["b3"] or 0))
    out = {"period": _period_info(s, e),
           "income_eur": {"salary": _r(r["salary"]), "other_income": _r(r["other_income"]), "total": income},
           "spending_eur": {BASKETS[i]["name"]: _r(r[f"b{i}"]) for i in (1, 2, 3)} | {"total": spending},
           "moved_to_own_savings_or_investments_eur": {
               "salary_sweep_to_other_account": _r(r["sweep"]), "investment_deposits": _r(r["invest_in"]),
               "investment_withdrawals": _r(r["invest_out"])},
           "income_minus_spending_eur": _r(income - spending),
           "balance_eur": {"start": _r(r["bal_start"]), "end": _r(r["bal_end"]),
                           "change": _r((r["bal_end"] or 0) - (r["bal_start"] or 0))}}
    if r["sweep"]:
        out["note"] = ("Most of the salary is swept to another account right after payday, so most day-to-day "
                       "spending probably happens elsewhere. This account shows only part of the picture.")
    return out


def get_three_baskets(cid: str, period: str | None = "last_3_months", start: str | None = None,
                      end: str | None = None) -> dict:
    s, e = resolve_period(period, start, end)
    info = _period_info(s, e)
    rows = _q("""SELECT basket, sub, -sum(amount) total, count(*) n FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ?
                 AND basket IS NOT NULL GROUP BY ALL ORDER BY total DESC""", [cid, s, e])
    total = sum(r["total"] for r in rows) or 1
    out = []
    for b, meta in BASKETS.items():
        items = [r for r in rows if r["basket"] == b]
        t = sum(r["total"] for r in items)
        out.append({"basket": b, "name": meta["name"], "meaning": meta["explain"], "total_eur": _r(t),
                    "per_month_eur": _per_month(t, info), "share_of_spending": round(t / total, 3),
                    "transactions": sum(r["n"] for r in items),
                    "top": [{"merchant_type": r["sub"], "total_eur": _r(r["total"]), "transactions": r["n"]}
                            for r in items[:4]]})
    oneoffs = _q("SELECT tx_date, sub, -amount amount FROM tx WHERE customer_id = ? AND tx_date BETWEEN ? AND ? "
                 "AND one_off ORDER BY amount", [cid, s, e])
    return {"period": info, "baskets": out, "total_spending_eur": _r(total if rows else 0),
            "large_one_offs": [{"date": str(o["tx_date"]), "merchant_type": o["sub"], "amount_eur": _r(o["amount"])}
                               for o in oneoffs]}


def _salary_rhythm(cid: str) -> dict | None:
    rows = _q("SELECT tx_date, amount FROM tx WHERE customer_id = ? AND category = 'Salary' ORDER BY tx_date DESC "
              "LIMIT 6", [cid])
    if not rows:
        return None
    day = round(statistics.median(r["tx_date"].day for r in rows))
    y, m = TODAY.year, TODAY.month
    while True:
        d = date(y, m, min(day, calendar.monthrange(y, m)[1]))
        if d > TODAY:
            break
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return {"typical_day": day, "typical_amount_eur": _r(statistics.median(r["amount"] for r in rows)),
            "last_payday": rows[0]["tx_date"], "next_payday": d}


def get_safe_to_spend(cid: str) -> dict:
    """Safe-to-spend until next payday and for the next 7 days, with every step shown.

    Pay-cycle model: money already in the account before the last payday counts as savings and stays untouched;
    only this cycle's money is spendable."""
    bal = customer(cid)["balance"]
    pay = _salary_rhythm(cid)
    carried = 0.0
    if pay:
        before = _q("SELECT balance - amount b FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date = ? "
                    "ORDER BY seq LIMIT 1", [cid, pay["last_payday"]])
        carried = max(float(before[0]["b"]), 0.0) if before else 0.0
    cycle_money = bal - carried
    nxt = pay["next_payday"] if pay else TODAY + timedelta(days=30)
    last = pay["last_payday"] if pay else TODAY - timedelta(days=30)
    days = max((nxt - TODAY).days, 1)
    six = _month_start(TODAY, 5)
    bills = []
    for cat in ("Housing", "Utilities"):
        monthly = _q("SELECT strftime(tx_date, '%Y-%m') m, -sum(amount) t FROM tx WHERE customer_id = ? AND category = ? "
                     "AND tx_date >= ? GROUP BY 1", [cid, cat, six])
        months = {r["m"]: r["t"] for r in monthly}
        if not months:
            continue
        typical = statistics.median([months.get(_month_start(TODAY, i).strftime("%Y-%m"), 0) for i in range(6)])
        paid = _q("SELECT -sum(amount) t FROM tx WHERE customer_id = ? AND category = ? AND tx_date > ?",
                  [cid, cat, last])[0]["t"] or 0
        bills.append({"bill": cat, "typical_per_month_eur": _r(typical), "paid_since_last_payday_eur": _r(paid),
                      "still_to_come_eur": _r(max(typical - paid, 0))})
    bills_left = sum(b["still_to_come_eur"] for b in bills)
    since = TODAY - timedelta(days=89)
    daily = _q("""SELECT -sum(amount) FILTER (WHERE basket = 1 AND category NOT IN ('Housing', 'Utilities')) / 90 ess,
                         -sum(amount) FILTER (WHERE basket = 2 AND NOT one_off) / 90 sur,
                         -sum(amount) FILTER (WHERE basket = 3) / 90 ext
                  FROM tx WHERE customer_id = ? AND tx_date >= ?""", [cid, since])[0]
    essentials = (daily["ess"] or 0) * days
    surprises = (daily["sur"] or 0) * days
    safe = min(cycle_money, bal) - bills_left - essentials - surprises
    week_days = min(7, days)
    steps = [
        {"step": "Balance now", "eur": _r(bal)},
        {"step": "Savings carried over from before payday (kept safe, not for spending)", "eur": -_r(min(carried, bal))},
        {"step": f"Bills still due before payday ({', '.join(b['bill'] for b in bills) or 'none found'})",
         "eur": -_r(bills_left)},
        {"step": f"Groceries and commuting for {days} days (your 90-day average)", "eur": -_r(essentials)},
        {"step": f"Buffer for surprises for {days} days (health, repairs; your 90-day average)", "eur": -_r(surprises)},
    ]
    return {"as_of": TODAY.isoformat(), "next_payday": nxt.isoformat() if pay else None,
            "days_until_payday": days, "salary": ({"typical_day_of_month": pay["typical_day"],
                                                   "typical_amount_eur": pay["typical_amount_eur"]} if pay else None),
            "steps": steps, "bills": bills,
            "savings_in_account_eur": _r(min(carried, bal)),
            "used_savings_this_cycle_eur": _r(max(-cycle_money, 0)),
            "safe_until_payday_eur": _r(safe), "safe_per_day_eur": _r(safe / days),
            "safe_this_week_eur": _r(max(safe, 0) / days * week_days),
            "your_usual_extras_per_week_eur": _r((daily["ext"] or 0) * 7),
            "warning": (f"Nothing is safe to spend: you are about {_r(-safe)} EUR short before payday."
                        if safe < 0 else None),
            "method": ("This pay cycle's money (balance minus savings carried over from before payday), minus bills still "
                       "due, your usual essentials and a surprise buffer until payday.")}


def simulate_cut(cid: str, cut_percent: float, category: str | None = None, subcategory: str | None = None,
                 basket: int | None = None, months: int = 6) -> dict:
    """What-if: cut spending in an area by X %. Baseline is the average of the last full months, one-offs excluded."""
    if not (category or subcategory or basket):
        raise ToolError("Give a category, subcategory or basket to cut.")
    if not 0 < cut_percent <= 100:
        raise ToolError("cut_percent must be between 0 and 100")
    months = max(1, min(int(months), 12))
    s, e = _month_start(TODAY, months - 1), TODAY
    where, params = _filters(category, subcategory, basket)
    r = _q(f"SELECT -sum(amount) FILTER (WHERE NOT one_off) t, count(*) FILTER (WHERE NOT one_off) n FROM tx "
           f"WHERE customer_id = ? AND tx_date BETWEEN ? AND ? AND {where}", [cid, s, e] + params)[0]
    per_month = (r["t"] or 0) / months
    save = per_month * cut_percent / 100
    return {"based_on": _period_info(s, e), "area": {"category": category, "subcategory": subcategory, "basket": basket},
            "now_per_month_eur": _r(per_month), "purchases_per_month": round((r["n"] or 0) / months, 1),
            "cut_percent": cut_percent, "saving_per_month_eur": _r(save), "saving_per_year_eur": _r(save * 12),
            "new_per_month_eur": _r(per_month - save),
            "note": "Large one-off purchases are left out of the baseline."}


def get_spender_profile(cid: str) -> dict:
    """Habits plus a comparison with customers of the same age group (within this bank's data)."""
    c = customer(cid)
    lo, hi = (c["age"] // 10) * 10, (c["age"] // 10) * 10 + 9
    six = _month_start(TODAY, 5)
    peers = _q("""WITH p AS (SELECT customer_id, sum(b1) b1, sum(b2) b2, sum(b3) b3, sum(income) inc FROM cm
                  WHERE month >= ? GROUP BY 1),
                  r AS (SELECT p.*, b3 / nullif(b1 + b2 + b3, 0) x3, (b1 + b2 + b3) / nullif(inc, 0) ratio FROM p
                        JOIN cust USING (customer_id) WHERE age BETWEEN ? AND ? AND customer_id < 'CUST05001')
                  SELECT count(*) n, median(x3) x3, median(b3) / 6 b3m, median(ratio) ratio,
                         (SELECT x3 FROM r WHERE customer_id = ?) me_x3,
                         (SELECT b3 / 6 FROM r WHERE customer_id = ?) me_b3m,
                         (SELECT ratio FROM r WHERE customer_id = ?) me_ratio,
                         (SELECT avg((x3 < (SELECT x3 FROM r WHERE customer_id = ?))::INT) FROM r) pct
                  FROM r""", [six, lo, hi, cid, cid, cid, cid])[0]
    h = _q("""SELECT count(*) FILTER (WHERE basket = 3 AND amount > -10) / 6 small_per_month,
                     -sum(amount) FILTER (WHERE basket = 3 AND amount > -10) / 6 small_eur_month,
                     avg((hour(ts) >= 20)::INT) FILTER (WHERE basket = 3) evening_share,
                     avg((dayofweek(tx_date) IN (0, 6))::INT) FILTER (WHERE basket = 3) weekend_share,
                     count(*) FILTER (WHERE balance < 0) overdraft_tx
              FROM tx WHERE customer_id = ? AND tx_date >= ?""", [cid, six])[0]
    top = _q("SELECT sub, count(*) n, -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date >= ? AND basket = 3 "
             "GROUP BY 1 ORDER BY n DESC LIMIT 3", [cid, six])
    return {"based_on": _period_info(six, TODAY), "age": c["age"],
            "you": {"extras_share_of_spending": round(pdf(peers["me_x3"]), 3),
                    "extras_per_month_eur": _r(peers["me_b3m"]),
                    "spending_vs_income": round(pdf(peers["me_ratio"]), 2)},
            "peers_same_age_group": {"age_group": f"{lo}-{hi}", "customers": peers["n"],
                                     "median_extras_share": round(pdf(peers["x3"]), 3),
                                     "median_extras_per_month_eur": _r(peers["b3m"]),
                                     "median_spending_vs_income": round(pdf(peers["ratio"]), 2)},
            "extras_share_percentile_among_peers": round(pdf(peers["pct"]) * 100),
            "habits": {"small_extras_under_10_eur_per_month": round(pdf(h["small_per_month"]), 1),
                       "small_extras_eur_per_month": _r(h["small_eur_month"]),
                       "extras_after_8pm_share": round(pdf(h["evening_share"]), 2),
                       "extras_on_weekends_share": round(pdf(h["weekend_share"]), 2),
                       "transactions_while_overdrawn": h["overdraft_tx"],
                       "most_frequent_extras": [{"merchant_type": t["sub"], "times": t["n"], "total_eur": _r(t["t"])}
                                                for t in top]},
            "note": "Peers are customers of the same age group in this dataset, not national statistics."}


def pdf(x) -> float:
    return float(x or 0)


def overview(cid: str) -> dict:
    """Home screen: balance, safe-to-spend, this month's baskets vs the 6-month average."""
    c = customer(cid)
    sts = get_safe_to_spend(cid)
    month = get_three_baskets(cid, "this_month")
    avg = _q("SELECT avg(coalesce(b1, 0)) b1, avg(coalesce(b2, 0) + coalesce(oneoff, 0)) b2, avg(coalesce(b3, 0)) b3 "
             "FROM cm WHERE customer_id = ? AND month >= ? AND month < ?",
             [cid, _month_start(TODAY, 6), _month_start(TODAY)])[0]
    # Bills usually paid every month but not yet charged this month (so a low "must-pays" isn't read as good news).
    not_yet = [b["bill"] for b in sts["bills"] if b["typical_per_month_eur"] > 0 and not _q(
        "SELECT 1 FROM tx WHERE customer_id = ? AND category = ? AND tx_date >= ? LIMIT 1",
        [cid, b["bill"], _month_start(TODAY)])]
    return {"customer": c, "safe_to_spend": sts, "month": month, "not_yet_charged_this_month": not_yet,
            "six_month_avg_eur": {b: _r(avg[f"b{b}"]) for b in (1, 2, 3)},
            "baskets": {b: m for b, m in BASKETS.items()}}
