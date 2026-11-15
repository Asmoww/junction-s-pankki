# S-Bank money coach: see your money's future, and change it (Junction 2026, S-Pankki challenge)

A mobile coach for S-mobiili that lets you talk with your own transactions and shows where your money is heading,
not only where it went. Every number is computed from the data by code; the AI picks the calculation and explains it.

## Try it
- Live demo: https://spankki.psavela.com. Pick a demo customer: Emma (23, first job, short
  before payday) carries the story; Mikko, Aino, Jussi (salary moves to another bank) and Ville (saving for a home).
  They are synthetic customers from the challenge data with invented names.
- Five-minute path: `docs/DEMO.md`, section P.

## What it does
- **Home, led by the AI:** one sentence on where your money stands (written by the AI, every number checked), three
  questions about your own money picked for you this week and answered right there, and "why?" on anything on the
  graph. No chat box needed; the cards below are ordered for you.
- **The line:** your balance since payday and the forecast to the next one, with bills as steps, AI notes on the
  line, and a zoom out to 3 months, 12 months and 2 years.
- **Ask:** a coach in English, Finnish and Swedish that answers from your own data with charts ("taxis last month",
  "what kind of spender am I", "what is safe to spend this week", "save if I cut dining out by 20 %").
- **Change:** what-if in your own words (purchases get live prices from shop pages), preset changes, and
  **Play your next two weeks**: your likely days as cards, with the three baskets as the rules (rent can't be
  skipped but can move, surprises stay, extras are your choice).
- **The three baskets** everywhere, plus **Sort with the AI**: the AI asks about your genuinely unclear purchases
  and your answers re-sort your money in every number.
- **Safe to spend and safe to save** (from your own last 12 pay months), the surprise pot, **monthly drains**
  (habits that recur like subscriptions), and a **PSD2** consent flow for the full picture across banks (demo data
  for the other bank).
- **Money year** (Wrapped-style story with a shareable poster without amounts) and **Money Detective** (a learning
  map of the money concepts you've explored).

## Evidence
- **Numbers from code, checked:** `app/verify.py` matches every € and % in an answer to the tool results; the UI
  says "numbers matched to your data" and flags anything unmatched.
- **Trap suite** (`tests/traps/`, `scripts/run_traps.py`): 25 questions where money coaches typically fail (wrong
  "last month", invented merchants, prompt injection for another customer's data, quick loans, made-up projections,
  compound growth beyond income), run against the live coach; results on the Learn tab.
- **AI in Finland:** every AI job runs on Gemma 4 31B that we host on a Verda GPU in Finland (`app/eu.py`,
  `AI_PROVIDER=eu`): 25/25 traps, 51/51 numbers matched. The Claude path is still in the code for comparison but
  switched off. See `docs/VERDA.md`.
- **Live web data** with sources (`app/live.py`, Context.dev): prices confirmed on shop pages, official rules
  (loan cap, transfer tax, Euribor, HSL fares). See `docs/CONTEXT_DEV.md`.
- Offline tests: `pytest tests` (about 110).

## Privacy
The model sees computed totals and the question; never names, customer ids or account numbers. Live web lookups send
only an item name or a rule query. With the AI in Finland, no customer data leaves the country.

## Run locally
See "Stack and how to run" in `CLAUDE.md` (Python 3.12+, DuckDB, FastAPI, Anthropic SDK; the challenge data is not in
git: `scripts/fetch_data.sh`, then `scripts/build_data.py`).

## Limits
Synthetic data, one account per customer, no merchant names, a fixed "today" (30 Sep 2026). Rules from public
sources are shown with their source and date. Nothing here is S-Bank credit policy or financial advice.

Built by Pyry and Rasmus with Claude; Rasmus's side contributed reviews, outside tests, safe-to-save, the learning
map, the trend zoom and the coach's calculation fix. More: `docs/CHALLENGE.md` (brief), `docs/DECISIONS.md`,
`docs/ASSUMPTIONS.md`, `docs/DEMO.md`.
