import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection


class MockModel:
    pass


def test_rank_slots_uses_scores(use_test_db):
    from agents.preference_agent import PreferenceAgent
    conn = get_connection()
    conn.execute("INSERT INTO PreferenceScores (teacher_id,day,time_slot,score) VALUES (1,'Monday','08:00-10:00',2.5)")
    conn.execute("INSERT INTO PreferenceScores (teacher_id,day,time_slot,score) VALUES (1,'Monday','10:00-12:00',1.0)")
    conn.commit(); conn.close()
    agent = PreferenceAgent(MockModel())
    slots = [("Monday", "10:00-12:00"), ("Monday", "08:00-10:00")]
    ranked = agent.rank_slots(1, slots)
    assert ranked[0] == ("Monday", "08:00-10:00")


def test_unknown_slot_defaults_to_1(use_test_db):
    from agents.preference_agent import PreferenceAgent
    agent = PreferenceAgent(MockModel())
    assert agent.get_score(99, "Friday", "16:00-18:00") == 1.0


def test_record_used_preferred_boosts_score(use_test_db):
    from agents.preference_agent import PreferenceAgent
    agent = PreferenceAgent(MockModel())
    agent.record_used(1, "Monday", "08:00-10:00", was_preferred=True, was_negotiated=False)
    assert agent.get_score(1, "Monday", "08:00-10:00") > 1.0


def test_record_used_negotiated_decays_score(use_test_db):
    from agents.preference_agent import PreferenceAgent
    agent = PreferenceAgent(MockModel())
    agent.record_used(1, "Monday", "10:00-12:00", was_preferred=False, was_negotiated=True)
    assert agent.get_score(1, "Monday", "10:00-12:00") < 1.0


def test_score_clamped_at_max(use_test_db):
    from agents.preference_agent import PreferenceAgent
    agent = PreferenceAgent(MockModel())
    for _ in range(20):
        agent.record_used(1, "Monday", "08:00-10:00", was_preferred=True, was_negotiated=False)
    assert agent.get_score(1, "Monday", "08:00-10:00") <= 3.0


def test_score_clamped_at_min(use_test_db):
    from agents.preference_agent import PreferenceAgent
    agent = PreferenceAgent(MockModel())
    for _ in range(20):
        agent.record_used(1, "Monday", "08:00-10:00", was_preferred=False, was_negotiated=True)
    assert agent.get_score(1, "Monday", "08:00-10:00") >= 0.1


def test_update_scores_persists_to_db(use_test_db):
    from agents.preference_agent import PreferenceAgent
    agent = PreferenceAgent(MockModel())
    agent.record_used(1, "Monday", "08:00-10:00", was_preferred=True, was_negotiated=False)
    agent.update_scores()
    conn = get_connection()
    row = conn.execute(
        "SELECT score FROM PreferenceScores WHERE teacher_id=1 AND day='Monday' AND time_slot='08:00-10:00'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[0] > 1.0
