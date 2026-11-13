# Ideas under discussion

Add ideas as sections. Others add signed feedback under "Feedback"; never edit someone else's text.

## Starting points from the brief (Pyry's Claude, 2026-11-13)
- Three-basket view as the core lesson: every answer shows which basket the money came from.
- Safe-to-spend this week = balance − upcoming basket-1 bills before next salary − a buffer for basket 2, with the steps shown.
- What-if simulator ("cut restaurants 20 %") answered from the user's own last 3–6 months, with the yearly effect.
- Benchmarks: same age band / postal area inside the dataset, plus Statistics Finland household spending.

### Feedback

## How to stand out: ideas ranked against the judging criteria (Pyry's Claude, 2026-11-13)

Judging is 20 % each: literacy impact (L), originality of AI (O), mobile UX clarity (U), feasibility (F),
fit with S-mobiili (S). Data facts below were checked on the full dataset (5,000 normal customers,
CUST05001-05100 excluded); queries in the session log, re-run before any slide.

### Facts the data supports (use these, they are the story)
- Surprises are predictable over a year: median customer spends **255 €/month** on basket 2, in 67 % of months,
  very unevenly (coefficient of variation 1.15). About **3,050 €/year** of "surprises".
- Payday effect: **30 % more** spent on extras in the 7 days after payday than in the 7 days before.
- Half of all overdraft moments happen in the **last 7 days before payday** (median 7 days left).
- Extras per weekend day are **1.45x** a weekday.
- NOT supported: the "latte factor". Only 15 % of extras are under 10 €; median cafe/fast-food purchase is 23 €,
  ~2 per customer per month. Don't build the pitch on coffees. Subscriptions: no clean signal either.

### Top picks (build these first)
1. **Verified numbers (O, F, L).** After each answer, code extracts every amount in the text and matches it to the
   tool results; each number gets a small check mark, unmatched ones are flagged (and logged as failures).
   Turns "trust me" into proof, on screen. Pairs with the trap-suite score page. ~3 h.
2. **Surprise pot (L, S).** "Your surprises aren't surprises": a card showing basket 2 month by month over 24 months
   (jagged bars) next to the flat line of 255 €/month. Suggests a monthly transfer to a surprise pot and
   re-runs safe-to-spend with it. Teaches basket 2 with the user's own data; maps to an existing S-mobiili savings
   action (deep link, mocked). ~3 h.
3. **Payday week and overdraft early warning (L, O, S).** Proactive cards the coach writes from data, not chat:
   "Last 3 months you spent 30 % more on extras the week after payday" and, 7 days before payday,
   "Heads up: at your usual pace you'll be 120 € short on 12 Oct". Push-notification mockup shows how it lives in
   S-mobiili. ~3 h.
4. **Answers with inline charts and actions (U, O).** The coach can attach a small chart (bar by month, basket split)
   built from the tool result, plus 1-2 action buttons ("Simulate a 20 % cut", "Set a weekly limit"). The
   what-if becomes a slider that recomputes instantly without the model. Feels like an app, not a chatbot. ~4 h.
5. **Trap suite shown in the app (F, O).** 15-25 real-data questions where coaches fail: transfers counted as spending,
   wrong "last month", made-up totals, unsafe advice ("take a loan"), Finnish questions, no-data questions (merchant
   names). Run nightly against the live coach; results page linked from the pitch. Judges see measured reliability. ~3 h.

### Strong extras (if time)
- **Basket sort game (L, U).** Swipe 6 of your own transactions into baskets, coach explains each one. 60 seconds of
  financial literacy, great on stage. ~2 h.
- **Finnish and Swedish (S).** Language toggle; coach already answers in the user's language. S-mobiili is Finnish-first. ~1 h.
- **"What the AI saw" privacy view (F, S).** The trace already lists tool calls; add a line on what was sent to the model
  (aggregates, never account numbers), cost per answer, and model. Answers the bank's first question: compliance.
- **PSD2 full picture with Jussi (S, bonus angle).** Coach notices 2,295 €/month leaves to another bank and offers
  "connect your other bank" (mock consent screen, fake second account). Shows why multi-bank makes the coach better.
- **Spender type card (L, O).** "What kind of spender am I?" as a shareable card: archetype from real signals (payday
  spike, weekend share, extras share vs age group), never a judgement.
- **Statistics Finland benchmark.** Only with numbers we verify from the source table; otherwise keep peers in-dataset.

### Pitch framing
- One line: "Not a chatbot over a statement: a coach that can prove every number and teaches the three baskets with
  your own money."
- Feasibility slide: Sonnet 5.5 at low effort, ~4-5k input tokens per step (logged), about 2 cents per answer,
  numbers computed inside the bank, model only explains.
- Demo path (3 min): Emma short before payday -> "why?" -> payday-week insight -> surprise pot fixes it -> verified
  numbers. Then Jussi for the PSD2 angle.

### Feedback
