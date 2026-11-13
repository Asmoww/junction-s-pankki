"""Offline tests for the Context.dev layer: a fake client replays the shapes seen in the live dry runs.
No network, no credits."""
import hashlib
import hmac
import json
from types import SimpleNamespace as NS

import pytest

from app import homeplan, live


class Fake:
    """Records every call so we can check that no customer data ever leaves."""

    def __init__(self, answers=None, pages=None, search_url=None, json_pages=None):
        self.calls = []
        self._answers, self._pages, self._search_url, self._json = answers or {}, pages or {}, search_url, json_pages or {}
        self.web = NS(answers=self.answers, scrape=self.scrape, search=self.search)

    def answers(self, **kw):
        self.calls.append(("answers", kw))
        return NS(json_content=self._answers, request_id="req_answers", sources=[])

    def search(self, **kw):
        self.calls.append(("search", kw))
        return NS(request_id="req_search", results=[NS(url=self._search_url)] if self._search_url else [])

    def scrape(self, **kw):
        self.calls.append(("scrape", kw))
        url = kw["url"]
        cache = NS(age_ms=120_000, status="hit")
        if kw["formats"].get("json"):
            data = self._json.get(url)
            return NS(request_id="req_json", cache_metadata=cache,
                      json_=NS(success=data is not None, data=data, error_code=None if data else "no_data"))
        prod = self._pages.get(url)
        if prod is None:
            return NS(request_id="req_scrape", cache_metadata=cache, product=NS(success=False, data=None, error_code="blocked"))
        return NS(request_id="req_scrape", cache_metadata=cache, product=NS(success=True, error_code=None, data=NS(
            is_product_page=True, product=NS(price=prod[0], currency=prod[1], name="iPhone 17 256 Gt <b>musta</b>",
                                             availability="in_stock", regular_price=None))))


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "STATE", tmp_path)
    monkeypatch.setattr(live, "MONITORS_FILE", tmp_path / "monitors.json")

    def install(f):
        monkeypatch.setattr(live, "_client", f)
        return f
    return install


VK = "https://www.verkkokauppa.com/fi/product/iphone17"
GIG = "https://www.gigantti.fi/product/iphone17"
POW = "https://www.power.fi/iphone17"


def test_answers_price_never_used_page_price_wins(fake):
    # Dry run: web-answers said 879 € for verkkokauppa, the page itself says 999 €.
    f = fake(Fake(answers={"offers": [{"shop": "Verkkokauppa", "url": VK, "price_eur": 879},
                                      {"shop": "Gigantti", "url": GIG, "price_eur": 879},
                                      {"shop": "Power", "url": POW, "price_eur": 899}]},
                  pages={VK: (999.0, "EUR"), GIG: (989.0, "EUR")}))
    r = live.check_purchase("iPhone 17 256 GB")
    assert [o["price_eur"] for o in r["confirmed"]] == [989.0, 999.0]
    vk = next(o for o in r["confirmed"] if o["url"] == VK)
    assert vk["claim_differed"] and vk["claimed_price_eur"] == 879
    assert r["summary"]["low_eur"] == 989.0 and 879 not in (r["summary"]["low_eur"], r["summary"]["high_eur"])
    assert [o["url"] for o in r["not_confirmed"]] == [POW] and r["not_confirmed"][0]["price_eur"] is None
    assert all(kw["max_age_ms"] <= 3_600_000 for k, kw in f.calls if k == "scrape")
    assert "<" not in vk["name"]  # untrusted page text is reduced to a plain label


def test_nothing_confirmed_means_unknown_not_zero(fake):
    fake(Fake(answers={"offers": [{"shop": "X", "url": POW, "price_eur": 899}]}, pages={}))
    r = live.check_purchase("Levi weekend")
    assert r["confirmed"] == [] and r["summary"] is None


def test_non_euro_or_absurd_price_is_not_confirmed(fake):
    fake(Fake(answers={"offers": [{"shop": "A", "url": VK}, {"shop": "B", "url": GIG}]},
              pages={VK: (999.0, "SEK"), GIG: (0.5, "EUR")}))
    r = live.check_purchase("iPhone")
    assert r["confirmed"] == [] and len(r["not_confirmed"]) == 2


def test_only_the_item_name_leaves_the_bank(fake):
    f = fake(Fake(answers={"offers": []}))
    live.check_purchase("iPhone 17 for CUST01610 FI21 1234 5600 0007 85")
    sent = json.dumps([kw for _, kw in f.calls], default=str)
    assert "CUST01610" not in sent and "FI21" not in sent and "iPhone 17" in sent


FSA = "https://www.finanssivalvonta.fi/en/publications-and-press-releases/press-release/2026/loan-cap"


def test_rule_registry_keeps_unknown_and_validates(fake):
    fake(Fake(search_url=FSA, json_pages={FSA: {"value": 95, "as_of": "2026-06-30", "effective_from": None}}))
    r = live.refresh_rule("loan_cap_general")
    assert r["status"] == "confirmed" and r["value"] == 95 and r["source_url"] == FSA and r["effective_from"] is None
    assert r["source_date"] == "2026-06-30" and r["fetched_at"] and r["request_id"]
    fake(Fake(search_url=FSA, json_pages={FSA: {"value": 950}}))  # implausible → not stored over the good value
    r2 = live.refresh_rule("loan_cap_general")
    assert r2["value"] == 95 and r2["last_refresh_failed"]
    assert live.registry()["euribor_12m"]["value"] is None and live.registry()["euribor_12m"]["status"] == "unknown"


def test_home_plan_reads_registry(fake, monkeypatch):
    reg = {"loan_cap_general": {"status": "confirmed", "value": 95.0},
           "transfer_tax_shares": {"status": "confirmed", "value": 1.5}, "euribor_12m": {"status": "confirmed", "value": 3.293}}
    monkeypatch.setattr(live, "registry", lambda: {k: {"key": k, "label": v["label"], **reg.get(k, {"status": "unknown", "value": None})}
                                                   for k, v in live.RULES.items()})
    p = homeplan.plan_home("CUST04138", 250_000)  # Mikko, as in Rasmus's dry run
    assert p["loan_eur"] == 237_500 and p["transfer_tax_eur"] == 3_750 and p["equity_and_costs_needed_eur"] == 16_800
    assert p["extra_collateral_needed_eur"] == 57_500
    assert p["unknown"] == ["bank margin (monthly payment is a lower bound)"]
    monkeypatch.setattr(live, "registry", lambda: {k: {"key": k, "label": v["label"], "status": "unknown", "value": None}
                                                   for k, v in live.RULES.items()})
    q = homeplan.plan_home("CUST04138", 250_000)
    assert q["loan_eur"] is None and q["months_to_goal"] is None and "loan cap" in q["unknown"]


def test_webhook_signature():
    body, secret, t = b'{"id":"evt_1","event":"change.detected"}', "whsec_test", 1_800_000_000
    v1 = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    assert live.verify_signature(body, f"t={t},v1={v1}", secret, now=t + 10)
    assert not live.verify_signature(body + b" ", f"t={t},v1={v1}", secret, now=t)        # tampered body
    assert not live.verify_signature(body, f"t={t},v1={v1}", secret, now=t + 301)          # too old
    assert not live.verify_signature(body, f"t={t},v1={v1}", "whsec_other", now=t)         # wrong secret


def test_rule_refresh_prefers_newest_release(fake):
    old = "https://www.finanssivalvonta.fi/tiedotteet/2024/lainakatto-ennallaan/"
    new = "https://www.finanssivalvonta.fi/tiedotteet/2026/lainakatto-nousee-95-prosenttiin/"
    f = Fake(json_pages={new: {"value": 95, "as_of": "2026-06-30"}, old: {"value": 90, "as_of": "2024-06-28"}})
    f.web.search = lambda **kw: NS(request_id="r", results=[NS(url=old), NS(url="https://www.finanssivalvonta.fi/en/"), NS(url=new)])
    fake(f)
    assert live.refresh_rule("loan_cap_general")["value"] == 95
