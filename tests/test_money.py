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


def test_extra_income_raises_both_figures_consistently():
    # Outside browser test 14 Nov: Emma +5,000 € gave 4,324.29 € until payday but 0 € this week.
    from app import charts
    sts = money.get_safe_to_spend("CUST01610")
    f = charts.forecast_with_events("CUST01610", [{"label": "Bonus", "amount": 5000, "date": "2026-10-01", "kind": "income"}])
    days = sts["days_until_payday"]
    assert f["safe_until_payday_after_eur"] == pytest.approx(sts["safe_until_payday_eur"] + 5000, abs=0.01)
    assert f["safe_this_week_after_eur"] == pytest.approx(f["safe_until_payday_after_eur"] / days * min(7, days), abs=0.01)
    g = charts.forecast_with_events(MIKKO, [{"label": "Concert", "amount": 80, "date": "2026-10-02"}])
    assert g["safe_this_week_after_eur"] == pytest.approx(max(0, g["safe_this_week_before_eur"] - 80), abs=0.01)


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


def test_basket_answers_flow_everywhere_and_reset(monkeypatch, tmp_path):
    # Sort with the AI: the customer's answer moves money between baskets in every tool; reset restores the data.
    from app import sorter
    monkeypatch.setattr(sorter, "ANSWERS", tmp_path / "a.json")
    monkeypatch.setattr(sorter, "_forget_ai_caches", lambda cid: None)
    monkeypatch.setattr(sorter.future, "_json_call", lambda *a, **k: {"takeaway": "x"})
    before = money.get_three_baskets(EMMA, "last_12_months")["baskets"]
    pool = {c["id"]: c for c in sorter.candidates(EMMA)}
    assert "s:Parking" in pool and pool["s:Parking"]["data_basket"] == 3
    r = sorter.answer(EMMA, {"s:Parking": 1})
    moved = pool["s:Parking"]["total_eur"]
    assert r["after"]["baskets_eur"]["1"] == pytest.approx(r["before"]["baskets_eur"]["1"] + moved, abs=0.02)
    assert r["after"]["baskets_eur"]["3"] == pytest.approx(r["before"]["baskets_eur"]["3"] - moved, abs=0.02)
    assert r["after"]["safe_until_payday_eur"] < r["before"]["safe_until_payday_eur"]  # a must-pay leaves less room
    sorter.reset(EMMA)
    assert money.get_three_baskets(EMMA, "last_12_months")["baskets"] == before


def test_limit_works_through_the_tx_view():
    # Regression: with LEFT JOINs in the override view, DuckDB ignored LIMIT (Wrapped's guess showed 23 options).
    assert len(money._q("SELECT sub FROM tx WHERE customer_id = ? LIMIT 4", [EMMA])) == 4
    from app import wrapped
    assert len(wrapped.facts(EMMA)["top_extras"]) == 4


def test_play_two_weeks_matches_the_forecast():
    # Keep every card = the usual forecast; skip every extra = the no-extras line; Emma's rescue = skip extras + move rent.
    from app import future, play
    d = play.deal(EMMA)
    f = future.future(EMMA)
    extras = [c["id"] for c in d["cards"] if c["kind"] == "extra"]
    assert play.outcome(EMMA, extras, False, d)["end_eur"] == pytest.approx(f["base"]["end_eur"], abs=0.05)
    assert play.outcome(EMMA, [], False, d)["end_eur"] == pytest.approx(f["no_extras"]["end_eur"], abs=0.05)
    rescue = play.outcome(EMMA, [], True, d)
    assert rescue["end_eur"] > 0 and rescue["rent_moved_after_payday"]
    assert all(c["kind"] != "extra" or c["basket"] == 3 for c in d["cards"])  # only extras are choices


def test_ticket_swap_replaces_parking_and_taxis(monkeypatch):
    # The live ticket price (Context.dev, hsl.fi) replaces the parking and taxi cards; offline here with a fixed price.
    from app import live, play
    monkeypatch.setattr(live, "registry", lambda: {"hsl_30day_ab": {"status": "confirmed", "value": 73.9,
                                                                     "source_url": "https://www.hsl.fi/x", "source_date": "2026-01-01"}})
    d = play.deal(EMMA)
    sw = d["swap"]
    assert sw and sw["replaces"] and all(c["label"] in play.TRANSPORT for c in d["cards"] if c["id"] in sw["replaces"])
    extras = [c["id"] for c in d["cards"] if c["kind"] == "extra"]
    plain, swapped = play.outcome(EMMA, extras, False, d), play.outcome(EMMA, extras, False, d, swap=True)
    assert swapped["end_eur"] == pytest.approx(plain["end_eur"] + sw["replaced_eur"] - 73.9, abs=0.05)
    assert swapped["swapped_to_ticket"]["source"] == "hsl.fi"


def test_eu_mode_routes_json_jobs_and_coach(monkeypatch):
    # EU mode: the structured AI jobs and the coach's tool loop run on the OpenAI-compatible endpoint (faked here).
    from app import coach, eu, future
    monkeypatch.setenv("EU_LLM_BASE_URL", "https://eu.example/v1")
    monkeypatch.setenv("EU_LLM_MODEL", "google/gemma-test")
    sent = []

    def fake_post(body, timeout=120):
        sent.append(body)
        if body.get("response_format"):
            return {"choices": [{"message": {"content": '{"takeaway": "ok"}'}}], "model": body["model"]}
        if not any(m["role"] == "tool" for m in body["messages"]):
            call = {"id": "c1", "type": "function", "function": {"name": "get_safe_to_spend", "arguments": "{}"}}
            return {"choices": [{"message": {"content": None, "tool_calls": [call]}, "finish_reason": "tool_calls"}], "model": body["model"]}
        sts = money.get_safe_to_spend(EMMA)
        return {"choices": [{"message": {"content": f"You are short by {abs(sts['safe_until_payday_eur']):,.2f} €."}, "finish_reason": "stop"}],
                "model": body["model"], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    monkeypatch.setattr(eu, "_post", fake_post)
    tok = eu.provider.set("eu")
    try:
        assert future._json_call("s", "u", {"type": "object"}) == {"takeaway": "ok"}
        r = coach.chat(EMMA, [{"role": "user", "text": "What is safe to spend?"}])
    finally:
        eu.provider.reset(tok)
    assert r["eu"] and not r["error"] and r["trace"][0]["tool"] == "get_safe_to_spend"
    assert all(n["status"] != "unverified" for n in r["numbers"])
    assert sent[1]["tools"][0]["type"] == "function"
    assert eu.cache_tag() == ""  # back to Claude outside the request


def test_graph_notes_are_rendered_from_facts_in_proper_finnish():
    # The AI only picks kind + date; text and value come from code (no "Kuluin eniten", no invented amounts).
    from app import future
    f = future.line_facts(EMMA, "fi")
    top = f["biggest_spending_days"][0]
    n = future._render_note("big_day", top["date"], f, "fi")  # the biggest day is always called the biggest
    assert n["kind"] == "biggest_day" and n["text"].startswith("Suurin menopäivä ") and n["text"].endswith(" €")
    assert future._render_note("below_zero", "2026-10-01", f, "fi") is None or f["goes_below_zero_on"] == "2026-10-01"
    assert future._render_note("biggest_day", "1999-01-01", f, "fi") is None
    bz = future._render_note("below_zero", f["goes_below_zero_on"], f, "sv")
    assert bz["text"] == "Kontot på minus"


def test_monthly_drains_add_up_and_stay_honest():
    from app import drains
    d = drains.drains(EMMA)
    assert d["habits"] and all(h["months_present"] >= drains.HABIT_MIN_MONTHS for h in d["habits"])
    assert d["drain_eur_month"] == pytest.approx(sum(h["eur_month"] for h in d["habits"]) + sum(s["eur_month"] for s in d["subscriptions"]), abs=0.05)
    assert d["drain_eur_year"] == pytest.approx(d["drain_eur_month"] * 12, abs=0.1)
    eat = next(h for h in d["habits"] if h["habit"] == "eating_out")
    assert "Restaurants" in eat["merchant_types"]
    assert {b["bill"] for b in d["bills"]} <= {"Housing", "Utilities"}


def test_psd2_full_picture_is_consented_labelled_and_revocable(monkeypatch, tmp_path):
    from app import psd2
    monkeypatch.setattr(psd2, "STATE", tmp_path / "psd2.json")
    jussi = "CUST00724"
    assert not psd2.status(jussi)["connected"] and psd2.status(jussi)["relevant"]   # salary moves to another bank
    assert psd2.get_other_accounts(jussi)["connected"] is False
    psd2.connect(jussi, "Nordea")
    o = psd2.get_other_accounts(jussi)
    assert o["connected"] and "demo" in o["source"] and o["total_eur"] == pytest.approx(o["s_bank_balance_eur"] + o["other_balance_eur"], abs=0.01)
    psd2.revoke(jussi)
    assert not psd2.status(jussi)["connected"]


@pytest.mark.parametrize("expr, want", [("(412,30+380,10)/2", 396.20), ("1,234.50 + 1", 1235.50), ("985 280,02 - 0,02", 985280.0),
                                        ("2 * 3", 6.0), ("4000 * ((1 + 0.08/12) ** 48 - 1) / (0.08/12)", 225399.66)])
def test_calculate_reads_numbers_like_the_number_check(expr, want):
    # Review: stripping every comma turned (412,30+380,10)/2 into 39,620, and the check then marked it verified.
    from app import coach
    assert coach.calculate(EMMA, expr)["result"] == pytest.approx(want, abs=0.01)


def test_numbers_from_earlier_answers_count_as_known():
    from app import verify
    earlier = ["Over 12 months that is 985 280,02 € in total, and halving it saves about 122 € a month."]
    n = verify.check("Yes: about 122 € a month, from the 985 280,02 € total.", [], ["yes"], "fi", earlier=earlier)
    assert [x["status"] for x in n] == ["earlier", "earlier"]
    assert verify.check("About 123 € a month.", [], [], "en", earlier=earlier)[0]["status"] == "unverified"


def test_month_breakdown_lists_every_month_so_row_averages_are_right():
    # Review: kiosks Apr-Sep listed 3 of 6 months; the mean of the rows was 70.55 € vs the true 35.27 €.
    r = money.get_spending(EMMA, start="2026-04-01", end="2026-09-30", subcategory="Kiosks & convenience stores", group_by="month")
    assert [b["key"] for b in r["breakdown"]] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    assert sum(b["total_eur"] for b in r["breakdown"]) / 6 == pytest.approx(r["average_per_month_eur"], abs=0.01)


def test_exact_arithmetic_shown_in_the_answer_is_derived_not_flagged():
    # Gemma probe 14 Nov: a total of listed baskets, a 3-month average and their difference were all cent-exact but flagged
    from app import verify
    trace = [{"tool": "get_three_baskets", "error": False, "result": {"b1": 1089.66, "b2": 368.60, "b3": 699.45, "income_3_months": 5723.97}}]
    ans = ("Fixed 1 089,66 €, surprises 368,60 €, extras 699,45 €. Yhteensä 2 157,71 €. Tulot 1 907,99 € kuussa "
           "(5 723,97 € / 3). Ylitys 249,72 €.")
    st = {n["text"]: n["status"] for n in verify.check(ans, trace, [], "fi")}
    assert st["2 157,71 €"] == st["1 907,99 €"] == st["249,72 €"] == "derived"
    assert verify.check("You could save 200.00 € a month.", [], ["Plan my spending so I can save 200 euros a month"], "en")[0]["status"] == "yours"
    assert verify.check("About 2 157,72 €.", trace, [], "fi")[0]["status"] == "unverified"   # one cent off stays flagged
