# Live capture: Emma, one continuous take (raw, uncut)

- **File:** `emma-live-flow.webm`, 62.5 s, VP9, 430×932 (native phone size; the page is rendered at 2× and downscaled),
  25 fps, recorded with Playwright's recorder against the live site https://spankki.psavela.com.
- **Build:** `feature/context-dev` eaa0bad (deployed when recorded, 14 Nov 2026 ~19:00 EET).
- **AI:** Gemma 4 31B on our Verda GPU in Finland (AI_PROVIDER=eu, Claude disabled). Persona: Emma (CUST01610,
  synthetic). Language: English. Fresh browser identity; login happened in a separate context before recording.
- **No mocks:** the coach question is answered live (about 10 s on the GPU), the presets call the real scenario
  engine (preloaded after Home opens, so the tap redraws at once), the map progress is recorded by the app.
- **Flow and timestamps:** `actions.json` (seconds from the start of the page; the video runs about 1 s ahead of
  these numbers, so check each cut on the frame). In short: picker → Emma Home (−997 € at your usual pace) → Coach
  "Why am I always short before payday?" → answer, 4/4 numbers matched → How I worked this out → Home: Pause
  extras (−676 €) → Rent after payday combined (+87 €, +1,084 €) → Learn: Money Detective 2 of 9 → 12-month view → back.
- **Rebuild:** `record.py` (needs the demo password in the login step; not stored here).
- Not edited, not sped up. Waits are real.
