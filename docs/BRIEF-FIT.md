# Does the solution meet the S-Pankki brief? Gaps, fixes, and how we stand out
> Rasmus's Claude, Sat 14 Nov 12:15, branch `feature/home-readiness`. **For Asmoww's Claude and Pyry.**
> Read against `docs/CHALLENGE.md` and the live app (via `origin/feature/context-dev` eae8ccf + this branch).
> Scores are my judgment (1-5), not measured.

## 1. What the brief literally asks for, and where we are
| Brief asks | Status |
|---|---|
| Chat with your own money: simple ("taxis last month") to deep ("what kind of spender", "safe this week", "save if dining −20 %") | **Yes.** All four example questions work; numbers come from tools |
| Three baskets as the pedagogical angle | **Yes** (baskets, sort game). Weak spot: basket 1 counts all supermarket spending as mandatory; users can't correct it (TRACKER D4, C4) |
| Help people see where money really goes; MyData: explore freely, not fixed charts | **Partly.** Chat + `show_chart` + what-ifs explore freely, but the user can't correct or own the data (no recategorise, no "won't repeat", no editable assumptions) |
| Plain-language explanations of financial concepts | **Partly.** Answers explain; "How I worked this out" shows only a label, not the steps (UX review). No concept lessons on Learn |
| What-if scenarios | **Yes** (strong: forecast redraws, +117 € example) |
| Guide to healthier habits: **safe-to-spend and safe-to-save** | Safe-to-spend **yes, but too generous** (replica backtest: dips into protected savings in 40.7 % of positive answers). **Safe-to-save was missing entirely; now on this branch** (§3) |
| Young adults especially | **Personas yes** (Emma 23, Aino 22); nothing in the product is aimed at a first-job situation beyond that |
| Optional: PSD2 multi-bank view | **Signal only** (Jussi's sweep; readiness asks about money elsewhere). No consent / aggregation story on screen |
| Output: mobile or embeddable web app | **Yes** (S-mobiili-like webview) |
| "No Finnish bank yet lets customers chat with their own data" | This is the opening S-Pankki gave us: **chat is the product, not something to avoid** |

## 2. Scorecard against the five criteria (20 % each)
| Criterion | Now | Biggest gap | Fix that moves it most |
|---|---|---|---|
| Financial literacy impact | 3 | We show numbers; we don't show that a user *understood* something | One learning loop: question → steps shown → change one assumption → one-line check ("why isn't all of your balance spendable?"). Safe-to-save (§3) teaches "pay yourself first" |
| Originality of AI integration | 3 | Tool-grounded chat is now common (Revolut AIR, Starling, Nordea) | The AI *questions the graph with you* and asks the one question that changes the answer (next-best-question, already in readiness); every number traceable |
| Clarity of mobile UX | 3 | Home leads with balance + graph; cards compete (score, rules, wrapped, benchmark) | Decision first: "This pay month: spend X-Y, save Z" above a shorter graph; one card row; score and rules demoted (A1 done) |
| Feasibility | 4 | Safe-to-spend not calibrated; "verified" meant matched | Range instead of a point; run the app backtest (D6); meaning check later (B4) |
| Fit to S-mobiili | 3.5 | No story for identity, consent, where data and model run | One slide + README section: inside S-mobiili session (no new login), consent screen per data source (PSD2), data stays in the bank, EU-hosted model, AI Act Art. 50 notice, fallback when AI is down |

## 3. Built now: safe to save (`app/saving.py`, tool `get_safe_to_save`, `GET /api/safe-to-save/{cid}`)
"How much can I move to savings on payday without running short before the next one?" For each of the customer's
last 12 pay months: the lowest point of that month's own money (balance minus savings carried in; transfers to own
savings added back), minus a buffer = their own monthly average of surprise must-pays. Safe = fits in ≥ 3 of 4
months (25th percentile), rounded down to tens; stretch = about half. Pay months start at the salary row, not the date.
Persona check (pandas replica of the same method, re-check via the API):
| | Safe on payday | Stretch | Months it fits | Story |
|---|---|---|---|---|
| Emma 23 | 0 € | 0 € | 2/12 | Close the monthly gap first (why_zero) |
| Mikko 40 | 0 € | 190 € | 6/12 | Big repair months eat the room: the surprise pot matters |
| Aino 22 | 210 € | 500 € | 9/12 | Already invests ~115 €/month; could do more |
| Jussi 32 | 1,990 € | 2,300 € | 9/12 | Already moves more than this (already_note) |
| Ville 32 | 420 € | 940 € | 9/12 | Feeds the home plan |
Tests: `tests/test_saving.py` (5). UI not built: a line under safe-to-spend: "Safe to save on payday: 210 € (fits 9
of your last 12 months) › set up".

## 4. How we stand out (what others at Junction will most likely build)
Most teams will build: chat over transactions + category charts + baskets + a safe-to-spend number + maybe a score.
Our differentiators, in order of strength:
1. **The forecast is the conversation.** You see where your balance is heading before payday, ask why, change one
   thing, and the line moves. (Others answer questions; we show consequences.)
2. **Every number is provable, and we say what we don't know.** Tools compute, a checker matches, a trap suite
   attacks it nightly, and assumptions/ranges are shown. Bank-grade trust is S-Pankki's real problem with AI.
3. **Your data, your corrections** (MyData made concrete): mark "not essential", "won't repeat", "payday moved";
   the coach recomputes. Not built yet (C4): the cheapest strong differentiator left.
4. **Spend and save as one decision** for the pay month (safe-to-spend + safe-to-save), and a path to big decisions
   (home readiness: what blocks you and the one question that changes it).
5. **Live public rules with sources** (Context.dev) where they matter, not on Home.
One sentence to test: "S-mobiili's coach shows what your money will do before payday, lets you question and correct
it, and proves every number." If a judge can repeat that, we're differentiated.

## 5. Recommended order (Pyry decides; each item: does it demonstrate the core concept better?)
1. Merge this branch (refusal, coverage, readiness, safe-to-save, slider, rules card, README).
2. Home decision line: "This pay month: spend up to X (range), save Z on payday" + "How I worked this out" with the
   real steps (backend already returns them).
3. Corrections (C4) on 2 things only: "not essential" and "won't repeat"; recompute safe-to-spend live.
4. One learning check after a what-if or a "why" answer.
5. S-mobiili integration slide/README section (identity, consent, data boundary, AI notice, fallback).
6. Run the app backtest (D6); if the dip rate is high, show safe-to-spend as a range.
