# What the S-Pankki solution still needs: research plan, first findings, next steps
> Rasmus's Claude, Sat 14 Nov 05:20, branch `feature/home-readiness` (not merged). **For Asmoww's Claude.**
> Rasmus's standing instruction: don't plan around feature freezes; ignore the "freeze" advice in the outside
> reviews and in `review/rasmus-next-build`.
> Tags: [D] computed from the challenge data here, [W] web source (listed at the end), [J] judgment.

## 1. Research plan
Two tracks, each question with the evidence that would settle it.

### A. Technical: what the product still needs
| # | Question | How to settle it | Status |
|---|---|---|---|
| A1 | Is the deployed app in git? (score, Live rules card) | compare server tree with `origin/main` | **Open, Pyry**: score isn't in any branch |
| A2 | Do the planner's inputs agree with the rest of the app? (salary, savings, surplus) | one definition per figure; check personas | **Done, see F1** |
| A3 | Is "own funds" right for customers who move money out? | net Invest/Sweep per customer | **Done, see F2; fixed in code** |
| A4 | Is the loan cap rule primary-sourced? | FIN-FSA release | **Done, F3** |
| A5 | What does the planner say across all customers? (is the demo typical?) | run readiness on 5,000 customers | **Done, F4** |
| A6 | Do readiness answers survive the trap suite? | add 5 home traps (single date, invented rule, deficit user told to buy, 0 for unknown, Finnish question) | **Open** |
| A7 | Does the coach pick `home_readiness` over `plan_home` and end with next_question? | 10 live questions, Sonnet 5.5, log tool choice | **Open** (needs server) |
| A8 | Offline demo: rules cached with timestamp, refresh button, works when Context.dev is down | kill the key, run the demo path | **Open** |
| A9 | Latency: readiness loops over prices (reachable price) | time `/api/readiness` for 4 personas; target < 300 ms | **Open** |

### B. Business and problem: what the solution still needs
| # | Question | How to settle it | Status |
|---|---|---|---|
| B1 | What do Finnish bank apps already do? (budget, categories, health check) | bank pages | **Done, F5**: budgeting is table stakes |
| B2 | Which public rules decide first-home buying in 2026? (ASP, cap, term) | Valtiokonttori, FIN-FSA, banks | **Done, F6** |
| B3 | Why S-Pankki cares now | S-Pankki releases | **Done, F7** |
| B4 | Who is the user? Brief stresses young adults | data: age vs readiness; S-Pankki's own literacy survey | **Partly, F7**; age split open |
| B5 | Is "binding constraint + next question" actually understood? | 5 people, 60 s, can they say what blocks them? | **Open: Rasmus at the venue** |
| B6 | What would S-Pankki measure in a pilot? | ask booth mentors (Calle Holmberg) | **Open: Rasmus, booth questions below** |

## 2. Findings so far

**F1. There are two "Mikkos".** [D] Our analytics used CUST04138 (salary 4,385 €/month, ready for 250 k in
~5 months at 95 % cap). The live app's Mikko is CUST04588 (salary 3,289 €, one salary payment a month, typical
surplus ~257 €). That explains the 4,385 vs 3,289 mismatch. Never mix them on slides.

**F2. Own funds are undercounted for 1,728 of 5,000 customers.** [D] They moved money out (Invest Deposit,
Salary Sweep; median net 7,868 € over the data). Jussi (CUST00724) swept 52,112 € to another bank. The planner
can't see that money, so it must ask, not assume. **Fixed:** `assess(moved_out_eur=…)` adds the question
"You've moved N € to savings or investments. Could that go to the home?" and computes its effect. For Jussi it
is the top question (likely 49 months → much sooner if yes). This doubles as the PSD2 bonus story: with consent the
coach could see the other bank and stop asking.

**F3. Loan cap 95 % for all borrowers is primary-sourced.** [W1] FIN-FSA press release 30 Jun 2026 raises the cap
for non-first-home loans to 95 % (first-home stays 95 %). Finnish sources describe it as temporary [W2]; effective
1 Jul 2026 per Nordea [W3]. A later FIN-FSA release says the eased cap stays unchanged [W4]. The outside review's
worry is resolved; the rules card should cite W1 and say "temporary".

**F4. Across 5,000 customers, a 250 k home is a stretch.** [D] (95 % cap, 1.5 % tax, Euribor 3.293 %)
- Binding constraint: income caps the loan 58.5 %, monthly deficit 26.3 %, own funds 9.4 %, collateral 5.8 %.
- 250 k likely within 5 years: 24.6 %; within 10 years: 33.1 %.
- Price reachable within 5 years: median 159 k; 27.7 % have none (deficit or near-zero pace).
- Next question chosen: reachable price 32.9 %, fix the month 26.7 %, cheaper 23.3 %, savings elsewhere 7.6 %,
  ASP 5.8 %, save more 3.7 %. So the "next question" really differs by person.
- Personas: Mikko 04588 → income caps loan, reachable ~198 k (2 y) / 207 k (5 y); Emma → fix the month first;
  Aino → income caps loan, ~132 k in 5 y; **Jussi → savings elsewhere (52 k)**. Laura 00414 (old analytics) gets
  no question (pace ~4 €/month): edge case to handle with a plain "not on today's numbers" message.
[J] Demo: Mikko asks for 250 k → "your income is the limit, ~200 k is reachable in 2 years" → change price → plan
updates. Then Jussi for the "money elsewhere" + PSD2 moment. Numbers are from a pandas replica; re-check via the API.

**F5. Budgeting and categories are table stakes; "financial health" is taken.** [W5][W6] Nordea's app already
has spending overview, income/expense categorisation, budgets, subscription management and other banks' balances.
Nordea won The Banker's 2026 Financial Health award with a "Financial Health Check" that groups money into buckets
and suggests next steps. [J] So our baskets + score + budget are not unique. Our edge is: (1) chat with your own
data where every number is verified, (2) a decision answer (can I buy, what blocks me, what to ask next), (3) live
public rules with sources. Lead with those; keep budget and score as supporting features.

**F6. ASP changed on 1 Jun 2026 and fits the planner.** [W7][W8][W9] No upper age limit any more; save
50-1,500 €/month for at least 20 months; target at least 10 % of the price; ASP loan has a free state guarantee and
interest subsidy (state pays 70 % of interest above 3.8 % for 10 years); ASP interest is tax-free. [J] The state
guarantee answers the collateral constraint, so ASP is now a computed next question when collateral blocks and
first-home status is unknown. Open check: one bank page says ASP loan + additional loan max 90 % of price; verify
against the Valtiokonttori guideline (W9) before showing it.

**F7. Why S-Pankki cares now.** [W10][W11] S-Pankki is buying Oma Säästöpankki (deal expected Q4 2026), and
its CEO calls S-mobiili the centre of the renewal. S-Pankki's own "Suomalaisten talousosaaminen 2026" survey
says about one in six Finns struggle to cover ordinary expenses. [J] A planner that turns S-mobiili users into
well-prepared home buyers (and ASP savers) feeds the mortgage book the OmaSP deal grows; the literacy survey is a
pitch number from S-Pankki itself.

## 3. Next steps (concrete; owner in brackets)
Technical
1. [Pyry] Commit the deployed score + Live rules card; put CONTEXT_DEV_API_KEY in `.env`; restart.
2. [Pyry's Claude] Review and merge `feature/home-readiness` after: `pytest -q tests`, `/api/readiness` for the
   4 personas vs F4, timing (A9).
3. [Pyry's Claude] Plan tab UI per `docs/HOME_READINESS.md`; price slider that re-calls the API; "Ask the coach"
   on the next question; sources drawer (rule W1 + date, assumptions, bank data).
4. [Pyry's Claude] Rules registry: add the ASP rules (W9) as static confirmed rules with source + date; mark the
   loan cap "temporary".
5. [Pyry's Claude] 5 home traps (A6) + 10-question tool-choice check (A7).
6. [Pyry's Claude] Offline mode for rules (A8).
7. [Rasmus's Claude, next] Budget folded into the plan: "monthly room after buying" vs today's basket 3; a
   suggested monthly saving that reaches the reachable price; backtest on the user's last 12 months.
8. [Rasmus's Claude, next] Age split of F4 (brief: young adults) and an ASP view for under-30s.

Business / pitch
9. [Rasmus] Booth (ask Calle Holmberg): "Would you rather show a customer a range and their binding constraint, or
   a single date?" · "Is ASP a priority product for S-Pankki after 1 June?" · "What would a pilot measure: loan
   applications, ASP accounts opened, or customers who can name what blocks them?" · "Is the 6 %/25 y stress test
   what S-Pankki uses, or should we call it only an assumption?"
10. [Rasmus] 5-person hallway test (B5): show Mikko's card for 60 s, ask "what is stopping him?".
11. [Rasmus] Pitch line: "Nordea tells you how healthy your money is. We tell you what is stopping your next big
    decision, prove every number, and ask the one question that changes it."

## Sources
- W1 FIN-FSA press release 30 Jun 2026, "Housing loan cap to be increased to 95% for all borrowers":
  finanssivalvonta.fi/en/publications-and-press-releases/Press-release/2026/macroprudential-decision-housing-loan-cap-to-be-increased-to-95-for-all-borrowers--capital-buffer-requirements-for-banks-to-remain-unchanged/
  (title read; body not loaded) and the STT copy (sttinfo.fi announcement 72171635), paragraph 1.
- W2 taloustaito.fi "Asuntolainaa pienemmillä säästöillä – lainakatto nousee 95 prosenttiin", 30 Jun 2026, first paragraph ("väliaikaisesti").
- W3 nordea.com/fi/uutiset/asuntomarkkinoiden-suunta-muuttuu, first paragraph ("95 prosenttiin kaikille lainanottajille 1.7. alkaen").
- W4 finanssivalvonta.fi/tiedotteet-ja-julkaisut/lehdistotiedotteet/2026/ list: "Pankkien muuttuva lisäpääomavaatimus ja kevennetty lainakatto säilyvät ennallaan".
- W5 nordea.fi … mobiilipankki/taloudenhallinnan-tyokalut.html: tracking, categorisation, budgeting, subscriptions, other banks.
- W6 nordea.com/en/news/nordeas-mobile-feature-helps-customers-take-control-of-their-financial-situation (Financial Health Check, bucket approach) and the 2026 The Banker award news.
- W7 nordea.fi … asp-tili.html: changes from 1 Jun 2026 (no upper age limit, 50 € opening deposit), free state guarantee and interest subsidy for 10 years.
- W8 taloustaito.fi "Asp-lainan saaminen helpottuu": 50-1,500 €/month for at least 20 months; state pays 70 % of interest above 3.8 % for 10 years.
- W9 Valtiokonttori, "Ohje asuntosäästölainoitukseen" 1 Jun 2026 (cdn.valtiokonttori.fi …/Ohje-asuntosaastolainoitukseen_01062026.pdf), §2.
- W10 inderes.fi release "S-Pankki Oyj:n puolivuosikatsaus 1–6/2026": OmaSP offer and S-mobiili at the centre.
- W11 sttinfo.fi release 72453580, S-Pankki "Suomalaisten talousosaaminen 2026" (Kantar, n = 1,117).
- Data: challenge transactions, last 12 months to 30 Sep 2026; replica code in this session, the model is `app/readiness.assess`.
