# Plan: scenario planning that suggests, explains and lets people play (Rasmus's request, 14 Nov 11:42)
> Branch `feature/home-readiness`. **For Asmoww's Claude.** Backend + tests done; UI not built (spec below).

## What it is
Months ahead (3-36), not just to payday (`future.simulate` keeps doing the pay month). Built from the customer's
own last 12 full months: salary, irregular other income, fixed must-pays, lumpy surprise must-pays, extras by
category, and money already moved to savings / another bank (counted as saving, not spending).

**Robust:** Monte Carlo (400 futures, fixed seed). Each simulated month re-draws one of the person's real months for
surprises, extras mix and other income, so repair months and irregular income produce a range: bad / typical / good
(10th / 50th / 90th percentile) and the chance the account goes below zero. Baseline and scenario share the same
draws, so the difference is the lever, not noise. Money you can't move isn't moved (no saving into overdraft).

**Clear assumptions:** `assumptions` lists every input with value, unit, source ("your data: last 12 months,
median", "your edit", "default") and, for levers, min/max/step. Unknown settings and categories are reported in
`notes`, out-of-range values are clamped and reported, never silently ignored.

**Suggested from the person's habits and income** (`suggestions`, each with `why` from their data and its effect):
close the monthly gap (cuts on their biggest extras; if > 50 % is needed it says "halve them: closes N % of the
gap"), cut the biggest extra by 20 %, save on payday (only the amount *beyond* what they already move), other income
stops (if ≥ 8 % of income is non-salary), a repeat of their biggest surprise month (if surprises are lumpy and the
biggest ≥ 200 €), rent +5 % (if housing ≥ 100 €/month). Ordered by relevance to their situation, then effect size.

**Levers the user plays with:** months ahead · salary change % · other income that continues % · change in fixed
must-pays € · surprises vs your past % · cut all extras % · cut per category % · save on payday € · one-offs
(month, amount, label).

## API and coach
- `GET /api/plan/{cid}` → baseline + assumptions + suggestions. `POST /api/plan` `{customer_id, levers}` → re-run.
- Coach tool `plan_scenario(levers)`: "what if I get a 3 % raise and rent goes up 50 €?" → the model sets only the
  levers mentioned; code computes; the answer names the assumptions used. The AI chooses scenarios, never computes.
- Pure core `run / suggest / assumptions` in `app/scenarios.py`; tests `tests/test_scenarios.py` (8): identical
  baseline when nothing changes, ordered ranges, saving moves money not spends it, clamping + notes, every assumption
  sourced, suggestions follow the situation (gap / irregular income / lumpy surprises / safe-to-save), lumpy
  surprises widen the range, no double saving.

## Persona check (pandas replica of the same profile; re-check via the API)
| Persona | Account in 12 months (bad / typical / good) | Below zero | Top suggestions |
|---|---|---|---|
| Emma 23 | −3,863 / −1,768 / +149 € | 94 % | Halve Entertainment, Restaurants, Lifestyle: closes ~71 % of the gap (+3,733 €, below zero 94 % → 8 %) · a 416 € surprise · Entertainment −20 % |
| Mikko 40 | 20,638 / 22,599 / 24,285 € | 0 % | A 556 € surprise · Lifestyle −20 % (+789 €) · rent +5 % |
| Aino 22 | 13,545 / 15,702 / 18,249 € | 0 % | Move 90 € more on payday (already ~115 €) · Restaurants −20 % |
| Jussi 32 | 5,988 / 6,645 / 7,359 € | 0 % | Move 420 € to savings on payday · (his sweep to another bank is already counted) |
| Ville 32 | 23,747 / 26,753 / 29,280 € | 0 % | Move 420 € on payday (+5,040 € saved) · a 520 € surprise · Restaurants −20 % (+872 €) |

## UI to build (Plan tab; Pyry's module)
1. Top: "Your next 12 months" band chart (bad-typical-good shaded, today's line, zero line) + one sentence:
   "Typical: X € in 12 months; in 1 of 10 futures below Y". Chance below zero as a chip if > 0.
2. "Try these" cards from `suggestions`: title, why (one line), effect ("+3,733 € · below zero 94 % → 8 %").
   Tap = apply levers; the band redraws with baseline ghosted.
3. "Your assumptions" drawer: every row from `assumptions` with its source; levers as sliders/steppers within
   min/max; category cuts as a list of the person's own categories; "Add a one-off" (month, amount, label).
   Edited rows show "your edit" and a reset.
4. "Ask the coach about this plan" passes the current levers. Answers come from `plan_scenario`.
5. Home readiness (C1) and safe-to-save (F1) live in the same tab: one place for "what should be".
