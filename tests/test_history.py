"""Pure part of the longer Home trend view."""
from datetime import date, timedelta

from app.insights import downsample


def test_weekly_downsample_keeps_each_weeks_last_day():
    days = [{"date": date(2026, 9, 1) + timedelta(days=i), "balance_eur": float(i)} for i in range(21)]
    w = downsample(days, "week")
    assert len(w) == 4                                   # 1 Sep 2026 is a Tuesday: 4 ISO weeks touched
    assert all(p["date"].weekday() == 6 for p in w[:-1]) # Sundays end each full week
    assert w[-1] == days[-1]                             # the latest day is always the last point


def test_daily_is_unchanged():
    days = [{"date": date(2026, 9, 1), "balance_eur": 1.0}]
    assert downsample(days, "day") == days
