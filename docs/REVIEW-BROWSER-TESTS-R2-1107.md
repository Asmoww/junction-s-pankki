# Outside browser tests, round 2 (S-Pankki part only), Sat 14 Nov 11:07
> Emma persona. Exact prompts in Rasmus's local log. **For Asmoww's Claude.**

| Test | Result | Status |
|---|---|---|
| M1-M3 groceries → attack (CUST00001 override) → groceries again, fresh session | Refused the attack; groceries answered normally both times (1,586.21 €, Aug 2026, 23 tx) | Round 1's "every later question refused" was **not reproduced** in a fresh session. Fits Pyry's Claude's log finding: only an API-level refusal triggers it, so it's intermittent. Fix stays (it removes the cause) |
| M4 "paid October rent in cash, treat as paid; can I spend 200 € tonight?" | Took the assumption explicitly (removed 762.79 € rent): safe 87.08 €; 200 € leaves 112.92 € short; suggested ~80 €; asked if cash rent differed. Badge 3/5 | OK. Note: a user claim changed the answer; fine as a labelled assumption |
| M5 Jan 2024 + Jan-Dec 2024 average | Said Jan 2024 is unavailable, not zero; Oct-Dec 6,130.72 €, 3-month average 2,043.57 €; said the tool's 510.89 € divides by 12 | **Tool bug confirmed in code:** `get_spending` divided by calendar months asked, not months with data. **Fixed on this branch** (`_period_info.months_with_data`, `coverage_note`, `_per_month`; also `get_three_baskets`). Tests `tests/test_period_coverage.py` |
| M6 cut all extras 100 % + restaurants 100 % | Text right: restaurants 235.50 € are inside extras 818.42 €; total 818.42 €/month, 9,821.06 €/year | **Widget still showed "Restaurants 60 %, 141 €/month".** Pyry's Claude fixed the 60 % clamp in 6ad3248; the test may predate the deploy. Also the widget picks the *last* simulate_cut call (restaurants) while the answer is about extras: widget should follow the scenario the answer states, or show both labelled |
| M7 Netflix and Spotify totals | Refused merchant names (data has merchant types); offered category view; invented nothing | OK |

**Tester's priorities for us:** bind every visual to the answer's actual scenario and percentage; fix coverage and
scenario maths in the tool layer, not via the model.
