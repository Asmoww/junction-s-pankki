"""Offline tests for the money tools (no API calls). Need data/tx.parquet (scripts/build_data.py)."""
import pytest

from app import money

EMMA, MIKKO, JUSSI = "CUST01610", "CUST04588", "CUST00724"


def test_balance_chain_holds_everywhere():
    bad = money._q("""SELECT count(*) n FROM (SELECT amount, balance,
                      lag(balance) OVER (PARTITION BY customer_id ORDER BY seq) pb FROM tx)
                      WHERE pb IS NOT NULL AND abs(pb + amount - balance) >= 0.011""")[0]["n"]
    assert bad == 0


def test_transfers_are_never_spending():
    rows = money._q("SELECT count(*) n FROM tx WHERE category IN ('Salary Sweep', 'Invest Deposit') AND kind = 'spend'")
    assert rows[0]["n"] == 0
    cf = money.get_cashflow(JUSSI, "last_month")
    assert cf["moved_to_own_savings_or_investments_eur"]["salary_sweep_to_other_account"] > 2000
    assert cf["spending_eur"]["total"] < 500  # the sweep must not show up as spending
    assert "note" in cf


def test_last_month_is_august_2026():
    s, e = money.resolve_period("last_month")
    assert (s.isoformat(), e.isoformat()) == ("2026-08-01", "2026-08-31")


def test_taxi_answer_reports_unclassifiable_purchases():
    r = money.get_spending(MIKKO, "last_month", subcategory="Taxis")
    assert r["total_eur"] == pytest.approx(61.77)
    assert r["not_classifiable"]["count"] >= 1


def test_safe_to_spend_steps_add_up():
    for cid in (EMMA, MIKKO, JUSSI):
        r = money.get_safe_to_spend(cid)
        assert sum(s["eur"] for s in r["steps"]) == pytest.approx(r["safe_until_payday_eur"], abs=0.05)
        assert r["safe_this_week_eur"] >= 0


def test_savings_are_not_safe_to_spend():
    r = money.get_safe_to_spend(MIKKO)
    assert r["savings_in_account_eur"] > 10000
    assert r["safe_until_payday_eur"] < 2000


def test_short_customer_gets_a_warning():
    r = money.get_safe_to_spend(EMMA)
    assert r["safe_until_payday_eur"] < 0 and r["warning"]


def test_baskets_sum_to_total():
    r = money.get_three_baskets(MIKKO, "last_3_months")
    assert sum(b["total_eur"] for b in r["baskets"]) == pytest.approx(r["total_spending_eur"], abs=0.05)


def test_bad_input_is_a_tool_error():
    with pytest.raises(money.ToolError):
        money.get_spending(EMMA, subcategory="Unicorns")
    with pytest.raises(money.ToolError):
        money.simulate_cut(EMMA, 20)


def test_cashflow_gives_balance_change_so_the_model_never_subtracts():
    b = money.get_cashflow(JUSSI, "last_month")["balance_eur"]
    assert b["change"] == pytest.approx(b["end"] - b["start"], abs=0.01)


def test_verify_statuses():
    from app import verify
    trace = [{"tool": "x", "error": False, "result": {"total_eur": 997.4, "share": 0.362}}]
    got = {n["text"]: n["status"] for n in verify.check(
        "You spent 997.40 €, about 1,000 €, 36.2% of it, and 12 €. Want to see a 30% cut?", trace, [], "en",
        {"balance": 699.85})}
    assert got == {"997.40 €": "verified", "1,000 €": "rounded", "36.2%": "verified", "12 €": "unverified",
                   "30%": "suggestion"}
    fi = verify.check("Säästät 47,10 € kuussa, saldo 699,85 €.", [{"tool": "x", "error": False,
                      "result": {"s": 47.1}}], [], "fi", {"balance": 699.85})
    assert [n["status"] for n in fi] == ["verified", "verified"]


def test_forecast_puts_rent_on_its_day():
    from app import insights
    f = insights.payday_forecast(EMMA)
    assert f["runs_out_around"] == "2026-10-03"  # 777 € rent on the 3rd is bigger than the 699.85 € balance
    assert f["balance_at_payday_at_usual_pace_eur"] < 0
    assert f["daily_path"][-1]["balance_eur"] == f["balance_at_payday_at_usual_pace_eur"]


def test_future_engine_matches_forecast_and_safe_to_spend():
    from app import future, insights
    f = future.future(EMMA)
    assert f["base"]["end_eur"] == pytest.approx(insights.payday_forecast(EMMA)["balance_at_payday_at_usual_pace_eur"], abs=0.05)
    # pausing every extra lands exactly on the "even with no extras" shortfall
    assert -f["no_extras"]["end_eur"] == pytest.approx(-money.get_safe_to_spend(EMMA)["safe_until_payday_eur"], abs=0.05)
    s = future.future(EMMA, {"one_offs": [{"label": "Concert", "amount": 150, "date": "2026-10-02"}]})["scenario"]
    assert s["delta_at_payday_eur"] == pytest.approx(-150, abs=0.01)
    moved = future.future(EMMA, {"move_bills": [{"bill": "Housing", "date": "2026-10-16"}]})["scenario"]
    assert moved["delta_at_payday_eur"] == pytest.approx(762.79, abs=0.05)


def test_rahakunto_matches_reference_backtest_people():
    from app import insights
    m = insights.money_health(MIKKO)
    assert m["score"] == 70 and m["parts"] == {"spend": 81, "on_time": 100, "buffer": 100, "long_term": 0}
    assert m["steps"][0]["part"] == "long_term"
    e = insights.money_health(EMMA)
    assert e["score"] == 19 and e["tier"] == "vulnerable" and e["tone"] == "comfort"
    assert e["steps"][0]["target"] == "break_even" and e["steps"][0]["gap_eur_month"] == pytest.approx(206, abs=3)
    j = insights.money_health(JUSSI)
    assert j["parts"]["long_term"] is None and j["coverage"] == "3 of 8"  # unknown is never averaged in as 0


def test_charts_and_dated_events():
    from app import charts
    c = charts.show_chart(MIKKO, "monthly_spend", months=12)
    aug = next(p["v"] for p in c["series"][0]["points"] if p["x"] == "2026-08")
    assert aug == pytest.approx(money.get_cashflow(MIKKO, "last_month")["spending_eur"]["total"], abs=0.01)
    f = charts.forecast_with_events(MIKKO, [{"label": "Dentist", "amount": 150, "date": "2026-10-08"}])
    assert f["safe_this_week_after_eur"] == f["safe_this_week_before_eur"]  # next week's cost doesn't hit this week
    assert f["safe_until_payday_after_eur"] == pytest.approx(f["safe_until_payday_before_eur"] - 150, abs=0.01)


def test_verify_derived_sums_only_within_one_tool():
    from app import verify
    tr = [{"tool": "a", "error": False, "result": {"groceries": 397.73, "buffer": 163.30}},
          {"tool": "b", "error": False, "result": {"x": 100.00}}]
    got = {n["text"]: n["status"] for n in verify.check("About 561.03 € more, and 497.73 € elsewhere, and 777.77 €.", tr, [])}
    assert got == {"561.03 €": "derived", "497.73 €": "unverified", "777.77 €": "unverified"}


def test_wrapped_facts_add_up():
    from app import wrapped
    f = wrapped.facts(EMMA)
    assert sum(f["baskets_eur"].values()) == pytest.approx(f["money_out_eur"], abs=0.05)
    t = f["twins"]
    assert t["twins_who_never_went_below_zero"] >= 20  # a group, never one person
    assert t["your_extras_per_month_eur"] == pytest.approx(f["baskets_eur"]["3"] / 12, abs=0.01)
    assert f["no_spend_days"] >= f["longest_no_spend_streak_days"] > 0
