# Vision

Draft by Rasmus's Claude, 14 Nov. For Pyry and Asmoww to accept, change or reject. Nothing here changes code.

## Why this doc exists

We have five taglines and twenty features, and they don't all point the same way:

| Where | Line |
|---|---|
| DEMO.md (Asmoww) | "See your money's future, and change it." |
| BRIEF-FIT.md | "Shows what your money will do before payday, lets you question and correct it, and proves every number." |
| RESEARCH-NEXT.md | "We tell you what is stopping your next big decision, prove every number, and ask the one question that changes it." |
| Video v7 | "Your money. Your next question." / "They drown you in graphs. We give you one line." |
| Learning notes | "It learns from you, not about you." |

They don't contradict each other. They describe the same product from different features. The fix is to
pick one sentence, keep Asmoww's tagline (the demo, the UI and the video already use it), and hang every
feature off it. If a feature doesn't fit, it gets demoted.

## The vision

**See your money's future, and change it.**

Long version, for the pitch and the README:

> Your S-mobiili already knows where your money went. We show where it's going: one line, from today to
> your next payday and beyond. Ask it anything in your own words and it answers from your own data. Change
> the line in words ("what if I pay rent after payday?") and watch it move. Every number on screen is
> checked against your transactions, and the more you correct it, the better it knows you.

The problem it solves, in one line: **people don't run out of money because of coffee. They run out because
of timing.** In the dataset, half of all overdraft moments happen in the last 7 days before payday, and
purchases under 10 € are only 15 % of extras (DEMO.md, computed 14 Nov 02:40). A backward-looking pie chart
of categories can't show timing. A line into the future can.

Who it's for first: a young adult with a first job (Emma, 23), for whom the week before payday is the hard
part. The same line scales up to a big decision (Ville, 32, buying a home).

## The shape: one line, three verbs, two promises

```
                 SEE  ──────  ASK  ──────  CHANGE
          (the line ahead)  (in your words)  (move the line)
        ─────────────────────────────────────────────────
        Promise 1  PROVEN: every number comes from code and is matched to your data
        Promise 2  LEARNS FROM YOU: your corrections and questions make it yours
```

The line is the product. Chat is how you talk to it. Everything else either makes the line clearer, answers a
question about it, or moves it.

### SEE: the line
| Feature | Role | Status |
|---|---|---|
| Forecast balance line with the three baskets on it | The home screen. You see which basket sinks the line | Live |
| AI notes on the line | Explain the line's shape in one sentence each | Live |
| Trend ranges (pay period / 3 m / 12 m / 2 y) | Zoom out: the past that explains the future | `feature/trend-range`, needs Pyry |
| Safe to spend | The line's lowest point before payday, as one number | Live |
| Safe to save | The same idea after payday: what you can move without the line dipping | Live (ported) |
| PSD2 full picture | Money in your other bank goes on the same line | Live (mock) |
| Your money year (Wrapped) | The line looking back over twelve months. "Show the data simply, then turn it into insights" | Live |

### ASK: the coach
| Feature | Role | Status |
|---|---|---|
| Coach chat (EN/FI/SV, voice) | Any question about your money, in your words | Live |
| Charts in answers | The coach shows, not only tells | Live |
| "How I worked this out" | Opens the tools and numbers behind each answer | Live |
| Benchmarks (Statistics Finland) | Context inside answers, not a screen of its own | Live |

### CHANGE: move the line
| Feature | Role | Status |
|---|---|---|
| What-if in words | "Concert 150 € on Friday" moves the line | Live |
| Play your next two weeks | Swipe your likely spending; the baskets set the rules | Live |
| Scenario planner (Monte Carlo over your own months) | The honest version of what-if: bad / typical / good, assumptions shown and editable | `feature/home-readiness` |
| Check a purchase (live prices) | A single big buy dropped on the line | Live |
| Home readiness + loan rules | The biggest change: when can I buy, and what's blocking me | `feature/home-readiness` |
| Budgets | **A budget is a what-if you decide to keep.** Save a scenario, it becomes a target on the line, and the coach tells you when the real line drifts from it | Not built |

The budget idea solves an open question from earlier: Rasmus asked for a budgeting tab and a purchase/loan
planner, and they looked like separate products. They aren't. Both are saved changes to the line, built on
the engine that already runs what-if and the scenario planner. One "Plan" tab holds them: your saved
scenarios, your budgets, your big purchase.

### Promise 1: proven
| Feature | Role |
|---|---|
| Verified numbers (verify.py) | Every € and % in an answer is matched to tool results, and flagged if not |
| Trap suite (nightly, shown on Learn) | Public proof the coach can't be tricked into making numbers up |
| Live rules with sources | Loan cap, Euribor, transfer tax read from FIN-FSA / vero.fi, with dates |
| Privacy summary, EU mode (Gemma in Finland) | What the AI saw, and that a bank can keep it in Europe |

This is the feasibility and S-mobiili answer in one: a bank can't ship a coach that invents numbers.

### Promise 2: learns from you
| Feature | Role | Status |
|---|---|---|
| Three baskets | The brief's pedagogy: the vocabulary for everything above | Live |
| Sort with the AI | Your answers re-sort your money everywhere | Live |
| Corrections in chat ("taxis are essential for me") | Same as Sort, from a sentence | Not built |
| Curiosity map + guesses | Rewards wanting to learn: explore each idea once, guess before you see | `feature/learning-progress` |

"Learns from you, not about you" means: no model trained on customer data. It uses your own history as the
baseline and keeps your corrections as an overlay. That's honest about what we built, and it's the privacy
story too.

## What gets demoted

| Feature | Why | Where it goes |
|---|---|---|
| Rahakunto / money fitness score | A score of your past doesn't tell you where you're heading. Judges asked "what do I do with 19?" | A sheet from Learn, not a Home card |
| Live rules card on Home | Only matters inside a big decision | Inside the home planner |
| Spender type | Interesting once, not daily | A Wrapped slide |
| Monthly drains, extra cards | Good facts, but each one is a fifth thing on Home | Fold into AI notes on the line |

The rule for Home: if it isn't the line, a note on the line, or a door to Ask or Change, it doesn't go there.

## How it maps to judging (20 % each)

| Criterion | What carries it |
|---|---|
| Financial literacy | Three baskets on the line; timing as the lesson; curiosity map and guesses |
| Originality of AI | You change your future in words; every number proven |
| Mobile UX | One line, three verbs; Home has nothing else |
| Feasibility | Numbers from code, traps, about 2 cents an answer, EU mode |
| S-mobiili fit | Web view on the bank's own APIs; payday push; PSD2 on the same line |

## The test for anything new

Before building or demoing something, ask:

1. Does it make the line clearer, answer a question about it, or change it?
2. Can every number in it be proven against the data?
3. Does it demonstrate the core concept better than what's already in the demo?

Two yeses and it can be built. Three and it can go in the demo. This replaces "is it cool".

## Open decisions (Pyry and Asmoww)

- Accept the tagline as the vision, or replace it.
- A "Plan" tab (saved scenarios, budgets, big purchase) vs keeping Change only as buttons on Home.
- Whether the money fitness score leaves Home before Sunday.
