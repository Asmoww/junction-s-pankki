"""EU mode: the same AI jobs on an open-weight model we host in Europe (Verda, Finland), instead of a US API.

The model sits behind an OpenAI-compatible endpoint (vLLM or SGLang on a Verda GPU, or Verda's managed inference),
configured in .env:
  EU_LLM_BASE_URL  e.g. https://<container>.verda.com/v1
  EU_LLM_API_KEY   bearer token for that endpoint
  EU_LLM_MODEL     model id as served, e.g. google/gemma-3-27b-it
  EU_LLM_LABEL     what the app shows, e.g. "Gemma 3 27B · Verda, Finland"

The provider is chosen per request (header X-AI-Provider: eu|claude) through a context variable, so the coach, the
notes, Wrapped, Sort and the game all switch together. Numbers are still computed by code and checked by verify.py:
the model only explains, whichever model it is.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import re

import httpx

log = logging.getLogger("eu")
provider: contextvars.ContextVar[str] = contextvars.ContextVar("ai_provider", default="claude")


def configured() -> bool:
    return bool(os.environ.get("EU_LLM_BASE_URL") and os.environ.get("EU_LLM_MODEL"))


def active() -> bool:
    return provider.get() == "eu" and configured()


def cache_tag() -> str:
    """Suffix for AI caches, so EU answers and Claude answers never mix."""
    return ":eu" if active() else ""


def label() -> str:
    return os.environ.get("EU_LLM_LABEL") or os.environ.get("EU_LLM_MODEL", "open model")


def info() -> dict:
    return {"configured": configured(), "label": label() if configured() else None, "model": os.environ.get("EU_LLM_MODEL")}


def _post(body: dict, timeout: float = 120) -> dict:
    key = os.environ.get("EU_LLM_API_KEY", "")
    r = httpx.post(os.environ["EU_LLM_BASE_URL"].rstrip("/") + "/chat/completions", json=body, timeout=timeout,
                   headers={"Authorization": f"Bearer {key}"} if key else {})
    r.raise_for_status()
    return r.json()


def complete(messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 2000, **extra) -> dict:
    """One chat completion. Returns the message dict and usage."""
    body = {"model": os.environ["EU_LLM_MODEL"], "messages": messages, "max_tokens": max_tokens, "temperature": 0, **extra}
    if tools:
        body["tools"] = tools
    d = _post(body)
    return {"message": d["choices"][0]["message"], "finish": d["choices"][0].get("finish_reason"), "usage": d.get("usage") or {},
            "model": d.get("model") or body["model"]}


def _json_from(text: str) -> dict:
    text = (text or "").strip()
    m = re.search(r"\{.*\}", text, re.S)  # tolerate code fences or a sentence around the object
    return json.loads(m.group(0) if m else text)


def json_call(system: str, user: str, schema: dict, max_tokens: int = 1500) -> dict:
    """Structured output: JSON-schema guided decoding where the server supports it, else JSON mode plus the schema in
    the prompt. The caller validates the result the same way as for Claude."""
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        out = complete(msgs, max_tokens=max_tokens,
                       response_format={"type": "json_schema", "json_schema": {"name": "out", "schema": schema, "strict": True}})
    except httpx.HTTPStatusError as e:
        if e.response.status_code not in (400, 422):
            raise
        msgs[0]["content"] += "\nReply with one JSON object only, matching this JSON schema:\n" + json.dumps(schema)
        out = complete(msgs, max_tokens=max_tokens, response_format={"type": "json_object"})
    return _json_from(out["message"].get("content"))


def tools_openai(tools: list[dict]) -> list[dict]:
    """Anthropic tool definitions → OpenAI function tools (same JSON schema)."""
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
            for t in tools]
