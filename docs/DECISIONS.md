# Decisions

One line per decision, with why. Newest last.

- 2026-11-13 Numbers come only from deterministic queries (DuckDB) over the data; Claude picks tools and explains. Why: a money coach that invents numbers loses trust instantly.
- 2026-11-13 App model Claude Sonnet 5.5 (`claude-sonnet-5-5`). Why: team default; switch only after an eval.
- 2026-11-13 Mobile web app, embeddable in the S-mobiili webview. Why: brief asks for mobile or embeddable web; one codebase, no app store.
- 2026-11-13 Dataset stays in `data/raw/` (gitignored), fetched by `scripts/fetch_data.sh` with a hash check. Why: challenge-only data, 350 MB LFS file.
- 2026-11-13 Salary Sweep, Invest Deposit/Withdraw are transfers, not spending or income. Why: see ASSUMPTIONS.md; counting them would inflate spending by ~36 M EUR.
- 2026-11-13 Demo "today" is 2026-09-30 (end of data); "last month" = August 2026. Why: answers must match the data, not the real date.
- 2026-11-13 Baskets: 1 = Housing, Utilities, supermarket groceries, public transport and fuel; 2 = Health, Home & Tech from 100 €, and one-offs (>1,000 € and >20x own median); 3 = everything else (restaurants, cafes, bars, taxis, parking, entertainment, lifestyle, travel, kiosks). Why: simple, explainable rule; refine with mentor feedback.
- 2026-11-13 Safe-to-spend uses the pay cycle: balance minus savings carried over from before the last payday, minus bills still due, usual essentials and a surprise buffer until next payday. Why: counting savings as spendable gave 8,600 €/week for a typical saver.
- 2026-11-13 Coach effort `low`, tools are strict enums for period/category/subcategory. Why: chat latency; enums stop the model inventing categories or dates.
- 2026-11-13 Demo personas are 4 ordinary customers (CUST01610, 04588, 00388, 00724) with invented names; CUST05001-05100 avoided as they carry most injected anomalies.
- 2026-11-13 Mobile only (no desktop layout), deployed at spankki.psavela.com behind one password. Why: Pyry; S-Bank customers are on mobile.
