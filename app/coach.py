"""The money coach: Claude picks money tools, the tools compute every number, Claude explains them.

Returns the answer plus a trace of the tool calls, so the UI can show "How I worked this out".
"""
from __future__ import annotations

import ast
import json
import logging
import operator
import os

import anthropic

from . import homeplan, insights, live, money, verify
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
    {"name": "calculate",
     "description": "Exact arithmetic on numbers you got from other tools (e.g. 675.71 + 150.04, 235.5 * 0.2). "
                    "Use it for every sum, difference or percentage you state. Only + - * / and parentheses.",
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


def _calc(node):
    if isinstance(node, ast.Expression):
        return _calc(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.left), _calc(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    raise money.ToolError("Only numbers, + - * / and parentheses are allowed.")


def calculate(cid: str, expression: str, what: str = "") -> dict:
    if len(expression) > 200:
        raise money.ToolError("Expression too long.")
    try:
        val = _calc(ast.parse(expression.replace(",", ""), mode="eval"))
    except (SyntaxError, ZeroDivisionError) as e:
        raise money.ToolError(f"Can't calculate: {e}")
    return {"expression": expression, "what": what, "result": round(val, 2)}


_FUNCS["calculate"] = calculate
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
- Every number you state must come from a tool result in this conversation. Never estimate, add up or invent
  amounts yourself. If you need a number, call a tool; for sums, differences or percentages use calculate.
  If no tool can answer, say what you can't see.
- Always say which period an amount covers (e.g. "in August 2026").
- Answer exactly what was asked, in the user's own words and categories. Do not swap their question for another.
- Teach with the three baskets: {'; '.join(f"{b['name']} = {b['explain']}" for b in BASKETS.values())}
  Mention the basket when it helps the user understand where money goes.
- Transfers to the customer's own savings or investments are saving, not spending.
- If the user is short of money or overdrawn, say so kindly and plainly, with one concrete next step.
- Prices of things to buy and outside rules (loan cap, transfer tax, Euribor) come only from check_purchase and
  plan_home, with the shop or source named. If a value is unknown, say it is unknown; never use 0 or a guess.
- Keep the two shortfalls apart: "at your usual pace" (get_payday_forecast, extras included) vs "even with no
  extras" (get_safe_to_spend). Say which one you mean.
- Explain financial terms in plain language. Be warm and practical, never preachy.
- No investment, loan or tax product advice; suggest talking to S-Bank for those.
- This is a phone screen: keep answers short (usually under 90 words). Use **bold** for key amounts. Use short
  bullet lists only when listing 3+ items. End with at most one helpful follow-up suggestion.
- Use the user's exact numbers when they give them (e.g. "cut by 20 %").
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


def _attachments(trace: list[dict]) -> list[dict]:
    """Charts and widgets for the UI, built from tool results (never from model text)."""
    out, seen = [], set()
    for t in reversed(trace):
        if t["error"] or t["tool"] in seen:
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


def chat(cid: str, history: list[dict], lang: str = "en") -> dict:
    """history: [{"role": "user"|"assistant", "text": str}, ...] ending with the user's new message."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"answer": "The coach is not connected yet (no API key on the server).", "trace": [], "error": True}
    c = money.customer(cid)
    messages: list[dict] = [{"role": h["role"], "content": h["text"]} for h in history[-12:] if h.get("text")]
    lang = lang if lang in LANGS else "en"
    system = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}},
              {"type": "text", "text": f"Reply in {LANGS[lang]}\nCustomer: age {c['age']}, postal code "
                                       f"{c['postal_code']}, balance now {c['balance']} €."}]
    trace = []
    usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0, "calls": 0}
    client = _client()
    for _ in range(MAX_STEPS):
        try:
            # No refusal fallback on purpose: it may retry on a bigger model, and the team caps the app at Sonnet.
            resp = client.messages.create(
                model=MODEL, max_tokens=4000, system=system, tools=TOOLS, messages=messages,
                output_config={"effort": "low"})
        except anthropic.RateLimitError:
            return {"answer": "The coach is busy right now. Please try again in a moment.", "trace": trace, "error": True}
        except anthropic.APIStatusError as e:
            log.warning("API error %s %s", e.status_code, e.message)
            return {"answer": "Sorry, I couldn't reach the coach. Please try again.", "trace": trace, "error": True}
        except anthropic.APIConnectionError:
            return {"answer": "No connection to the coach right now. Please try again.", "trace": trace, "error": True}
        if resp.stop_reason == "refusal":
            return {"answer": "I can't help with that one. Try asking about your spending, saving or bills.",
                    "trace": trace, "error": False}
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
            numbers = verify.check(text, trace, [h["text"] for h in history if h["role"] == "user"], lang,
                                   {"balance": c["balance"], "age": c["age"]})
            bad = [n for n in numbers if n["status"] == "unverified"]
            if bad:
                log.warning("unverified numbers %s in answer to %r", [n["text"] for n in bad], history[-1]["text"][:80])
            return {"answer": text, "trace": trace, "error": False, "model": resp.model, "numbers": numbers,
                    "attachments": _attachments(trace), "usage": usage, "privacy": _privacy(trace), "lang": lang}
        results = []
        for u in uses:
            out, is_err = _run_tool(cid, u.name, dict(u.input))
            trace.append({"tool": u.name, "input": dict(u.input), "result": out, "error": is_err})
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": json.dumps(out, default=str),
                            "is_error": is_err})
        messages.append({"role": "user", "content": results})
    return {"answer": "That took too many steps. Could you ask in a simpler way?", "trace": trace, "error": True}
