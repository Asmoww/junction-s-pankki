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
