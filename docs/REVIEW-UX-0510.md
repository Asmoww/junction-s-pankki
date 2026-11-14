# UX review of the live app (outside AI, via Rasmus, Sat 14 Nov 05:10) + Rasmus's instruction
> Branch `feature/home-readiness`. **For Asmoww's Claude.**

## Rasmus's instruction to Asmoww's Claude
- **Be extra critical** of this review and of everything on this branch. Push back where it's wrong.
- **Approve and merge nothing on your own.** Ask Asmoww (Pyry) first. The approval test is one question:
  **does the change demonstrate the core concept better?**
- The review's main point: **our biggest weakness is prioritisation**. Important user decisions compete with
  technical proof (traps, verification, live rules) and secondary features (score, game, benchmarks).

## The review (summary, reviewer's own tests on the live app)
Kept as is: green palette, type, rounded cards, bottom nav (fits S-mobiili); the forecast what-if ("Eat out −50 %"
changed the payday forecast 17,324 → 17,440 €, +117 €, redrawn); specific coach answers built on deterministic
`money.py`; the basket exercise with the user's own transactions; Emma's persona (shortfall, zero crossing, warning).

| Priority | Observed problem | Recommended change |
|---|---|---|
| Critical | Learn tab shows the engineering trap suite, including offensive adversarial wording | Move the test report to a separate technical/demo view. Learn = lessons, progress, next steps |
| High | Emma: "Safe this week −676 €" vs forecast "−997 € by payday", unexplained | Show "Available for extras: 0 €"; explain the projected shortfall per spending assumption; same time periods; say why they differ |
| High | "How I worked this out" only says "Calculated safe-to-spend" | Show the real steps: balance − protected savings − bills − essentials − buffer (backend already returns `steps`) |
| High | Balance and graph dominate the first screen; safe-to-spend sits below | Lead with the decision ("What can I spend?" / "What needs attention?"); smaller chart; balance secondary |
| Medium | "Check a purchase": "A bicycle for 600 euros" became shopping results | Two paths: Check an amount / Find a price. A known amount goes straight to an affordability scenario |
| Medium | "Fixed must-pays" includes supermarket spending; the game treats it as definitive | Rename "Regular essentials"; say supermarket trips can include optional items; allow corrections |

Presentation: "Rahakunto 19 — Vulnerable" feels judgmental → "Your budget needs attention" + main reason + one
next step. Graph legend: actual vs forecast, "Today", is the payday point before or after salary. "Biggest day" /
"Another 213 € day" observe without helping → say category or consequence. Live loan rules and Euribor distract
from everyday coaching → move into the home/borrowing flow. "Numbers verified" ≠ "advice verified" → say the badge
checks numerical grounding; forecasts still rest on assumptions.

**Proposed first screen:** this week's spending room → one explanation → one useful action → compact forecast →
three spending baskets.

## Rasmus's Claude: cross-check with our own findings (be critical of these too)
- **Agrees with our evidence:** the safe-to-spend backtest (`docs/REVIEW-RESPONSE.md`) says the number dips into
  protected savings in 40.7 % of positive answers. "Spending room" must be a range with visible assumptions,
  or leading with it makes the weakest number the most prominent.
- **−676 vs −997:** that split is a documented decision (DECISIONS 2026-11-13: "even with no extras" vs "at your
  usual pace"). Labels exist but users don't see why; the fix is UI wording, not a new calculation.
- **Rules card:** already proposed for moving off Home (`review/rasmus-next-build` §2, `docs/HOME_READINESS.md`).
- **Score:** both this review and the earlier benchmark (Saavi won Junction 2020 with financial health; Nordea's
  2026 Financial Health Check) say demote it. Keep it at most as a secondary card with plain wording.
- **Trap suite on Learn:** agree it's critical. Keep it as judge evidence (README, a /proof page), not customer content.
- **Possible conflict:** the reviewer wants a decision-first Home; Pyry chose Design E (graph-first) on purpose
  (DECISIONS 2026-11-14). Ask Pyry; one option is a decision card above a shorter graph.

## Suggested order (Pyry decides)
1. Learn tab: remove the trap suite and adversarial text (Critical, small).
2. Home: spending room as a range + its steps + one action, graph below with legend and "Today".
3. Explain −676 vs −997 in one line each.
4. "Check an amount" path for purchases.
5. Rename basket 1 to "Regular essentials"; corrections allowed.
6. Score and rules card off Home (or demoted).
