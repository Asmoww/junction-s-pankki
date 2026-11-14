# Verda Compute Track: a banking coach whose AI stays in Finland

**One line:** our S-Pankki money coach can run every AI job on Gemma 4 that we host ourselves on a Verda GPU in
Finland, instead of a US model API. The customer's transactions never leave the bank's side; the model only ever sees
computed totals, and every number it writes is checked against the data before it is shown.

## Why this needs Verda (and why not a laptop)
A bank cannot send customers' money questions to someone else's API in another jurisdiction. The coach needs a model
that is strong enough for multi-step tool use (6-8 tools per answer), fast enough for a chat (1-3 s), and able to
pre-compute AI notes and a "money year" story for millions of customers. That is a 31B model on a 96 GB GPU, in the
EU, under our control: Verda's GPU instances in Finland, on renewable energy.

## Product choice
| Verda product | Used for | Why |
|---|---|---|
| **GPU instance**, 1× RTX PRO 6000 Blackwell (96 GB), FIN-03, spot | vLLM 0.33 serving `google/gemma-4-31B-it` (also tested `gemma-4-26B-A4B-it`) | Gemma 4 isn't in the managed catalogue; 96 GB fits the 31B dense model in bf16 with room for a 32k context; spot at 1.42 €/h while testing |
| Cloud API (OAuth client credentials) | create SSH key, list availability and prices, launch and stop the instance from our server | everything scripted, nothing clicked |
| *(next)* Batch jobs / serverless containers | the nightly pre-compute for all customers; scale to zero between runs | see "From demo to a bank" |

The vLLM server listens only on the instance's localhost; our app server reaches it through an SSH tunnel (a systemd
service), with an API key on top. No model port is open to the internet.

## What runs on Gemma in Finland (switch "AI in Finland" in the app header)
The coach (tool use: spending, safe-to-spend, forecasts, charts, purchase checks), AI notes on the balance graph,
Money Wrapped captions, "Sort with the AI" questions, the "Play your next two weeks" plan and summary, and the
"What if…" parser. The app sends `X-AI-Provider: eu`; one module (`app/eu.py`) routes every AI call to the
OpenAI-compatible vLLM endpoint (tool calls via vLLM's `gemma4` parser, structured output via JSON-schema guided
decoding). Caches are kept apart per provider.

## Results (14 Nov 2026)
**Quality: our 22-question trap suite** (real customer-data questions where AI money coaches go wrong: wrong "last
month", transfers counted as spending, invented merchants, prompt injection for another customer's data, quick-loan
advice, made-up projections…), run against the live coach, every number checked against the data:

| Model | Traps passed | Numbers matched to the data |
|---|---|---|
| Claude Sonnet 5.5 (US API, reference) | 21-22 / 22 | 97 / 99 |
| Gemma 4 26B-A4B on Verda (first try) | 18 / 22 | 51 / 52 |
| Gemma 4 31B on Verda (first try) | 21 / 22 | 47 / 47 |
| Gemma 4 31B on Verda, after two prompt rules + temperature 0 (two runs) | **21 / 22, 21 / 22** | **46 / 46, 47 / 47** |

How we improved it: we read every failed answer. Gemma added money the user *claimed* to have in another bank
("you have 5,000 € available") and skipped why quick loans are a bad idea. Two plain rules in the coach's
instructions fixed both (3/3 reruns each) and are good coaching for any model. Sampling temperature 0 made runs
repeatable (the 31B varied 20-21/22 at 0.2). The one remaining miss: for a cost next week, it doesn't restate this
week's unchanged figure.

**Speed:** a JSON job 1.7 s, a coach answer with a tool call 1-3 s (faster than the US API in our tests).

**Scale test** (`scripts/eu_batch.py`): AI notes + 9 Wrapped captions for **200 random customers, 0 failures, 306 s**
on one GPU with 16 parallel requests = **1.5 s per customer**; 400 model calls, 339k input / 41k output tokens;
100 % of captions passed the number check.

## From demo to a bank
S-Bank has 3.5 M customers. At the measured 1.5 s per customer (the facts are computed on our side, so this is an
upper bound for the GPU), one full nightly refresh of notes and Wrapped is about **1,500 GPU-hours**: about
**4,200 €** on on-demand RTX PRO 6000s or 2,100 € on spot, i.e. **0.1-0.2 cents per customer**. Running it as a Verda
batch job across 40 GPUs finishes in under 40 hours; most customers' data changes little day to day, so a real
schedule refreshes only accounts with new transactions. The chat stays on an always-on serving pool sized to traffic,
in the EU, on infrastructure the bank controls.

## Path from idea to prototype
1. Built the coach on a US API first, with all numbers from code and a checker for every number the AI writes.
2. Abstracted every AI call behind one switch (`app/eu.py`); faked the endpoint in an offline test.
3. Verda: API credentials → SSH key → availability (no on-demand GPU free in FIN-01/02; spot RTX PRO 6000 in FIN-03)
   → launch → vLLM + Gemma 4 26B up in about 4 minutes → SSH tunnel → app switch.
4. Trap suite on both Gemma sizes, read the failures, fixed the instructions, re-ran; batch test for scale.

Code: `app/eu.py`, `app/coach.py` (`_chat_eu`), `scripts/run_traps.py --eu`, `scripts/eu_batch.py`.
