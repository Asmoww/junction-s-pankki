"""Fixes for two trap failures on Gemma (14 Nov): 'next Thursday' read as tomorrow, and a correct compound-growth
answer (225,399.66 €) failing the trap's pattern. Also pins "$4000" in a question as the user's own number."""
import re

import pytest

from app import charts, verify
from tests.traps.cases import cases

MIKKO = "CUST04588"


@pytest.mark.parametrize("said, iso", [("next Thursday", "2026-10-08"), ("Thursday", "2026-10-01"), ("this Thursday", "2026-10-01"),
                                       ("tomorrow", "2026-10-01"), ("the 10th", "2026-10-10"), ("in 2 weeks", "2026-10-14"),
                                       ("ensi torstaina", "2026-10-08"), ("nästa torsdag", "2026-10-08"), ("2026-10-08", "2026-10-08")])
def test_resolve_day(said, iso):
    assert charts.resolve_day(said).isoformat() == iso


def test_dentist_next_thursday_does_not_touch_this_week():
    r = charts.forecast_with_events(MIKKO, [{"label": "dentist", "amount": 150, "date": "next Thursday"}])
    assert r["events"][0]["date"] == "2026-10-08" and r["events"][0]["day"] == "Thursday 8 October 2026"
    assert r["safe_this_week_after_eur"] == r["safe_this_week_before_eur"]
    assert r["safe_until_payday_after_eur"] == round(r["safe_until_payday_before_eur"] - 150, 2)


def test_compound_growth_trap_accepts_the_exact_answer():
    case = next(c for c in cases() if c["trap"].startswith("Compound growth"))
    for ok in ("about 225,399.66 €", "roughly 225 400 €", "226,902.32 € if you invest at the start of each month"):
        assert re.search(case["must"][0], ok), ok
    assert not re.search(case["must"][0], "192,000.00 €")


def test_dollar_amount_in_question_is_the_users():
    q = "If I were to invest in S&P 500 $4000 a month for 4 years with 8 % expected return, how much money would I have?"
    found = verify.check("Investing **4,000.00 €** a month at 8 %…", [], [q], "en", explain=True, notes=[])
    assert [(n["text"], n["status"]) for n in found] == [("4,000.00 €", "yours"), ("8 %", "yours")]
