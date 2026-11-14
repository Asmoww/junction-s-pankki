"""Backtest the app's own safe-to-spend (money.get_safe_to_spend), not a replica.

For each sampled customer and checkpoint day T (3 days after a payday, and 7 days before the next one):
  1. make the app see only the data up to T: money.TODAY = T and the `tx` view is cut at T;
  2. ask money.get_safe_to_spend(cid) for "safe until payday";
  3. replay what really happened from T+1 until the day before the next actual salary, but replace the customer's
     everyday extras (basket 3) with spending exactly the safe amount, spread evenly over the days;
  4. record the lowest balance. Failures: below the protected savings (what the app said it keeps aside), below 0.

Transfers to own savings/investments (kind 'transfer') are left out of the replay: the app doesn't treat them as
spending, and including them would blame the method for the user's own saving.

Run on the server (needs data/tx.parquet):
  .venv/bin/python scripts/analysis/backtest_app_safe_to_spend.py 300
Writes state/backtest_safe_to_spend.json (gitignored) and prints a summary table.
Rasmus's Claude, 14 Nov. Not run by its author (no duckdb in that sandbox): check the first few rows by hand.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import money  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
PARQUET = money.DATA / "tx.parquet"
FULL_TODAY = money.TODAY


def as_of(t: date) -> None:
    """Make every money.* query see only data up to t."""
    money.TODAY = t
    with money._lock:
        money._con.execute(f"CREATE OR REPLACE VIEW tx AS SELECT * FROM '{PARQUET}' WHERE tx_date <= DATE '{t}'")


def full() -> None:
    money.TODAY = FULL_TODAY
    with money._lock:
        money._con.execute(f"CREATE OR REPLACE VIEW tx AS SELECT * FROM '{PARQUET}'")


def protected_from(r: dict) -> float:
    """The savings amount the app says it keeps aside ("savings carried over from before payday")."""
    return float(r.get("savings_in_account_eur") or 0.0)


def main() -> None:
    full()
    cids = [r["customer_id"] for r in money._q("SELECT DISTINCT customer_id FROM tx WHERE category = 'Salary'")]
    random.Random(7).shuffle(cids)
    rows = []
    for cid in cids[:N]:
        full()
        pays = [r["d"] for r in money._q("SELECT DISTINCT tx_date d FROM tx WHERE customer_id = ? AND category = 'Salary' "
                                          "ORDER BY 1", [cid])]
        if len(pays) < 8:
            continue
        flows = money._q("SELECT tx_date d, amount a, basket b, kind k, balance FROM tx WHERE customer_id = ? ORDER BY seq",
                         [cid])
        for i in range(6, len(pays) - 1):
            for early in (True, False):
                last, nxt_actual = pays[i], pays[i + 1]
                t = last + timedelta(days=3) if early else nxt_actual - timedelta(days=7)
                if not (last <= t < nxt_actual - timedelta(days=1)):
                    continue
                as_of(t)
                try:
                    r = money.get_safe_to_spend(cid)
                except money.ToolError:
                    continue
                safe = r.get("safe_until_payday_eur")
                if safe is None:
                    continue
                bal = money.customer(cid)["balance"]
                prot = protected_from(r)
                predicted = date.fromisoformat(r["next_payday"]) if r.get("next_payday") else None
                span = max((nxt_actual - t).days - 1, 1)
                per_day = max(safe, 0.0) / span
                b, low = bal, bal
                for k in range(1, span + 1):
                    d = t + timedelta(days=k)
                    b += sum(f["a"] for f in flows if f["d"] == d and f["b"] != 3 and f["k"] != "transfer") - per_day
                    low = min(low, b)
                actual_extras = -sum(f["a"] for f in flows if t < f["d"] < nxt_actual and f["b"] == 3)
                rows.append({"cid": cid, "t": t.isoformat(), "early": early, "safe": round(safe, 2), "balance": bal,
                             "protected": prot, "low": round(low, 2), "actual_extras": round(actual_extras, 2),
                             "payday_wrong": predicted is not None and predicted != nxt_actual,
                             "neg_start": bal < 0,
                             "dip_savings": safe > 0 and low < min(prot, bal) - 1, "overdraft": safe > 0 and low < -1})
    full()
    out = Path(__file__).resolve().parents[2] / "state" / "backtest_safe_to_spend.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rows, indent=1))

    def rate(sub, key):
        return f"{100 * sum(x[key] for x in sub) / len(sub):.1f} % of {len(sub)}" if sub else "n/a"
    pos = [x for x in rows if x["safe"] > 0]
    print(f"checkpoints {len(rows)}, customers {len({x['cid'] for x in rows})}")
    print(f"safe > 0: {100 * len(pos) / max(len(rows), 1):.1f} %")
    for name, sub in [("all positive answers", pos), ("3 days after payday", [x for x in pos if x["early"]]),
                      ("7 days before payday", [x for x in pos if not x["early"]]),
                      ("payday predicted wrong", [x for x in pos if x["payday_wrong"]])]:
        print(f"  {name}: overdraft {rate(sub, 'overdraft')}, savings dip {rate(sub, 'dip_savings')}")
    print("  negative balance at T but safe > 0:", sum(1 for x in rows if x["neg_start"] and x["safe"] > 0))
    if pos:
        print(f"  median safe {statistics.median(x['safe'] for x in pos):.0f} €, "
              f"median actual extras in the same window {statistics.median(x['actual_extras'] for x in pos):.0f} €")
    print("Compare with the pandas replica in docs/REVIEW-RESPONSE.md §2 (savings dip 40.7 %, overdraft 5.5 %).")


if __name__ == "__main__":
    main()
