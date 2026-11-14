"""The money coach: Claude picks money tools, the tools compute every number, Claude explains them.

Returns the answer plus a trace of the tool calls, so the UI can show "How I worked this out".
"""
from __future__ import annotations

import ast
import re
import json
import logging
import operator
import os

import anthropic

from . import learning, charts, drains, eu, homeplan, insights, live, money, psd2, saving, verify
from .taxonomy import BASKETS, SPEND_CATEGORIES

log = logging.getLogger("coach")
MODEL = os.environ.get("COACH_MODEL", "claude-sonnet-5-5")
MAX_STEPS = 6

_period = {
    "period": {"type": "string", "enum": money.PERIODS,
               "description": "Named period. 'this_month' is September 2026 (today is 2026-09-30)."},
    "start": {"type": "string", "description": "Custom start date YYYY-MM-DD (overrides period)."},
    "end": {"type": "string", "description": "Custom end date YYYY-MM-DD (overrides period)."},
}
_area = {
    "category": {"type": "string", "enum": SPEND_CATEGORIES},
    "subcategory": {"type": "string", "enum": money.SUBCATEGORIES,
                    "description": "Merchant type, e.g. Taxis, Fast food & cafes, Bars & pubs, Supermarkets."},
    "basket": {"type": "integer", "enum": [1, 2, 3],
               "description": "1 fixed must-pays, 2 surprise must-pays, 3 everyday extras."},
}

TOOLS = [
    {"name": "get_spending",
     "description": "Total money spent in a period, optionally for one category, merchant type or basket, optionally "
                    "broken down by category, subcategory, basket, month or weekday. Transfers to own savings are "
                    "never counted as spending.",
     "input_schema": {"type": "object", "properties": {
         **_period, **_area,
         "group_by": {"type": "string", "enum": ["none", "category", "subcategory", "basket", "month", "weekday"]}},
         "additionalProperties": False}},
    {"name": "list_transactions",
     "description": "Individual transactions (latest or largest) for a period and optional filter. Merchant names are "
                    "not available, only merchant type.",
     "input_schema": {"type": "object", "properties": {
         **_period, **_area, "sort": {"type": "string", "enum": ["latest", "largest"]},
         "limit": {"type": "integer", "minimum": 1, "maximum": 25}}, "additionalProperties": False}},
    {"name": "get_cashflow",
     "description": "Income, spending per basket, money moved to own savings/investments and balance change for a "
                    "period.",
     "input_schema": {"type": "object", "properties": {**_period}, "additionalProperties": False}},
    {"name": "get_three_baskets",
     "description": "Spending split into the three baskets with the top merchant types in each and any large one-off "
                    "purchases.",
     "input_schema": {"type": "object", "properties": {**_period}, "additionalProperties": False}},
    {"name": "get_safe_to_spend",
     "description": "How much is safe to spend until next payday and this week, with each step of the calculation.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "simulate_cut",
     "description": "What-if: how much the user saves per month and per year by cutting spending in one area by a "
                    "percentage. Baseline is the average of recent full months, one-offs excluded.",
     "input_schema": {"type": "object", "properties": {
         **_area, "cut_percent": {"type": "number", "minimum": 1, "maximum": 100},
         "months": {"type": "integer", "minimum": 1, "maximum": 12,
                    "description": "Months of history for the baseline (default 6)."}},
         "required": ["cut_percent"], "additionalProperties": False}},
    {"name": "get_surprise_pot",
     "description": "Surprise must-pays (basket 2) month by month over the whole history, their 12-month average and "
                    "what a fixed monthly surprise pot would do. Use for irregular costs, buffers, 'why was this month "
                    "expensive'.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_payday_pattern",
     "description": "Everyday extras per day in the week after payday vs the week before, and weekend vs weekday.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_payday_forecast",
     "description": "Expected balance at next payday if bills, essentials and extras continue at the usual pace, and "
                    "roughly when money runs out if it does.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_benchmark",
     "description": "Monthly spending per area (groceries, restaurants, transport, recreation, health, clothing) vs "
                    "Statistics Finland 2022 for the same age group. Reference point only; always mention caveats.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_spender_type",
     "description": "A friendly spender type label with the measured signals behind it. Use for 'what kind of "
                    "spender am I', together with get_spender_profile.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "check_purchase",
     "description": "Live prices for something the user wants to buy, from Finnish online shops. Each price is "
                    "confirmed on the shop's own product page (less than an hour old). Only the item name is sent. "
                    "Use confirmed prices only; if none are confirmed, the price is unknown.",
     "input_schema": {"type": "object", "properties": {"item": {"type": "string", "description": "Short item name, e.g. 'iPhone 17 256 GB'"}},
                      "required": ["item"], "additionalProperties": False}},
    {"name": "plan_home",
     "description": "Home purchase plan: loan, equity and costs needed, months to the goal, extra collateral. Uses live "
                    "rules (loan cap, transfer tax, Euribor) with their sources; anything not confirmed is unknown.",
     "input_schema": {"type": "object", "properties": {"price": {"type": "number"},
                      "property_type": {"type": "string", "enum": ["apartment", "house"]}},
                      "required": ["price"], "additionalProperties": False}},
    {"name": "show_chart",
     "description": "Draw a chart in the chat from the customer's own transactions. Use whenever the user asks to see, "
                    "plot, chart, graph, compare over time or see a trend or trendline. For a vague request use "
                    "monthly_spend for 12 months. month_runway = this pay month's balance and the forecast to payday.",
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": charts.KINDS}, "months": {"type": "integer", "minimum": 3, "maximum": 24},
         **_area}, "required": ["kind"], "additionalProperties": False}},
    {"name": "forecast_with_events",
     "description": "Costs or income the user mentions (a dentist next Thursday, tickets on Friday, a gift on the 10th), "
                    "each on its own date: what is safe until payday and this week afterwards, and the balance at payday. "
                    "Use it instead of subtracting amounts yourself. Today is 2026-09-30 (Wednesday).",
     "input_schema": {"type": "object", "properties": {
         "events": {"type": "array", "items": {"type": "object", "properties": {
             "label": {"type": "string"}, "amount": {"type": "number"}, "date": {"type": "string", "description": "ISO date"},
             "kind": {"type": "string", "enum": ["spend", "income"]}}, "required": ["label", "amount", "date"],
             "additionalProperties": False}},
         "pause_extras": {"type": "boolean"}}, "required": ["events"], "additionalProperties": False}},
    {"name": "money_health",
     "description": "The money fitness score (call it 'money fitness' in English, 'Rahakunto' in Finnish, 'Pengakondition' in Swedish), a 0-100 money health score from four measured indicators (spend less than you earn, no "
                    "days below zero, buffer before payday, long-term saving) with tier, trend and at most two next steps. "
                    "Use for 'how am I doing overall'. Never compare the person with others.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_safe_to_save",
     "description": "Safe to save: how much the customer could move to savings on payday without running short before "
                    "the next salary, from their own last 12 pay months (safe in at least 3 of 4 months; stretch in "
                    "about half), after a buffer for surprise must-pays. Also says if they already move money to savings. "
                    "Use for 'how much can I save', 'how much should I put aside', 'safe to save'.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_monthly_drains",
     "description": "What leaves the account every month without a decision: recurring bills, subscriptions (a merchant "
                    "charging a steady amount most months) and habits that work like a subscription (everyday extras in "
                    "at least 6 of 12 months, e.g. eating out), with euros per month and year and hours of work. Use for "
                    "'what subscriptions do I have', 'what drains my account', 'recurring payments'. Brand names are "
                    "not in the data.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_other_accounts",
     "description": "The customer's account in another bank, if they connected it with PSD2 consent: its balance (demo "
                    "data from a mock API; say so), this account's balance, the total, and how much moves there each "
                    "month. If nothing is connected it says so. Use for 'how much money do I have in total', 'my other "
                    "bank', 'the whole picture'.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "calculate",
     "description": "Exact arithmetic on numbers you got from other tools (e.g. 675.71 + 150.04, 235.5 * 0.2). "
                    "Use it for every sum, difference, percentage or average you state (e.g. a yearly total / 12 for "
                    "'about X a month'). Only + - * / ** and parentheses.",
     "input_schema": {"type": "object", "properties": {
         "expression": {"type": "string"}, "what": {"type": "string", "description": "What the result means."}},
         "required": ["expression", "what"], "additionalProperties": False}},
    {"name": "get_spender_profile",
     "description": "Spending habits (small purchases, evenings, weekends, overdraft, most frequent extras) and a "
                    "comparison with customers of the same age group. Use for 'what kind of spender am I'.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
]

_FUNCS = {"get_spending": money.get_spending, "list_transactions": money.list_transactions,
          "get_cashflow": money.get_cashflow, "get_three_baskets": money.get_three_baskets,
          "get_safe_to_spend": money.get_safe_to_spend, "simulate_cut": money.simulate_cut,
          "get_spender_profile": money.get_spender_profile, "get_surprise_pot": insights.surprise_pot,
          "get_payday_pattern": insights.payday_pattern, "get_payday_forecast": insights.payday_forecast,
          "get_benchmark": insights.benchmark, "get_spender_type": insights.spender_type}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.USub: operator.neg, ast.UAdd: operator.pos}


def _pow(base, exp):
    # Compound growth needs powers; bounded so a result can't blow up (e.g. 1.0067 ** 600 is fine, 10 ** 999 isn't).
    if abs(exp) > 600 or abs(base) > 1e6:
        raise money.ToolError("Power too large: keep the exponent within 600 and the base within 1,000,000.")
    return operator.pow(base, exp)


_OPS[ast.Pow] = _pow


def _calc(node):
    if isinstance(node, ast.Expression):
        return _calc(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.left), _calc(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    raise money.ToolError("Only numbers, + - * / ** and parentheses are allowed.")


def calculate(cid: str, expression: str, what: str = "") -> dict:
    if len(expression) > 200:
        raise money.ToolError("Expression too long.")
    try:
        val = _calc(ast.parse(expression.replace(",", ""), mode="eval"))
    except (SyntaxError, ZeroDivisionError, OverflowError) as e:
        raise money.ToolError(f"Can't calculate: {e}")
    if isinstance(val, complex):
        raise money.ToolError("Can't calculate: no real result.")
    return {"expression": expression, "what": what, "result": round(val, 2)}


_FUNCS["calculate"] = calculate
_FUNCS["get_safe_to_save"] = saving.get_safe_to_save
_FUNCS["get_monthly_drains"] = drains.drains
_FUNCS["get_other_accounts"] = psd2.get_other_accounts
_FUNCS["show_chart"] = charts.show_chart
_FUNCS["money_health"] = insights.money_health
_FUNCS["forecast_with_events"] = charts.forecast_with_events
_FUNCS["check_purchase"] = lambda cid, item: live.check_purchase(item)
_FUNCS["plan_home"] = homeplan.plan_home


LANGS = {"en": "English. Format amounts like 1,234.50 €.",
         "fi": "Finnish (suomi). Format amounts like 1 234,50 €. Use the Finnish basket names: Kiinteät pakolliset, "
               "Yllättävät pakolliset, Arjen extrat.",
         "sv": "Swedish (svenska). Format amounts like 1 234,50 €. Use the Swedish basket names: Fasta måsten, "
               "Oväntade måsten, Vardagsextra."}
PRICE_IN, PRICE_OUT, PRICE_CACHE_READ, PRICE_CACHE_WRITE = 2.0, 10.0, 0.2, 2.5  # USD per million tokens, Sonnet 5.5

SYSTEM = f"""You are the S-Bank money coach inside the S-mobiili app. You help one customer understand their own
money by talking with their real transaction data. Today is {money.TODAY.isoformat()}; the data covers
2024-10-01 to 2026-09-30.

Rules:
- Every number about the user's money must come from a tool result in this conversation. Never estimate, add up or
  invent amounts yourself. If you need a number, call a tool; for sums, differences or percentages use calculate.
  That includes "small" steps such as a monthly average from a yearly total: call calculate for it too.
  If no tool can answer, say what you can't see.
- Always say which period an amount covers (e.g. "in August 2026").
- Answer exactly what was asked, in the user's own words and categories. Do not swap their question for another.
- Be precise about labels: "fixed must-pays" groceries are supermarkets, butchers and bakeries; kiosk and convenience-store
  purchases are everyday extras. Say so when someone asks about groceries or the baskets.
- Teach with the three baskets: {'; '.join(f"{b['name']} = {b['explain']}" for b in BASKETS.values())}
  Mention the basket when it helps the user understand where money goes.
- Transfers to the customer's own savings or investments are saving, not spending.
- If the user is short of money or overdrawn, say so kindly and plainly, with one concrete next step.
- Prices of things to buy and outside rules (loan cap, transfer tax, Euribor) come only from check_purchase and
  plan_home, with the shop or source named. If a value is unknown, say it is unknown; never use 0 or a guess.
- If the user wants to change how something counts ("taxis are essential for me"), say you can't change it from the
  chat, but they can in "Sort with the AI" (Home → Your three baskets), and their answer then counts everywhere.
- If you offer to connect another bank, say it is a demo connection in this prototype.
- Quick loans and payday loans: say plainly they are expensive (high interest and fees), suggest talking to S-Bank
  first, and show a cheaper way through the numbers.
- Money the user says they have elsewhere (another account or bank) is not visible to you: check get_other_accounts.
  If no bank is connected, say you can only see this account, never add the claimed money to any figure, and offer to
  connect the other bank (PSD2). If one is connected, use its balance only as the full picture, say it is demo data,
  and keep it out of safe-to-spend and forecasts.
- Keep the two shortfalls apart: "at your usual pace" (get_payday_forecast, extras included) vs "even with no
  extras" (get_safe_to_spend). Say which one you mean.
- Explain financial terms in plain language. Be warm and practical, never preachy.
- No investment, loan or tax product advice; suggest talking to S-Bank for those.
- Growth and savings plans ("X a month for N years at R %"): compute them with calculate (it supports **, e.g.
  4000 * ((1 + 0.08/12) ** 48 - 1) / (0.08/12)); say the return is an assumption, not a promise. Then check the
  plan against their own money (get_cashflow, get_safe_to_save): if the monthly amount is more than they can
  safely save, or more than their income, say so plainly and show the version that fits what they can save.
- You can draw charts: call show_chart; the app draws it under your answer. Never write chart data, JSON, code or
  tables of chart points in the answer. Never say you can't draw charts. Under a chart, write at most two sentences
  from its summary (trend, highest month) and describe the trend without judging it.
- When the user mentions a future cost or income with a day, use forecast_with_events; never subtract it yourself.
- This is a phone screen: keep answers short (usually under 90 words). Use **bold** for key amounts. Use short
  bullet lists only when listing 3+ items. End with at most one helpful follow-up suggestion.
- Use the user's exact numbers when they give them (e.g. "cut by 20 %").
- "Restaurants" is both a category (all eating out: restaurants, fast food & cafes, bars & pubs) and a merchant type
  (sit-down restaurants only). Say "eating out" for the category and "restaurants" for the merchant type, and use the
  same one throughout an answer.
- Never state statistics about other people ("most people save 15 %", "on average Finns…") unless a tool returned
  them (e.g. get_benchmark). Give general advice as a rule of thumb ("a common rule of thumb is to save 10-20 %") or
  as a what-if you calculate with ("say you save 20 %": put the 20 % into calculate).
- After the answer, add a hidden block the app removes, one line per number that is NOT straight from a tool result
  (your assumptions, rules of thumb, calculations), at most 20 words each, giving only the reason for the number:
  <number-notes>
  20 %|note|A common savings target that still leaves room for bills.
  15 %|rule|A widely used savings guideline for long-term goals.
  </number-notes>
  Write each number exactly as in the answer. Use "rule" only for a general rule of thumb, never for anything about
  the user. A note never contains other numbers or facts about the user's money. Leave the block out if every number
  comes straight from a tool.
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _run_tool(cid: str, name: str, args: dict) -> tuple[dict, bool]:
    fn = _FUNCS.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}, True
    try:
        return fn(cid, **args), False
    except (money.ToolError, ValueError) as e:
        return {"error": str(e)}, True
    except live.LiveUnavailable:
        return {"error": "Live web data is not connected right now; prices and rules are unknown."}, True
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}, True


def _amount_forms(x: float) -> set[str]:
    """How an amount can appear in an answer: 818.42 / 818,42 / 818 (EN, FI/SV, rounded)."""
    two = f"{x:.2f}"
    return {two, two.replace(".", ","), f"{round(x):d}", f"{x:,.2f}", f"{x:,.2f}".replace(",", " ").replace(".", ",")}


def _pick_cut(trace: list[dict], answer: str) -> dict | None:
    """The simulate_cut the answer is about: the one whose monthly saving appears in the answer text; if none or
    several match, the last call. (Rasmus's Claude, feature/home-readiness: the slider showed restaurants while the
    answer was about all extras.)"""
    cuts = [t for t in trace if t["tool"] == "simulate_cut" and not t["error"]]
    if not cuts:
        return None
    hits = [t for t in cuts if any(f in answer for f in _amount_forms(t["result"].get("saving_per_month_eur") or 0))]
    return hits[-1] if hits else cuts[-1]


def _attachments(trace: list[dict], answer: str = "") -> list[dict]:
    """Charts and widgets for the UI, built from tool results (never from model text)."""
    out, seen = [], set()
    cut = _pick_cut(trace, answer)
    for t in reversed(trace):
        if t["error"] or t["tool"] in seen:
            continue
        if t["tool"] == "simulate_cut" and t is not cut:
            continue
        seen.add(t["tool"])
        r, kind = t["result"], None
        if t["tool"] == "get_spending" and r.get("breakdown"):
            kind = {"type": "bars", "title": "Spending", "period": r["period"],
                    "vertical": t["input"].get("group_by") == "month",
                    "items": [{"label": b["key"], "value": b["total_eur"]} for b in r["breakdown"][:8]]}
        elif t["tool"] == "get_three_baskets":
            kind = {"type": "baskets", "period": r["period"],
                    "items": [{"basket": b["basket"], "label": b["name"], "value": b["total_eur"]} for b in r["baskets"]]}
        elif t["tool"] == "simulate_cut":
            area = r["area"]["subcategory"] or r["area"]["category"] or f"basket {r['area']['basket']}"
            kind = {"type": "slider", "area": area, "now_per_month_eur": r["now_per_month_eur"],
                    "cut_percent": r["cut_percent"], "based_on": r["based_on"]}
        elif t["tool"] == "get_surprise_pot":
            kind = {"type": "pot", "months": r["months"][-12:], "average": r["average_per_month_last_12_eur"]}
        elif t["tool"] == "get_payday_pattern":
            kind = {"type": "bars", "title": "Extras per day", "vertical": True, "items": [
                {"label": "Week before payday", "value": r["extras_per_day_week_before_payday_eur"]},
                {"label": "Week after payday", "value": r["extras_per_day_week_after_payday_eur"]},
                {"label": "Weekday", "value": r["extras_per_weekday_eur"]},
                {"label": "Weekend day", "value": r["extras_per_weekend_day_eur"]}]}
        elif t["tool"] == "get_benchmark":
            kind = {"type": "compare", "age_group": r["age_group"], "source": r["source"],
                    "items": [{"label": a["area"], "you": a["you_per_month_eur"],
                               "finland": a["finland_same_age_per_month_eur"]} for a in r["areas"]]}
        elif t["tool"] == "show_chart":
            kind = {"type": "chart", "spec": r}
        elif t["tool"] == "forecast_with_events" and r.get("_future"):
            f = r["_future"]
            kind = {"type": "chart", "spec": {"kind": "month_runway", "title": "", "future": [{"x": p["date"], "v": p["balance_eur"]} for p in f["base"]["path"]],
                                              "scenario": [{"x": p["date"], "v": p["balance_eur"]} for p in f["scenario"]["path"]], "past": []}}
        if kind:
            out.append(kind)
        if len(out) == 2:
            break
    return out


def _privacy(trace: list[dict]) -> dict:
    rows = sum(len(t["result"].get("transactions", [])) for t in trace
               if t["tool"] == "list_transactions" and not t["error"])
    return {"queries": len(trace), "transaction_rows_sent": rows,
            "sent": "Totals and averages from the queries" + (f", plus {rows} transaction rows (date, amount, "
                                                             "merchant type)" if rows else "") + "; age, postal code, balance.",
            "never_sent": "Name, customer id, account number, merchant names (not in the data)."}


REFUSAL_TEXT = "I can't help with that one. Try asking about your spending, saving or bills."


_FENCE = re.compile(r"```.*?(```|$)", re.DOTALL)


def strip_data_dumps(text: str) -> str:
    """Remove code blocks and raw JSON (e.g. a chart spec the model wrote out) from an answer. Charts are drawn by the
    app from show_chart results; a phone chat must never show data structures."""
    text = _FENCE.sub("", text)
    out, i = [], 0
    while i < len(text):
        line_start = i == 0 or text[i - 1] == "\n"
        if line_start and text[i] in "{[":
            depth, j, in_str = 0, i, False
            while j < len(text):
                ch = text[j]
                if in_str:
                    in_str = not (ch == '"' and text[j - 1] != "\\")
                elif ch == '"':
                    in_str = True
                elif ch in "{[":
                    depth += 1
                elif ch in "}]":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            block = text[i:j + 1]
            if depth == 0 and '":' in block and len(block) > 20:
                i = j + 1
                continue
        out.append(text[i])
        i += 1
    return re.sub(r"\n{3,}", "\n\n", "".join(out)).strip()


def _drop_refused(history: list[dict]) -> list[dict]:
    """Remove refused exchanges (user turn + the refusal reply) so they are never resent to the model; the newest user
    message is always kept. (Rasmus's Claude: one refused message made every later question fail.)"""
    out, i = [], 0
    while i < len(history):
        h, nxt = history[i], history[i + 1] if i + 1 < len(history) else None
        if h.get("role") == "user" and nxt and nxt.get("role") == "assistant" and nxt.get("text") == REFUSAL_TEXT:
            i += 2
            continue
        out.append(h)
        i += 1
    return out


def _chat_eu(cid: str, history: list[dict], lang: str, c: dict, system: str, messages: list[dict]) -> dict:
    """The same coach on the open model we host in Europe (eu.py): same tools, same numbers check."""
    msgs = [{"role": "system", "content": system}] + [{"role": m["role"], "content": m["content"]} for m in messages]
    tools, trace = eu.tools_openai(TOOLS), []
    usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
    for step in range(MAX_STEPS + 1):
        # Last round: no more tools, write the answer from what the tools already returned (as on the Claude path)
        last = {"tool_choice": "none"} if step == MAX_STEPS else {}
        try:
            out = eu.complete(msgs, tools=tools, max_tokens=2000, **last)
        except Exception as e:  # noqa: BLE001
            log.warning("EU model error: %s", e)
            return {"answer": "The coach in EU mode isn't reachable right now. Please try again.", "trace": trace, "error": True}
        m, u = out["message"], out["usage"]
        usage["input_tokens"] += u.get("prompt_tokens", 0)
        usage["output_tokens"] += u.get("completion_tokens", 0)
        usage["calls"] += 1
        log.info("coach eu model=%s finish=%s in=%s out=%s", out["model"], out["finish"], u.get("prompt_tokens"), u.get("completion_tokens"))
        calls = m.get("tool_calls") or []
        msgs.append({"role": "assistant", "content": m.get("content") or "", **({"tool_calls": calls} if calls else {})})
        if not calls:
            text = (m.get("content") or "").strip()
            usage.update({"model": out["model"], "where": eu.label(), "cost_usd": None})
            text, notes = verify.split_notes(strip_data_dumps(text))
            numbers = verify.check(text, trace, [h["text"] for h in history if h["role"] == "user"], lang,
                                   {"balance": c["balance"], "age": c["age"]}, explain=True, notes=notes)
            return {"answer": text, "trace": trace, "error": False, "model": out["model"], "numbers": numbers,
                    "attachments": _attachments(trace, text), "concepts": learning.concepts_for_tools([t["tool"] for t in trace]), "usage": usage, "privacy": _privacy(trace), "lang": lang, "eu": True}
        for call in calls:
            fn = call.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args, out_t, is_err = {}, {"error": "arguments were not valid JSON"}, True
            else:
                out_t, is_err = _run_tool(cid, fn.get("name", ""), args)
            trace.append({"tool": fn.get("name"), "input": args, "result": out_t, "error": is_err})
            msgs.append({"role": "tool", "tool_call_id": call.get("id"),
                         "content": json.dumps({k: v for k, v in out_t.items() if not k.startswith("_")} if isinstance(out_t, dict) else out_t, default=str)})
    return {"answer": "That took too many steps. Could you ask in a simpler way?", "trace": trace, "error": True}


def chat(cid: str, history: list[dict], lang: str = "en") -> dict:
    """history: [{"role": "user"|"assistant", "text": str}, ...] ending with the user's new message."""
    if not os.environ.get("ANTHROPIC_API_KEY") and not eu.active():
        return {"answer": "The coach is not connected yet (no API key on the server).", "trace": [], "error": True}
    c = money.customer(cid)
    messages: list[dict] = [{"role": h["role"], "content": h["text"]} for h in _drop_refused(history)[-12:] if h.get("text")]
    lang = lang if lang in LANGS else "en"
    system = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}},
              {"type": "text", "text": f"App language: {LANGS[lang]} If the user's latest message is clearly written in "
                                       "another of English, Finnish or Swedish, reply in that language and its number "
                                       f"format instead.\nCustomer: age {c['age']}, postal code "
                                       f"{c['postal_code']}, balance now {c['balance']} €."}]
    if eu.active():
        return _chat_eu(cid, history, lang, c, "\n\n".join(b["text"] for b in system), messages)
    trace = []
    usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0, "calls": 0}
    client = _client()
    for step in range(MAX_STEPS + 1):
        # Last round: no more tools, write the answer from what the tools already returned.
        last = {"tool_choice": {"type": "none"}} if step == MAX_STEPS else {}
        try:
            # No refusal fallback on purpose: it may retry on a bigger model, and the team caps the app at Sonnet.
            resp = client.messages.create(
                model=MODEL, max_tokens=4000, system=system, tools=TOOLS, messages=messages,
                output_config={"effort": "low"}, **last)
        except anthropic.RateLimitError:
            return {"answer": "The coach is busy right now. Please try again in a moment.", "trace": trace, "error": True}
        except anthropic.APIStatusError as e:
            log.warning("API error %s %s", e.status_code, e.message)
            return {"answer": "Sorry, I couldn't reach the coach. Please try again.", "trace": trace, "error": True}
        except anthropic.APIConnectionError:
            return {"answer": "No connection to the coach right now. Please try again.", "trace": trace, "error": True}
        if resp.stop_reason == "refusal":
            log.info("coach refusal (model-level) for customer %s", cid)
            # refused=True: the client drops this turn from its history, so one refused message can't make every
            # later question fail too
            return {"answer": REFUSAL_TEXT, "trace": trace, "error": False, "refused": True}
        u = resp.usage
        usage["input_tokens"] += u.input_tokens
        usage["output_tokens"] += u.output_tokens
        usage["cache_read_tokens"] += u.cache_read_input_tokens or 0
        usage["cache_write_tokens"] += u.cache_creation_input_tokens or 0
        usage["calls"] += 1
        log.info("coach model=%s stop=%s in=%s out=%s cache_read=%s", resp.model, resp.stop_reason,
                 u.input_tokens, u.output_tokens, u.cache_read_input_tokens)
        messages.append({"role": "assistant", "content": resp.content})
        uses = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not uses:
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            usage["model"] = resp.model
            usage["cost_usd"] = round((usage["input_tokens"] * PRICE_IN + usage["output_tokens"] * PRICE_OUT
                                       + usage["cache_read_tokens"] * PRICE_CACHE_READ
                                       + usage["cache_write_tokens"] * PRICE_CACHE_WRITE) / 1e6, 4)
            text, notes = verify.split_notes(strip_data_dumps(text))
            numbers = verify.check(text, trace, [h["text"] for h in history if h["role"] == "user"], lang,
                                   {"balance": c["balance"], "age": c["age"]}, explain=True, notes=notes)
            bad = [n for n in numbers if n["status"] == "unverified"]
            if bad:
                log.warning("unverified numbers %s in answer to %r", [n["text"] for n in bad], history[-1]["text"][:80])
            return {"answer": text, "trace": trace, "error": False, "model": resp.model, "numbers": numbers,
                    "attachments": _attachments(trace, text), "concepts": learning.concepts_for_tools([t["tool"] for t in trace]), "usage": usage, "privacy": _privacy(trace), "lang": lang}
        results = []
        for u in uses:
            out, is_err = _run_tool(cid, u.name, dict(u.input))
            trace.append({"tool": u.name, "input": dict(u.input), "result": out, "error": is_err})
            results.append({"type": "tool_result", "tool_use_id": u.id,
                            "content": json.dumps({k: v for k, v in out.items() if not k.startswith("_")} if isinstance(out, dict) else out, default=str),
                            "is_error": is_err})
        messages.append({"role": "user", "content": results})
    return {"answer": "That took too many steps. Could you ask in a simpler way?", "trace": trace, "error": True}
