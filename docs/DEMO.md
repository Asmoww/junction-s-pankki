# Demo plan

All numbers below were computed from the app on 14 Nov 02:40 (data as of 30 Sep 2026). Re-check after any change.

## The one story
**"People don't run out of money because of coffee. They run out because of timing."** Half of all
overdraft moments in the data happen in the last 7 days before payday; small purchases under 10 € are only
15 % of extras. So the coach shows your money's **future**, explains it, and lets you **change it in words**.

## A. 3-minute version (stage, video, first minutes at the table)
Phone screen mirrored (or Chrome device mode, Pixel 7, zoom 125 %). Emma, English, logged in, home tab.

| Time | Do | Say (short) |
|---|---|---|
| 0:00 | Home, Emma | "Emma, 23, first job. 699.85 € today. This line is her real balance since payday, and the dotted part is where it's heading." |
| 0:15 | Point at the rent marker | "Rent, 763 € on 3 Oct, takes her below zero. On payday she'd be 997 € short." |
| 0:30 | Point at the AI notes | "The AI reads her line: biggest day 205 € right after payday. Every number in a note is checked against her data before it's shown." |
| 0:45 | Tap **Pause extras** | "Pause every extra: still 676 € short. It's not the coffee." |
| 1:00 | Clear, tap **What if…**, type "What if I pause extras and pay rent after payday?" | "She asks in her own words. The AI turns it into a plan, code redraws the future." |
| 1:10 | Line turns up, result **+87 €** | "Two moves, and she makes it to payday with 87 € left. That's literacy: she sees which basket sinks her." |
| 1:25 | **Check a purchase** → "iPhone 17 256 GB" | "Can she buy a phone? We check live prices, and every price is read from the shop's own page. Search engines guessed 879 € for a page that says 999 €; we only trust the page." |
| 1:45 | Tap the 879 € offer | "Line drops to −1,876 €. Not this month." |
| 2:00 | Coach tab: "Why am I always short before payday?" | "The coach answers from her data, draws the chart, and shows its work." Open **How I worked this out** → **What the AI saw**: "about 2 cents an answer, no name or account number ever sent." |
| 2:30 | Learn tab → report card | "22 trick questions run against the live coach every night: 22/22, 92 of 92 numbers verified." |
| 2:45 | Close | "Built to live in S-mobiili: a push before payday, a card on the home screen, the rules from official sources. **See your money's future, and change it.**" |

## B. Table version (5-8 min, let the judge drive)
1. Do A up to 1:10 (Emma, the two-move fix).
2. **Hand the phone over**: "Type any what-if." Good prompts if they freeze: "concert tickets 150 € on Friday",
   "Mitä jos syön ulkona puolet vähemmän?" (Finnish works).
3. **Rahakunto** (strip card): 19, "A tight year, one thing first: spend 206 € a month less to break even". Tap the
   step: the coach takes over.
4. **Ville, 32**: "When can I buy a 250,000 € home?" → about 4 months. Open **Live rules**: loan cap 95 %
   (FIN-FSA, 30 Jun 2026), Euribor 3.293 %, transfer tax 1.5 % (vero.fi). "The planner reads live rules, so it
   wasn't stuck on last year's 90 % cap. And it shows the catch: 57,500 € of extra collateral."
5. **Jussi**: "Your salary moves to another bank" → the PSD2 connect flow (mock).
6. Questions (below).

## C. Prep checklist (the hour before)
- [ ] Phone hotspot as backup network; laptop charged; screen mirroring tested.
- [ ] Logged in on the demo device; Emma selected; language EN; home tab; no scenario active; chat empty.
- [ ] Warm everything once: open Emma, Ville, Jussi (AI notes are cached), ask the coach one question, run
      "Check a purchase: iPhone 17 256 GB" (page reads are reused for an hour, so the second run is faster).
- [ ] Re-check rules in the Live rules sheet (shows fetched time).
- [ ] Backup video of version A on the laptop desktop; screenshots of every step in a folder.
- [ ] Who does what: Pyry drives the phone, Rasmus tells the data story and takes analytics questions.
- [ ] Rehearse A three times with a timer; it must fit in 3:00 with one slow API call.

## D. If something breaks
| Problem | Do |
|---|---|
| What-if box slow (>8 s) | Use the chips (instant, no AI): Pause extras, then Rent after payday, explaining "the AI does this from words" |
| Live prices fail | The sheet says "not connected": say "unknown stays unknown, we never guess", move on |
| Coach slow | Ask the same question from a chip; or show the report card while it loads |
| Wi-Fi dead | Switch to the hotspot; if still dead, play the backup video |

## E. Likely questions, short answers
- **Is this real customer data?** Synthetic data modelled on S-Bank's, 5,100 customers, two years. Nothing real.
- **How do you stop the AI making up numbers?** It can't compute: every number comes from code. A checker
  matches every amount in an answer to the data; anything else is flagged on screen. Proof: the nightly trap suite.
- **Privacy?** The model sees totals and the questions; never names, ids or account numbers. Live web lookups send
  only an item name or a rule.
- **Cost?** About 2 cents per coach answer (Sonnet 5.5, logged per call); AI notes are cached per customer.
- **How would S-Pankki ship it?** A web view inside S-mobiili on the bank's own transaction APIs; push for the
  payday warning; the model behind the bank's own API gateway.
- **Why three baskets on a graph?** It's the brief's pedagogy made visible: you see which basket sinks the line.
- **What's original about the AI?** It edits your future from your sentence, and it explains your past on the line,
  with every number verified.

## Open
- Voice input for the what-if (~1-2 h): a judge *saying* the sentence is a stronger moment than typing. Note: in
  Chrome the audio goes to Google's speech service; say so on screen.
- Product name and tagline: working tagline "See your money's future, and change it."
