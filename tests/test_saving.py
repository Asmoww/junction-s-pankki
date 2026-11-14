"""Offline tests for app/saving.assess (safe to save on payday)."""
from app.saving import assess


def _c(lows):
    return [{"start": f"2026-{i + 1:02d}-15", "low_own_money_eur": x} for i, x in enumerate(lows)]


def test_safe_amount_fits_at_least_three_of_four_months():
    r = assess(_c([400, 520, 610, 380, 700, 450, 300, 560, 640, 480, 510, 590]), buffer_eur=100, salary_eur=2500)
    assert r["status"] == "ok"
    assert r["months_it_would_have_been_safe"] >= 9 and r["safe_to_save_on_payday_eur"] % 10 == 0
    assert r["stretch_eur"] >= r["safe_to_save_on_payday_eur"]


def test_deficit_months_give_zero_and_say_why():
    r = assess(_c([-200, -50, 30, -400, 10, -120]), buffer_eur=80)
    assert r["safe_to_save_on_payday_eur"] == 0 and "gap" in r["why_zero"]


def test_buffer_lowers_the_amount():
    lows = _c([500] * 12)
    assert assess(lows, buffer_eur=0)["safe_to_save_on_payday_eur"] > assess(lows, buffer_eur=200)["safe_to_save_on_payday_eur"]


def test_too_little_history():
    assert assess(_c([100, 200]), buffer_eur=0)["status"] == "too_little_history"


def test_already_saving_is_recognised():
    r = assess(_c([2500] * 12), buffer_eur=0, already_moving_eur=2600)
    assert "already" in r["already_note"]
