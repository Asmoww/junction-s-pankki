"""Run the trap suite against the live coach (real API calls, about 2-3 cents per case) and save
state/traps.json, which the app shows on the Learn tab. Usage: .venv/bin/python scripts/run_traps.py
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from app import coach  # noqa: E402
from tests.traps.cases import cases  # noqa: E402


def run_case(c):
    r = coach.chat(c["persona"], [{"role": "user", "text": c["q"]}], c.get("lang", "en"))
    ans, failed = r["answer"], []
    nums = [n for n in r.get("numbers", []) if n["status"] not in ("suggestion", "yours")]
    if r.get("error"):
        failed.append("coach error")
    bad = [n["text"] for n in nums if n["status"] == "unverified"]
    if bad:
        failed.append(f"unverified numbers: {', '.join(bad)}")
    for v in c.get("values", []):
        if not any(abs(n["value"] - round(v, 2)) <= 0.01 or (n["status"] == "rounded" and abs(n["value"] - v) <= max(5, 0.06 * v))
                   or abs(n["value"] - round(v)) < 0.01 for n in nums):
            failed.append(f"expected {v:.2f} € not in answer")
    if c.get("attachment") and not r.get("attachments"):
        failed.append("no chart drawn")
    for rx in c.get("must", []):
        if not re.search(rx, ans, re.I):
            failed.append(f"missing: {rx}")
    for rx in c.get("must_not", []):
        if re.search(rx, ans, re.I):
            failed.append(f"forbidden: {rx}")
    return {"trap": c["trap"], "question": c.get("shown", c["q"]), "persona": c["persona"], "ok": not failed, "failed": failed,
            "answer": ans if "shown" not in c else "(not stored: the question is hidden)", "tools": [t["tool"] for t in r.get("trace", [])],
            "numbers_total": len(nums), "numbers_verified": len(nums) - len(bad),
            "cost_usd": (r.get("usage") or {}).get("cost_usd", 0), "model": (r.get("usage") or {}).get("model", "")}


def main():
    cs = cases()
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(run_case, cs))
    run = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "model": coach.MODEL,
           "passed": sum(r["ok"] for r in res), "total": len(res),
           "numbers_verified": sum(r["numbers_verified"] for r in res), "numbers_total": sum(r["numbers_total"] for r in res),
           "cost_usd": round(sum(r["cost_usd"] for r in res), 3), "cases": res}
    out = ROOT / "state" / "traps.json"
    out.parent.mkdir(exist_ok=True)
    old = json.loads(out.read_text())["runs"] if out.exists() else []
    out.write_text(json.dumps({"runs": [run] + old[:9]}, indent=1, default=str))
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + r["trap"] + ("" if r["ok"] else f"  -> {r['failed']}"))
    print(f"{run['passed']}/{run['total']} passed, numbers {run['numbers_verified']}/{run['numbers_total']}, ${run['cost_usd']}")


if __name__ == "__main__":
    main()
