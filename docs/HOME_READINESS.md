# Home readiness (Plan tab hero) — branch `feature/home-readiness` (Rasmus's Claude, Sat 14 Nov 04:45)
Built on `feature/context-dev` (needs the Context.dev key on the server, see CONTEXT_DEV.md). Not merged.
Why: both outside reviews (docs/proposals/NEXT-BUILD.md on `review/rasmus-next-build`) say the S-Pankki demo
should be one loop: "Can I buy this home, when, and what is stopping me?", shown as a range with the binding
constraint, every number traceable, life after buying, and one question that changes the plan.

## What's here
- `app/readiness.py`: `assess()` (pure maths, same formula and constants as `homeplan.plan_home`) and
  `home_readiness(cid, price, property_type)` (reads the data + live rules). Returns:
  `range` (earliest / likely / cautious months from the customer's good / typical / weak months; None = not within
  10 years), `reachable_price` (2 and 5 years), `binding` + `also` (deficit → income caps loan → own funds →
  collateral → life after buying), `after_buying` (payment at Euribor + 0.6 % assumed margin and at 6 % stress, room
  after must-pays vs today's extras), `next_question` (re-runs the maths for each candidate answer and picks the one
  that saves most months; falls back to the reachable price or "fix the month first"), `provenance` (rule /
  assumption / data), disclaimer.
- `GET /api/readiness/{cid}?price=250000&property_type=apartment`
- Coach tool `home_readiness` + system prompt rule (lead with the binding constraint, range not date, label the stress
  formula as an assumption, end with next_question).
- `tests/test_readiness.py`: 10 offline tests (incl. savings moved elsewhere, ASP). **Not run here:** test_api / the app itself (no duckdb/fastapi in
  this sandbox). Run `.venv/bin/python -m pytest -q tests` on the server before merging.

## Sanity check (pandas replica of the inputs, rules 95 % / 1.5 % / 3.293 %) — re-check on the server
| | Mikko CUST04588, 250 k | Emma CUST01610, 150 k |
|---|---|---|
| Binding | income caps the loan (~178.7 k) | monthly gap (~407 €/month out more than in) |
| Range | earliest ~99 months; likely/cautious not within 10 y | none (negative pace) |
| Next question | reachable price within 5 years | fix the month first |
| After buying | ~933 €/mo payment (~1,151 at stress); extras don't fit at stress | extras don't fit |
**Check:** the replica's median monthly salary for Mikko is 3,289 €, while SOLUTION.md quoted 4,385 € (likely a
different definition). `plan_home` uses the app's own salary query; compare the two before any number goes on a slide.
If Mikko's 250 k is out of reach, the demo price should be what the tool says is reachable (e.g. ask the 5-year
price), not a number picked for the story.

## UI to build (Pyry's module, not touched here)
Plan tab card, top to bottom: price input (default from persona) → **binding constraint** sentence (big) → range bar
earliest | likely | cautious (or "not on today's pace" + reachable price) → "Life after buying" row (payment,
room left, extras fit yes/no, at stress yes/no) → **next question** as a button that sends it to the coach →
"Where numbers come from" drawer listing rule (with source chip + date) / assumption / bank data → disclaimer.
Move the Live rules card from Home into the drawer.
