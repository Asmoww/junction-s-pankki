# Audit + build: gamified retention ("Money Detective") — Rasmus's Claude, Sat 14 Nov 16:10
> Branch `feature/learning-progress`, cut from `feature/context-dev` e4b919a so it ports cleanly. **For Asmoww's
> Claude.** Approval: ask Pyry; the test is "does it demonstrate the core concept better?".

## 1. Audit of recent changes (feature/context-dev 11:05 → 15:45, 22 commits)
**Shipped by Asmoww, relevant to learning/retention:** Sort with the AI (a2984cb: customer sorts unclear items into
baskets, answers saved per customer, undo/reset) · Play your next two weeks (ad0e393: card game over predicted days,
choices move the forecast) · Wrapped with a guess-your-top-extra game (f15ff59) · Learn tab as three calm cards
(fb872e0) · safe to save (3b396ee, ported from our branch) · PSD2 full picture (e4b919a) · EU mode, voice, graph work.

**Codex's gamified learning proposal** (`docs/GAMIFIED-LEARNING-RESEARCH.md` and F8 in
`docs/CUSTOMER-EXPLORATION-PERSONALISATION-LEARNING.md` on `review/rasmus-research-coach`):
| Proposal element | In the code? |
|---|---|
| Predict → evidence → explain → feedback loop | **Partly**: Wrapped guess and Play choices predict/act, but nothing checks understanding |
| Concept progress: explored / explained / revisited | **No** |
| First try vs assisted recorded separately | **No** |
| Revisit with a new equivalent question after 3 days (transfer) | **No** |
| Weekly goal the person picks, no streak reset | **No** (Wrapped shows a no-spend streak: that rewards a money behaviour, not learning) |
| Private milestones, points hidden by default, hide/pause/reset/practice | **No** |
| Idempotent server-side award ledger, per-device/persona isolation | **No** |
| Never reward money outcomes, products or data sharing | n/a (nothing to reward yet) |
**Verdict: not implemented.** The games Asmoww built are strong *activities*; what's missing is the retention and
proof-of-learning layer around them. Nobody has replied to Codex's F6-F8 packages on PR #1 yet.

**Also still not ported from `feature/home-readiness` (PR #1):** refusal recovery (`_drop_refused`), averages over
months with data (`months_with_data`), slider follows the answer (`_pick_cut`), "Money fitness" in English, the Home
rules card demotion (the "Live rules" card with finanssivalvonta.fi is **still on Home**), home readiness,
scenario planner. See `docs/TRACKER.md` there.

## 2. Built on this branch (backend + tests; UI not built)
`app/learning.py`, endpoints in `app/main.py`, tests `tests/test_learning.py` (8 pass locally, db/AI stubbed).

**Three quests, one concept each, built from the person's own numbers** (or `practice=true` for a fixed case):
| Quest | Predict (never scored) | Evidence | Concept check (scored, feedback, retry) | Revisit after ≥ 3 days (new example) |
|---|---|---|---|---|
| q1 Follow the money | share of spending on everyday extras (bands) | `get_three_baskets` last 3 months | "Moving 200 € to your own savings: is it spending?" | "Which is an everyday extra: rent / dentist / takeaway?" |
| q2 Balance isn't spending room | how much of your balance is free until payday | `get_safe_to_spend` steps | "Why is the free amount smaller than your balance?" | "Balance 900, rent 600 unpaid, groceries 150: how much is free?" |
| q3 Plan for the irregular | in how many months a surprise must-pay hit | `insights.surprise_pot` | "Why put aside X € every month for costs that don't come monthly?" | "Phone screen 240 € every two years: fair monthly pot?" |
Right answers and numbers are code; no AI. All strings EN/FI/SV.

**Progress (`state/learning.json`, key = device id + persona, never global):**
not explored → explored (guess made) → explained (check right; `first_try` true/false) → revisited (transfer
question right, ≥ 3 days later). Weekly goal 1-3 quests, counted per ISO week; a missed week resets nothing.
Milestones at 1/2/3 explained: First insight / Pattern explorer / Thoughtful planner. Points (5/10/5) only if
`show_points`. Settings: hide rewards, pause prompts, weekly goal; `DELETE` resets. Replayed `event_id` = no change.
The summary contains no euros, balances or scores (test).

**API:** `GET /api/learn/{cid}?device=&lang=` (summary) · `GET /api/learn/{cid}/quest/{q1|q2|q3}?lang=&practice=&revisit=`
· `POST /api/learn/{cid}` `{device, quest, step: predict|check|revisit, choice, event_id, lang}` → feedback ·
`POST /api/learn/{cid}/settings` · `DELETE /api/learn/{cid}?device=`.

## 3. UI plan (Pyry's module; smallest version that demos well)
1. **Learn tab top:** "Money Detective · 1 of 3 explained · this week 1/2" + three concept chips (grey / half / full /
   star). Device id = random UUID in localStorage (shared demo login).
2. **Quest sheet (60-90 s):** guess chips → reveal card with the real number and "Show the evidence" (opens the same
   tool view the coach uses) → concept question → feedback; wrong = explanation + retry. End: "Explained ✓".
3. **Home nudge (one line, only if not paused):** "A 60-second Money Detective is waiting" or "Revisit: 1 concept".
4. **Hooks into what exists:** after Play your next two weeks → offer q2; after Sort with the AI → q1; on the
   surprise card → q3. The coach can say "Want to try the 60-second quest on this?" (no new tool needed).
5. **Settings row:** Hide rewards · Pause prompts · Weekly goal 1/2/3 · Reset · Practice data.
Demo line: "We don't just show your numbers; we check you understood them, and come back three days later with a
new example."

## 4. Before claiming impact
Measure on a few testers: first-try rate and revisit success (transfer), plus "did this feel judging?". Report it as
a small usability sample, not proof of literacy gains (Codex's caution stands).
