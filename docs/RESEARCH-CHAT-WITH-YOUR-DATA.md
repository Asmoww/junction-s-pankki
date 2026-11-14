# Research: "chat with your own data" (the booth's foundational idea)
> Rasmus's Claude, started Sat 14 Nov 05:15, branch `feature/home-readiness`. Progress is updated in this file.
> Why: S-Pankki's booth called "chat with your own data" foundational. We want to know what the idea really
> means (in banking, MyData, AI), what has worked and failed, and how it should shape our product.

## Questions
| # | Question | Where to look | Status |
|---|---|---|---|
| Q1 | Where does the phrase come from, and what does it mean? (MyData movement, "talk to your data" in BI/LLM tools, Open Banking/PSD2) | MyData Global declaration, Sitra, BI vendors, banking press | Running (deep research) |
| Q2 | Who has shipped it in banking, and what happened? (Bank of America Erica, Revolut AI, Monzo, Cleo, Nordea, Klarna, OP, Danske, DBS) | product pages, usage numbers, reviews | Running |
| Q3 | What goes wrong? (hallucinated numbers, wrong period, trust, privacy, regulation: EU AI Act, GDPR, PSD2/PSD3, FIDA, FIN-FSA advice rules) | papers, regulators, incident reports | Running |
| Q4 | What design patterns work? (grounded tools / text-to-SQL, showing provenance, visual + conversational, proactive vs reactive, user-correctable data) | HCI papers, fintech UX writing | Running |
| Q5 | Does it improve financial literacy or behaviour? Evidence, not claims. | academic studies on budgeting apps, nudges, AI coaching | Running |
| Q6 | What does "own data" add beyond chat? (data portability, correcting your data, consent, multi-bank) | MyData, PSD2/FIDA | Running |
| Q7 | Implications for us: what to keep, change, add | synthesis against our app and the brief | After Q1-Q6 |

## Working hypotheses (to test, not conclusions)
- H1: "Chat" alone is commodity; the value is in **the user's own data becoming something they can question and
  correct** (MyData = control, not just access).
- H2: Trust comes from **provenance**: every number traceable to transactions, which our verifier partly does.
- H3: Chat works best **attached to a visual** (forecast) rather than as a blank chat box.
- H4: Literacy gains need **a learning loop** (question → explanation → changed scenario → choice → check).

## Progress log
- 05:15 Plan written. Deep research task launched with Q1-Q6 (results pending; will be summarised here with sources).
- 05:15 Related evidence already in hand: verifier only matches numbers, not meaning; safe-to-spend backtest
  (`docs/REVIEW-RESPONSE.md`): savings dipped in 40.7 % of positive answers, overdraft 5.5 %.
