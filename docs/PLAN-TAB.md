# The Plan tab: one spec for goals, budgets, scenarios, purchases and loans, and your categories
Rasmus's Claude, Sat 14 Nov 16:55. Supersedes the scattered pieces: NEXT-BUILD.md §4 (`review/rasmus-next-build`),
PLAN-SCENARIOS.md, PLAN-GOALS.md, HOME_READINESS.md "UI to build", tracker rows A10, A11, C2, C3, C4, F1, F5.
Approval: ask Asmoww; the test is "does it demonstrate the core concept better?". No feature-freeze planning (Rasmus).

## Why one tab, and what it is
Home shows where your money is heading. Coach answers questions about it. **Plan is where you decide what you want
it to do, and keep that decision.** In VISION.md terms it is CHANGE made permanent: a what-if you decide to keep.
Every section below saves a change to the same forecast line, so they share one engine (`future.simulate` plus the
scenario planner) and one rule: nothing in a plan may push the person below their safe-to-save.

Tabs become: Home · Coach · **Plan** · Learn.

## Rasmus's instructions, checked
| Rasmus asked (when) | Where it is in this spec | Status before this doc |
|---|---|---|
| Financial planner for purchases **and loans** (Fri/Sat) | §4 Big purchases and loans: any purchase, any loan, home | Home only (live + `feature/home-readiness`); no general loan planner |
| Budgeting tool: budget per **category** and for the **whole** month (Sat) | §2 Budget | Proposed in NEXT-BUILD §4, then cut to "one line" by the outside-review reconciliation (see note) |
| Categorise spending (auto, user can change) + **how regular** (one-time etc.) (Sat) | §5 Your categories | Proposed (C4), never built; Sort with the AI covers only unclear buys |
| Planner/budget in **its own tab** (Sat) | This whole doc | Proposed (C2), never built |
| Advanced, robust **scenario planning**: suggested from spending habits and income sources, assumptions clear, user can play with them (Sat) | §3 Scenarios | Engine + API + coach tool on `feature/home-readiness` (F5); no UI |
| **Goal with progress** as the retention that brings people back (Sat 16:44) | §1 Goals + §6 the payday loop | Planned in BUILD-BRIEF v3, never a tracker row, never built |
| Gamified learning (Sat 16:36) | §7 ties Plan actions to the Money Detective map | Built on `feature/learning-progress` |
| Investment-style "X a month at R %" must be calculated right and flagged when it doesn't fit (Sat 16:40) | §3 and §4 use the same feasibility check | Fix on `feature/coach-calc` |
| Rules card off Home (Sat) | §4: rules and sources live inside the home planner | Small entry on Home on `feature/home-readiness` |
| 4 of 8 metrics; link them to the coach (Sat) | §8: "plan ahead" measured from Plan | OPEN (A10) |

**Note on the cut:** NEXT-BUILD §6 proposed shrinking the budget to one line and moving recategorising to "if time",
because two outside reviews warned about "five products in one app" and a freeze. Rasmus has since said not to plan
around freezes and asked for these again, so this spec restores them. The way to answer the "five products" risk is
that they are one product: five ways of keeping a change to the same line, all on one engine.

## §1 Goals (the retention hook)
- Set in words ("1,500 € for a trip by next summer") or in a sheet: name, amount, date or monthly amount.
  The coach proposes, the person confirms (a plan never changes without a yes).
- **Feasibility first:** needed per month vs safe-to-save → on track / tight / doesn't fit, and the version that
  fits (later date or smaller amount). If the month itself runs short, the goal waits ("fix the month first").
- **Progress from real money:** transfers to her own accounts since the start date (the rows `saving.py` already
  counts). No manual ticking.
- On the line: the monthly amount is a step on payday; a bar under the line on Home links here.
- **Fixed demo clock:** a goal may start in the past, labelled "replay"; progress is rebuilt from her real transfers
  month by month ("you'd be at 640 €; March was the hard month").
- Details: PLAN-GOALS.md.

## §2 Budget: the whole month and per category
Basket-shaped, so it teaches the brief's three baskets instead of being a generic envelope app.
- **Whole month:** income − goal saving − basket 1 (forecast from bills, not budgeted) − basket 2 (surprise pot,
  suggested from her 12-month average) = what's left for everyday spending. That number is the same as
  safe-to-spend, so the app never shows two "you can spend" numbers.
- **Per category:** caps on any category she picks (restaurants, taxis, clothes…), shown as bars for this month with
  "at your usual pace you'll end at X".
- **Suggest a budget:** computed from her own months, then backtested: "you'd have stayed inside it in 7 of the last
  12 months". The coach explains; code computes.
- Going over a cap: one note on the line and in Coach, never a red alarm. Next month starts fresh; nothing is lost.

## §3 Scenarios (advanced, suggested, assumptions you can touch)
Engine on `feature/home-readiness` (`app/scenarios.py`, `/api/plan`, coach tool `plan_scenario`): Monte Carlo over
her own months, bad / typical / good, common random draws so scenarios compare fairly.
- **Suggested from her own data:** e.g. "the gap before payday", "irregular income", "lumpy surprises", "room to
  save", picked by what her data shows, with the reason in one line.
- **Every assumption visible and editable:** income, must-pays, surprises vs her past, cut extras %, cut per
  category %, save on payday, one-offs. Each shows its source (her data, a rule, or "your choice").
- **Play:** sliders move the range on the line live.
- **Keep it:** a scenario can become a budget (§2) or a goal (§1). That's the "what-if you decide to keep".
- Growth plans ("X a month at R %"): computed exactly (`calculate` with `**`, `feature/coach-calc`), return labelled
  as an assumption, then checked against safe-to-save and income.

## §4 Big purchases and loans
One flow for anything big: "Can I afford X?" / "What would a loan for X cost me?"
- **Purchase:** live price read from the shop's page (Context.dev, live), dropped on the line.
- **Loan (new, general):** amount, term, interest (default: today's rate for that loan type, sourced; editable) →
  monthly payment (annuity), total interest, and the line with the payments on it. Feasibility: payment vs
  safe-to-save and vs her basket-3 room; if it doesn't fit, the term or amount that would. No product advice;
  "talk to S-Bank" for an offer.
- **Home:** readiness (range, binding constraint, life after buying, next best question, provenance) from
  `feature/home-readiness`; loan cap, Euribor and transfer tax with sources live here, not on Home.
- Every result has **Add as goal**.

## §5 Your categories (correct the app, it learns from you)
- On any transaction (Coach lists, Home notes, Wrapped): **Change category** and **How regular?**: every month /
  now and then / one-time / everyday. Apply to "this one" or "everything like it".
- One-time items leave the averages, so one holiday doesn't inflate "usual" spending forever.
- One override table read by every money query, so Home, Coach, budgets and scenarios agree. Sort with the AI writes
  to the same table. In chat: "taxis are essential for me" → preview → confirm → saved.
- Plan shows the list of her rules with undo and reset (the demo login is shared).

## §6 The payday loop (why people come back)
On payday (a push in S-mobiili; a card on Home in the demo), one screen:
1. "Payday. Move 180 € to Trip?" (goal) — one tap.
2. Last month vs budget: two lines, one fact each, no scolding.
3. This month's budget restarts; the forecast line shows the month ahead.
Milestones at 25 / 50 / 75 / 100 % of a goal. A missed month re-plans the date; nothing resets. Rewards are progress
on her own goal and new understanding, never spending less for its own sake.

## §7 Learning tie-in
Plan actions light the Money Detective map: setting a goal or budget → "Saving"; keeping a scenario → "What-ifs";
a loan or purchase check → "Big decisions"; a category fix → "The three baskets" (kind: corrected).

## §8 Money fitness score
"Plan ahead" becomes measured from Plan: 100 if she has a goal or budget and stayed on track last month, 50 if set,
0 if none. That takes the score from 4 to 5 of 8 measured parts, and each part links to the Coach with context.

## Build order (each step ships on its own)
| # | Step | Done when | Effort |
|---|---|---|---|
| 1 | Plan tab shell + §4 home and purchase moved in + rules card here | Home has no rules; Plan opens the planner | 1 h |
| 2 | §1 Goals: `app/goals.py` (pure, tested), `/api/goals`, coach tool `set_goal` with confirm, Home bar, replay | Emma's trip goal: feasibility, bar, replay | 3 h |
| 3 | §3 Scenarios UI on the existing engine; "Keep it" → goal | sliders move the range; assumptions sourced | 2-3 h |
| 4 | §2 Budget: whole month + category caps, suggest + backtest | Emma and Mikko: suggestion with "N of 12 months" | 3 h |
| 5 | §4 Loan planner (general) | car loan for Emma: payment, interest, fits / doesn't | 1.5 h |
| 6 | §5 Your categories + regularity, one override table | a change moves Home, Coach and budget consistently; traps pass | 3 h |
| 7 | §6 payday card, §8 score part | payday card on Home; score shows 5 of 8 | 1.5 h |
Trap suite and verified numbers must pass after each step. Add traps: a goal above safe-to-save, a loan she can't
carry, "save 10,000 € by December".

## Demo (60 s inside the 5-minute pitch)
Plan tab → Emma: "1,500 € for a trip by June" → "At what's safe for you, that's August. Or 1,100 € by June." → keeps
August → slide "cut restaurants 30 %" in Scenarios → August becomes June → Keep it → bar under the line on Home →
replay: "since last October you'd be at 640 €". One line, her own data, a reason to open the app on payday.
