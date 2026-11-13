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
- 2026-11-13 App model capped at Sonnet: no server-side refusal fallback (it can retry on Opus). Why: Pyry, cost.
- 2026-11-13 Verified numbers: code matches every € and % in an answer to tool results; percentages in a closing question are "suggestions" and not checked. Why: proof on screen instead of "trust the AI".
- 2026-11-13 Coach gets a `calculate` tool and must use it for any arithmetic. Why: the trap suite caught the model inventing "1,000 € would cover it" from its own mental math.
- 2026-11-13 Forecast and safe-to-spend give two different shortfalls on purpose: "at your usual pace" (extras included) vs "even with no extras". Both are labelled in UI and coach. Why: an unlabelled 997 € vs 676 € confused the first version.
- 2026-11-13 Benchmarks: Statistics Finland 2022 table 14q4, per consumption unit per month by age. Housing not compared (includes owners' imputed rent). Synthetic data runs far above national figures, so always shown with caveats.
- 2026-11-13 Insight card texts are templates filled with computed numbers (not model-written). Why: instant, translatable, and nothing to verify.
- 2026-11-13 PSD2 is a consent mock only; no fake second-bank data. Why: invented transactions would undercut the "every number is real" story.
- 2026-11-13 Trap suite runs nightly (~$0.15/run, Sonnet). Why: judges see measured reliability that stays current.
- 2026-11-14 Design E built as a second front end at /e, sharing app.js and the API; / unchanged. Why: try it without risking the working demo.
- 2026-11-14 Login keeps the requested page (/login?next=), only local paths. Why: links to /e and /design survive the password gate.
- 2026-11-14 Design E is the main page; the first design stays at /classic. Why: Pyry; the graph-first design with AI inside it is the direction.
