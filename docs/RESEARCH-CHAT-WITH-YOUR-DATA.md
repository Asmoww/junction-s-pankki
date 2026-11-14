# Research: "chat with your own data" (the booth's foundational idea)
> Rasmus's Claude, started Sat 14 Nov 05:15, branch `feature/home-readiness`. Progress is updated in this file.
> Why: S-Pankki's booth called "chat with your own data" foundational. We want to know what the idea really
> means (in banking, MyData, AI), what has worked and failed, and how it should shape our product.

## Questions
| # | Question | Where to look | Status |
|---|---|---|---|
| Q1 | Where does the phrase come from, and what does it mean? (MyData movement, "talk to your data" in BI/LLM tools, Open Banking/PSD2) | MyData Global declaration, Sitra, BI vendors, banking press | First pass done |
| Q2 | Who has shipped it in banking, and what happened? (Bank of America Erica, Revolut AI, Monzo, Cleo, Nordea, Klarna, OP, Danske, DBS) | product pages, usage numbers, reviews | First pass done |
| Q3 | What goes wrong? (hallucinated numbers, wrong period, trust, privacy, regulation: EU AI Act, GDPR, PSD2/PSD3, FIDA, FIN-FSA advice rules) | papers, regulators, incident reports | First pass done |
| Q4 | What design patterns work? (grounded tools / text-to-SQL, showing provenance, visual + conversational, proactive vs reactive, user-correctable data) | HCI papers, fintech UX writing | First pass done |
| Q5 | Does it improve financial literacy or behaviour? Evidence, not claims. | academic studies on budgeting apps, nudges, AI coaching | First pass done |
| Q6 | What does "own data" add beyond chat? (data portability, correcting your data, consent, multi-bank) | MyData, PSD2/FIDA | First pass done |
| Q7 | Implications for us: what to keep, change, add | synthesis against our app and the brief | After Q1-Q6 |

## Working hypotheses (to test, not conclusions)
- H1: "Chat" alone is commodity; the value is in **the user's own data becoming something they can question and
  correct** (MyData = control, not just access).
- H2: Trust comes from **provenance**: every number traceable to transactions, which our verifier partly does.
- H3: Chat works best **attached to a visual** (forecast) rather than as a blank chat box.
- H4: Literacy gains need **a learning loop** (question → explanation → changed scenario → choice → check).

## Progress log
- 05:15 Plan written. The deep research tool was out of usage (try again ~09:30); did a first pass with web search instead.
- 05:35 First-pass findings below (S1-S12). A deeper pass can add Nordic banks, user reviews and literacy RCTs.
- 05:15 Related evidence already in hand: verifier only matches numbers, not meaning; safe-to-spend backtest
  (`docs/REVIEW-RESPONSE.md`): savings dipped in 40.7 % of positive answers, overdraft 5.5 %.

## First-pass findings (05:35)
**Q1/Q6 What "own data" means.** MyData (Finnish origin; Open Knowledge Finland white paper, Poikola, Kuikkaniemi,
Honko) says personal data not under the individual's own control "cannot be called MyData" [S1]; the six
principles are human-centric control, the individual as the point of integration, empowerment, portability,
transparency and accountability, interoperability [S2]; portability should be practical, not only a legal right [S3].
→ **For us: "chat with your own data" is about control, not a chat box.** The user should be able to question,
correct and reuse their data: recategorise, mark one-offs, fix payday, see where each number comes from, export.
This matches the outside AI's "user-owned assumptions" and supports H1.

**Q2 The market.** Chat over transactions is now mainstream:
- Revolut AIR (UK, 9 Apr 2026): spending insights, investments, subscriptions, card controls in one chat; accesses
  only data already visible in the app; zero data retention with AI partners [S4][S5]. A UX teardown notes it leans
  on category tags, so wrong categories give wrong answers [S6].
- Starling (2026): opt-in natural-language questions about spending, answered with graphs and the payments behind
  them [S7].
- Bank of America Erica: 24.6 M active users, 200 M interactions in Q2 2026 [S8]; over 1.9 B of 3.6 B interactions
  were proactive, personalised insights [S9].
→ **Chat alone is table stakes** (and Nordea has budgeting + a financial health check, see RESEARCH-NEXT F5).
What differs: proactive insight at the right moment (Erica), graphs next to answers (Starling), correctable
categories (AIR's weak spot), and provable numbers.

**Q3/Q5 Evidence and risks.**
- RCT, 39,607 Mint users (Management Science 2026): AI-predicted overdraft reminders cut overdraft fees; simpler,
  loss-framed messages worked best [S10]. → our payday early warning is evidence-backed; keep messages short.
- Experiment: a GPT-based chatbot raised optimal choices by 23.6 pp when it promoted the good option and cut them by
  29.3 pp when it promoted the bad one; bank framing didn't make people more careful [S11]. → AI advice is very
  persuasive, so steering must be visible: show assumptions, alternatives and sources, never a hidden nudge.
- Chatbots give inconsistent financial advice across platforms and personas (UGA, Journal of Financial Planning) [S12].
  → keep numbers deterministic (we do) and test consistency (trap suite).
- EU AI Act Art. 50 chatbot transparency applies from 2 Aug 2026 even though high-risk rules were delayed [S13];
  Commission guidance names financial advice as a sensitive context where periodic reminders may be needed [S14].
  → label the coach as AI on first use and in advice moments.

## What this means for our product (proposal)
1. **Reframe the pitch:** "your own data, under your control": ask it, question it, correct it, see its source.
2. **Assumption chips on every answer** (payday, bills to come, buffer, protected savings) that the user taps to
   change; the forecast and the answer recompute. This is the MyData "control" principle made concrete.
3. **Correct your data:** recategorise / mark one-off / "won't repeat"; stored per user, reset in demo.
4. **Chat attached to the graph** (Design E): "Can I spend 80 € this weekend?" answered on the forecast with a range.
5. **Proactive, short, loss-framed warnings** before payday (S10), not long advice.
6. **Show steering:** when the coach suggests something, show the alternative and what it assumes (S11).
7. **AI disclosure** on first use and in advice moments (S13, S14).
8. **Learning check:** one question after a scenario ("why isn't all of your balance spendable?").

## Sources (first pass)
- S1 github.com/okffi/mydata, "1 - What is MyData?" (white paper, Open Knowledge Finland).
- S2 Ball et al., "MyData: Applying human-centric principles to health data", Medical Writing 29(2), 2020, Figure 3.
- S3 mydata.org/declaration/ (Declaration v1.0), principle on portability.
- S4 revolut.com/news, "Revolut enters new era of money intelligence with launch of AI assistant", 9 Apr 2026.
- S5 thepaypers.com, "Revolut launches AI-powered in-app financial assistant".
- S6 craftinnovations.global/revolut-air-ux-analysis/, section 1.2.
- S7 getcoai.com, "Starling Bank launches AI tool that assesses spending routines".
- S8 customerexperiencedive.com, BofA Q2 2026 earnings brief.
- S9 thefinancialbrand.com, "BofA augments internal EricaAssist with GenAI".
- S10 Management Science 72(1), 2026, "Using AI and Behavioral Finance to Cope with Limited Attention and Reduce
  Overdraft Fees" (EBSCO abstract; EurekAlert release 1084047).
- S11 CESifo Working Paper 12925 (ifo.de), results paragraph on chatbot treatments.
- S12 University of Georgia news, "Should a chatbot manage your bank account? Probably not".
- S13 ergomania.eu, "EU AI Act transparency design problem"; risk.net on the high-risk delay.
- S14 paytechlaw.com, "AI Act: New Transparency Obligations under Article 50 for Financial Institutions", section 3.
