"""Offline tests for app/readiness.assess (pure maths, no database, no API)."""
from app.readiness import assess, core

BASE = dict(price=250_000, salary=4_000, have=14_720, cap_pct=95, tax_pct=1.5, euribor_pct=3.293,
            surpluses=[600, 800, 975, 975, 1100, 1300, 700, 900, 1000, 1200, 850, 950],
            must_pays_month=1_900, housing_month=900, extras_month=700)


def test_core_matches_plan_home_formula():
    c = core(250_000, 4_385, 14_720, 95, 1.5)
    assert round(c["by_income"], 2) == round(4_385 / 0.018409, 2)   # plan_home's stress formula
    assert c["loan"] == min(c["by_income"], c["by_cap"])
    assert round(c["need"], 2) == round(250_000 - c["loan"] + 3_750 + 550, 2)


def test_range_is_ordered_and_binding_is_income():
    r = assess(**BASE)
    g = r["range"]
    assert g["earliest_months"] <= g["likely_months"] <= g["cautious_months"]
    assert r["binding"]["key"] == "income_caps_loan"
    assert {a["key"] for a in r["also"]} >= {"own_funds", "collateral"}


def test_deficit_is_binding_and_no_date():
    r = assess(**{**BASE, "surpluses": [-300, -200, -250, 100]})
    assert r["binding"]["key"] == "monthly_gap"
    assert r["range"]["likely_months"] is None              # never a date on a negative pace


def test_cheap_home_has_nothing_blocking():
    r = assess(**{**BASE, "price": 60_000, "have": 40_000})
    assert r["gap_eur"] == 0 and r["range"]["likely_months"] == 0
    assert r["binding"]["key"] in ("none", "collateral", "life_after")


def test_next_question_is_computed_not_fixed():
    r = assess(**BASE)
    q = r["next_question"]
    assert q is not None and q["months_saved"] > 0
    # It must be the candidate that saves the most months, and the answer changes with the person's numbers
    assert q["months_saved"] == max(c["months_saved"] for c in r["questions_considered"])
    alt = assess(**{**BASE, "salary": 3_000, "extras_month": 3_000})
    assert alt["next_question"]["key"] == "save_more"


def test_provenance_labels_the_stress_formula_as_assumption():
    r = assess(**BASE)
    assert any("not S-Pankki credit policy" in a for a in r["provenance"]["assumption"])
    assert "S-Bank decides" in r["disclaimer"]


def test_slow_pace_gives_reachable_price_instead_of_silence():
    r = assess(**{**BASE, "surpluses": [250] * 12, "salary": 3_300})
    assert r["range"]["likely_months"] is None
    assert r["reachable_price"]["within_60_months_eur"] is not None
    assert r["next_question"]["key"] == "reachable_price"


def test_deficit_asks_to_fix_the_month_first():
    r = assess(**{**BASE, "surpluses": [-400] * 12})
    assert r["next_question"]["key"] == "fix_month"
    assert r["reachable_price"]["within_24_months_eur"] is None


def test_money_moved_elsewhere_becomes_a_question_not_a_silent_assumption():
    r = assess(**{**BASE, "moved_out_eur": 52_000})
    assert r["have_eur"] == BASE["have"]                     # not counted without asking
    assert any(c["key"] == "savings_elsewhere" for c in r["questions_considered"])
    assert r["next_question"]["key"] == "savings_elsewhere"  # 52 k would move the date most


def test_asp_offered_when_collateral_blocks_and_first_home_unknown():
    r = assess(**{**BASE, "price": 200_000, "have": 40_000})
    asp = [c for c in r["questions_considered"] if c["key"] == "asp"]
    assert asp and asp[0]["likely_months_if_yes"] >= 20      # ASP needs at least 20 months of saving
    assert not any(c["key"] == "asp" for c in assess(**{**BASE, "first_home": False})["questions_considered"])
