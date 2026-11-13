"""Home planner: "When can I buy a €250k home?" Reads the loan cap, transfer tax and Euribor from the live rules
registry (app/live.py). If a rule is not confirmed, every number that depends on it is None ("unknown"), never a
default. Customer numbers come from the bank data; no customer data goes to the web.
"""
from __future__ import annotations

import math
import statistics

from . import live, money
from .money import TODAY, _month_start, _q, _r

STRESS_INCOME_PER_LOAN = 0.018409   # required income / loan in all 200 mortgage rows (6 %, 25 y, 35 %)
FEES_EUR = 550.0                    # valuation 350 € + bank fee 200 € (medians in the mortgage data)
COLLATERAL_SHARE = 0.72             # home valued at ~72 % of price as collateral (median in the mortgage data)
TERM_YEARS = 25


def _annuity(rate_pct: float, years: int) -> float:
    r = rate_pct / 100 / 12
    return 1 / (years * 12) if r == 0 else r / (1 - (1 + r) ** -(years * 12))


def plan_home(cid: str, price: float, property_type: str = "apartment") -> dict:
    if not 20_000 <= price <= 3_000_000:
        raise money.ToolError("price must be between 20,000 and 3,000,000 €")
    if property_type not in ("apartment", "house"):
        raise money.ToolError("property_type must be apartment or house")
    reg = live.registry()
    cap = live.rule_value("loan_cap_general")
    tax_key = "transfer_tax_shares" if property_type == "apartment" else "transfer_tax_real_estate"
    tax = live.rule_value(tax_key)
    eur12 = live.rule_value("euribor_12m")
    six = _month_start(TODAY, 5)
    # 12 months of salary, as in the review-branch planner, so both teams quote the same loan figures
    sal = [r["a"] for r in _q("SELECT amount a FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date >= ?",
                              [cid, _month_start(TODAY, 11)])]
    salary = statistics.median(sal) if sal else None
    months = _q("SELECT coalesce(income, 0) - coalesce(b1, 0) - coalesce(b2, 0) - coalesce(b3, 0) - coalesce(oneoff, 0) s, "
                "coalesce(b1, 0) + coalesce(b2, 0) m FROM cm WHERE customer_id = ? AND month >= ? AND month < ?",
                [cid, six, _month_start(TODAY)])
    surplus = statistics.median([m["s"] for m in months]) if months else None
    buffer = statistics.median([m["m"] for m in months]) if months else 0.0
    bal = money.customer(cid)["balance"]
    have = max(bal - buffer, 0.0)
    by_income = salary / STRESS_INCOME_PER_LOAN if salary else None
    by_cap = price * cap / 100 if cap is not None else None
    loan = min(by_cap, by_income) if by_cap is not None and by_income is not None else None
    tax_eur = price * tax / 100 if tax is not None else None
    need = price - loan + tax_eur + FEES_EUR if loan is not None and tax_eur is not None else None
    gap = max(need - have, 0.0) if need is not None else None
    months_to = (0 if gap == 0 else math.ceil(gap / surplus) if surplus and surplus > 0 else None) if gap is not None else None
    used = {k: {f: reg[k].get(f) for f in ("label", "value", "unit", "status", "source_url", "source_date", "fetched_at",
                                           "request_id", "effective_from")}
            for k in ("loan_cap_general", tax_key, "euribor_12m")}
    return {
        "price_eur": _r(price), "property_type": property_type,
        "salary_month_eur": _r(salary) if salary else None,
        "max_loan_by_income_eur": _r(by_income) if by_income else None,
        "max_loan_by_cap_eur": _r(by_cap) if by_cap is not None else None,
        "loan_eur": _r(loan) if loan is not None else None,
        "transfer_tax_eur": _r(tax_eur) if tax_eur is not None else None,
        "fees_eur": FEES_EUR, "equity_and_costs_needed_eur": _r(need) if need is not None else None,
        "savings_counted_eur": _r(have), "kept_as_buffer_eur": _r(buffer),
        "gap_eur": _r(gap) if gap is not None else None,
        "surplus_per_month_eur": _r(surplus) if surplus is not None else None,
        "months_to_goal": months_to,
        "extra_collateral_needed_eur": _r(max(loan - COLLATERAL_SHARE * price, 0)) if loan is not None else None,
        "monthly_payment_at_euribor_only_eur": _r(loan * _annuity(eur12, TERM_YEARS)) if loan is not None and eur12 is not None else None,
        "unknown": [k for k, v in (("loan cap", cap), ("transfer tax", tax), ("12-month Euribor", eur12)) if v is None]
                   + ["bank margin (monthly payment is a lower bound)"],
        "rules_used": used,
        "assumptions": {"stress_formula": "required income = 0.018409 × loan (6 %, 25 years, 35 %), from the mortgage data",
                        "fees": "valuation 350 € + bank fee 200 € (medians in the mortgage data)",
                        "collateral": "home valued at about 72 % of price as collateral (median in the mortgage data)",
                        "term_years": TERM_YEARS},
    }
