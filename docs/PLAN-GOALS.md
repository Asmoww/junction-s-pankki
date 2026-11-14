# Goals with progress (the retention loop): plan
> Part of the Plan tab: see **PLAN-TAB.md** (§1 and §6) for how goals fit with budgets, scenarios, loans and categories.
Rasmus's Claude, Sat 14 Nov 16:50. Rasmus asked: "let the user set a financial goal and see progress to it, as the
retention that brings them back. Wasn't this already part of the plan?"

## Was it planned? Yes. Why nothing was built
- **Planned three times.** BUILD-BRIEF v3 (Sat 00:30): "Save the plan", a Säästäjä goal on one tap, check-ins judged
  *against the plan*. FRAMEWORK-spankki v0.2: the goal ladder "When can I afford X?". Codex's personalisation doc
  (`review/rasmus-research-coach`): "selected goal and protected cash buffer" as explicit user choices.
- **Only one goal type got built:** the home purchase (Ville, `homeplan.py` live; readiness on `feature/home-readiness`).
  It answers "when", but nothing is saved and there is no progress, so it doesn't bring anyone back.
- **Why it slipped:** (1) the plan lived on `review/spankki`, which is never merged, and the port only took the home
  planner; (2) TRACKER.md never had a row for a general goal (only A10, "plan ahead measured from a goal", marked low
  priority), so it fell out of every handoff; (3) progress over time looks impossible to demo with "today" fixed at
  30 Sep 2026, and nobody wrote down the answer to that (below). (2) is Rasmus's Claude's miss.

## Where it fits (VISION.md)
CHANGE: "a budget is a what-if you decide to keep". A goal is the same thing: a saved target on the line. Promise 2
(learns from you): the goal is the person's own choice, kept and shown back. It also gives the Plan tab its first
real content.

## Design
1. **Set it in words or in a sheet.** "I want 3,000 € for a trip by June." Coach tool `set_goal(name, amount, by_date |
   monthly)`, confirmed by the person before saving (anything that changes their plan needs a yes). Stored per device +
   persona like `learning.json` (in production: per customer at the bank).
2. **Feasibility first (the goal ladder).** Needed per month = (amount − saved) / months left. Compare with
   **safe-to-save** (`saving.py`, already live): on track / tight / doesn't fit. If it doesn't fit, say so and show the
   version that fits: the date reachable at safe-to-save, or the amount by that date. If the month itself runs short
   (safe-to-spend < 0), park the goal: "fix the month first". Same check as the S&P 500 bug (`feature/coach-calc`).
   Scenario planner gives the likely and cautious date (p50 / p80) from her own months.
3. **Progress from real money, not clicks.** Saved = transfers to her own accounts since the start date (the same
   rows `saving.py` counts as "already moving"). No manual ticking.
4. **On the line.** The monthly amount shows as a step on payday in the forecast; a thin progress bar under the line on
   Home: "Trip · 1,240 / 3,000 € · on track for May". Tap → the Plan tab.
5. **What brings people back (retention) without punishing them:**
   - payday check-in: "Payday. Move 180 € to Trip?" (push in production; in the demo a card on Home);
   - milestones at 25 / 50 / 75 / 100 %, shown once each;
   - a missed month never resets anything; the coach re-plans the date instead ("June → August, or 40 € more a month");
   - the reward is progress on her own goal, never spending less for its own sake. Goal money is never pushed above
     safe-to-save.
6. **Learning tie-in.** Setting a goal lights the "Saving" corner on the Money Detective map (kind: tried a what-if).

## The fixed-clock problem, solved honestly
"Today" is 30 Sep 2026 and the data ends there, so a goal set today can't move in a 5-minute demo. Two honest options:
- **Replay (recommended):** let the goal start in the past, labelled. "If you'd started this a year ago": progress is
  rebuilt from her real transfers month by month, so the bar and the milestones are real data, and the coach can say
  "you fell behind in March, caught up in June". Label on screen: "Started 1 Oct 2025 (replay)".
- Demo clock: a "+1 month" button that applies the planned transfer to the forecast. Clearly labelled; weaker.

## Effort and order
About 3-4 h: `app/goals.py` (pure core: needed/month, status, progress from rows, replay; unit tests) → API
`/api/goals/{cid}` GET/POST/DELETE → coach tool `set_goal` with confirmation → Home bar + Plan sheet (EN/FI/SV) →
payday card → trap case ("save 10,000 € by December" for Emma must say it doesn't fit and give the version that does).

## Demo (30 s)
Emma: "I want 1,500 € for a trip by next summer." → coach: "At what's safe for you to save (X €/month) that's August,
not June. Or 1,100 € by June." → she picks August → bar on Home under the line → tap → replay: "Since last October
you'd be at 640 €; March was the hard month." Judge sees: own data, honest feasibility, a reason to come back on payday.
