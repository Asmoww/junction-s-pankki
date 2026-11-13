# Data assumptions and quirks

Every quirk of the provided data, with evidence and how we handle it. Checked 2026-11-13 with DuckDB on the
full files (sha256 of the transactions CSV `49b3265d…6f1e63`).

## Shape
- `tx_junction_transactions.csv`: 3,626,755 rows, 5,100 customers, exactly one `bank_account_id` per customer.
  Dates 2024-10-01 to 2026-09-30 (24 full months, ~150 k rows per month, flat). No nulls in category/amount/balance.
  Rows per customer: min 148, median 700, max 1,543.
- `tx_customers_junction.csv`: 5,100 customers, all present in transactions. Age 18–90, heavy in the 40s
  (2,096 of 5,100), 182 aged 18–19, 535 in their 20s. Postal codes are all `00xxx`–`02xxx`
  (Helsinki, Espoo, Vantaa area), 290 distinct.
- All CSVs start with a UTF-8 BOM: read with `utf-8-sig` (DuckDB `read_csv_auto` handles it).

## Fields
- `tx_timestamp` is text like `03OCT24:09:04:04` (SAS format). Parse with `%d%b%y:%H:%M:%S`. Hours run 05–23;
  we assume Finnish local time.
- `tx_amount_eur`: negative = money out, positive = money in. The sign is consistent with the category
  (no positive Groceries, no negative Salary). No zero amounts.
- `category` (15 values) maps 1:1 to `transaction_type` for non-purchases. `purchase` rows carry the spending
  categories.
- `merchant_id` is an anonymous id like `MRC-GRO-0035` (no merchant names); the middle part matches the
  category. 515 merchants.
- `mcc_code` (36 codes) gives a sub-category and is the only way to answer "taxis" (4121), "fuel"
  (5541/5542), "fast food" (5814), "bars" (5813), "pharmacy" (5912) etc. Map in code, not in the prompt.
- `merchant_id` and `mcc_code` are null on 786,668 rows: all non-purchase rows plus 160,624 purchases
  (e.g. 75 k Transportation). Handling: those purchases count in their category but cannot be split by
  sub-category; answers must say "N EUR could not be classified further" instead of dropping them.

## Money flows that are not spending
- `Salary Sweep` (264 customers, 14–24 times each, 0–2 days after salary in 97 % of cases): moves most of the salary out of the account.
  It is a transfer to the customer's own savings/other account, not consumption. Excluded from spending.
- `Invest Deposit` (1,500 customers) / `Invest Withdraw`: transfers to and from investments. Shown as saving,
  not spending or income.
- `Other Income`: real income (median 2,081 EUR), irregular.
- Together Salary Sweep + Invest Deposit are 36.4 M EUR over the dataset; counting them as spending would be
  a big error (a trap case).

## Baskets (starting mapping, to refine with evidence)
- Basket 1, mandatory regular: Housing (monthly), Utilities.
- Basket 2, mandatory irregular: Health, large Home & Tech (appliances), car repairs/large Transportation.
- Basket 3, everyday slips: Restaurants, Entertainment, Lifestyle, small Groceries top-ups, taxis.
- Groceries: necessary but partly basket 3. Decide per merchant type / size, record the rule in DECISIONS.md.

## Quirks to handle
- **Housing missing some months.** e.g. CUST00002 has no Housing in 5 of 24 months, while CUST00001 has all 24.
  218 customers have no Housing at all. Housing amounts vary month to month (CUST00001: 491–539 EUR), so
  "rent" is not a fixed amount. Handling: recurring-bill detection must tolerate gaps and ±10 % amounts.
- **Extreme one-off purchases.** 136 purchases are both over 1,000 EUR and more than 20× the customer's own
  median for that category, e.g. a 6,874 EUR Groceries purchase (CUST05014). Max single purchase 30,935 EUR
  (Home & Tech). Handling: show them as basket-2 one-offs, keep them out of "typical month" and
  safe-to-spend baselines, but never hide them from totals.
- **Negative balances.** 89,398 rows (3,526 customers) have `balance_after_eur` < 0, min −1,985 EUR. Treat as
  overdraft; the coach must notice it.
- **Same-second ties.** 59 account/timestamp pairs share a timestamp. Ordered by timestamp alone, 51 rows break
  the running balance (prev balance + amount ≠ balance_after); all of them sit on these ties. Handling: order by
  timestamp, then by the order that makes the balance chain consistent. The latest balance = `balance_after_eur`
  of the last row in that order.
- **Data ends 2026-09-30.** "Today" in the demo is 2026-09-30 (or a chosen date inside the data), not the real
  date. "Last month" = September 2026. Every answer states the period it used.

## Special customers
- `CUST05001`–`CUST05100` (100 customers, average age 55 vs 43) hold 124 of the 136 extreme one-offs and many odd
  patterns. Probably injected edge cases. Handling: good for the trap suite; not used as demo personas.

## Mortgage files (probably out of scope)
- `mtg_tx_customer_link_and_final_mtg_infio.csv`: 200 mortgage applications linked 1:1 to `customer_id`, with final
  decision, loan, equity, required monthly income, LTV (column typo `lfinal_loan_to_value`).
- `mtg_negotiation_history.csv`: event log per application (created, contact, property added, price updated,
  decision…) with free-text `note`.
- Possible use: "can I afford a home?" coaching for those 200 customers. Not needed for the core challenge.
