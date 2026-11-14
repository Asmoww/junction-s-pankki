"""Outside test 14 Nov: the answer was about cutting all extras 100 % (818.42 €/month) but the slider showed the
last simulate_cut call (restaurants, 141 €/month). The widget must follow the scenario the answer states."""
from app.coach import _attachments


def _cut(area, pct, now, save):
    return {"tool": "simulate_cut", "error": False, "input": {},
            "result": {"area": {"category": area, "subcategory": None, "basket": None}, "cut_percent": pct,
                       "now_per_month_eur": now, "saving_per_month_eur": save, "based_on": "6 months"}}


def test_slider_shows_the_scenario_in_the_answer():
    trace = [_cut(None, 100, 818.42, 818.42), _cut("Restaurants", 60, 235.50, 141.30)]
    trace[0]["result"]["area"] = {"category": None, "subcategory": None, "basket": 3}
    ans = "Cutting all everyday extras would save 818.42 € a month (restaurants are already inside that)."
    sliders = [a for a in _attachments(trace, ans) if a.get("type") == "slider"]
    assert len(sliders) == 1 and sliders[0]["cut_percent"] == 100 and sliders[0]["area"] == "basket 3"


def test_falls_back_to_last_call_when_answer_names_no_amount():
    trace = [_cut("Groceries", 20, 400.0, 80.0), _cut("Restaurants", 50, 200.0, 100.0)]
    sliders = [a for a in _attachments(trace, "Here is the idea.") if a.get("type") == "slider"]
    assert sliders[0]["area"] == "Restaurants"
