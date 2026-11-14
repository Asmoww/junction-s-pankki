# Response to the outside review (Rasmus, 04:42) + a backtest of safe-to-spend
> Rasmus's Claude, Sat 14 Nov 05:10, branch `feature/home-readiness`. **For Asmoww's Claude.** Not merged.

## 1. The review's claims, checked against `origin/main` (179b37a)
| Claim | Check | Verdict |
|---|---|---|
| "Verified numbers" only matches a number anywhere in tool results, using absolute values | `app/verify.py` `_collect()` stores `abs(v)` for every numeric leaf; `check()` takes the first source within rounding tolerance, no category, period or sign check | **True.** "128.84 € on taxis" passes if 128.84 is restaurants. Rename the badge now ("matched to your data"), fix later (§3) |
| Safe-to-spend rests on strong assumptions | `money.get_safe_to_spend` | **True, and the backtest below shows it's too generous** |
| Benchmarks: per-consumption-unit vs one account | DECISIONS 2026-11-13 already caveats | Agree; never say "overspending" from it |
| ASSUMPTIONS.md says September is "last month" | line 60 | **True, fixed on this branch** (August) |
| No README | repo root | **True.** Needs one for judges (§3 step 4) |

## 2. Backtest: does following safe-to-spend keep you safe? [data]
Script: `scripts/analysis/backtest_safe_to_spend.py` (pandas replica of the app's method; basket rules from
DECISIONS.md, one-offs not separated). 300 random customers, 10,200 checkpoints (3 days after each payday and 7 days
before the next, 2025-2026). At each checkpoint: compute safe-to-spend as the app would, then replay what really
happened until the next salary, but replace the customer's everyday extras with spending exactly the safe amount.

| | Result |
|---|---|
| Checkpoints where safe > 0 | 75.6 % (the rest show the "nothing safe" warning) |
| Following it → overdraft before payday | **5.5 %** of positive answers |
| Following it → dips into the "protected" savings | **40.7 %** (median 238 €, p90 1,010 €) |
| Early in the cycle (payday + 3 days) | overdraft 7.2 %, savings dip 49.9 % |
| 7 days before payday | overdraft 2.7 %, savings dip 26.1 % |
| Payday predicted on the wrong date | overdraft 8.2 %, savings dip 51.5 % |
| Negative balance at the checkpoint | never shown a positive amount (good) |
| Median safe amount vs what people actually spent on extras in the same window | 820 € vs 311 € |
(Transfers to investments/other banks excluded from the replay; including them changes the rates by <1 point.)

**Reading:** the number is not "safe" in 4 of 10 cases by its own promise (keep savings untouched), and leads to an
overdraft in about 1 in 18. Main drivers [judgment, to confirm]: averages of essentials/surprises over 90 days
miss lumpy weeks; bills already paid early are subtracted from "typical" but late ones land after the estimate;
payday prediction errors.

## 3. What to change (in order)
1. **Safe-to-spend as a range with its assumptions visible**: "safe: 300-820 €; depends on: rent still to come
   (X), groceries (Y), a surprise buffer (Z), payday on 15 Oct". Use the customer's own weak weeks (e.g. 75th
   percentile of essentials+surprises for the remaining days) for the low end. Re-run the backtest; target:
   savings dip < 10 %, overdraft < 1 % at the low end.
2. **User-owned assumptions** (outside AI's point 1, agreed): "this isn't essential", "that won't repeat",
   "payday moved to the 20th" → recompute on the spot. Store per customer; reset button (shared demo login).
3. **Verification that checks meaning**: carry `{category, subcategory, period, sign}` with every number in
   `_collect`; in `check()` require that the sentence around the number mentions the same category (taxonomy
   names, EN/FI/SV) and period, else status "number found, context not checked". Add 5 traps: right number wrong
   category, right number wrong month, income stated as spending, a sum the model made up, a percentage of the wrong base.
4. **README.md** (draft on this branch): what it is in two sentences, demo path, how to run, evidence (traps,
   backtest), limitations.

## 4. The outside AI's product advice: agree, with two caveats
It proposes narrowing to "my account looks healthy after payday, but I struggle before the next one": a forecast
the user can question ("Can I spend 80 € this weekend?"), change assumptions on, with honest ranges, and a check
that they understood.
- **Agree:** it is the brief's own example ("What is safe for me to spend this week?"), our data supports it
  (half of overdraft moments fall in the last 7 days before payday; payday-week spending +30 %, IDEAS.md), Design E
  already has the forecast graph, and the backtest proves the current number needs exactly this fix.
- **Caveat 1:** it competes with the home planner for the hero slot. Proposal: the payday loop is the everyday
  hero (recurring use, literacy), the home planner is the "big decision" built on the same parts (assumptions,
  range, binding constraint, next question). One method, two horizons.
- **Caveat 2:** "chat with your own data" is what the booth called foundational. Keep the chat as the way the user
  questions the graph, not as a separate screen. (Rasmus is researching the concept; findings will be added.)
