"""CARD-243: Education learner model - strengths/weaknesses/patterns + weak-preferring quiz."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.learner_model import (
    LEARNER_ENTITY,
    LEARNER_CATEGORY,
    record_learner_from_grade,
    select_quiz_items,
    build_ask_pressure_clause,
    summarize_learner_model,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _seed(repo, item_id, topic, grade="unseen", miss_count=0, pass_count=0, next_due=None, prompt=None):
    repo.upsert_education_mastery(
        item_id=item_id,
        topic=topic,
        wiki_path=f"notes/{topic}.md",
        prompt=prompt or f"Prompt for {item_id}?",
        expected_answer="answer",
        grade=grade,
        next_due=next_due,
    )
    if miss_count or pass_count or grade != "unseen":
        with repo.get_connection() as conn:
            conn.execute(
                "UPDATE education_mastery SET grade=?, miss_count=?, pass_count=?, next_due=COALESCE(?, next_due) WHERE item_id=?",
                (grade, miss_count, pass_count, next_due, item_id),
            )


def test_record_learner_from_grade_writes_weakness_and_pattern_facts(tmp_path):
    repo = _repo(tmp_path)
    _seed(repo, "edu_weak_1", "Standing Jobs", grade="unseen")
    row = repo.record_education_grade(item_id="edu_weak_1", correct=False)
    assert row["grade"] == "miss"

    facts = record_learner_from_grade(repo, item=row, correct=False)
    assert facts["weakness_fact_id"]
    assert facts["pattern_fact_id"]

    weak = [f for f in repo.list_facts_for_entity(LEARNER_ENTITY) if f.get("attribute") == "weakness"]
    patterns = [f for f in repo.list_facts_for_entity(LEARNER_ENTITY) if f.get("attribute") == "pattern"]
    assert any("edu_weak_1" in (f.get("value") or "") for f in weak)
    assert any("miss" in (f.get("value") or "").lower() for f in patterns)
    assert all(f.get("category") == LEARNER_CATEGORY for f in weak + patterns)
    assert "memory" in str(repo.db_path).replace("\\", "/").lower() or "assistant_memory" in str(repo.db_path)


def test_record_pass_writes_strength_fact(tmp_path):
    repo = _repo(tmp_path)
    _seed(repo, "edu_strong_1", "Wiki", grade="unseen")
    row = repo.record_education_grade(item_id="edu_strong_1", correct=True)
    facts = record_learner_from_grade(repo, item=row, correct=True)
    assert facts["strength_fact_id"]
    strengths = [f for f in repo.list_facts_for_entity(LEARNER_ENTITY) if f.get("attribute") == "strength"]
    assert any("edu_strong_1" in (f.get("value") or "") for f in strengths)


def test_grade_path_auto_syncs_learner_facts(tmp_path):
    """record_education_grade itself must sync learner facts (no second tutor runtime)."""
    repo = _repo(tmp_path)
    _seed(repo, "edu_auto_1", "Priming", grade="unseen")
    repo.record_education_grade(item_id="edu_auto_1", correct=False)
    weak = [f for f in repo.list_facts_for_entity(LEARNER_ENTITY) if f.get("attribute") == "weakness"]
    assert any("edu_auto_1" in (f.get("value") or "") for f in weak)


def test_select_quiz_prefers_due_then_weak_over_strong(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 20, 0, 0, tzinfo=timezone.utc)
    _seed(
        repo,
        "edu_strong",
        "StrongTopic",
        grade="pass",
        pass_count=3,
        miss_count=0,
        next_due=(now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        prompt="Easy strong item?",
    )
    _seed(
        repo,
        "edu_weak",
        "WeakTopic",
        grade="miss",
        miss_count=2,
        pass_count=0,
        next_due=(now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        prompt="Hard weak item?",
    )
    _seed(
        repo,
        "edu_due",
        "DueTopic",
        grade="miss",
        miss_count=1,
        next_due=(now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        prompt="Due weak item?",
    )
    _seed(repo, "edu_unseen", "NewTopic", grade="unseen", prompt="Unseen item?")

    picked = select_quiz_items(repo, limit=3, as_of=now)
    ids = [p["item_id"] for p in picked]
    assert ids[0] == "edu_due", ids
    assert "edu_weak" in ids
    if "edu_strong" in ids and "edu_weak" in ids:
        assert ids.index("edu_weak") < ids.index("edu_strong")


def test_select_quiz_not_random_when_miss_known(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 20, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        _seed(repo, f"edu_pass_{i}", "Strong", grade="pass", pass_count=2, prompt=f"Strong {i}?")
    _seed(repo, "edu_known_miss", "Weak", grade="miss", miss_count=3, prompt="Known miss?")
    for _ in range(5):
        picked = select_quiz_items(repo, limit=1, as_of=now)
        assert picked[0]["item_id"] == "edu_known_miss"


def test_kill_resume_memory_db_still_pressures_miss(tmp_path):
    """Simulate restart: new AgentMemoryRepository on same db still selects known miss."""
    db = tmp_path / "assistant_memory.db"
    repo1 = AgentMemoryRepository(db_path=db)
    repo1.initialize_schema()
    _seed(repo1, "edu_resume_miss", "Resume", grade="unseen", prompt="Resume miss?")
    _seed(repo1, "edu_resume_pass", "Resume", grade="pass", pass_count=2, prompt="Resume pass?")
    repo1.record_education_grade(item_id="edu_resume_miss", correct=False)

    repo2 = AgentMemoryRepository(db_path=db)
    repo2.initialize_schema()
    picked = select_quiz_items(repo2, limit=1)
    assert picked[0]["item_id"] == "edu_resume_miss"
    weak = [f for f in repo2.list_facts_for_entity(LEARNER_ENTITY) if f.get("attribute") == "weakness"]
    assert any("edu_resume_miss" in (f.get("value") or "") for f in weak)


def test_build_ask_pressure_clause_targets_known_miss():
    items = [
        {
            "item_id": "edu_x",
            "topic": "Jobs",
            "prompt": "What mints resurface?",
            "grade": "miss",
            "miss_count": 2,
        }
    ]
    clause = build_ask_pressure_clause(items)
    low = clause.lower()
    assert "edu_x" in low or "what mints resurface" in low
    assert "miss" in low or "weak" in low or "pressure" in low
    assert "random" in low


def test_summarize_learner_model(tmp_path):
    repo = _repo(tmp_path)
    _seed(repo, "edu_s1", "A", grade="miss", miss_count=2)
    _seed(repo, "edu_s2", "B", grade="pass", pass_count=1)
    repo.record_education_grade(item_id="edu_s1", correct=False)
    summary = summarize_learner_model(repo)
    assert summary["weakness_count"] >= 1
    assert "items" in summary
