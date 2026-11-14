"""Scale test for EU mode: generate every customer's AI notes and money-year captions on the open model hosted in
the EU (app/eu.py), and measure what it would take for a whole bank.

Usage: .venv/bin/python scripts/eu_batch.py [N customers, default 200] [--workers 16]
Writes state/eu_batch.json: customers done, failures, wall time, tokens, calls per second, and the share of AI
outputs whose numbers all matched the data (the same check the app applies; failures are dropped, not shown).
Customer data never leaves the bank's side: the model gets computed facts only, no ids or names.
"""
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from app import eu, future, wrapped  # noqa: E402
from app.money import _q  # noqa: E402

N = int(next((a for a in sys.argv[1:] if a.isdigit()), 200))
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 16
tokens = {"in": 0, "out": 0, "calls": 0}
_lock = threading.Lock()
_orig = eu.complete


def counted(*a, **k):
    r = _orig(*a, **k)
    with _lock:
        tokens["in"] += r["usage"].get("prompt_tokens", 0)
        tokens["out"] += r["usage"].get("completion_tokens", 0)
        tokens["calls"] += 1
    return r


eu.complete = counted


def one(cid: str) -> dict:
    eu.provider.set("eu")  # per worker thread
    t = time.time()
    try:
        notes = future.annotations(cid, "en")
        caps = wrapped.captions(cid, "en")
        return {"cid": cid, "ok": True, "s": round(time.time() - t, 2), "notes": len(notes.get("notes", [])),
                "captions": sum(1 for v in (caps.get("captions") or {}).values() if v)}
    except Exception as e:  # noqa: BLE001
        return {"cid": cid, "ok": False, "s": round(time.time() - t, 2), "error": f"{type(e).__name__}: {str(e)[:120]}"}


def main():
    if not eu.configured():
        sys.exit("EU model not configured (EU_LLM_BASE_URL, EU_LLM_MODEL in .env)")
    cids = [r["customer_id"] for r in _q("SELECT customer_id FROM cust WHERE customer_id < 'CUST05001' ORDER BY hash(customer_id) LIMIT ?", [N])]
    t0 = time.time()
    with ThreadPoolExecutor(WORKERS) as ex:
        res = list(ex.map(one, cids))
    wall = time.time() - t0
    ok = [r for r in res if r["ok"]]
    out = {"model": eu.label(), "customers": len(cids), "done": len(ok), "failed": len(res) - len(ok), "workers": WORKERS,
           "wall_s": round(wall, 1), "per_customer_s": round(wall / max(len(cids), 1), 2), "llm_calls": tokens["calls"],
           "tokens_in": tokens["in"], "tokens_out": tokens["out"],
           "captions_kept_share": round(sum(r["captions"] for r in ok) / max(9 * len(ok), 1), 3),
           "notes_per_customer": round(sum(r["notes"] for r in ok) / max(len(ok), 1), 2),
           "errors": [r for r in res if not r["ok"]][:10]}
    (ROOT / "state" / "eu_batch.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "errors"}, indent=1))


if __name__ == "__main__":
    main()
