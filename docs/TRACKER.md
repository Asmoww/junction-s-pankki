# Tracker: everything Rasmus's side has proposed or built since Fri 13 Nov (S-Pankki)
> Rasmus's Claude, Sat 14 Nov 11:35. **Single list for Asmoww's Claude.** Checked against `origin/feature/context-dev`
> eae8ccf and `origin/main` 64058bf. Approval rule: ask Pyry; the test is "does it demonstrate the core concept better?".
> Status: **DONE** (in Asmoww's code) · **ON BRANCH** (built on `feature/home-readiness`, waiting for merge) ·
> **OPEN** (proposed, not built) · **PYRY** (needs Pyry's decision).
> Older proposals sit on branches your Claude doesn't read; their content is summarised here with the link.

## A. Home screen (Design E)
| # | Item | Status | Where it's described |
|---|---|---|---|
| A1 | **Move the "Live rules" card (loan cap, Euribor, finanssivalvonta.fi) off Home** into the home planner / Plan view. A regular user doesn't need it on the front page; outside UX review agrees. Still on Home in `e.js` (line ~280) | **OPEN** (you agreed to demote) | `review/rasmus-next-build` docs/proposals/NEXT-BUILD.md §2; this branch docs/REVIEW-UX-0510.md |
| A2 | Rules card attribution: Euribor is published by Suomen Pankki (EMMI), not FIN-FSA; one source chip + date per value; "95 % for all" is **temporary** (FIN-FSA 30 Jun 2026 release) | **OPEN** | NEXT-BUILD.md §2; docs/RESEARCH-NEXT.md F3 |
| A3 | Score name per UI language: EN still says "Rahakunto" (`e.js` hk.name). Proposal: en "Money fitness", fi "Rahakunto", sv keeps "Pengakondition" | **OPEN** | NEXT-BUILD.md §0c |
| A4 | Demote the score; plain wording ("Your budget needs attention" + reason + one step) instead of "19 Vulnerable" | **PYRY** (you agreed to demote) | docs/REVIEW-UX-0510.md |
| A5 | Decision first: "spending room" (as a range, with its steps) + one action above a shorter graph | **PYRY** | docs/REVIEW-UX-0510.md; docs/REVIEW-RESPONSE.md §3.1 |
| A6 | Graph legend: actual vs forecast, "Today" line, is the payday point before or after salary | **OPEN** | docs/REVIEW-UX-0510.md |
| A7 | Trend chart ranges Week / Pay period / Year / 2 years + y-axis gridlines, last-value label | **OPEN** | NEXT-BUILD.md §1 |
| A8 | Explain −676 € ("even with no extras") vs −997 € ("at your usual pace") in one line each | **OPEN** | docs/REVIEW-UX-0510.md |
| A9 | Every score bar and "What would lift it" step opens Coach with context `{part, value, target, gap_eur, points}` | partly DONE (steps have askQ); bars **OPEN** | `review/rasmus-health-score` docs/proposals/HEALTH-SCORE.md; NEXT-BUILD.md §3 |
| A10 | "4 of 8 measured": 3-question check-in (debt, insurance) + "plan ahead" measured from a budget/goal → 7 of 8 | **OPEN** (lower priority) | NEXT-BUILD.md §3 |

## B. Coach and numbers
| # | Item | Status | Where |
|---|---|---|---|
| B1 | A refused message no longer blocks later questions (`refused` flag, `_drop_refused`, refusal log line) | **ON BRANCH** (you recommended merge) | docs/REVIEW-BROWSER-TESTS-0523.md |
| B2 | Weekly vs payday figure from one scenario | **DONE** 6ad3248 | — |
| B3 | Badge wording "numbers matched to your data" | **DONE** 6ad3248 | — |
| B4 | Meaning check in `verify.py` (category, period, sign) + 5 traps | **OPEN** (after demo-critical items) | docs/REVIEW-RESPONSE.md §3.3 |
| B5 | Slider 60 % clamp | **DONE** 6ad3248 | — |
| B6 | Widget must follow the scenario the answer states (it shows the last `simulate_cut`, e.g. restaurants while the answer was all extras) | **OPEN** | docs/REVIEW-BROWSER-TESTS-R2-1107.md |
| B7 | Averages over months with data only (Jan-Dec 2024 was divided by 12) | **ON BRANCH** | same file; tests/test_period_coverage.py |
| B8 | "Check a purchase": "a bicycle for 600 €" became shopping results; add "Check an amount" path | **OPEN** | docs/REVIEW-UX-0510.md |

## C. Home purchase (the booth's ask)
| # | Item | Status | Where |
|---|---|---|---|
| C1 | `home_readiness`: range, binding constraint, life after buying, next best question (money elsewhere, ASP, cheaper, save more), provenance; coach tool + `/api/readiness`; `plan_home` off the coach's tools | **ON BRANCH** (your review applied in 08cbb1e) | docs/HOME_READINESS.md |
| C2 | Plan view/tab that uses `/api/readiness` (nothing in the UI uses it yet) + rules card moved there (A1) | **OPEN** | docs/HOME_READINESS.md "UI to build"; NEXT-BUILD.md §4 |
| C3 | Budget folded into the plan ("monthly room after buying", basket-3 budget, backtest) | **OPEN** | NEXT-BUILD.md §4.1 |
| C4 | Recategorise / regularity tag (monthly, now and then, one-time, everyday), one override table, reset | **OPEN** | NEXT-BUILD.md §4.4 |

## D. Learn tab and evidence
| # | Item | Status | Where |
|---|---|---|---|
| D1 | Offensive trap wording hidden from customers | **DONE** 6ad3248 | — |
| D2 | Move the whole trap report to a `/proof` view; Learn = lessons, progress, next steps | **PYRY** (demo script uses it at 2:30) | docs/REVIEW-UX-0510.md |
| D3 | README for judges | **ON BRANCH** | README.md |
| D4 | Rename basket 1 "Regular essentials"; supermarket can include optional items; allow corrections | **OPEN** | docs/REVIEW-UX-0510.md |
| D5 | ASSUMPTIONS.md "last month" = August | **ON BRANCH** | — |
| D6 | Safe-to-spend backtest against `money.get_safe_to_spend` with a movable today (replica said savings dip 40.7 %) | **OPEN** (Rasmus's Claude can do it) | docs/REVIEW-RESPONSE.md §2 |

## E. Research and pitch (reference, no code)
docs/RESEARCH-CHAT-WITH-YOUR-DATA.md (what the booth's "chat with your own data" should mean: control, correction,
provenance) · docs/RESEARCH-NEXT.md (ASP 2026 rules, Nordea already has budgets + health check, OmaSP deal) ·
two Mikkos: Ville CUST04138 is the home demo (you already did this in personas).

## Suggested next 5 (Pyry decides)
1. Merge this branch (B1, B7, C1, D3, D5).
2. A1 + A2: rules card off Home, correct sources.
3. A3: score name per language.
4. B6: widget follows the answer's scenario.
5. C2: a small Plan view on `/api/readiness` for Ville.
