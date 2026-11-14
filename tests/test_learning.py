"""Offline tests for app/learning (Money Detective quests + progress). No database, no AI."""
from datetime import datetime, timedelta

from app import learning as L

F = L.PRACTICE_FACTS
NOW = datetime(2026, 11, 14, 12, 0)


def test_quests_use_the_persons_numbers_in_three_languages():
    for lang in ("en", "fi", "sv"):
        q = L.quest("q2", F, lang)
        assert "1 450" in q["predict"]["question"] and "240" in q["reveal"]
        assert len(q["check"]["options"]) == 3
    q1 = L.quest("q1", F)
    assert q1["predict"]["options"][q1["predict"]["closest"]] == "20-40 %"   # 38 %


def test_flow_explored_then_explained_first_try():
    s = L.new_state()
    assert L.record(s, event_id="e1", qid="q1", step="predict", choice=0, now=NOW)["awarded"]
    r = L.record(s, event_id="e2", qid="q1", step="check", choice=L.CORRECT["q1"], now=NOW)
    assert r["correct"] and s["concepts"]["q1"]["status"] == "explained" and s["concepts"]["q1"]["first_try"]


def test_wrong_then_right_counts_as_assisted_not_first_try():
    s = L.new_state()
    L.record(s, event_id="a", qid="q2", step="predict", choice=1, now=NOW)
    assert not L.record(s, event_id="b", qid="q2", step="check", choice=0, now=NOW)["correct"]
    L.record(s, event_id="c", qid="q2", step="check", choice=1, now=NOW)
    assert s["concepts"]["q2"]["status"] == "explained" and s["concepts"]["q2"]["first_try"] is False


def test_replayed_events_award_nothing_twice():
    s = L.new_state()
    L.record(s, event_id="x", qid="q3", step="predict", choice=2, now=NOW)
    assert L.record(s, event_id="x", qid="q3", step="predict", choice=2, now=NOW)["duplicate"]
    L.record(s, event_id="y", qid="q3", step="predict", choice=1, now=NOW)            # new id, same quest
    assert len([a for a in s["awards"] if a["kind"] == "explored"]) == 1


def test_cannot_skip_the_evidence_and_revisit_waits_three_days():
    s = L.new_state()
    assert not L.record(s, event_id="1", qid="q1", step="check", choice=1, now=NOW)["ok"]
    L.record(s, event_id="2", qid="q1", step="predict", choice=0, now=NOW)
    L.record(s, event_id="3", qid="q1", step="check", choice=1, now=NOW)
    early = L.record(s, event_id="4", qid="q1", step="revisit", choice=L.REVISIT_CORRECT["q1"], now=NOW + timedelta(days=1))
    assert not early["ok"] and early["opens"]
    later = L.record(s, event_id="5", qid="q1", step="revisit", choice=L.REVISIT_CORRECT["q1"], now=NOW + timedelta(days=3))
    assert later["correct"] and s["concepts"]["q1"]["status"] == "revisited"


def test_weekly_goal_never_resets_and_rewards_can_be_hidden():
    s = L.new_state()
    L.record(s, event_id="1", qid="q1", step="predict", choice=0, now=NOW)
    L.record(s, event_id="2", qid="q1", step="check", choice=1, now=NOW)
    assert L.summary(s, NOW)["quests_this_week"] == 1
    nxt = L.summary(s, NOW + timedelta(days=14))
    assert nxt["quests_this_week"] == 0 and nxt["concepts"][0]["status"] == "explained"   # progress kept
    assert any(m["reached"] for m in L.summary(s, NOW)["milestones"])
    L.set_settings(s, hide_rewards=True)
    assert "milestones" not in L.summary(s, NOW) and "points" not in L.summary(s, NOW)


def test_progress_contains_no_money():
    s = L.new_state()
    L.record(s, event_id="1", qid="q2", step="predict", choice=0, now=NOW)
    txt = str(L.summary(s, NOW))
    assert "€" not in txt and "eur" not in txt.lower() and "score" not in txt.lower()


def test_every_language_has_every_string():
    keys = set(L.T["en"])
    assert all(set(L.T[l]) == keys for l in ("fi", "sv"))
