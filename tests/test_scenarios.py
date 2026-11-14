"""Offline tests for app/scenarios (pure core: run, suggest, assumptions)."""
from app.scenarios import assumptions, run, suggest


def _profile(gap=False, irregular=False, lumpy=False):
    months = []
    for i in range(12):
        sur = (1200 if i == 4 else 40) if lumpy else 150
        months.append({"month": f"2025-{i % 12 + 1:02d}", "salary": 2600, "other_income": (900 if i % 3 == 0 else 0) if irregular else 0,
                       "fixed": 1500, "housing": 800, "surprise": sur, "moved_out": 0.0,
                       "extras": {"Restaurants": 500 if gap else 250, "Shopping": 600 if gap else 200, "Transport": 120}})
    return {"balance": 1200.0, "months": months, "extras_categories": ["Restaurants", "Shopping", "Transport"]}


def test_baseline_and_no_change_scenario_are_identical():
    r = run(_profile())
    assert r["status"] == "ok" and r["effect_on_total_money"]["typical"] == 0
    assert r["baseline"]["account_end"] == r["scenario"]["account_end"]


def test_cut_improves_total_and_range_is_ordered():
    r = run(_profile(), {"category_cuts_pct": {"Restaurants": 50}})
    e = r["scenario"]["account_end"]
    assert e["bad"] <= e["typical"] <= e["good"]
    assert r["effect_on_total_money"]["typical"] == 125 * 12          # 50 % of 250 € for 12 months


def test_saving_moves_money_not_spends_it():
    r = run(_profile(), {"save_on_payday_eur": 200})
    assert r["effect_on_total_money"]["typical"] == 0 and r["effect_on_savings"]["typical"] == 2400
    assert r["scenario"]["savings_end_typical_eur"] == 2400


def test_bad_inputs_are_clamped_and_reported():
    r = run(_profile(), {"extras_cut_pct": 150, "category_cuts_pct": {"Netflix": 50}, "wat": 1})
    assert any("limited" in n for n in r["notes"]) and any("Netflix" in n for n in r["notes"])
    assert any("wat" in n for n in r["notes"])


def test_every_assumption_has_a_source_and_levers_have_bounds():
    rows = assumptions(_profile(), {"salary_change_pct": 5})
    assert all(r["source"] for r in rows)
    lever = [r for r in rows if r["key"] == "salary_change_pct"][0]
    assert lever["source"] == "your edit" and lever["min"] == -50 and lever["max"] == 50


def test_suggestions_follow_the_persons_situation():
    gap = [s["key"] for s in suggest(_profile(gap=True))]
    assert gap[0] == "close_gap"
    irr = [s["key"] for s in suggest(_profile(irregular=True), k=6)]
    assert "income_stops" in irr
    lumpy = [s["key"] for s in suggest(_profile(lumpy=True), k=6)]
    assert "surprise" in lumpy
    assert "save_on_payday" in [s["key"] for s in suggest(_profile(), safe_to_save_eur=200, k=6)]


def test_lumpy_surprises_widen_the_range():
    flat, lumpy = run(_profile())["baseline"]["account_end"], run(_profile(lumpy=True))["baseline"]["account_end"]
    assert (lumpy["good"] - lumpy["bad"]) > (flat["good"] - flat["bad"])


def test_saving_suggestion_never_doubles_an_existing_habit():
    p = _profile()
    for x in p["months"]:
        x["moved_out"] = 300.0
    assert "save_on_payday" not in [s["key"] for s in suggest(p, safe_to_save_eur=250, k=6)]
    s = [s for s in suggest(p, safe_to_save_eur=500, k=6) if s["key"] == "save_on_payday"][0]
    assert s["levers"]["save_on_payday_eur"] == 200 and "more" in s["title"]
