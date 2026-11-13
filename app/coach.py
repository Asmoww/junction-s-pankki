"""The money coach: Claude picks money tools, the tools compute every number, Claude explains them.

Returns the answer plus a trace of the tool calls, so the UI can show "How I worked this out".
"""
from __future__ import annotations

import json
import logging
import os

import anthropic

from . import money
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
    {"name": "get_spender_profile",
     "description": "Spending habits (small purchases, evenings, weekends, overdraft, most frequent extras) and a "
                    "comparison with customers of the same age group. Use for 'what kind of spender am I'.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
]

_FUNCS = {"get_spending": money.get_spending, "list_transactions": money.list_transactions,
          "get_cashflow": money.get_cashflow, "get_three_baskets": money.get_three_baskets,
          "get_safe_to_spend": money.get_safe_to_spend, "simulate_cut": money.simulate_cut,
          "get_spender_profile": money.get_spender_profile}

SYSTEM = f"""You are the S-Bank money coach inside the S-mobiili app. You help one customer understand their own
money by talking with their real transaction data. Today is {money.TODAY.isoformat()}; the data covers
2024-10-01 to 2026-09-30.

Rules:
- Every number you state must come from a tool result in this conversation. Never estimate, add up or invent
  amounts yourself. If you need a number, call a tool. If no tool can answer, say what you can't see.
- Always say which period an amount covers (e.g. "in August 2026").
- Answer exactly what was asked, in the user's own words and categories. Do not swap their question for another.
- Teach with the three baskets: {'; '.join(f"{b['name']} = {b['explain']}" for b in BASKETS.values())}
  Mention the basket when it helps the user understand where money goes.
- Transfers to the customer's own savings or investments are saving, not spending.
- If the user is short of money or overdrawn, say so kindly and plainly, with one concrete next step.
- Explain financial terms in plain language. Be warm and practical, never preachy.
- No investment, loan or tax product advice; suggest talking to S-Bank for those.
- This is a phone screen: keep answers short (usually under 90 words). Use **bold** for key amounts. Use short
  bullet lists only when listing 3+ items. End with at most one helpful follow-up suggestion.
- Reply in the language the user writes in (English or Finnish). Format amounts like 1,234.50 €.
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _run_tool(cid: str, name: str, args: dict) -> tuple[dict, bool]:
    fn = _FUNCS.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}, True
    try:
        return fn(cid, **args), False
    except money.ToolError as e:
        return {"error": str(e)}, True
    except TypeError as e:
        return {"error": f"bad arguments: {e}"}, True


def chat(cid: str, history: list[dict]) -> dict:
    """history: [{"role": "user"|"assistant", "text": str}, ...] ending with the user's new message."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"answer": "The coach is not connected yet (no API key on the server).", "trace": [], "error": True}
    c = money.customer(cid)
    messages: list[dict] = [{"role": h["role"], "content": h["text"]} for h in history[-12:] if h.get("text")]
    system = SYSTEM + f"\nCustomer: age {c['age']}, postal code {c['postal_code']}, balance now {c['balance']} €."
    trace = []
    client = _client()
    for _ in range(MAX_STEPS):
        try:
            resp = client.beta.messages.create(
                model=MODEL, max_tokens=4000, system=system, tools=TOOLS, messages=messages,
                output_config={"effort": "low"},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default")
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
        messages.append({"role": "assistant", "content": resp.content})
        uses = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not uses:
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            return {"answer": text, "trace": trace, "error": False, "model": resp.model}
        results = []
        for u in uses:
            out, is_err = _run_tool(cid, u.name, dict(u.input))
            trace.append({"tool": u.name, "input": dict(u.input), "result": out, "error": is_err})
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": json.dumps(out, default=str),
                            "is_error": is_err})
        messages.append({"role": "user", "content": results})
    return {"answer": "That took too many steps. Could you ask in a simpler way?", "trace": trace, "error": True}
