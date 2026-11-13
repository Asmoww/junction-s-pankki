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
