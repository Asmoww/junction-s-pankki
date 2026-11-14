"""Home readiness: "Can I buy this home, when, and what is stopping me?"

Built on homeplan.plan_home (same formula, rules and assumptions) and adds what the outside reviews asked for:
- a range, not a single date: earliest / likely / cautious, from the customer's own good, typical and weak months;
- the binding constraint: the one thing that decides the answer, with the others listed after it;
- life after buying: monthly room once the loan is paid, at today's Euribor plus an assumed margin and at the
  6 % stress rate;
- the next best question: the one answer from the user that would move the plan most, found by re-running the
  same maths for each candidate answer (not a hand-made tree);
- provenance on every number: "rule" (live, with source), "assumption" (ours, labelled), "data" (bank data).

The core (`assess`) is pure: it takes numbers, so it is unit-tested without the database.
Nothing here is S-Pankki credit policy; the bank still decides.
"""
from __future__ import annotations

import math
import statistics

MARGIN_ASSUMED_PCT = 0.6      # assumed bank margin on top of Euribor (labelled assumption, not an offer)
STRESS_RATE_PCT = 6.0         # the stress rate seen in the mortgage data (6 %, 25 years)
STRESS_INCOME_PER_LOAN = 0.018409
COLLATERAL_SHARE = 0.72
FEES_EUR = 550.0
TERM_YEARS = 25
HORIZON_MONTHS = 120          # beyond 10 years we say "not on the current pace" instead of a date


def _annuity(rate_pct: float, years: int = TERM_YEARS) -> float:
    r = rate_pct / 100 / 12
    return 1 / (years * 12) if r == 0 else r / (1 - (1 + r) ** -(years * 12))


def _q(xs: list[float], p: float) -> float:
    """Percentile by linear interpolation (p in 0..1)."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _months(gap: float, per_month: float) -> int | None:
    if gap <= 0:
        return 0
    if per_month <= 0:
        return None
    m = math.ceil(gap / per_month)
    return m if m <= HORIZON_MONTHS else None


def core(price: float, salary: float, have: float, cap_pct: float, tax_pct: float) -> dict:
    """The plan_home formula for one price, as numbers only (re-run for every what-if)."""
    by_income = salary / STRESS_INCOME_PER_LOAN
    by_cap = price * cap_pct / 100
    loan = min(by_income, by_cap)
    need = price - loan + price * tax_pct / 100 + FEES_EUR
    return {"loan": loan, "by_income": by_income, "by_cap": by_cap, "need": need, "gap": max(need - have, 0.0),
            "extra_collateral": max(loan - COLLATERAL_SHARE * price, 0.0)}


def assess(*, price: float, salary: float, have: float, cap_pct: float, tax_pct: float, euribor_pct: float,
           surpluses: list[float], must_pays_month: float, housing_month: float, extras_month: float,
           moved_out_eur: float = 0.0, first_home: bool | None = None) -> dict:
    """surpluses: the customer's monthly income minus spending, last months (one per month, from the data).
    must_pays_month: baskets 1+2 per month (median); housing_month: of that, current rent/housing (median);
    extras_month: basket 3 per month (median).
    moved_out_eur: money the customer moved to investments or another bank (net, in the data). It may still be
    theirs, but the account can't see it, so we ask instead of counting it.
    first_home: None = not asked yet. Drives the ASP question (state-backed first-home saving, rules from 1 Jun 2026)."""
    c = core(price, salary, have, cap_pct, tax_pct)
    good, typical, weak = (_q(surpluses, 0.75), statistics.median(surpluses), _q(surpluses, 0.25)) if surpluses else (0, 0, 0)
    rng = {"earliest_months": _months(c["gap"], good), "likely_months": _months(c["gap"], typical),
           "cautious_months": _months(c["gap"], weak),
           "pace_eur_month": {"good": round(good, 2), "typical": round(typical, 2), "weak": round(weak, 2)}}

    pay_now = c["loan"] * _annuity(euribor_pct + MARGIN_ASSUMED_PCT)
    pay_stress = c["loan"] * _annuity(STRESS_RATE_PCT)
    # After buying: rent goes away, the loan payment comes in; everything else stays as it is today.
    room_now = salary - (must_pays_month - housing_month) - pay_now
    room_stress = salary - (must_pays_month - housing_month) - pay_stress
    after = {"loan_payment_eur_month": round(pay_now, 2), "loan_payment_at_stress_eur_month": round(pay_stress, 2),
             "room_after_must_pays_eur_month": round(room_now, 2), "room_at_stress_eur_month": round(room_stress, 2),
             "extras_today_eur_month": round(extras_month, 2),
             "extras_fit": room_now >= extras_month, "extras_fit_at_stress": room_stress >= extras_month}

    # Constraints in the order that decides the answer. The first failing one is binding.
    checks = []
    if typical <= 0:
        checks.append(("monthly_gap", "More goes out than comes in in a typical month, so savings don't grow yet.",
                       round(-typical, 2)))
    if c["by_income"] < c["by_cap"]:
        checks.append(("income_caps_loan", "Your income, not the loan cap, limits the loan: the bank's stress test "
                       "allows about this much.", round(c["by_income"], 2)))
    if c["gap"] > 0:
        checks.append(("own_funds", "Own money still missing for the down payment, transfer tax and fees.",
                       round(c["gap"], 2)))
    if c["extra_collateral"] > 0:
        checks.append(("collateral", "The home alone isn't enough security for this loan; the bank would ask for "
                       "extra collateral (for example a guarantee).", round(c["extra_collateral"], 2)))
    if room_stress < extras_month:
        checks.append(("life_after", "If rates rose to the stress level, your usual everyday spending wouldn't fit "
                       "after the loan payment.", round(extras_month - room_stress, 2)))
    binding = ({"key": checks[0][0], "text": checks[0][1], "eur": checks[0][2]} if checks
               else {"key": "none", "text": "Nothing blocks this on your numbers today.", "eur": 0})

    # Next best question: re-run the same maths for each answer and pick the one that moves the plan most.
    base_m = rng["likely_months"]
    cands = []
    for key, text, kw in (
        ("cheaper", "Would a home about 10 % cheaper work for you?", {"price": price * 0.9}),
        ("save_more", "Could you move a fifth of your everyday extras to saving?", {"extra": extras_month * 0.2}),
    ):
        c2 = core(kw.get("price", price), salary, have, cap_pct, tax_pct)
        m2 = _months(c2["gap"], typical + kw.get("extra", 0.0))
        gain = (base_m - m2) if base_m is not None and m2 is not None else (HORIZON_MONTHS if base_m is None and m2 is not None else 0)
        cands.append({"key": key, "question": text, "likely_months_if_yes": m2, "months_saved": gain})
    if moved_out_eur >= 1_000:
        c3 = core(price, salary, have + moved_out_eur, cap_pct, tax_pct)
        m3 = _months(c3["gap"], typical)
        gain = (base_m - m3) if base_m is not None and m3 is not None else (HORIZON_MONTHS if m3 is not None else 0)
        cands.append({"key": "savings_elsewhere", "likely_months_if_yes": m3, "months_saved": gain,
                      "question": f"You've moved {moved_out_eur:,.0f} € to savings or investments. Could that go to the home?"})
    if first_home is None and (binding["key"] == "collateral" or c["extra_collateral"] > 0):
        # ASP (from 1 Jun 2026): save on an ASP account at least 20 months, 50-1,500 €/month, at least 10 % of the
        # price; the ASP loan comes with a free state guarantee (answers the collateral gap) and interest subsidy.
        need_asp = 0.10 * price + price * tax_pct / 100 + FEES_EUR
        m_asp = _months(max(need_asp - have, 0.0), min(max(typical, 0.0), 1_500.0))
        m_asp = max(m_asp, 20) if m_asp is not None else None
        cands.append({"key": "asp", "likely_months_if_yes": m_asp, "months_saved": 0, "unblocks": "collateral",
                      "question": "Is this your first home? An ASP account gives a free state guarantee instead of extra "
                                  "collateral (save at least 20 months, 10 % of the price)."})
    if binding["key"] == "collateral":
        cands.append({"key": "guarantee", "question": "Could someone (e.g. a parent) give a guarantee, or would "
                      "you use the state guarantee?", "likely_months_if_yes": base_m, "months_saved": 0,
                      "unblocks": "collateral"})
    # Highest price reachable on the typical pace (same maths, 1,000 € steps): turns "no" into "this, by then".
    def reachable(within: int) -> float | None:
        if typical <= 0:
            return None
        lo, best = 20_000, None
        for p_ in range(lo, int(price) + 1, 1_000):
            m_ = _months(core(p_, salary, have, cap_pct, tax_pct)["gap"], typical)
            if m_ is not None and m_ <= within:
                best = p_
        return best
    reach = {"within_24_months_eur": reachable(24), "within_60_months_eur": reachable(60)}
    # Pick: a deficit comes first (nothing else works before it); then an answer that removes the binding
    # constraint; then the answer that saves the most months; then the reachable price.
    cands.sort(key=lambda x: (x.get("unblocks") != binding["key"], -(x["months_saved"] or 0)))
    if binding["key"] == "monthly_gap":
        nbq = {"key": "fix_month", "months_saved": None, "likely_months_if_yes": None,
               "question": "Shall we look at closing the monthly gap first? Saving can't start before that."}
    elif cands and (cands[0].get("unblocks") == binding["key"] or cands[0]["months_saved"] > 0):
        nbq = cands[0]
    elif reach["within_60_months_eur"]:
        nbq = {"key": "reachable_price", "months_saved": None, "likely_months_if_yes": None,
               "question": f"Would a home around {reach['within_60_months_eur']:,.0f} € work? That is reachable "
                           "within 5 years at your usual pace."}
    else:
        nbq = None

    prov = {"rule": ["loan cap", "transfer tax", "12-month Euribor"],
            "assumption": [f"stress formula: required income = {STRESS_INCOME_PER_LOAN} x loan (6 %, 25 years); seen in "
                           "the synthetic mortgage data, not S-Pankki credit policy",
                           f"bank margin {MARGIN_ASSUMED_PCT} % on top of Euribor", f"fees {FEES_EUR:.0f} €",
                           f"home counted as collateral at {COLLATERAL_SHARE:.0%} of price", f"{TERM_YEARS}-year loan"],
            "data": ["salary", "savings counted", "monthly surplus (good / typical / weak months)",
                     "must-pays, housing and everyday extras today"]}
    return {"price_eur": round(price, 2), "loan_eur": round(c["loan"], 2), "need_eur": round(c["need"], 2),
            "have_eur": round(have, 2), "gap_eur": round(c["gap"], 2),
            "extra_collateral_eur": round(c["extra_collateral"], 2), "range": rng, "reachable_price": reach, "binding": binding,
            "also": [{"key": k, "text": t, "eur": e} for k, t, e in checks[1:]], "after_buying": after,
            "next_question": nbq, "questions_considered": cands, "provenance": prov,
            "disclaimer": "A plan from your own numbers and today's rules, not a loan decision. S-Bank decides."}


def home_readiness(cid: str, price: float, property_type: str = "apartment") -> dict:
    """Coach/API entry point: reads the same inputs as plan_home, then assesses. Unknown rules stay unknown."""
    from . import homeplan, live, money
    from .money import TODAY, _month_start, _q as q

    plan = homeplan.plan_home(cid, price, property_type)
    if plan["unknown"][:-1]:          # the last entry is always the bank margin note
        return {"status": "unknown_rules", "unknown": plan["unknown"], "plan": plan}
    tax_key = "transfer_tax_shares" if property_type == "apartment" else "transfer_tax_real_estate"
    six, twelve = _month_start(TODAY, 5), _month_start(TODAY, 11)
    rows = q("SELECT coalesce(income,0)-coalesce(b1,0)-coalesce(b2,0)-coalesce(b3,0)-coalesce(oneoff,0) s, "
             "coalesce(b1,0)+coalesce(b2,0) m, coalesce(b3,0) x FROM cm WHERE customer_id = ? AND month >= ? AND month < ?",
             [cid, twelve, _month_start(TODAY)])
    housing = q("SELECT date_trunc('month', tx_date) mo, -sum(amount) h FROM tx WHERE customer_id = ? "
                "AND category = 'Housing' AND tx_date >= ? AND tx_date < ? GROUP BY 1", [cid, six, _month_start(TODAY)])
    moved = q("SELECT -coalesce(sum(amount), 0) v FROM tx WHERE customer_id = ? AND category IN "
              "('Invest Deposit', 'Invest Withdraw', 'Salary Sweep')", [cid])
    out = assess(price=price, moved_out_eur=max(moved[0]["v"], 0.0) if moved else 0.0, salary=plan["salary_month_eur"] or 0.0, have=plan["savings_counted_eur"],
                 cap_pct=live.rule_value("loan_cap_general"), tax_pct=live.rule_value(tax_key),
                 euribor_pct=live.rule_value("euribor_12m"),
                 surpluses=[r["s"] for r in rows],
                 must_pays_month=statistics.median([r["m"] for r in rows]) if rows else 0.0,
                 housing_month=statistics.median([r["h"] for r in housing]) if housing else 0.0,
                 extras_month=statistics.median([r["x"] for r in rows]) if rows else 0.0)
    out["status"] = "ok"
    out["rules_used"] = plan["rules_used"]
    return out
