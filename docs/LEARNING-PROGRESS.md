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

## 5. Critical review (16:40): rewarding *wanting* to learn, within this challenge
The brief's insight asks for a coach that "explains financial concepts in plain language" and judges "impact on
financial literacy". The question Rasmus raised is sharper: reward the person for *wanting* to learn about their own
money, not for finishing our homework.

**What's wrong with the quest-only design (mine and Codex's):**
- Three fixed quests feel like homework. They reward doing *our* questions, not asking *yours*. The brief's MyData line
  ("explore their own data freely rather than fixed charts") points the other way.
- Revisit-after-3-days and weekly goals can't be shown honestly in a 2-day demo where "today" is fixed at 30 Sep 2026.
  Showing them needs a labelled demo clock, or they stay a roadmap slide.
- A quest reward measures completion, not understanding. Judges can't see learning from a badge.

**What fits better, and is now on this branch:**
1. **Curiosity map.** Every coach tool belongs to one money concept (9: where money goes, baskets, spending room,
   irregular costs, what-ifs, payday and forecast, how you compare, big decisions, saving). `coach.chat` now returns
   `concepts` for each answer. The UI records five kinds of curiosity per concept: asked, opened the steps, tried a
   what-if, corrected a basket, guessed before a reveal. Each (concept, kind) counts **once, ever**, so repeating a
   question earns nothing; looking into a new corner of your own money lights it up. This rewards the person's own
   questions inside the normal chat, which is the product.
2. **Guess first, then see.** Any reveal (quest, Wrapped's top-extra game, a "guess first?" chip in chat) can record a
   guess. The summary shows "earlier off by 62 %, lately off by 15 %" once there are 4 guesses. That's a learning
   signal judges can watch improve inside one demo session, and it's the honest literacy metric: your sense of your
   own money getting sharper.
3. **Quests stay** as the optional "check yourself" on a lit concept (q1-q3), with feedback and retry.
4. **Weekly goal counts any learning** (quests or newly explored concepts); nothing resets.
**Guardrails kept:** no reward for spending less, earning more, buying products or sharing more data; nothing touches
the money-fitness score; progress has no euros; hide / pause / reset always there.

**Within the challenge constraints:** synthetic data and one shared login → progress per device id + persona;
"today" fixed → no fake streaks; S-mobiili → in production the bank stores progress per customer. Idea for the pitch
only (not built): S-Group's Bonus system could recognise learning milestones, never money outcomes; needs a
compliance check before anyone promises it.

**Demo (30 s):** ask the coach "Why am I short this month?" → the Spending room chip lights up → tap "How I worked
this out" → second kind lit → "Guess first: what share went to extras?" → reveal → "Earlier off by 40 %, now 10 %".

**UI to build (small):** a 9-dot curiosity map on the Learn tab (dots fill per kind seen); post
`/api/learn/{cid}/curiosity` with `{device, event_id, concept, kind}` after each coach answer (`concepts`), on "How I
worked this out", on a what-if, on a Sort answer; post `{metric, guess, actual}` after any guess game.
Tests: `tests/test_learning.py` (12; curiosity can't be farmed, tools map to concepts, guesses get sharper, all
languages).
