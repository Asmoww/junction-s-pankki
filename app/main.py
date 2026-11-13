"""Web app: password gate, JSON API for the mobile UI, static files.

Run: .venv/bin/uvicorn app.main:app --port 5202
"""
import hashlib
import hmac
import json
import html
import logging
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
_env = ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from . import coach, future, homeplan, insights, live, money  # noqa: E402  (after .env is loaded)
from .personas import PERSONAS  # noqa: E402

logging.basicConfig(level=logging.INFO)
PASSWORD = os.environ.get("DEMO_PASSWORD", "")
WEB = Path(__file__).resolve().parent / "web"
_COOKIE = "sp_session"
_token = hmac.new(PASSWORD.encode(), b"sp-session", hashlib.sha256).hexdigest() if PASSWORD else ""
OPEN_PATHS = {"/login", "/healthz", "/static/style.css", "/static/icon.svg", "/hooks/context"}

app = FastAPI(title="S-Pankki money coach (demo)", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB), name="static")
app.mount("/design", StaticFiles(directory=ROOT / "design" / "mockups", html=True), name="design")


@app.middleware("http")
async def password_gate(request: Request, call_next):
    if not PASSWORD or request.url.path in OPEN_PATHS:
        return await call_next(request)
    if secrets.compare_digest(request.cookies.get(_COOKIE, ""), _token):
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "login required"}, status_code=401)
    nxt = request.url.path if request.url.path in ("/", "/e", "/classic") or request.url.path.startswith("/design") else "/"
    return RedirectResponse(f"/login?next={nxt}", status_code=303)


LOGIN = (WEB / "login.html").read_text()


@app.get("/login", response_class=HTMLResponse)
def login_page(err: int = 0, next: str = "/"):
    nxt = next if next.startswith("/") and not next.startswith("//") else "/"
    return LOGIN.replace("{err}", '<p class="err">Wrong password, try again.</p>' if err else "").replace(
        "{next}", html.escape(nxt, quote=True))


@app.post("/login")
def login(password: str = Form(...), next: str = Form("/")):
    nxt = next if next.startswith("/") and not next.startswith("//") else "/"
    if not PASSWORD or not secrets.compare_digest(password, PASSWORD):
        return RedirectResponse(f"/login?err=1&next={nxt}", status_code=303)
    r = RedirectResponse(nxt, status_code=303)
    r.set_cookie(_COOKIE, _token, httponly=True, secure=True, samesite="lax", max_age=14 * 86400)
    return r


@app.get("/healthz")
def healthz():
    return {"ok": True}


# Cloudflare caches /static for hours: version asset URLs by content so each deploy is picked up at once.
_ver = hashlib.sha256(b"".join((WEB / f).read_bytes() for f in ("style.css", "app.js", "i18n.js", "e.css", "e.js"))).hexdigest()[:10]
INDEX = (WEB / "index.html").read_text().replace(".css\"", f".css?v={_ver}\"").replace(".js\"", f".js?v={_ver}\"")
LOGIN = LOGIN.replace(".css\"", f".css?v={_ver}\"")


E_PAGE = (WEB / "e.html").read_text().replace(".css\"", f".css?v={_ver}\"").replace(".js\"", f".js?v={_ver}\"")


@app.get("/")
def index():
    """Design E (the future as a graph) is the main page."""
    return HTMLResponse(E_PAGE, headers={"Cache-Control": "no-cache"})


@app.get("/e")
def index_e():
    return RedirectResponse("/", status_code=307)


@app.get("/classic")
def index_classic():
    """The first design, kept for comparison."""
    return HTMLResponse(INDEX, headers={"Cache-Control": "no-cache"})


def _cid(cid: str) -> str:
    try:
        money.customer(cid)
    except money.ToolError:
        raise HTTPException(404, "unknown customer")
    return cid


@app.get("/api/personas")
def personas():
    out = []
    for p in PERSONAS:
        c = money.customer(p["id"])
        out.append({**p, "age": c["age"]})
    return out


@app.get("/api/overview/{cid}")
def overview(cid: str):
    return money.overview(_cid(cid))


@app.get("/api/home/{cid}")
def home(cid: str):
    """Everything the home and learn screens need in one call."""
    cid = _cid(cid)
    return {"overview": money.overview(cid), "cards": insights.cards(cid), "pot": insights.surprise_pot(cid),
            "type": insights.spender_type(cid), "benchmark": insights.benchmark(cid), "ribbon": insights.ribbon(cid)}


@app.get("/api/future/{cid}")
def future_line(cid: str):
    return future.future(_cid(cid))


@app.get("/api/notes/{cid}")
def notes(cid: str, lang: str = "en"):
    return future.annotations(_cid(cid), lang if lang in ("en", "fi", "sv") else "en")


class ScenarioIn(BaseModel):
    customer_id: str
    scenario: dict


@app.post("/api/scenario")
def scenario(body: ScenarioIn):
    return future.future(_cid(body.customer_id), body.scenario)


class WhatIfIn(BaseModel):
    customer_id: str
    text: str = Field(min_length=2, max_length=300)
    lang: str = Field("en", pattern="^(en|fi|sv)$")


@app.post("/api/whatif")
def whatif(body: WhatIfIn):
    try:
        return future.parse_whatif(_cid(body.customer_id), body.text, body.lang)
    except Exception as e:  # API error or refusal: tell the UI plainly
        logging.getLogger("whatif").warning("whatif failed: %s", e)
        raise HTTPException(503, "The what-if helper is not available right now.")


def _warm_notes():
    for p in PERSONAS:
        for lg in ("en", "fi", "sv"):
            try:
                future.annotations(p["id"], lg)
            except Exception as e:  # noqa: BLE001 (warm-up only)
                logging.getLogger("notes").warning("warm-up failed for %s %s: %s", p["id"], lg, e)


@app.on_event("startup")
def warm():
    import threading
    threading.Thread(target=_warm_notes, daemon=True).start()


# ---------------------------------------------------------------- live web data (Context.dev)

def _live(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except live.LiveUnavailable as e:
        raise HTTPException(503, f"Live web data is not connected: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/live/status")
def live_status():
    return {"connected": bool(os.environ.get("CONTEXT_DEV_API_KEY")), "rules": live.registry(),
            "deliveries": (json.loads((ROOT / "state" / "live_deliveries.json").read_text())[:5]
                           if (ROOT / "state" / "live_deliveries.json").exists() else []),
            "monitors": {k: {f: m.get(f) for f in ("monitor_id", "url", "rule", "created_at", "webhook")}
                         for k, m in live.monitors().items()}, "cards": live.cards()[:5]}


class PurchaseIn(BaseModel):
    item: str = Field(min_length=2, max_length=120)


@app.post("/api/live/purchase")
def live_purchase(body: PurchaseIn):
    return _live(live.check_purchase, body.item)


class ApplyIn(BaseModel):
    customer_id: str
    item: str
    url: str
    date: str | None = None


@app.post("/api/live/purchase/apply")
def live_apply(body: ApplyIn):
    """Put a CONFIRMED price into the forecast. The amount is looked up server-side, never taken from the client."""
    saved = json.loads((ROOT / "state" / "live_purchases.json").read_text()) if (ROOT / "state" / "live_purchases.json").exists() else {}
    check = saved.get(body.item.lower())
    offer = next((o for o in (check or {}).get("confirmed", []) if o["url"] == body.url), None)
    if not offer:
        raise HTTPException(404, "That price was not confirmed; it can't enter the plan.")
    when = body.date or (money.TODAY + __import__("datetime").timedelta(days=1)).isoformat()
    res = future.future(_cid(body.customer_id), {"one_offs": [{"label": body.item, "amount": offer["price_eur"], "date": when}]})
    return {**res, "offer": offer, "label": f"{body.item} {offer['price_eur']:.0f} €"}


@app.get("/api/live/home/{cid}")
def live_home(cid: str, price: float, property_type: str = "apartment"):
    try:
        return homeplan.plan_home(_cid(cid), price, property_type)
    except money.ToolError as e:
        raise HTTPException(400, str(e))


@app.post("/api/live/rules/refresh")
def live_rules_refresh():
    return {k: _live(live.refresh_rule, k) for k in live.RULES}


@app.post("/api/live/monitors/setup")
def live_monitors_setup():
    hook = "https://spankki.psavela.com/hooks/context"
    return {k: _live(live.ensure_monitor, k, hook) for k in live.MONITOR_SPECS}


@app.post("/api/live/monitors/{key}/run")
def live_monitor_run(key: str):
    """Labelled demo control: run a monitor now instead of waiting for its daily schedule."""
    if key not in live.MONITOR_SPECS:
        raise HTTPException(404, "unknown monitor")
    return _live(live.run_monitor_now, key)


@app.post("/hooks/context")
async def context_webhook(request: Request):
    """Signed Context.dev monitor webhook: verify HMAC before parsing, dedupe on X-Context-Id, react to changes."""
    raw = await request.body()
    sig = request.headers.get("x-context-signature", "")
    mons = live.monitors()
    if not any(live.verify_signature(raw, sig, m.get("webhook_secret", "")) for m in mons.values()):
        return JSONResponse({"detail": "bad signature"}, status_code=401)
    try:
        ev = json.loads(raw)
    except ValueError:
        return JSONResponse({"detail": "bad json"}, status_code=400)
    if ev.get("id") != request.headers.get("x-context-id") or ev.get("event") != request.headers.get("x-context-event"):
        return JSONResponse({"detail": "envelope mismatch"}, status_code=400)
    if live.seen_event(ev["id"]):
        return JSONResponse({}, status_code=204)
    live.log_delivery(ev)
    change = (ev.get("data") or {}).get("change") or {}
    m = next((m for m in mons.values() if m.get("monitor_id") == change.get("monitor_id")), None)
    if ev.get("event") == "change.detected" and m:
        before = live.registry()[m["rule"]].get("value")
        try:
            after = live.refresh_rule(m["rule"], url=m["url"]).get("value")
        except Exception as e:  # noqa: BLE001 (record and acknowledge; the card says it couldn't re-read)
            logging.getLogger("hooks").warning("rule refresh after change failed: %s", e)
            after = None
        live.add_card({"kind": "rule_change", "rule": m["rule"], "before": before, "after": after, "source_url": m["url"],
                       "at": live.now_iso(), "change_id": change.get("id"), "via": "webhook"})
    return JSONResponse({}, status_code=204)


@app.get("/api/game/{cid}")
def game(cid: str, seed: int | None = None):
    return insights.basket_game(_cid(cid), seed=seed)


@app.get("/api/traps")
def traps():
    f = ROOT / "state" / "traps.json"
    return json.loads(f.read_text()) if f.exists() else {"runs": []}


@app.get("/api/baskets/{cid}")
def baskets(cid: str, period: str = "this_month"):
    try:
        return money.get_three_baskets(_cid(cid), period)
    except money.ToolError as e:
        raise HTTPException(400, str(e))


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(max_length=4000)


class ChatIn(BaseModel):
    customer_id: str
    history: list[Turn] = Field(min_length=1, max_length=40)
    lang: str = Field("en", pattern="^(en|fi|sv)$")


@app.post("/api/chat")
def chat(body: ChatIn):
    if body.history[-1].role != "user":
        raise HTTPException(400, "last turn must be the user's")
    return coach.chat(_cid(body.customer_id), [t.model_dump() for t in body.history], body.lang)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    detail = getattr(exc, "detail", "not found")
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": detail}, status_code=404)
    return HTMLResponse(f"<p>{html.escape(str(detail))}</p>", status_code=404)
