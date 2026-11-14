"""Backtest of the live app's safe-to-spend method (money.get_safe_to_spend, origin/main 179b37a), replicated in
pandas. For each customer and checkpoint date T we compute safe-to-spend as the app would on day T, then replay
what actually happened until the next salary, replacing the customer's actual everyday extras (basket 3) with
spending exactly the safe amount, spread evenly. Failure modes:
  dip_savings : balance would fall below the protected savings (carried over from before payday)
  overdraft   : balance would fall below zero
Basket rules follow DECISIONS.md 2026-11-13 (approximation: one-offs not separated)."""
import sys, calendar, statistics, numpy as np, pandas as pd
from datetime import timedelta, date
d = pd.read_pickle(sys.argv[1]); N = int(sys.argv[2]) if len(sys.argv) > 2 else 600
d = d[d.customer_id < "CUST05001"].copy()
d["dt"] = pd.to_datetime(d.tx_date).dt.date
d = d.sort_values(["customer_id", "ts"])
B1_MCC = {5411, 4111, 5541, 5542}
def basket(r_cat, mcc, amt):
    if r_cat in ("Housing", "Utilities"): return 1
    if r_cat in ("Groceries", "Transportation") and mcc in B1_MCC: return 1
    if r_cat == "Health" or (r_cat == "Home & Tech" and -amt >= 100): return 2
    return 3
spend = ~d.category.isin(["Salary", "Other Income", "Salary Sweep", "Invest Deposit", "Invest Withdraw"]) & (d.tx_amount_eur < 0)
d["bk"] = 0
d.loc[spend, "bk"] = [basket(c, m, a) for c, m, a in zip(d.category[spend], pd.to_numeric(d.mcc_code[spend], errors="coerce").fillna(0).astype(int), d.tx_amount_eur[spend])]
rng = np.random.default_rng(7)
cids = rng.choice(d.customer_id.unique(), size=N, replace=False)
rows = []
EXCL = len(sys.argv) > 3
for cid in cids:
    x = d[d.customer_id == cid]
    sal = x[x.category == "Salary"]
    pays = sorted(sal.dt.unique())
    if len(pays) < 8: continue
    irregular_income = (x.category == "Other Income").sum() >= 6
    for i in range(6, len(pays) - 1):
        for offset in (3, None):                       # early in the cycle, and 7 days before the next payday
            last_pay, next_actual = pays[i], pays[i + 1]
            T = last_pay + timedelta(days=3) if offset else next_actual - timedelta(days=7)
            if not (last_pay <= T < next_actual): continue
            past = x[x.dt <= T]; bal = past.balance_after_eur.iloc[-1]
            hist = sal[sal.dt <= T].tail(6)
            day = round(statistics.median(pd.to_datetime(hist.dt).dt.day))
            y, m = T.year, T.month
            while True:
                nd = date(y, m, min(day, calendar.monthrange(y, m)[1]))
                if nd > T: break
                y, m = (y + 1, 1) if m == 12 else (y, m + 1)
            days = max((nd - T).days, 1)
            first = x[(x.category == "Salary") & (x.dt == last_pay)].iloc[0]
            carried = max(first.balance_after_eur - first.tx_amount_eur, 0.0)
            six = pd.Timestamp(T).to_period("M") - 5
            bills_left = 0.0
            for cat in ("Housing", "Utilities"):
                c = past[past.category == cat]
                if c.empty: continue
                mon = (-c.tx_amount_eur).groupby(pd.to_datetime(c.dt).dt.to_period("M")).sum()
                typ = statistics.median([mon.get(six + k, 0.0) for k in range(6)])
                paid = -c[c.dt > last_pay].tx_amount_eur.sum()
                bills_left += max(typ - paid, 0.0)
            w = past[past.dt >= T - timedelta(days=89)]
            ess = -w[(w.bk == 1) & ~w.category.isin(["Housing", "Utilities"])].tx_amount_eur.sum() / 90 * days
            sur = -w[w.bk == 2].tx_amount_eur.sum() / 90 * days
            safe = min(bal - carried, bal) - bills_left - ess - sur
            # Replay T+1 .. day before next actual salary
            fut = x[(x.dt > T) & (x.dt < next_actual)]
            non_extra = fut[fut.bk != 3].tx_amount_eur                         # bills, essentials, surprises, income, transfers
            path, b = [], bal
            span = max((next_actual - T).days - 1, 1)
            per_day = max(safe, 0.0) / span
            for k in range(1, span + 1):
                dd = T + timedelta(days=k)
                day_rows = fut[(fut.dt == dd) & (fut.bk != 3)]
                if EXCL: day_rows = day_rows[~day_rows.category.isin(["Salary Sweep", "Invest Deposit", "Invest Withdraw"])]
                b += day_rows.tx_amount_eur.sum() - per_day
                path.append(b)
            low = min(path) if path else bal
            actual_extras = -fut[fut.bk == 3].tx_amount_eur.sum()
            rows.append(dict(cid=cid, T=T, early=bool(offset), safe=safe, bal=bal, carried=carried, low=low,
                             neg_start=bal < 0, irregular=irregular_income, payday_miss=(nd != next_actual),
                             actual_extras=actual_extras,
                             dip_savings=(safe > 0) and (low < min(carried, bal) - 1),
                             overdraft=(safe > 0) and (low < -1), short=max(min(carried, bal) - low, 0) if safe > 0 else 0))
r = pd.DataFrame(rows); r.to_pickle("/tmp/sts_backtest.pkl")
pos = r[r.safe > 0]
def rate(df, col): return f"{df[col].mean()*100:.1f} % of {len(df)}"
print("checkpoints", len(r), "customers", r.cid.nunique())
print("safe > 0 in", f"{(r.safe>0).mean()*100:.1f} %", "| safe <= 0 (warning shown):", f"{(r.safe<=0).mean()*100:.1f} %")
print("When safe > 0 -> overdraft:", rate(pos, "overdraft"), "| dip into protected savings:", rate(pos, "dip_savings"))
for name, sub in [("early in cycle", pos[pos.early]), ("7 days before payday", pos[~pos.early]),
                  ("irregular income (>=6 other-income tx)", pos[pos.irregular]), ("regular income", pos[~pos.irregular]),
                  ("predicted payday wrong", pos[pos.payday_miss]), ("negative balance at T", r[r.neg_start])]:
    if len(sub): print(f"  {name}: overdraft {rate(sub,'overdraft')}, savings dip {sub.dip_savings.mean()*100:.1f} %, safe>0 share {(sub.safe>0).mean()*100:.0f} %")
print("median safe (when > 0):", round(pos.safe.median()), "€ | median actual extras in same window:", round(pos.actual_extras.median()), "€")
print("median shortfall when savings dipped:", round(pos[pos.dip_savings].short.median()), "€; p90", round(pos[pos.dip_savings].short.quantile(.9)), "€")
print("negative-balance checkpoints where safe > 0:", int(((r.neg_start) & (r.safe > 0)).sum()))
