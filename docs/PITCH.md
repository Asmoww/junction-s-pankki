# Pitch plan (S-Pankki, Junction 2026)

Pyry's Claude, Sat 14 Nov evening. Rasmus owns the video; this is what we say and show live.
Numbers below are Emma's, from the app (data as of 30 Sep 2026). Re-check after any change.

## What makes it unique (say one, show all)
Every team will build "chat with your transactions". Ours differs in five ways, each visible on screen:

1. **Every number is a receipt.** The AI explains; code computes. Each number in an answer is coloured by where it
   comes from (green = your data, grey = your own number, blue = an assumption or calculation, amber = couldn't
   check). Tap a green number and you see the actual payments behind it. A bank can't ship an AI that invents
   amounts; ours can't do it without the customer seeing.
2. **It looks forward, not back.** Home is the balance line to the next payday, with the bills that hit it. You test a
   change and see honestly what it fixes and what it doesn't ("better, still short; the gap comes back every month").
3. **The AI asks the questions.** No chat box on Home: one sentence on where your money stands and the questions
   worth asking this week, picked from your own data and from what you haven't explored yet. That is the brief's
   "explore your own data freely, not fixed charts".
4. **The three baskets are the rules of a game.** Play your next two weeks: rent can't be skipped, surprises come
   anyway, extras are your choice. You learn the baskets by using them, then a guess-first quest checks it.
5. **The AI runs in Finland.** Gemma 4 on a GPU we host in Finland; the model sees totals, never names or account
   numbers. Feasible for a bank today.

**One sentence:** *Ask your own money anything: every number is one tap from the payments behind it, and you see
what's coming before payday and what would really change it.*
Tagline: *See your money's future, and change it.*

## Story (Emma, 23, first job)
She thinks coffee is the problem. Her money says otherwise: rent lands before payday, extras add up, and she spends
about 206 € a month more than she earns. Pausing every extra takes her from −997 € to −676 €: better, still short.
The app doesn't pretend a two-week trick fixes it; it shows her which basket to work on. That honesty is the point.

## Outline: 5 minutes at the table (peer review, demo included)
| Time | Show | Say | Criterion |
|---|---|---|---|
| 0:00 | Phone, Emma's Home | "No Finnish bank lets you talk to your own money yet. Emma is 23, first job, always short before payday, and thinks it's coffee." | Impact |
| 0:25 | The AI sentence, the line, the rent dot | "First thing she sees: one sentence the AI wrote from her numbers, and where her balance is heading. Rent hits on the 3rd; she's 997 € short on payday." | Mobile UX |
| 0:50 | Tap "Why will I run short before payday?" → Coach; talk over the live steps (about 10 s) | "No chat box needed: the AI picked this question for her. Watch what it does: it picks the tools, code calculates every amount." | Originality |
| 1:20 | Tap the green 762.79 € → "From your S-Bank account" → See the payment | "Every number is a receipt. Green is her data, and one tap shows the payments behind it. Blue would be an assumption, amber something it couldn't check." | Feasibility, trust |
| 2:00 | Coach suggestion (or Home → More questions): "What if I paused all my extras until payday?" → chart: usual −997 € vs with the change −676 € | "Her idea: stop all extras. Better. Still short." | Literacy |
| 2:20 | Play your next two weeks: swipe two extras, rent card, result | "Her next two weeks as cards, with the three baskets as rules. Rent can't be skipped; moving it needs the landlord and it's still owed. And the app says it plainly: her months run about 206 € short." | Literacy (baskets) |
| 3:10 | Learn → a quest: guess, then her data | "Then it checks she got it: she guesses under 20 % goes on extras. Her own data says 32 %." | Literacy |
| 3:40 | "What the AI saw" under an answer | "All of this runs on Gemma in Finland. The model sees totals, never her name or account. We test it with 25 trick questions; it passes all 25." | Feasibility, S-mobiili |
| 4:10 | Back to Home | "It's a mobile web view, ready to sit in S-mobiili. See your money's future, and change it." Then: "Questions?" | Integration |

**Two-minute version (stage or video):** 0:00 hook → 0:20 Home sentence + line → 0:40 tapped question + live steps →
1:05 tap green number → payments → 1:25 Pause extras "better, still short" → 1:45 close on the honest gap + tagline.

## Say / never say
- Say "matched to the calculations on her data", never "guaranteed correct" or "verified safe".
- Say "prototype on the challenge's synthetic data"; no real S-mobiili integration or real PSD2 (the other bank is demo data).
- Never present moving rent as a fix. Never "timing beats coffee".
- Quote one trap number, the latest run on the build we demo.

## Likely questions
- **Why not just a chatbot?** A chatbot can't prove its numbers. Ours shows the payments behind each one, and Home works without typing.
- **Hallucinations?** Numbers come from code; the checker colours anything it can't match, and 24 trick questions run against the live coach.
- **Cost / data?** One rented GPU in Finland; totals only leave the database, never identities.
- **What about other banks?** PSD2 consent flow is built (other bank's data is demo data).
- **Does it teach?** Guess-first quests and the three-basket game; we haven't measured learning outcomes, and we say so.

## Before tomorrow
1. `scripts/reset_demo.sh`: clear Sort answers, PSD2 consent and the demo device's learning progress (the todo for 09:45 points at it; it doesn't exist yet).
2. Fallback when the Finland GPU is unreachable: answer on Claude and say so under "What the AI saw" (otherwise the coach shows an error mid-pitch).
3. Coach dates in words ("3 Oct", not "2026-10-03").
4. "See the payments" on bill amounts (rent → her last rent payments), so the receipt moment works on the main demo answer.
5. One fresh trap run on the demo build; quote that number everywhere (README, DEMO, pitch).
6. Then freeze the UI for Rasmus's final capture.
