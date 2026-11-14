"""Home's AI layer (app/brief.py): code computes the findings; the AI only picks and writes one checked sentence."""
import pytest

from app import brief, verify

pytest.importorskip("duckdb")
EMMA = "CUST01610"


@pytest.fixture(autouse=True)
def no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(brief, "CACHE", tmp_path / "brief.json")


def test_findings_are_code_facts_with_questions_in_every_language():
    for lang in ("en", "fi", "sv"):
        f = brief.findings(EMMA, lang)
        ids = [x["id"] for x in f["findings"]]
        assert "short_payday" in ids and "rent_after" in ids          # Emma runs short, with rent due before payday
        assert all(x["question"].endswith("?") and "{" not in x["question"] for x in f["findings"])
        assert f["facts"]["balance_at_payday_usual_pace_eur"] < 0


def test_fallback_headline_numbers_match_the_facts():
    for lang in ("en", "fi", "sv"):
        f = brief.findings(EMMA, lang)
        head = brief._fallback(f, set(), lang)["headline"]
        nums = verify.check(head, [{"tool": "facts", "result": f}], [], lang)
        assert nums and all(n["status"] != "unverified" for n in nums), head


def test_spread_mixes_concepts():
    ranked = [{"id": "a", "concept": "x"}, {"id": "b", "concept": "x"}, {"id": "c", "concept": "y"}, {"id": "d", "concept": "z"}]
    assert brief._spread(ranked, []) == ["a", "c", "d"]
    assert brief._spread(ranked, ["b", "nope"]) == ["b", "c", "d"]


def test_ai_headline_with_an_unmatched_number_falls_back(monkeypatch):
    monkeypatch.setattr(brief.future, "_json_call", lambda *a, **k: {
        "headline": "You will be 1,234 € short by payday.", "questions": ["type", "made_up"], "cards": ["sort", "bogus"]})
    r = brief.brief(EMMA, "en")
    assert r["source"] == "rules" and "1,234" not in r["headline"]
    assert r["questions"][0]["id"] == "type" and len(r["questions"]) == 3   # the AI's valid pick kept, the rest filled
    assert r["cards"][0] == "sort" and sorted(r["cards"]) == sorted(brief.CARDS)


def test_ai_headline_with_matched_numbers_is_kept(monkeypatch):
    monkeypatch.setattr(brief.future, "_json_call", lambda *a, **k: {
        "headline": "You'll be missing 997 € by payday, mainly because 815 € of bills fall due first.",
        "questions": ["short_payday", "habit", "rent_after"], "cards": brief.CARDS})
    r = brief.brief(EMMA, "en")
    assert r["source"] == "ai" and "997 €" in r["headline"]


def test_ai_down_uses_code_picks(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(brief.future, "_json_call", boom)
    r = brief.brief(EMMA, "fi", ["forecast"])
    assert r["source"] == "rules" and r["cards_by"] == "rules" and len(r["questions"]) == 3
