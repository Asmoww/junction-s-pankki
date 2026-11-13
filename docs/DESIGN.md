# Design plan: from generic to personal

Status: proposal for the team (2026-11-13). Mockups in `design/mockups/` (open the `.html` files or see `compare.png`).
All mockups use Emma's real data (CUST01610, 30 Sep 2026).

## The problem

The current app is clean but could be any bank: green header, white cards, one radius, one shadow. Nothing on the first
screen is about *this* person, and nothing invites a tap except the chat box. Judges score mobile UX clarity and literacy
impact: the design should teach the three baskets and make the user want to poke at their own money.

## What makes it personal (applies to every direction)

1. **Open with a sentence about you, not a widget.** The first thing on screen is the one fact that matters today, in
   plain words from the data: "Rent leaves on 3 Oct and takes you below zero." Computed, templated, verified.
2. **Your month, not the calendar month.** Money runs payday to payday. Show bills as dated events ahead ("rent 763 €, 3 Oct").
3. **Things you can touch that answer back.** Every chart is a control: tap a jar, drag the dial, flip a toggle; the
   numbers recompute instantly in code, and the coach can explain any state.
4. **The coach remembers.** It refers to last week ("your biggest extra was 114.84 € on Friday"), not just this question.
5. **Finnish everyday materials.** Berry colours, the grocery receipt, the payday rhythm: things a Finnish customer
   recognises without a legend.
6. **One bold element per screen.** Everything around it stays quiet.

## Four directions

### A. Three jars (the baskets made physical)
- Hero: three jars filling over the month; dashed line = your usual month; pending bills shown as a hatched layer
  ("rent 763 € to come"). Below: your next 15 days as tiles, bills and the below-zero day marked.
- Colour: snow `#f3f5f7`, ink `#1d2433`, moss `#2f5d3a`, blueberry `#3d4f9a` (fixed), cloudberry `#e5a13a` (surprises),
  lingonberry `#c7354a` (extras). Finnish berries = the three baskets.
- Type: Bricolage Grotesque (headline sentence), Instrument Sans (body).
- Strength: teaches the three baskets at a glance; strongest for the literacy criterion. Tap a jar to pour it out into
  its purchases.
- Risk: jars are a metaphor to maintain across every screen.

### B. Pay-month dial (plan your way to payday)
- Hero: a ring from payday to payday, today as a knob, bills as dots, the below-zero stretch in red. Under it, toggles
  ("pause eating out, usually 118 € before payday") that close the gap live: −997 € → −879 €. Turning all extras off
  lands on −676 €, showing why "safe to spend" says what it says.
- Colour: night `#172347`, deep `#24335e`, paper `#eef1f6`, gold `#f2b544` (today, money), rose `#e0566a` (below zero),
  periwinkle `#8ea2ff`.
- Type: Unbounded (numbers, headings), Atkinson Hyperlegible (body; designed for low-vision readers: banking for everyone).
- Strength: most interactive; turns safe-to-spend into a plan you build yourself. Great live demo moment.
- Risk: the dial needs care to read at a glance; works best for people near payday trouble.

### C. Coach first (a conversation that knows you)
- Hero: the app opens on today's message from the coach, with a rich bubble (balance path to payday crossing zero on
  3 Oct) and three big quick replies. Yesterday's note above shows it remembers.
- Colour: sage `#e7ebe2`, pine `#23423a`, violet `#6b4fd0` (things you can tap), red `#c43d4b`, ink `#1e2622`.
- Type: Gabarito (headings), Hanken Grotesk (body).
- Strength: most personal and the clearest showcase of the AI (originality criterion); feels like a person, not a report.
- Risk: less "at a glance" for people who never chat; needs the home cards somewhere else.

### D. Monthly receipt (your month, printed)
- Hero: September as a long grocery-style receipt: lines per merchant type, subtotals per basket, rent "due 3 Oct",
  and an "extra for you" box where the bonus line would be (cut eating out 20 % = 47.10 € a month). Swipe between months.
- Colour: S-green `#0d5c3a`, paper `#fcfcf9`, ink `#20241f`, basket colours as small squares.
- Type: IBM Plex Mono for the receipt only (it is a receipt), Instrument Sans for the UI around it.
- Strength: instantly recognisable in Finland (S Group receipts), shareable, fun to swipe; perfect for "where did my
  money go".
- Risk: a single-screen idea; best as the monthly summary inside A, B or C rather than the whole app.

## Recommendation

Combine **C as the home** (the coach greets you with today's one thing) with **A's jars** as the baskets view and
**B's toggles** inside the "help me make it to payday" answer, and use **D** as the monthly summary screen. That gives one
bold idea per screen: conversation (home), jars (baskets), plan (payday), receipt (month).

If time is short, A alone is the safest single step up: it changes the first impression most for the least work.

## Next steps once a direction is chosen

1. Lock tokens (colour, type, radius scale by hierarchy, motion: one orchestrated moment per screen).
2. Rebuild the home screen in the app with real data, then baskets, then payday plan, then month receipt.
3. Keep FI/SV strings, verified numbers and "How I worked this out" in every new component.
4. Browser check every screen at phone size; reduced motion and contrast checks.

## Also found while designing

The payday forecast spread bills evenly and said Emma runs out "around 7 Oct". Her 763 € rent leaves on the 3rd and is
bigger than her balance, so she goes below zero on 3 Oct. The forecast needs to place bills on their usual day (fix in app).
