"""Web app: password gate, JSON API for the mobile UI, static files.

Run: .venv/bin/uvicorn app.main:app --port 5202
"""
import asyncio
import contextvars
import hashlib
import hmac
import json
import html
import logging
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
_env = ROOT / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from . import brief, coach, drains, eu, future, homeplan, insights, learning, live, money, play, psd2, saving, sorter, voice, wrapped  # noqa: E402  (after .env is loaded)
from .personas import PERSONAS  # noqa: E402

logging.basicConfig(level=logging.INFO)
PASSWORD = os.environ.get("DEMO_PASSWORD", "")
WEB = Path(__file__).resolve().parent / "web"
_COOKIE = "sp_session"
_token = hmac.new(PASSWORD.encode(), b"sp-session", hashlib.sha256).hexdigest() if PASSWORD else ""
OPEN_PATHS = {"/login", "/healthz", "/static/style.css", "/static/icon.svg", "/hooks/context"}

app = FastAPI(title="S-Pankki money coach (demo)", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB), name="static")


class AIProvider:
    """Per request: X-AI-Provider: eu runs every AI job on the open model hosted in the EU (eu.py), else Claude."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.inner(scope, receive, send)
        want = dict(scope.get("headers") or []).get(b"x-ai-provider", b"").decode()
        tok = eu.provider.set("eu" if want == "eu" else "claude")
        try:
            await self.inner(scope, receive, send)
        finally:
            eu.provider.reset(tok)


app.add_middleware(AIProvider)
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
_ver = hashlib.sha256(b"".join((WEB / f).read_bytes() for f in ("style.css", "app.js", "i18n.js", "e.css", "e.js", "learn.js"))).hexdigest()[:10]
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
            "type": insights.spender_type(cid), "benchmark": insights.benchmark(cid), "ribbon": insights.ribbon(cid),
            "health": insights.money_health(cid), "year": wrapped.calendar(cid), "surprise_example": live.surprise_example(),
            "save": saving.get_safe_to_save(cid), "drains": drains.drains(cid), "psd2": psd2.status(cid)}


class PlayIn(BaseModel):
    kept: list[str]
    move_rent: bool = False
    swap: bool = False
    lang: str = "en"


@app.get("/api/play/{cid}")
def play_deal(cid: str, lang: str = "en"):
    """Play your next two weeks: the cards, the no-extras line and the coach's suggested plan."""
    cid = _cid(cid)
    return {**play.deal(cid), "tip": play.tip(cid, lang if lang in ("en", "fi", "sv") else "en")}


@app.post("/api/play/{cid}")
def play_finish(cid: str, body: PlayIn):
    return play.finish(_cid(cid), body.kept, body.move_rent, body.lang if body.lang in ("en", "fi", "sv") else "en", body.swap)


class Psd2In(BaseModel):
    bank: str


@app.post("/api/psd2/{cid}")
def psd2_connect(cid: str, body: Psd2In):
    """Consent to read the customer's other bank (PSD2, demo): bank, 90 days, read-only."""
    try:
        return psd2.connect(_cid(cid), body.bank)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/psd2/{cid}")
def psd2_revoke(cid: str):
    return psd2.revoke(_cid(cid))


class SortIn(BaseModel):
    answers: dict[str, int]
    lang: str = "en"


class LearnIn(BaseModel):
    device: str = Field(max_length=64)
    quest: str
    step: str
    choice: int
    event_id: str = Field(max_length=64)
    lang: str = "en"


class LearnSettingsIn(BaseModel):
    device: str = Field(max_length=64)
    show_points: bool | None = None
    hide_rewards: bool | None = None
    pause_prompts: bool | None = None
    weekly_goal: int | None = None


def _lang(lang: str) -> str:
    return lang if lang in ("en", "fi", "sv") else "en"


@app.get("/api/learn/{cid}")
def learn_summary(cid: str, device: str, lang: str = "en"):
    """Money Detective progress: concepts explored / explained / revisited, weekly goal, milestones. No money here."""
    from datetime import datetime
    return learning.summary(learning.load(device, _cid(cid)), datetime.now(), _lang(lang))


@app.get("/api/learn/{cid}/quest/{qid}")
def learn_quest(cid: str, qid: str, lang: str = "en", practice: bool = False, revisit: bool = False):
    """One quest built from this customer's own numbers (or the practice case)."""
    facts = learning.PRACTICE_FACTS if practice else learning.facts_from_data(_cid(cid))
    try:
        return learning.quest(qid, facts, _lang(lang), revisit=revisit)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/learn/{cid}")
def learn_answer(cid: str, body: LearnIn):
    """Record one answer (idempotent by event_id) and return feedback in the user's language."""
    from datetime import datetime
    c = _cid(cid)
    st = learning.load(body.device, c)
    out = learning.record(st, event_id=body.event_id, qid=body.quest, step=body.step, choice=body.choice, now=datetime.now())
    if out.get("ok"):
        learning.save(body.device, c, st)
        if "correct" in out:
            t = learning.T[_lang(body.lang)]
            key = ("rev" if body.step == "revisit" else body.quest) + ("_ok" if out["correct"] else "_no")
            out["feedback"] = t[key]
    return out


class CuriosityIn(BaseModel):
    device: str = Field(max_length=64)
    event_id: str = Field(max_length=64)
    concept: str | None = None
    kind: str | None = None
    metric: str | None = None
    guess: float | None = None
    actual: float | None = None


@app.post("/api/learn/{cid}/curiosity")
def learn_curiosity(cid: str, body: CuriosityIn):
    """Record wanting to learn: a new concept asked about, steps opened, a what-if tried, a correction, or a guess."""
    from datetime import datetime
    c = _cid(cid)
    st = learning.load(body.device, c)
    if body.guess is not None and body.actual is not None and body.metric:
        out = learning.record_guess(st, event_id=body.event_id, metric=body.metric, guess=body.guess,
                                    actual=body.actual, now=datetime.now())
    else:
        out = learning.record_curiosity(st, event_id=body.event_id, concept=body.concept or "", kind=body.kind or "",
                                        now=datetime.now())
    if out.get("ok"):
        learning.save(body.device, c, st)
    return out


@app.post("/api/learn/{cid}/settings")
def learn_settings(cid: str, body: LearnSettingsIn):
    c = _cid(cid)
    st = learning.set_settings(learning.load(body.device, c), **body.model_dump(exclude={"device"}))
    learning.save(body.device, c, st)
    return st["settings"] | {"weekly_goal": st["weekly_goal"]}


@app.delete("/api/learn/{cid}")
def learn_reset(cid: str, device: str):
    learning.reset(device, _cid(cid))
    return {"reset": True}


@app.get("/api/history/{cid}")
def balance_history(cid: str, months: int = 12):
    """Home trend line zoomed out: 3, 12 or 24 months of real balances + money in/out per month."""
    try:
        return insights.balance_history(_cid(cid), months)
    except money.ToolError as e:
        raise HTTPException(400, str(e))


@app.get("/api/sort/{cid}")
def sort_cards(cid: str, lang: str = "en"):
    """Sort with the AI: the customer's unclear items, each with a question and three basket answers."""
    return sorter.questions(_cid(cid), lang if lang in ("en", "fi", "sv") else "en")


@app.post("/api/sort/{cid}")
def sort_answer(cid: str, body: SortIn):
    try:
        return sorter.answer(_cid(cid), body.answers, body.lang if body.lang in ("en", "fi", "sv") else "en")
    except money.ToolError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/sort/{cid}")
def sort_reset(cid: str):
    return sorter.reset(_cid(cid))


@app.get("/api/ai")
def ai_info():
    """Which AI the app can use: Claude (default) and, if configured, the open model hosted in the EU; voice on/off."""
    return {"eu": eu.info(), "voice": voice.configured()}


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=400)


@app.post("/api/speak")
def speak(body: SpeakIn):
    if not voice.configured():
        raise HTTPException(503, "Voice is not connected.")
    try:
        return FileResponse(voice.speak(body.text), media_type="audio/mpeg")
    except Exception as e:  # noqa: BLE001
        logging.getLogger("voice").warning("speak failed: %s", e)
        raise HTTPException(503, "Voice is not available right now.")


@app.get("/api/wrapped/{cid}")
def wrapped_year(cid: str, lang: str = "en"):
    return wrapped.wrapped(_cid(cid), lang if lang in ("en", "fi", "sv") else "en")


@app.get("/api/future/{cid}")
def future_line(cid: str):
    return future.future(_cid(cid))


@app.get("/api/brief/{cid}")
def home_brief(cid: str, lang: str = "en", explored: str = ""):
    """Home's AI layer: a one-line briefing, three questions picked for this person, and the order of the cards.
    explored: Money Detective concepts already lit (comma-separated), so the AI favours new corners."""
    return brief.brief(_cid(cid), lang, [c for c in explored.split(",") if c][:20])


@app.get("/api/history/{cid}/notes")
def history_notes(cid: str, months: int = 12, lang: str = "en"):
    """2-3 notes that explain the 3/12/24-month line (code finds the moments, the AI picks, labels from code)."""
    if months not in insights.HISTORY_RANGES:
        raise HTTPException(400, "months must be 3, 12 or 24")
    return future.long_annotations(_cid(cid), months, lang)


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
    if os.environ.get("CONTEXT_DEV_API_KEY"):  # live prices used on Home and in the game, refreshed once a day
        for f in (lambda: live.surprise_example(fetch=True), lambda: live.refresh_rule("hsl_30day_ab")):
            try:
                f()
            except Exception as e:  # noqa: BLE001 (warm-up only)
                logging.getLogger("live").warning("live warm-up failed: %s", e)
    for p in PERSONAS:
        for lg in ("en", "fi", "sv"):
            try:
                future.annotations(p["id"], lg)
                wrapped.captions(p["id"], lg)
                sorter.questions(p["id"], lg)
                play.tip(p["id"], lg)
            except Exception as e:  # noqa: BLE001 (warm-up only)
                logging.getLogger("notes").warning("warm-up failed for %s %s: %s", p["id"], lg, e)


@app.on_event("startup")
def warm():
    import threading
    sorter.load_all()
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
    f, g = ROOT / "state" / "traps.json", ROOT / "state" / "traps_eu.json"
    out = json.loads(f.read_text()) if f.exists() else {"runs": []}
    out["eu_runs"] = json.loads(g.read_text())["runs"] if g.exists() else []  # same suite on the EU-hosted open model
    if eu.forced() and out["eu_runs"]:  # Gemma only: its score is the main one; Claude's is shown for comparison
        out = {"runs": out["eu_runs"], "eu_runs": [], "claude_runs": out["runs"]}
    return out


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


_STEP_KEYS = ("period", "start", "end", "category", "subcategory", "basket", "group_by", "what", "item", "sort")


@app.post("/api/chat/stream")
async def chat_stream(body: ChatIn):
    """The same answer as /api/chat, as NDJSON: one {"step": ...} line per tool the coach really runs (name and filters
    only, no results), then {"done": result}. The app shows the steps while it waits."""
    if body.history[-1].role != "user":
        raise HTTPException(400, "last turn must be the user's")
    cid = _cid(body.customer_id)
    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def progress(step, args):
        info = {k: args[k] for k in _STEP_KEYS if isinstance(args, dict) and k in args and isinstance(args[k], (str, int))}
        loop.call_soon_threadsafe(q.put_nowait, {"step": {"tool": step, **info}})

    def run():
        try:
            out = coach.chat(cid, [t.model_dump() for t in body.history], body.lang, progress)
        except Exception:  # noqa: BLE001
            logging.getLogger("coach").exception("chat stream failed")
            out = {"answer": "Something went wrong. Please try again.", "error": True, "trace": []}
        loop.call_soon_threadsafe(q.put_nowait, {"done": out})

    ctx = contextvars.copy_context()  # keeps the per-request AI provider (EU or Claude) inside the worker thread
    loop.run_in_executor(None, ctx.run, run)

    async def lines():
        while True:
            ev = await q.get()
            yield json.dumps(ev, default=str) + "\n"
            if "done" in ev:
                return

    return StreamingResponse(lines(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.exception_handler(404)
async def not_found(request: Request, exc):
    detail = getattr(exc, "detail", "not found")
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": detail}, status_code=404)
    return HTMLResponse(f"<p>{html.escape(str(detail))}</p>", status_code=404)
