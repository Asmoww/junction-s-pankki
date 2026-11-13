# Chat with your own money (S-Pankki, Junction 2026)

Every Claude session on this team reads this file first. Keep it short and current.

## The challenge
Build a mobile-first AI money coach that lets S-Bank customers chat with their own transaction data:
"How much did I spend on taxis last month?", "What kind of spender am I?", "What is safe to spend this week?",
"How much could I save if I cut dining out by 20 %?". Pedagogical angle: every expense falls into one of
three baskets: (1) mandatory regular, (2) mandatory irregular, (3) everyday spending that slips away.
MyData spirit: let users explore freely, not fixed charts. Optional: Statistics Finland benchmarks, PSD2 multi-bank view.
Full brief: `docs/CHALLENGE.md`. Judging (20 % each): financial literacy impact, originality of AI integration,
clarity of mobile UX, feasibility, potential to integrate into S-mobiili.

## Architecture
```
Mobile web UI (embeddable in S-mobiili webview)
   │  chat + small inline charts
   ▼
API (FastAPI) ── Coach (Claude, tool use) ── Money tools: deterministic DuckDB queries
                                               ├─ spend by category / merchant type / period
                                               ├─ three-basket classifier
                                               ├─ safe-to-spend / what-if simulator
                                               └─ benchmarks (Statistics Finland, open data)
```
Numbers always come from the tools, never from the model. Claude chooses tools and explains the results.

## Module ownership (fill in names)
| Module | Owner | Folder |
|---|---|---|
| Data build + money tools | ? | `scripts/build_data.py`, `app/money.py`, `app/taxonomy.py` |
| Coach (Claude, prompts, tool use) | ? | `app/coach.py` |
| Mobile UI | ? | `app/web/` |
| Benchmarks (open data) | ? | (not started) |
| Tests + trap suite | ? | `tests/` |
| Demo script + pitch | ? | `docs/` |

Only edit another owner's folder after agreeing in chat. Shared contracts in `contracts/` change only by
agreement; record the change in `docs/DECISIONS.md`.

## Rules for every session
1. Start: `git pull`, read `docs/STATUS.md` and `docs/DECISIONS.md` (or run `/sync`).
   Ideas still under discussion go in `docs/IDEAS.md`; add your feedback there, signed.
2. Build against `contracts/`, not against another module's internals.
3. Small commits, merge to `main` every 1–2 hours. Don't break the demo flow on `main`.
   Review teammates' branches critically before merging; `review/...` branches are never merged.
4. Never commit secrets. `.env` is gitignored (chmod 600); variable names in `.env.example`.
   Before every push check that no `.env`, `data/` or `state/` file is tracked.
5. Data quirks go in `docs/ASSUMPTIONS.md` with evidence. Verify every number against the data before
   it goes in the UI or on a slide; AI research is claims to test.
6. Before finishing: update `docs/STATUS.md` and `docs/DECISIONS.md`, commit, push (or run `/handoff`).
7. Discord update on real milestones only: a short title line, then one bullet per change. Concise,
   no emojis. Example: `python scripts/notify.py $'S-Pankki demo: safe-to-spend live\n- Added: weekly safe-to-spend\n- Tests: 20 offline, 8/8 traps'`
8. Everything in English: code, comments, docs, commit messages, UI text.
9. App model: Claude Sonnet 5.5 (`claude-sonnet-5-5`) at most; never Opus (Pyry). Compare on a small eval before switching.

## Data
Challenge data is challenge-only: it lives in `data/raw/` (gitignored). `scripts/fetch_data.sh` downloads it
and checks the hash. 3.6 M transactions, 5,100 customers (one account each), 2024-10-01 to 2026-09-30.
Quirks and handling: `docs/ASSUMPTIONS.md`.

## Stack and how to run
Python 3.12, DuckDB over `data/tx.parquet`, FastAPI, Anthropic SDK, vanilla JS mobile UI, pytest.
```bash
python3 -m venv .venv && .venv/bin/pip install duckdb fastapi 'uvicorn[standard]' anthropic python-multipart pytest
scripts/fetch_data.sh                          # dataset into data/raw/ (hash-checked)
.venv/bin/python scripts/build_data.py         # data/tx.parquet + customers.parquet (fails if the balance chain breaks)
.venv/bin/python -m pytest -q tests            # offline tests, no API calls
.venv/bin/uvicorn app.main:app --port 5202     # local run (.env: ANTHROPIC_API_KEY, DEMO_PASSWORD)
```

## Code map
- `app/money.py` every number: spending, transactions, cashflow, three baskets, safe-to-spend, what-if cut, spender profile, overview. "Today" is 2026-09-30.
- `app/insights.py` surprise pot, payday pattern + forecast, Statistics Finland benchmark, spender type, basket game, PSD2 signal, home cards.
- `app/coach.py` Claude tool-use loop (Sonnet 5.5, effort low, no fallback to bigger models; model logged per call), `calculate` tool for any
  arithmetic, charts/widgets built from tool results, usage + cost, privacy summary. EN/FI/SV answers.
- `app/verify.py` verified numbers: every € and % in an answer is matched to tool results (verified / rounded / suggestion / unverified).
- `app/main.py` password gate, `/api/home|overview|chat|game|traps|personas`, asset versioning (Cloudflare caches /static).
- `app/web/` mobile UI, tabs Home / Coach / Learn; `i18n.js` holds every UI string in en, fi, sv.
- `app/bench_statfin.json` Statistics Finland 2022 table 14q4 (open data), rebuilt by `scripts/fetch_benchmarks.py`.
- `tests/traps/cases.py` + `scripts/run_traps.py` trap suite against the live coach (~$0.15/run) -> `state/traps.json`, shown on Learn.
  Nightly: user timer `spankki-traps.timer` (03:17).
- `app/personas.py` four demo customers (real ids, invented names).

## Deployment
https://spankki.psavela.com (password in team chat). User service `spankki-coach` (port 5202, MemoryMax 600M):
`systemctl --user restart spankki-coach` after changes. Tunnel: user service `cloudflared`, config `~/.cloudflared/config.yml`
(back it up before editing; a restart briefly drops every site on the tunnel).
