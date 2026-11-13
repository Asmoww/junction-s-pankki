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

from . import coach, future, insights, money  # noqa: E402  (after .env is loaded)
from .personas import PERSONAS  # noqa: E402

logging.basicConfig(level=logging.INFO)
PASSWORD = os.environ.get("DEMO_PASSWORD", "")
WEB = Path(__file__).resolve().parent / "web"
_COOKIE = "sp_session"
_token = hmac.new(PASSWORD.encode(), b"sp-session", hashlib.sha256).hexdigest() if PASSWORD else ""
OPEN_PATHS = {"/login", "/healthz", "/static/style.css", "/static/icon.svg"}

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
    nxt = request.url.path if request.url.path in ("/", "/e") or request.url.path.startswith("/design") else "/"
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


@app.get("/e")
def index_e():
    return HTMLResponse(E_PAGE, headers={"Cache-Control": "no-cache"})


@app.get("/")
def index():
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
