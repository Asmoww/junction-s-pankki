# Status

Update at the end of every session (or run `/handoff`).

## In progress
- (none)

## Next up
- Rehearse the 3-minute demo path (see IDEAS.md "Pitch framing") and record a backup video
- Streaming answers / step progress while the coach works (answers take 4-10 s)
- Spending explorer screen (MyData: tap any category/month)
- Mentor feedback on the basket rules (DECISIONS.md) and the safe-to-spend method

- Pick the design: `/e` (money ribbon) vs `/`; then make it the default

## Blocked / waiting
- Team: module owners

## Done
- 2026-11-14 Number sources in the coach chat (colours, badges, number sheet with coach's note); branch `claude/number-sources`, no PR yet, needs a live check of the notes block on Claude and the EU model (Joona's Claude). Same branch: plain-language "From your S-Bank account" popup with See the payments (`/api/payments`); untested against real data. Known gap: safe-to-spend step names come from money.py in English. Full suite 97/97 with the data (19:30)
- 2026-11-14 Trap suite: hateful-request case no longer fails correct refusals (13 offline grading tests); Money year receipt loader (Joona's Claude)
- 2026-11-13 Repo set up, dataset profiled (ASSUMPTIONS.md) (Pyry's Claude)
- 2026-11-13 Money tools, Claude coach, mobile UI live at spankki.psavela.com (Pyry's Claude)
- 2026-11-13 Verified numbers, surprise pot, payday-week + overdraft forecast cards with push mockup, inline charts and
  what-if slider, trap suite (18/18 twice, 80/80 numbers verified) shown in app + nightly run, basket sort game,
  EN/FI/SV, "What the AI saw" (model, tokens, cost, data sent), PSD2 connect mock for Jussi, spender type,
  Statistics Finland benchmark (Pyry's Claude)
- 2026-11-14 Design E (money ribbon) live at /e: real balance since payday + forecast to next payday, drag readout, EN/FI/SV (Pyry's Claude)
- 2026-11-14 Smoke-test defects fixed (charts in chat, badge counting the user's numbers, dated costs, reply language, basket labels, shortfall headline); Rahakunto card; Ville persona; traps 22/22, 92/92 numbers (Pyry's Claude)
