# Context.dev side challenge: how it could fit the money coach

Status: options for the team (2026-11-14), nothing built yet. The challenge needs at least one Context.dev
endpoint **in the core flow**, with its data **visibly driving the demo**, plus a note on endpoints and why.
API facts below are from docs.context.dev (agent quickstart, credits, monitors pages).

## Ground rules for any option
- **No customer data leaves the bank.** We send only generic queries ("HSL monthly ticket price", "12-month
  Euribor"), never amounts, ids or transactions. Say this on the slide; it matters to S-Pankki.
- **Numbers still come from code.** A live web value enters as a tool result with its source URL, so the existing
  "verified numbers" check covers it, and the UI shows a source chip.
- **Cache results** (store in our DB; set `maxAgeMs: 0` only when freshness matters). We have 50,000 credits.
- Check every output's `success` flag; a 200 response can still hold a failed output.

## Options, ranked

### 1. "Can I afford it?" with live prices (core flow, strongest)
The user names a thing, not a number: "Can I afford a weekend in Levi in February?", "When can I buy an iPhone 17?".
The coach calls a new tool `live_price(query)`, then the existing safe-to-spend / goal planner computes yes, no or when.
- Endpoints: `POST /web/answers` in fast mode (task + `json_format` → `{price_eur, what, source_url}`, 10 credits),
  or `POST /web/search` + `POST /web/scrape` with format `json` (1 + 1 + 4 credits).
- Visible in the demo: the price card shows the live price, the shop's logo and "checked today at verkkokauppa.com".
  The answer changes if the price changes.
- Why it wins: it turns the brief's "Can I afford…" from a number the user must know into a real-world question,
  and fits S-Pankki's booth ask (a purchase/loan planner).

### 2. Cheaper switches with live public prices (core of what-ifs)
The what-if tool compares the user's own spending with a live alternative. For example, taxis and parking
(Emma: 12 parking payments, 535 € in 6 months) vs an HSL season ticket, or utilities vs current electricity offers.
- Endpoints: `POST /web/scrape` with format `json` and a schema `{product, price_eur, period}` on the official
  price page (hsl.fi, etc.), cached daily.
- Visible: "An HSL 30-day ticket costs X € today (hsl.fi). You spent Y € on parking and taxis last month: switching
  saves Z € a month." X comes from Context.dev, Y and Z from our data.

### 3. Every outside fact has a live source (extends "verified numbers")
Facts the coach needs that aren't in the bank data, fetched live with a source URL: the 12-month Euribor (for the loan
planner's payment), the transfer tax rate, the loan cap, Kela student aid amounts.
- Endpoint: `POST /web/answers` (fast) with a `json_format`, or `scrape` + `json` on a fixed official page.
- Visible: in "How I worked this out", a fact chip ("Euribor 12 m: x.xx %, suomenpankki.fi, today"). The verified-
  numbers badge counts outside facts too.

### 4. Monitors → proactive cards ("react when the web changes")
Monitor a few pages (Euribor, electricity prices, HSL fares, S-Pankki's rate page). On `change.detected`, the webhook
(through our Cloudflare tunnel, signed, deduplicated on `X-Context-Id`) recomputes the affected forecasts and posts a
card: "Euribor fell: the payment in your home plan drops by X €/month."
- Endpoints: `POST /monitors` (target `extract`, 10 credits per run, default daily), webhook receiver.
- Demo risk: changes are slow, so show one real detected change or trigger a run by hand. Good as the second act.

### 5. Merchant logos from transaction descriptors (production story, not the demo)
`POST /brand/retrieve` accepts a **transaction descriptor**, which is exactly what bank statements contain. It returns
the logo, colours and company info. That would make transaction lists and the "monthly receipt" design recognisable.
- Limitation: the challenge data has only anonymous merchant ids (`MRC-GRO-0035`), so we can't show it honestly on
  the synthetic customers. Mention it as the production path; don't fake mappings.

## Recommendation
Build **1 as the core flow** and **3 as the trust layer** (same tool pattern, a few hours), with **4** if time allows.
Endpoints for the submission note: `/web/answers` (live prices and facts as JSON with sources), `/web/scrape` with
`json` (fixed official price pages), `/monitors` (react to changes). Estimated use for the demo and testing:
< 5,000 credits [est].

## Open questions
- **Rules:** can one project enter both the S-Pankki challenge and the Context.dev challenge? (Rasmus is already
  asking the info desk about two projects; ask this too.)
- **Account:** someone needs to sign up and redeem `JUNCTION26`. The key goes in `.env` as `CONTEXT_DEV_API_KEY`
  (Python: `pip install context.dev`, `from context.dev import ContextDev`).
- Which Finnish shops allow automated access (respect their terms); prefer official pages and big retailers.
