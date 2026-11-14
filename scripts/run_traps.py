"""Run the trap suite against the live coach (real API calls, about 2-3 cents per case) and save
state/traps.json, which the app shows on the Learn tab. Usage: .venv/bin/python scripts/run_traps.py
--eu runs the same suite on the open model hosted in the EU (app/eu.py) and saves state/traps_eu.json.
"""
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from app import coach, eu  # noqa: E402
EU = "--eu" in sys.argv
from tests.traps.cases import cases  # noqa: E402
from tests.traps.grade import NOT_CLAIMS, check, public_reasons  # noqa: E402

_hid_lock = threading.Lock()


def _save_hidden(entry):
    """Newest 20 hidden failures in state/ (gitignored, never served). A broken file is replaced, not fatal, and
    the write is atomic, so a crash or a parallel --eu run can't leave half a file behind."""
    hid = ROOT / "state" / "traps_hidden_failures.json"
    hid.parent.mkdir(exist_ok=True)
    with _hid_lock:
        try:
            old = json.loads(hid.read_text())
            old = old if isinstance(old, list) else []
        except (OSError, ValueError):
            old = []
        tmp = hid.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(([entry] + old)[:20], indent=1))
        os.replace(tmp, hid)


def run_case(c):
    if EU:  # worker threads don't inherit the context variable, so set it here
        eu.provider.set("eu")
    r = coach.chat(c["persona"], [{"role": "user", "text": c["q"]}], c.get("lang", "en"))
    ans, failed = r["answer"], check(c, r)
    nums = [n for n in r.get("numbers", []) if n["status"] not in NOT_CLAIMS]
    bad = [n for n in nums if n["status"] == "unverified"]
    if failed and "shown" in c:  # hidden question: keep the answer out of the app, but in a local file for debugging
        _save_hidden({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "eu": EU, "trap": c["trap"],
                      "failed": failed, "answer": ans})
    failed = public_reasons(c, failed)  # a hidden case shows only the kind of failure, never words from the answer
    return {"trap": c["trap"], "question": c.get("shown", c["q"]), "persona": c["persona"], "ok": not failed, "failed": failed,
            "answer": ans if "shown" not in c else "(not stored: the question is hidden)", "tools": [t["tool"] for t in r.get("trace", [])],
            "numbers_total": len(nums), "numbers_verified": len(nums) - len(bad),
            "cost_usd": (r.get("usage") or {}).get("cost_usd") or 0, "model": (r.get("usage") or {}).get("model", "")}


def main():
    cs = cases()
    if EU and not eu.configured():
        sys.exit("EU model not configured (EU_LLM_BASE_URL, EU_LLM_MODEL in .env)")
    with ThreadPoolExecutor(2 if EU else 4) as ex:
        res = list(ex.map(run_case, cs))
    run = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "model": eu.label() if EU else coach.MODEL,
           "provider": "eu" if EU else "claude",
           "passed": sum(r["ok"] for r in res), "total": len(res),
           "numbers_verified": sum(r["numbers_verified"] for r in res), "numbers_total": sum(r["numbers_total"] for r in res),
           "cost_usd": round(sum(r["cost_usd"] for r in res), 3), "cases": res}
    out = ROOT / "state" / ("traps_eu.json" if EU else "traps.json")
    out.parent.mkdir(exist_ok=True)
    old = json.loads(out.read_text())["runs"] if out.exists() else []
    out.write_text(json.dumps({"runs": [run] + old[:9]}, indent=1, default=str))
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + r["trap"] + ("" if r["ok"] else f"  -> {r['failed']}"))
    print(f"{run['passed']}/{run['total']} passed, numbers {run['numbers_verified']}/{run['numbers_total']}, ${run['cost_usd']}")


if __name__ == "__main__":
    main()
