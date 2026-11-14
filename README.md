# S-Bank money coach (Junction 2026, S-Pankki challenge)

A mobile coach inside S-mobiili that lets you talk with your own transactions. Every number in an answer is
computed from the data by code; the AI only picks the calculation and explains it.

## Try it
- Live demo: https://spankki.psavela.com (password from the team).
- Pick a demo customer (Emma, Mikko, Aino, Jussi). They are real synthetic customers from the challenge data with
  invented names.
- Demo path: Home graph (balance since payday + forecast) → ask "What is safe for me to spend this week?" → ask
  "why?" → change one assumption in a what-if → see the forecast move.

## What it does
- Answers questions about your own spending ("taxis last month", "what kind of spender am I").
- Sorts every expense into the brief's three baskets: fixed must-pays, surprise must-pays, everyday extras.
- Safe to spend until payday, payday forecast, what-if cuts, a surprise pot, Statistics Finland comparison.
- Answers in English, Finnish and Swedish.

## Evidence
- Trap suite (`tests/traps/`): questions where money coaches typically fail, run nightly against the live coach;
  results on the Learn tab.
- Number check (`app/verify.py`): every € and % in an answer is matched to a value in the tool results.
  Today this checks the number, not yet its category or period (see `docs/REVIEW-RESPONSE.md`).
- Safe-to-spend backtest (`scripts/analysis/backtest_safe_to_spend.py`): results and limits in `docs/REVIEW-RESPONSE.md`.

## Run locally
See "Stack and how to run" in `CLAUDE.md` (Python 3.12, DuckDB, FastAPI, Anthropic SDK; data is challenge-only
and not in git).

## Limits
Synthetic data, one account per customer, no credit or loan data. Rules from public sources (FIN-FSA, Vero,
Suomen Pankki) are shown with their source and date. Nothing here is S-Bank credit policy or financial advice.

More: `docs/CHALLENGE.md` (brief), `docs/DECISIONS.md` (decisions and why), `docs/ASSUMPTIONS.md` (data quirks).
