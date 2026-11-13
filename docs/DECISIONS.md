# Decisions

One line per decision, with why. Newest last.

- 2026-11-13 Numbers come only from deterministic queries (DuckDB) over the data; Claude picks tools and explains. Why: a money coach that invents numbers loses trust instantly.
- 2026-11-13 App model Claude Sonnet 5.5 (`claude-sonnet-5-5`). Why: team default; switch only after an eval.
- 2026-11-13 Mobile web app, embeddable in the S-mobiili webview. Why: brief asks for mobile or embeddable web; one codebase, no app store.
- 2026-11-13 Dataset stays in `data/raw/` (gitignored), fetched by `scripts/fetch_data.sh` with a hash check. Why: challenge-only data, 350 MB LFS file.
- 2026-11-13 Salary Sweep, Invest Deposit/Withdraw are transfers, not spending or income. Why: see ASSUMPTIONS.md; counting them would inflate spending by ~36 M EUR.
