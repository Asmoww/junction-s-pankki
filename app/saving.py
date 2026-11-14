"""Safe to save: "How much can I move to savings on payday without running short before the next one?"

The brief names safe-to-save next to safe-to-spend; the app had only the second. Method, from the customer's own
pay months (no averages that hide bad months):
  for each of the last pay months, headroom = the lowest point of this month's own money
  (balance minus the savings carried in from before payday), minus a safety buffer.
  Moving X on payday lowers the whole month by X, so X was safe that month if X <= headroom.
  safe_to_save = the amount that was safe in at least 9 of the last 12 months (25th percentile of headroom),
  stretch = the amount safe in half of them (median).
Buffer = the customer's own monthly average of surprise must-pays (basket 2), so a broken washing machine still fits.
The core (`assess`) is pure numbers so it is unit-tested without the database.
"""
from __future__ import annotations

import math

OWN_SAVINGS = "('Salary Sweep', 'Invest Deposit', 'Invest Withdraw')"


def _q(xs: list[float], p: float) -> float:
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def assess(cycles: list[dict], buffer_eur: float, salary_eur: float | None = None,
           already_moving_eur: float = 0.0) -> dict:
    """cycles: one dict per past pay month, oldest first:
    {"start": "2026-08-15", "low_own_money_eur": float}  (lowest balance - savings carried in, during that month)."""
    if len(cycles) < 3:
        return {"status": "too_little_history", "pay_months_seen": len(cycles)}
    head = [c["low_own_money_eur"] - buffer_eur for c in cycles]
    safe = max(_q(head, 0.25), 0.0)
    stretch = max(_q(head, 0.50), 0.0)
    safe = math.floor(safe / 10) * 10          # round down to whole tens: an amount people actually set up
    stretch = max(math.floor(stretch / 10) * 10, safe)
    ok = sum(1 for h in head if h >= safe)
    ok_stretch = sum(1 for h in head if h >= stretch)
    out = {"status": "ok", "safe_to_save_on_payday_eur": float(safe), "stretch_eur": float(stretch),
           "months_it_would_have_been_safe": ok, "months_stretch_would_have_been_safe": ok_stretch,
           "pay_months_seen": len(cycles), "buffer_eur": round(buffer_eur, 2),
           "share_of_salary": round(safe / salary_eur, 3) if salary_eur else None,
           "per_month": [{"pay_month_start": c["start"], "headroom_eur": round(h, 2)} for c, h in zip(cycles, head)],
           "method": ("For each of your last pay months: the lowest point of that month's own money (balance minus "
                      "savings you already had), minus a buffer for surprise must-pays. The safe amount would have "
                      "fitted in at least 3 of 4 months; the stretch amount in about half."),
           "not_advice": "Based on your past months; a month with a big surprise can still need it back."}
    out["already_moving_to_savings_eur_month"] = round(already_moving_eur, 2)
    if already_moving_eur >= safe > 0:
        out["already_note"] = ("You already move about this much or more to savings or investments each month, so "
                               "this is confirmation, not a new step.")
    if safe == 0:
        out["why_zero"] = ("In most of your pay months the money ran down to the buffer or below before the next "
                           "salary, so moving money out on payday would have left you short. Closing the monthly gap "
                           "comes first.")
    return out


def get_safe_to_save(cid: str, months: int = 12) -> dict:
    """Coach/API entry point: builds the pay months from the transactions, then assesses."""
    from .money import TODAY, _month_start, _q as q

    # Pay months start at the salary transaction itself (seq), not at the date: spending earlier that day belongs
    # to the month before. Transfers to own savings/investments are added back: they already are saving.
    pays = q("SELECT seq, tx_date d, balance - amount carried FROM tx WHERE customer_id = ? AND category = 'Salary' "
             "AND tx_date <= ? ORDER BY seq", [cid, TODAY])
    if len(pays) < 4:
        return {"status": "too_little_history", "pay_months_seen": max(len(pays) - 1, 0),
                "note": "Needs a regular salary into this account."}
    pays = pays[-(months + 1):]
    cycles, moved = [], []
    for a, b in zip(pays, pays[1:]):
        r = q(f"""SELECT min(balance + tr) low, max(tr) moved FROM (
                    SELECT balance, sum(CASE WHEN category IN {OWN_SAVINGS} THEN -amount ELSE 0 END)
                                    OVER (ORDER BY seq) tr
                    FROM tx WHERE customer_id = ? AND seq >= ? AND seq < ?)""", [cid, a["seq"], b["seq"]])
        if r and r[0]["low"] is not None:
            cycles.append({"start": a["d"].isoformat(),
                           "low_own_money_eur": float(r[0]["low"]) - max(float(a["carried"]), 0.0)})
            moved.append(float(r[0]["moved"] or 0.0))
    pot = q("SELECT -sum(amount) FILTER (WHERE basket = 2) / 12 b FROM tx WHERE customer_id = ? AND tx_date >= ?",
            [cid, _month_start(TODAY, 11)])
    sal = q("SELECT median(amount) s FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date >= ?",
            [cid, _month_start(TODAY, 11)])
    out = assess(cycles, buffer_eur=float(pot[0]["b"] or 0.0) if pot else 0.0,
                 salary_eur=float(sal[0]["s"]) if sal and sal[0]["s"] else None,
                 already_moving_eur=sorted(moved)[len(moved) // 2] if moved else 0.0)
    out["as_of"] = TODAY.isoformat()
    return out
