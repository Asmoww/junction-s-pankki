"""Where each number in a coach answer comes from (verify.check with explain=True). Offline, no data needed."""
from app import verify

TRACE = [
    {"tool": "get_cashflow", "input": {"period": "last_12_months"}, "result": {"income_per_month_eur": 2412.60}},
    {"tool": "get_spending", "input": {"period": "last_12_months", "basket": 3}, "result": {"average_per_month_eur": 318.40}},
    {"tool": "calculate", "input": {"expression": "2412.60 * 0.2", "what": "monthly saving at 20 %"}, "result": {"result": 482.52}},
    {"tool": "calculate", "input": {"expression": "318.40 * 0.3", "what": "saved by a 30 % cut"}, "result": {"result": 95.52}},
    {"tool": "calculate", "input": {"expression": "1000000 / 482.52", "what": "months to a million"}, "result": {"result": 2072.45}},
]
ANSWER = ("Your pay averaged **2,412.60 €** a month and extras took **318.40 €**. Saving **20 %** would be **482.52 €** "
          "a month. Cutting extras by **30 %** adds **95.52 €**. That builds toward **1,000,000 €**. "
          "A common rule of thumb is to save at least **15 %** of your income for the long run. "
          "Want to see a 10 % cut?\n"
          "<number-notes>\n15 %|rule|A widely used savings guideline for long-term goals.\n"
          "20 %|note|A common savings target that still leaves room for bills.\n</number-notes>")


def run(answer=ANSWER, trace=TRACE, user=("How could I become a millionaire?",)):
    text, notes = verify.split_notes(answer)
    return text, {n["text"]: n for n in verify.check(text, trace, list(user), "en", explain=True, notes=notes)}


def test_notes_block_is_removed():
    text, _ = run()
    assert "number-notes" not in text and "guideline" not in text and text.endswith("Want to see a 10 % cut?")


def test_each_number_gets_its_source():
    _, n = run()
    st = {k: v["status"] for k, v in n.items()}
    assert st == {"2,412.60 €": "verified", "318.40 €": "verified", "20 %": "assumption", "482.52 €": "calculated",
                  "30 %": "assumption", "95.52 €": "calculated", "1,000,000 €": "yours", "15 %": "rule",
                  "10 %": "suggestion"}
    assert n["20 %"]["note"].startswith("A common savings target")
    assert "2412.60 * 0.2" in n["482.52 €"]["source"]


def test_statistic_stays_unchecked_even_if_marked_rule():
    ans = "Most people who get there save around **15 %** of their income.\n<number-notes>\n15 %|rule|Rule of thumb.\n</number-notes>"
    _, n = run(ans)
    assert n["15 %"]["status"] == "unverified"


def test_claim_about_user_stays_unchecked_even_if_marked_rule():
    ans = "You spent **15 %** of your pay on taxis.\n<number-notes>\n15 %|rule|Rule of thumb.\n</number-notes>"
    _, n = run(ans)
    assert n["15 %"]["status"] == "unverified"


def test_made_up_fact_through_calculate_is_never_green():
    trace = TRACE + [{"tool": "calculate", "input": {"expression": "450", "what": "taxis"}, "result": {"result": 450}}]
    _, n = run("You spent **450 €** on taxis.", trace)
    assert n["450 €"]["status"] in ("calculated", "assumption")


def test_calculation_from_data_only_stays_green():
    trace = TRACE + [{"tool": "calculate", "input": {"expression": "2412.60 - 318.40", "what": "left"}, "result": {"result": 2094.2}}]
    _, n = run("That leaves **2,094.20 €**.", trace)
    assert n["2,094.20 €"]["status"] == "verified"


def test_notes_cannot_add_numbers_or_data_claims():
    ans = ("Saving **20 %** helps.\n<number-notes>\n20 %|note|You could also save 500 € more.\n</number-notes>")
    _, n = run(ans)
    assert "note" not in n["20 %"]
    ans = ("Saving **20 %** helps.\n<number-notes>\n20 %|note|Eating out is your biggest extra.\n</number-notes>")
    _, n = run(ans)
    assert "note" not in n["20 %"]


def test_million_in_words_in_other_languages():
    _, n = run("Tavoite **1 000 000 €** on mahdollinen.", TRACE, ["Miten minusta tulee miljonääri?"])
    assert n["1 000 000 €"]["status"] == "yours"


def test_default_mode_unchanged_for_captions():
    # Captions (wrapped, sorter, play) call check() without explain: same rules as before, no assumption statuses.
    found = verify.check("Saving 20 % is 482.52 €.", TRACE, [], "en")
    assert {f["text"]: f["status"] for f in found} == {"20 %": "unverified", "482.52 €": "verified"}


def test_data_numbers_point_to_their_tool_call():
    trace = [{"tool": "get_spending", "input": {"period": "last_month"}, "result": {"total_eur": 997.40}},
             {"tool": "get_spending", "input": {"period": "last_month", "subcategory": "Restaurants"}, "result": {"total_eur": 412.80}},
             {"tool": "get_safe_to_spend", "input": {}, "result": {"steps": [{"step": "Groceries", "eur": -675.71}, {"step": "Buffer", "eur": -150.04}]}}]
    found = {n["text"]: n for n in verify.check("About **1,000 €**, restaurants **412.80 €**, together **825.75 €**.",
                                               trace, [], "en", explain=True)}
    assert found["412.80 €"]["ti"] == 1 and found["412.80 €"]["path"] == "total_eur"
    assert found["1,000 €"]["status"] == "rounded" and found["1,000 €"]["rounded_from"] == 997.40 and found["1,000 €"]["ti"] == 0
    d = found["825.75 €"]
    assert d["status"] == "derived" and [p["value"] for p in d["parts"]] == [675.71, 150.04]
    assert [p["path"] for p in d["parts"]] == ["steps[0].eur", "steps[1].eur"] and d["ti"] == 2


def test_calculation_from_data_lists_its_parts():
    trace = TRACE + [{"tool": "calculate", "input": {"expression": "2412.60 - 318.40", "what": "left"}, "result": {"result": 2094.2}}]
    _, n = run("That leaves **2,094.20 €**.", trace)
    e = n["2,094.20 €"]
    assert e["status"] == "verified" and [p["value"] for p in e["parts"]] == [2412.60, 318.40]
    assert [p["ti"] for p in e["parts"]] == [0, 1]


# ---- Review of PR #3: an invented number must never come out green ----
REAL_SHAPE = [{"tool": "get_safe_to_spend", "input": {}, "result": {"days_until_payday": 15, "steps": [{"step": "Bills", "eur": -814.54}],
               "bills": [{"bill": "Utilities", "still_to_come_eur": 47.3}]}},
              {"tool": "get_spending", "input": {"period": "last_6_months", "group_by": "month"},
               "result": {"period": {"months": 6}, "total_eur": 13561.47, "breakdown": [{"key": "2026-09", "total_eur": 2228.07, "transactions": 20}]}}]


def _st(answer, trace=REAL_SHAPE, user=()):
    text, notes = verify.split_notes(answer)
    return {n["text"]: n["status"] for n in verify.check(text, trace, list(user), "en", explain=True, notes=notes)}


def test_a_count_of_days_or_payments_never_matches_a_percentage():
    assert _st("Most people save 15 % of their pay.")["15 %"] == "unverified"       # 15 = days until payday
    assert _st("If you save 20 % you'd be fine.")["20 %"] == "unverified"           # 20 = payments


def test_calculate_with_an_invented_amount_is_not_data():
    calc = {"tool": "calculate", "input": {"expression": "6 * 100"}, "result": {"result": 600}}
    assert _st("Over 6 months that's 600 €.", REAL_SHAPE + [calc])["600 €"] == "calculated"
    real = {"tool": "calculate", "input": {"expression": "2228.07 / 6"}, "result": {"result": 371.35}}
    assert _st("That's 371.35 € a month.", REAL_SHAPE + [real])["371.35 €"] == "verified"


def test_rounded_match_needs_a_euro_field():
    assert _st("You have about 20 € left of it.")["20 €"] == "unverified"           # 20 is a payment count
    assert _st("Bills come to about 810 € before payday.")["810 €"] == "rounded"   # 814.54 €


RULE = "\n<number-notes>\n35 %|rule|General guideline.\n</number-notes>"


def test_rule_needs_the_words_and_no_claim_about_the_user():
    for ans in ["You spend 35 % on eating out.", "Your rent is 35 % of your income.", "Vuokrasi on 35 % tuloistasi.",
                "Din hyra är 35 % av lönen.", "Inflation in Finland is 35 % now.", "Experts recommend 35 % as a rule of thumb."]:
        assert _st(ans + RULE)["35 %"] == "unverified", ans
    assert _st("A common rule of thumb is to keep rent under 35 % of your income." + RULE)["35 %"] == "rule"


def test_notes_with_other_numbers_or_statistics_are_dropped():
    base = "A common rule of thumb is to save 20 %."
    for note in ["Stocks returned 7 percent a year.", "Banks in 12 countries use it.", "Most Finns your age save this much."]:
        text, notes = verify.split_notes(base + f"\n<number-notes>\n20 %|rule|{note}\n</number-notes>")
        n = verify.check(text, REAL_SHAPE, [], "en", explain=True, notes=notes)[0]
        assert "note" not in n, note  # the note is dropped; the sentence alone may still be a rule of thumb


def test_same_value_twice_uses_each_sentence():
    st = [n["status"] for n in verify.check("A common rule of thumb is to save 20 %. You spent 20 % of your pay on food.",
                                             REAL_SHAPE, [], "en", explain=True,
                                             notes=[{"value": 20.0, "pct": True, "kind": "rule", "note": "Guideline."}])]
    assert st == ["rule", "unverified"]


def test_every_notes_block_is_removed():
    for raw in ["Answer.\n```\n<number-notes>\n20 %|note|x\n</number-notes>\n```", "Answer.\n<number_notes>\n20 %|note|x\n</number_notes>",
                "Answer.\n<number-notes>a</number-notes>\n<number-notes>b</number-notes>", "Answer.\n<number-notes>\n20 %|note|cut off"]:
        text, _ = verify.split_notes(raw)
        assert text == "Answer.", (raw, text)


def test_rule_without_a_note_needs_the_same_sentence_test():
    assert _st("A common rule of thumb is to save 10-20 % of your income.")["20 %"] == "rule"
    assert _st("You spend 20 % on rent, a common rule of thumb.")["20 %"] == "unverified"
    assert _st("Most people save 20 %, a common rule of thumb.")["20 %"] == "unverified"


def test_chart_json_is_removed_from_answers():
    from app.coach import strip_data_dumps
    t = '{\n"chart_type": "category_trend",\n"data": [\n{"x": "2025-10", "y": 0.0}\n]\n}\n\nThe highest was **993.20 €**.'
    assert strip_data_dumps(t) == "The highest was **993.20 €**."
    assert strip_data_dumps("A\n```json\n{\"a\": 1}\n```\nB [x] {y}") == "A\n\nB [x] {y}"


def test_a_stray_fence_does_not_swallow_the_answer():
    from app.coach import strip_data_dumps
    assert strip_data_dumps("Use ``` carefully, then more text.") == "Use ``` carefully, then more text."
    assert strip_data_dumps("Answer.\n```json\n{\"cut\": 1") == "Answer."
