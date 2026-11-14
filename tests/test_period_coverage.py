"""Outside test 14 Nov: Jan-Dec 2024 spending averaged over 12 months although data starts 2024-10-01."""
from datetime import date

from app.money import _per_month, _period_info


def test_partial_year_averages_only_covered_months():
    info = _period_info(date(2024, 1, 1), date(2024, 12, 31))
    assert info["months"] == 12 and info["months_with_data"] == 3
    assert "unavailable, not zero" in info["coverage_note"]
    assert _per_month(6130.72, info) == 2043.57


def test_period_before_data_has_no_average():
    info = _period_info(date(2024, 1, 1), date(2024, 1, 31))
    assert info["months_with_data"] == 0 and _per_month(100.0, info) is None


def test_full_coverage_has_no_note():
    info = _period_info(date(2026, 4, 1), date(2026, 9, 30))
    assert info["months_with_data"] == 6 and "coverage_note" not in info
