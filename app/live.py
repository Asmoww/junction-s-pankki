"""Live web facts through Context.dev, with the rules this app lives by:

- Only an item name or a rule query is ever sent. Never customer ids, balances, amounts or transactions.
- Discover, then confirm. `web.answers` only finds candidate pages; a price enters a plan only after
  `web.scrape` (formats.product, maxAgeMs <= 1 h) read it from the product page itself.
- Scraped pages are untrusted. We keep schema fields only (price, currency, availability, name) and validate them;
  page text never reaches the coach model.
- Unknown stays unknown (None), never 0. Every value carries source URL, fetched_at and request_id.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger("live")
STATE = Path(__file__).resolve().parent.parent / "state"
PRICE_MAX_AGE_MS = 3_600_000          # confirmations may be at most 1 h old
RULE_MAX_AGE_MS = 6 * 3_600_000
TAGS = ["spankki-coach"]
_lock = threading.Lock()


class LiveUnavailable(RuntimeError):
    """No key configured, or Context.dev not reachable. The UI says so; nothing is guessed."""


_client = None


def client():
    """Context.dev SDK client (package `context.dev` on PyPI, github.com/context-dot-dev/context-python-sdk)."""
    global _client
    if _client is None:
        key = os.environ.get("CONTEXT_DEV_API_KEY", "")
        if not key:
            raise LiveUnavailable("CONTEXT_DEV_API_KEY is not set")
        from context.dev import ContextDev
        _client = ContextDev(api_key=key, timeout=30, max_retries=1)
    return _client


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean_text(s, n: int = 80) -> str | None:
    """Untrusted page text → short plain label (for display only)."""
    if not isinstance(s, str):
        return None
    s = re.sub(r"[\x00-\x1f<>]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] or None


def safe_query(item: str) -> str:
    """The only user text that leaves the bank: a short item name, without anything that looks like an id or IBAN."""
    q = re.sub(r"\b(CUST\d+|FI\d{2}[\d ]{10,}|\d{6}[-+A]\d{3}[0-9A-Y])\b", "", item or "", flags=re.I)
    q = re.sub(r"\s+", " ", q).strip()
    if len(q) < 2:
        raise ValueError("Tell me what you want to buy, e.g. 'iPhone 17 256 GB'.")
    return q[:80]


# --------------------------------------------------------------------------------------------- purchases

OFFERS_FORMAT = {"offers": [{"shop": "shop name", "url": "https://product page", "price_eur": 0}]}


def discover(item: str) -> dict:
    """Candidate shop pages for an item. Prices here are claims; they are kept only to show disagreement."""
    q = safe_query(item)
    r = client().web.answers(
        task=(f"Find current offers for '{q}' in online shops that sell to customers in Finland. For each offer give "
              "the shop name and the direct product page URL. Prefer Finnish shops. Up to 5 offers."),
        json_format=OFFERS_FORMAT, mode="fast", tags=TAGS)
    offers = []
    for o in (r.json_content or {}).get("offers", []) or []:
        url = o.get("url") if isinstance(o, dict) else None
        if not isinstance(url, str) or not url.startswith("https://"):
            continue
        claimed = o.get("price_eur")
        offers.append({"shop": _clean_text(o.get("shop"), 40) or urlparse(url).netloc, "url": url[:500],
                       "claimed_price_eur": claimed if isinstance(claimed, (int, float)) and claimed > 0 else None})
    seen, uniq = set(), []
    for o in offers:
        if o["url"] not in seen:
            seen.add(o["url"]); uniq.append(o)
    return {"query": q, "offers": uniq[:5], "request_id": r.request_id, "sources": list(r.sources or [])[:10]}


def confirm(url: str) -> dict:
    """Read the price from the product page itself. Returns status confirmed / not_confirmed with a reason."""
    out = {"url": url, "domain": urlparse(url).netloc.removeprefix("www."), "status": "not_confirmed", "price_eur": None}
    try:
        r = client().web.scrape(url=url, formats={"product": True}, max_age_ms=PRICE_MAX_AGE_MS, tags=TAGS)
    except Exception as e:  # network or API error for this page only
        out["reason"] = f"page could not be read ({type(e).__name__})"
        return out
    out["request_id"] = r.request_id
    cm = r.cache_metadata
    age_ms = getattr(cm, "age_ms", None) or getattr(cm, "ageMs", None) or 0
    out["fetched_at"] = now_iso()
    out["page_age_minutes"] = round(age_ms / 60000) if isinstance(age_ms, (int, float)) else None
    p = r.product
    if not p.success or not p.data or not p.data.is_product_page or not p.data.product:
        out["reason"] = "not a product page" if p.success else (p.error_code or "no product data")
        return out
    prod = p.data.product
    price, cur = prod.price, (prod.currency or "").upper()
    if not isinstance(price, (int, float)) or not (1 <= price <= 50_000):
        out["reason"] = "no plausible price on the page"
        return out
    if cur not in ("EUR", "€"):
        out["reason"] = f"price not in euros ({_clean_text(cur, 8) or 'unknown currency'})"
        return out
    out.update({"status": "confirmed", "price_eur": round(float(price), 2), "name": _clean_text(prod.name),
                "availability": _clean_text(str(prod.availability) if prod.availability else None, 30),
                "regular_price_eur": round(float(prod.regular_price), 2) if isinstance(prod.regular_price, (int, float)) and prod.regular_price > 0 else None})
    return out


def check_purchase(item: str) -> dict:
    """Discover offers, confirm each on its own page, summarise confirmed prices in code."""
    d = discover(item)
    with ThreadPoolExecutor(5) as ex:
        checks = list(ex.map(lambda o: {**o, **confirm(o["url"])}, d["offers"]))
    ok = sorted([c for c in checks if c["status"] == "confirmed"], key=lambda c: c["price_eur"])
    prices = [c["price_eur"] for c in ok]
    for c in checks:
        if c["status"] == "confirmed" and c.get("claimed_price_eur") and abs(c["claimed_price_eur"] - c["price_eur"]) > 0.5:
            c["claim_differed"] = True  # e.g. research said 879 €, the page says 999 €
    res = {"item": d["query"], "checked_at": now_iso(), "discover_request_id": d["request_id"],
           "confirmed": ok, "not_confirmed": [c for c in checks if c["status"] != "confirmed"],
           "summary": ({"low_eur": min(prices), "median_eur": round(statistics.median(prices), 2), "high_eur": max(prices),
                        "offers": len(prices)} if prices else None)}
    _save("purchases", res["item"].lower(), res)
    return res


# --------------------------------------------------------------------------------------------- rules registry

RULES = {
    "euribor_12m": {"label": "12-month Euribor", "unit": "%", "range": (-1.0, 10.0),
                    "query": "12 kuukauden euribor korko tänään", "domains": ["suomenpankki.fi"],
                    "schema": {"type": "object", "properties": {"value": {"type": ["number", "null"], "description": "Latest 12-month Euribor in percent"},
                                                                 "as_of": {"type": ["string", "null"], "description": "Date of that value, ISO"}}}},
    "transfer_tax_shares": {"label": "Transfer tax, housing-company shares", "unit": "%", "range": (0.0, 10.0),
                            "query": "varainsiirtovero asunto-osakkeet prosentti", "domains": ["vero.fi"],
                            "page": "https://www.vero.fi/en/individuals/property/transfer-tax/buyer-of-a-flat/",
                            "schema": {"type": "object", "properties": {"value": {"type": ["number", "null"], "description": "Transfer tax percent on housing company shares (apartments)"},
                                                                         "as_of": {"type": ["string", "null"], "description": "Date the rate applies from, ISO, if stated"}}}},
    "transfer_tax_real_estate": {"label": "Transfer tax, real estate", "unit": "%", "range": (0.0, 10.0),
                                 "query": "varainsiirtovero kiinteistö prosentti", "domains": ["vero.fi"],
                                 "page": "https://www.vero.fi/en/individuals/property/transfer-tax/buying_real_propert/",
                                 "schema": {"type": "object", "properties": {"value": {"type": ["number", "null"], "description": "Transfer tax percent on real estate (houses, land)"},
                                                                              "as_of": {"type": ["string", "null"], "description": "Date the rate applies from, ISO, if stated"}}}},
    "loan_cap_general": {"label": "Housing loan cap (all borrowers)", "unit": "%", "range": (50.0, 100.0),
                         "query": "Finanssivalvonta lainakatto 95 prosenttia kaikille", "domains": ["finanssivalvonta.fi"],
                         "schema": {"type": "object", "properties": {"value": {"type": ["number", "null"], "description": "Maximum loan-to-collateral percent for housing loans for all borrowers, as decided"},
                                                                      "as_of": {"type": ["string", "null"], "description": "Date of the decision or release, ISO"},
                                                                      "effective_from": {"type": ["string", "null"], "description": "Date the cap takes effect, ISO, only if the page states it"}}}},
}


def _registry() -> dict:
    f = STATE / "rules.json"
    return json.loads(f.read_text()) if f.exists() else {}


def registry() -> dict:
    """Every rule with its status. Missing rules are listed as unknown, never filled with a default."""
    reg = _registry()
    return {k: reg.get(k, {"key": k, "label": v["label"], "unit": v["unit"], "value": None, "status": "unknown"})
            for k, v in RULES.items()}


def rule_value(key: str):
    r = registry().get(key, {})
    return r.get("value") if r.get("status") == "confirmed" else None


def refresh_rule(key: str, url: str | None = None) -> dict:
    """Find the primary page (search limited to the official domain), then read the value from it as JSON."""
    spec = RULES[key]
    c = client()
    rid_search = None
    url = url or spec.get("page")  # official guidance page for evergreen rules; search otherwise
    if not url:
        s = c.web.search(query=spec["query"], include_domains=spec["domains"], num_results=3, tags=TAGS)
        rid_search = getattr(s, "request_id", None)
        results = getattr(s, "results", None) or getattr(s, "data", None) or []
        urls = [getattr(x, "url", None) or (x.get("url") if isinstance(x, dict) else None) for x in results]
        # Prefer the newest page: search ranked a 2024 "cap unchanged" release above the 2026 "cap to 95 %" one.
        year = lambda u: max([int(y) for y in re.findall(r"(?<!\d)(20\d{2})(?!\d)", u or "")] or [0])
        urls = sorted([u for u in urls if u], key=lambda u: -year(u))
        url = urls[0] if urls else None
        if not url:
            return _store_rule(key, {"status": "unknown", "reason": "no official page found", "search_request_id": rid_search})
    r = c.web.scrape(url=url, formats={"json": True}, json_params={"schema": spec["schema"],
                     "instructions": "Read only what the page states. Use null if the page does not state it."},
                     max_age_ms=RULE_MAX_AGE_MS, tags=TAGS)
    j = r.json_
    entry = {"source_url": url, "request_id": r.request_id, "search_request_id": rid_search, "fetched_at": now_iso()}
    if not j.success or not isinstance(j.data, dict):
        return _store_rule(key, {**entry, "status": "unknown", "reason": j.error_code or "page gave no value"})
    v = j.data.get("value")
    lo, hi = spec["range"]
    if not isinstance(v, (int, float)) or not (lo <= v <= hi):
        return _store_rule(key, {**entry, "status": "unknown", "reason": "no plausible value on the page"})
    as_of = j.data.get("as_of") if isinstance(j.data.get("as_of"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", j.data.get("as_of") or "") else None
    eff = j.data.get("effective_from")
    eff = eff if isinstance(eff, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", eff) else None
    out = {**entry, "status": "confirmed", "value": float(v), "source_date": as_of}
    if key == "loan_cap_general":
        out["effective_from"] = eff  # None = announced, effective date not confirmed
    return _store_rule(key, out)


def _store_rule(key: str, entry: dict) -> dict:
    spec = RULES[key]
    entry = {"key": key, "label": spec["label"], "unit": spec["unit"], "value": None, **entry}
    with _lock:
        reg = _registry()
        prev = reg.get(key)
        if entry["status"] != "confirmed" and prev and prev.get("status") == "confirmed":
            prev["last_refresh_failed"] = {"at": now_iso(), "reason": entry.get("reason")}
            entry = prev  # keep the last confirmed value, visibly marked as not refreshed
        reg[key] = entry
        STATE.mkdir(exist_ok=True)
        (STATE / "rules.json").write_text(json.dumps(reg, indent=1))
    return entry


# --------------------------------------------------------------------------------------------- monitors

MONITORS_FILE = STATE / "monitors.json"
MONITOR_SPECS = {
    "loan_cap": {"name": "FIN-FSA housing loan cap", "rule": "loan_cap_general",
                 "instructions": "Report a change only if the housing loan cap (lainakatto) percentage or its effective date changes."},
    "euribor": {"name": "12-month Euribor", "rule": "euribor_12m",
                "instructions": "Report a change only if the latest 12-month Euribor rate changes."},
}


def monitors() -> dict:
    return json.loads(MONITORS_FILE.read_text()) if MONITORS_FILE.exists() else {}


def ensure_monitor(key: str, webhook_url: str | None = None) -> dict:
    """Create (once) a semantic page monitor on the rule's source page."""
    mons = monitors()
    if key in mons:
        return mons[key]
    spec = MONITOR_SPECS[key]
    rule = registry()[spec["rule"]]
    if not rule.get("source_url"):
        raise LiveUnavailable(f"refresh the rule {spec['rule']} first (no source page yet)")
    kw = {"name": spec["name"], "tags": TAGS,
          "target": {"type": "page", "url": rule["source_url"], "instructions": spec["instructions"]},
          "change_detection": {"type": "semantic"}, "schedule": {"type": "interval", "frequency": 1, "unit": "days"}}
    if webhook_url:
        kw["webhook"] = {"url": webhook_url, "events": ["change.detected", "run.completed"]}
    m = client().monitors.create(**kw)
    entry = {"key": key, "monitor_id": m.id, "url": rule["source_url"], "rule": spec["rule"], "created_at": now_iso(),
             "webhook": bool(webhook_url)}
    secret = getattr(getattr(m, "webhook", None), "secret", None)
    if secret:
        entry["webhook_secret"] = secret  # stored in state/ (gitignored), never logged or shown
    with _lock:
        mons = monitors(); mons[key] = entry
        STATE.mkdir(exist_ok=True); MONITORS_FILE.write_text(json.dumps(mons, indent=1))
    return entry


def run_monitor_now(key: str, wait_s: int = 90) -> dict:
    """Demo control: run the monitor immediately, wait for the run, and on a change re-read the rule."""
    m = monitors().get(key)
    if not m:
        raise LiveUnavailable(f"monitor {key} not created yet")
    c = client()
    started = c.monitors.run(m["monitor_id"])
    run = None
    t0 = time.time()
    while time.time() - t0 < wait_s:
        run = c.monitors.retrieve_run(started.run_id, monitor_id=m["monitor_id"])
        if run.status in ("completed", "failed", "skipped"):
            break
        time.sleep(3)
    res = {"key": key, "run_id": started.run_id, "request_id": started.request_id, "status": getattr(run, "status", "timeout"),
           "change_detected": bool(getattr(run, "change_detected", False)), "at": now_iso()}
    if res["change_detected"]:
        before = registry()[m["rule"]].get("value")
        after = refresh_rule(m["rule"], url=m["url"])
        res.update({"rule": m["rule"], "before": before, "after": after.get("value")})
        add_card({"kind": "rule_change", "rule": m["rule"], "before": before, "after": after.get("value"),
                  "source_url": m["url"], "at": res["at"], "run_id": started.run_id})
    _save("monitor_runs", f"{key}:{res['at']}", res)
    return res


def add_card(card: dict) -> None:
    with _lock:
        f = STATE / "live_cards.json"
        cards = json.loads(f.read_text()) if f.exists() else []
        cards.insert(0, card)
        f.write_text(json.dumps(cards[:20], indent=1))


def cards() -> list:
    f = STATE / "live_cards.json"
    return json.loads(f.read_text()) if f.exists() else []


def _save(kind: str, key: str, value: dict) -> None:
    with _lock:
        f = STATE / f"live_{kind}.json"
        d = json.loads(f.read_text()) if f.exists() else {}
        d[key] = value
        STATE.mkdir(exist_ok=True)
        f.write_text(json.dumps(d, indent=1, default=str))


def verify_signature(raw: bytes, header: str, secret: str, tolerance_s: int = 300, now: float | None = None) -> bool:
    """X-Context-Signature: t=<unix>,v1=<hex HMAC-SHA256 of 't.' + raw body> (docs.context.dev/webhooks)."""
    if not secret or not header:
        return False
    parts = {}
    for p in header.split(","):
        k, _, v = p.strip().partition("=")
        if not v or k in parts:
            return False
        parts[k] = v
    t, v1 = parts.get("t", ""), parts.get("v1", "")
    if not re.fullmatch(r"\d{1,12}", t) or not re.fullmatch(r"[0-9a-fA-F]{64}", v1):
        return False
    if abs((now or time.time()) - int(t)) > tolerance_s:
        return False
    expected = hmac.new(secret.encode(), t.encode() + b"." + raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1.lower())


def log_delivery(event: dict) -> None:
    """Keep the last deliveries (id, event, monitor, change flag) so the demo can show the webhook path works."""
    with _lock:
        f = STATE / "live_deliveries.json"
        d = json.loads(f.read_text()) if f.exists() else []
        data = event.get("data") or {}
        d.insert(0, {"id": event.get("id"), "event": event.get("event"), "received_at": now_iso(),
                     "monitor_id": ((data.get("run") or {}).get("monitor_id") or (data.get("change") or {}).get("monitor_id")),
                     "change": bool(data.get("change"))})
        f.write_text(json.dumps(d[:50], indent=1))


def seen_event(event_id: str) -> bool:
    with _lock:
        f = STATE / "live_events_seen.json"
        seen = json.loads(f.read_text()) if f.exists() else []
        if event_id in seen:
            return True
        seen = (seen + [event_id])[-500:]
        STATE.mkdir(exist_ok=True)
        f.write_text(json.dumps(seen))
    return False
