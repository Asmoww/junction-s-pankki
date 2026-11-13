"""Build data/tx.parquet from the raw challenge CSVs (see docs/ASSUMPTIONS.md for every rule applied here).

Usage: .venv/bin/python scripts/build_data.py
Adds: parsed timestamp, a balance-consistent order (seq), kind (spend/income/transfer), sub-category from MCC,
one-off flag and the three-basket label. Sorted by customer so per-customer queries read few row groups.
"""
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.taxonomy import MCC_LABELS, NO_MCC_SUB  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "tx.parquet"

con = duckdb.connect()
con.execute("SET memory_limit='3GB'")
con.execute("CREATE TABLE mcc(mcc BIGINT, sub VARCHAR)")
con.executemany("INSERT INTO mcc VALUES (?, ?)", list(MCC_LABELS.items()))

con.execute(f"""
CREATE TABLE t AS
SELECT customer_id, bank_account_id, tx_date,
       strptime(tx_timestamp, '%d%b%y:%H:%M:%S') AS ts,
       category, tx_amount_eur AS amount, balance_after_eur AS balance,
       transaction_type, merchant_id, mcc_code AS mcc
FROM read_csv_auto('{RAW}/tx_junction_transactions.csv', header=true, sample_size=-1)
""")

# Same-second ties: put first the row whose balance the other row continues from (fixes all 51 chain breaks).
con.execute("""
CREATE TABLE t2 AS
SELECT t.*,
       EXISTS (SELECT 1 FROM t s WHERE s.bank_account_id = t.bank_account_id AND s.ts = t.ts
               AND (s.balance <> t.balance OR s.amount <> t.amount)
               AND abs(t.balance + s.amount - s.balance) < 0.011) AS tie_first
FROM t
""")

con.execute("""
CREATE TABLE med AS
SELECT customer_id, category, median(amount) AS med FROM t2 WHERE transaction_type = 'purchase' GROUP BY ALL
""")

con.execute(f"""
COPY (
  SELECT t.customer_id, t.tx_date, t.ts, t.category, t.amount, t.balance, t.transaction_type, t.merchant_id, t.mcc,
         row_number() OVER (PARTITION BY t.customer_id ORDER BY t.ts, t.tie_first DESC) AS seq,
         CASE WHEN t.category IN ('Salary', 'Other Income') THEN 'income'
              WHEN t.category IN ('Salary Sweep', 'Invest Deposit', 'Invest Withdraw') THEN 'transfer'
              ELSE 'spend' END AS kind,
         coalesce(m.sub, CASE WHEN t.category IN ('Housing', 'Utilities') THEN
                                (CASE t.category WHEN 'Housing' THEN '{NO_MCC_SUB["Housing"]}' ELSE '{NO_MCC_SUB["Utilities"]}' END)
                              WHEN t.transaction_type <> 'purchase' THEN t.category
                              ELSE 'Other ' || lower(t.category) END) AS sub,
         (t.transaction_type = 'purchase' AND t.amount < -1000 AND t.amount < 20 * md.med) AS one_off,
         CASE
           WHEN t.category IN ('Salary', 'Other Income', 'Salary Sweep', 'Invest Deposit', 'Invest Withdraw') THEN NULL
           WHEN t.category IN ('Housing', 'Utilities') THEN 1
           WHEN t.transaction_type = 'purchase' AND t.amount < -1000 AND t.amount < 20 * md.med THEN 2
           WHEN t.category = 'Groceries' AND coalesce(t.mcc, 5411) IN (5411, 5422, 5451) THEN 1
           WHEN t.category = 'Transportation' AND (t.mcc IS NULL OR t.mcc IN (4111, 5541, 5542)) THEN 1
           WHEN t.category = 'Health' THEN 2
           WHEN t.category = 'Home & Tech' AND t.amount <= -100 THEN 2
           ELSE 3
         END AS basket
  FROM t2 t
  LEFT JOIN mcc m ON m.mcc = t.mcc
  LEFT JOIN med md ON md.customer_id = t.customer_id AND md.category = t.category
  ORDER BY t.customer_id, seq
) TO '{OUT}' (FORMAT parquet, ROW_GROUP_SIZE 20000, COMPRESSION zstd)
""")

con.execute(f"""
COPY (SELECT customer_id, customer_postal_code AS postal_code, customer_age AS age
      FROM read_csv_auto('{RAW}/tx_customers_junction.csv', header=true)) TO '{ROOT}/data/customers.parquet' (FORMAT parquet)
""")

# Sanity: the balance chain must hold everywhere after reordering.
bad = con.execute(f"""
SELECT count(*) FROM (
  SELECT amount, balance, lag(balance) OVER (PARTITION BY customer_id ORDER BY seq) pb FROM '{OUT}'
) WHERE pb IS NOT NULL AND abs(pb + amount - balance) >= 0.011
""").fetchone()[0]
n = con.execute(f"SELECT count(*) FROM '{OUT}'").fetchone()[0]
print(f"wrote {OUT} ({n} rows, {OUT.stat().st_size // 1_000_000} MB), balance chain breaks: {bad}")
sys.exit(1 if bad else 0)
