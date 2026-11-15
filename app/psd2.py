"""PSD2 multi-bank view (the brief's optional bonus): with the customer's consent, the coach sees their other bank too.

- Consent is real app state: bank, connected date, 90-day expiry, revocable (state/psd2.json).
- What we know from S-Bank's own data: how much moves to the other bank and when (salary sweeps, transfers).
- What a PSD2 account-information API would add: the other account's balance. The challenge data has no other bank,
  so that balance comes from a mock API and is labelled as demo data everywhere it is shown. It never enters
  safe-to-spend or forecasts; the coach shows it as the full picture and says where it comes from.
"""
from __future__ import annotations

import json
import statistics
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .money import TODAY, _month_start, _q, _r

STATE = Path(__file__).resolve().parent.parent / "state" / "psd2.json"
BANKS = ["OP", "Nordea", "Danske Bank", "Aktia", "Säästöpankki"]
OUT_TO_OTHER = ("Salary Sweep",)   # money the customer moves to their own account elsewhere
_lock = threading.Lock()


def _read() -> dict:
    with _lock:
        return json.loads(STATE.read_text()) if STATE.exists() else {}


def _write(d: dict) -> None:
    with _lock:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(d, indent=1))


def flows(cid: str) -> dict:
    """From S-Bank's own data: money moved to the customer's account in another bank, last 12 months."""
    start = _month_start(TODAY, 11)
    rows = _q(f"""SELECT strftime(tx_date, '%Y-%m') mo, -sum(amount) t FROM tx WHERE customer_id = ? AND tx_date >= ?
                  AND category IN {OUT_TO_OTHER} GROUP BY 1 ORDER BY 1""", [cid, start])
    sal = _q("SELECT median(amount) s FROM tx WHERE customer_id = ? AND category = 'Salary' AND tx_date >= ?", [cid, start])[0]["s"]
    per = [r["t"] for r in rows if r["t"] and r["t"] > 0]
    return {"months_with_transfers": len(per), "moved_last_12_months_eur": _r(sum(per)),
            "typical_month_eur": _r(statistics.median(per)) if per else 0.0, "salary_eur": _r(sal) if sal else None}


def status(cid: str) -> dict:
    c = _read().get(cid)
    f = flows(cid)
    if not c:
        return {"connected": False, "flows": f, "relevant": f["months_with_transfers"] >= 3}
    exp = datetime.fromisoformat(c["expires"])
    if exp < datetime.now(timezone.utc):
        return {"connected": False, "expired": True, "flows": f, "relevant": True}
    # Mock account-information API: a demo balance, deterministic per customer, never from the challenge data
    demo_balance = _r(round(f["typical_month_eur"] * 1.4, -1)) if f["typical_month_eur"] else 1240.0
    return {"connected": True, "bank": c["bank"], "connected_at": c["connected_at"], "expires": c["expires"],
            "days_left": max((exp - datetime.now(timezone.utc)).days, 0), "flows": f, "relevant": True,
            "other_account": {"bank": c["bank"], "iban_masked": "FI•• •••• •••• 4821", "balance_eur": demo_balance,
                              "source": "mock PSD2 account-information API (demo data, not from the dataset)"}}


def connect(cid: str, bank: str) -> dict:
    if bank not in BANKS:
        raise ValueError("unknown bank")
    now = datetime.now(timezone.utc)
    d = _read()
    d[cid] = {"bank": bank, "connected_at": now.isoformat(timespec="seconds"), "expires": (now + timedelta(days=90)).isoformat(timespec="seconds"),
              "scope": ["balances", "transactions"], "payments": False}
    _write(d)
    return status(cid)


def revoke(cid: str) -> dict:
    d = _read(); d.pop(cid, None); _write(d)
    return status(cid)


def get_other_accounts(cid: str) -> dict:
    """Coach tool: the customer's other bank, if they connected it (PSD2)."""
    s = status(cid)
    if not s["connected"]:
        return {"connected": False, "flows_seen_from_s_bank": s["flows"],
                "note": "No other bank is connected. Say you can only see this account and offer to connect it (PSD2)."}
    acc = s["other_account"]
    here = _q("SELECT balance FROM tx WHERE customer_id = ? AND tx_date <= ? ORDER BY seq DESC LIMIT 1", [cid, TODAY])[0]["balance"]
    return {"connected": True, "other_bank": acc["bank"], "other_balance_eur": acc["balance_eur"], "source": acc["source"],
            "s_bank_balance_eur": _r(here), "total_eur": _r(here + acc["balance_eur"]),
            "moved_to_other_bank_last_12_months_eur": s["flows"]["moved_last_12_months_eur"],
            "typical_monthly_transfer_eur": s["flows"]["typical_month_eur"], "consent_days_left": s["days_left"],
            "rule": "The other balance is demo data; say so. It is not part of safe-to-spend or the forecast."}
