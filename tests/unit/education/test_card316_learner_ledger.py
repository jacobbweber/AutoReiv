"""CARD-316: Education Learning OS — durable learner ledger prove-and-harden pins.

Fails if REQ-EDU-LOS-001..005 regress: memory.db store, miss→1-3-7-30 next_due,
binary external grade, restart-safe reopen, strength/weakness learner facts.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.learner_model import (
    LEARNER_ENTITY,
    record_learner_from_grade,
    summarize_learner_model,
)
from src.application.education.quiz_engine import grade_answer_binary
from src.application.education.srs import SRS_INTERVALS_DAYS
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _assert_memory_db_path(db: Path) -> None:
    name = db.name.lower()
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in name or "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_ledger_lives_in_memory_db_never_storage(tmp_path: Path):
    """[REQ-EDU-LOS-001] Durable store is agent memory.db — not storage.db."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    _assert_memory_db_path(Path(repo.db_path))
    repo.upsert_education_mastery(
        item_id="edu_316_path",
        topic="Path",
        wiki_path="notes/path.md",
        prompt="Where does the ledger live?",
        expected_answer="memory.db",
        grade="unseen",
    )
    row = repo.get_education_mastery("edu_316_path")
    assert row is not None
    assert row["item_id"] == "edu_316_path"
    # Explicit anti-theatre: no storage.db invented for mastery
    assert not (tmp_path / "storage.db").exists()


def test_miss_schedules_stage0_plus_one_day_and_pass_advances(tmp_path: Path):
    """[REQ-EDU-LOS-002] Miss → grade=miss, interval_stage=0, next_due ~+1d; pass advances."""
    assert SRS_INTERVALS_DAYS == (1, 3, 7, 30)
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
    repo.upsert_education_mastery(
        item_id="edu_316_miss",
        topic="SRS",
        wiki_path="notes/srs.md",
        prompt="Intervals?",
        expected_answer="1-3-7-30",
        grade="unseen",
    )
    miss = repo.record_education_grade(item_id="edu_316_miss", correct=False, now=now)
    assert miss["grade"] == "miss"
    assert miss["interval_stage"] == 0
    due = datetime.fromisoformat(miss["next_due"].replace("Z", "+00:00"))
    assert due == now + timedelta(days=1)

    passed = repo.record_education_grade(
        item_id="edu_316_miss",
        correct=True,
        now=now + timedelta(hours=1),
    )
    assert passed["grade"] == "pass"
    assert passed["interval_stage"] == 1
    due2 = datetime.fromisoformat(passed["next_due"].replace("Z", "+00:00"))
    assert due2 == now + timedelta(hours=1) + timedelta(days=3)


def test_binary_external_grade_no_llm_in_quiz_engine():
    """[REQ-EDU-LOS-004] Grade remains binary external — never LLM self-score."""
    assert grade_answer_binary("Standing Job", "standing job") is True
    assert grade_answer_binary("Standing Job", "toast theatre") is False
    import src.application.education.quiz_engine as qe

    src = inspect.getsource(qe)
    assert "complete(" not in src
    assert "openai" not in src.lower()
    assert "ollama" not in src.lower()
    # Route contract pin (import path used by quiz grade)
    from src.web.routers import education as edu_router

    route_src = inspect.getsource(edu_router.grade_quiz)
    assert "grade_answer_binary" in route_src
    assert "binary_external" in route_src or "grader" in route_src


def test_restart_safe_reopen_preserves_next_due_and_weakness(tmp_path: Path):
    """[REQ-EDU-LOS-005] After miss: close repo, open NEW on same db — next_due + weakness survive."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    now = datetime(2026, 9, 14, 15, 0, 0, tzinfo=timezone.utc)

    repo1 = AgentMemoryRepository(db_path=db)
    repo1.initialize_schema()
    repo1.upsert_education_mastery(
        item_id="edu_316_restart",
        topic="Restart",
        wiki_path="notes/restart.md",
        prompt="Does next_due survive kill/resume?",
        expected_answer="yes from memory.db",
        grade="unseen",
    )
    miss = repo1.record_education_grade(item_id="edu_316_restart", correct=False, now=now)
    assert miss["grade"] == "miss"
    assert miss["next_due"]
    expected_due = miss["next_due"]

    # Close / drop first handle (connections are per-call; drop ref = restart-safe proof)
    close = getattr(repo1, "close", None)
    if callable(close):
        close()
    del repo1

    repo2 = AgentMemoryRepository(db_path=db)
    repo2.initialize_schema()
    row = repo2.get_education_mastery("edu_316_restart")
    assert row is not None
    assert row["grade"] == "miss"
    assert row["next_due"] == expected_due
    assert row["interval_stage"] == 0

    summary = summarize_learner_model(repo2)
    assert summary["weakness_count"] >= 1
    blob_items = " ".join(
        str(x.get("item_id") or "") + " " + str(x.get("value") or "")
        for x in (summary.get("items") or [])
    )
    blob_facts = " ".join(
        str(f.get("value") or "") + " " + str(f.get("attribute") or "")
        for f in (summary.get("facts") or [])
    )
    assert "edu_316_restart" in blob_items or "edu_316_restart" in blob_facts


def test_grade_auto_syncs_strength_and_weakness_learner_facts(tmp_path: Path):
    """[REQ-EDU-LOS-001/002] record_education_grade auto-syncs learner semantic facts."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    repo.upsert_education_mastery(
        item_id="edu_316_weak",
        topic="Weak",
        wiki_path="notes/weak.md",
        prompt="Weak?",
        expected_answer="no",
        grade="unseen",
    )
    repo.record_education_grade(item_id="edu_316_weak", correct=False)
    weak = [f for f in repo.list_facts_for_entity(LEARNER_ENTITY) if f.get("attribute") == "weakness"]
    assert any("edu_316_weak" in (f.get("value") or "") for f in weak)

    repo.upsert_education_mastery(
        item_id="edu_316_strong",
        topic="Strong",
        wiki_path="notes/strong.md",
        prompt="Strong?",
        expected_answer="yes",
        grade="unseen",
    )
    repo.record_education_grade(item_id="edu_316_strong", correct=True)
    strong = [f for f in repo.list_facts_for_entity(LEARNER_ENTITY) if f.get("attribute") == "strength"]
    assert any("edu_316_strong" in (f.get("value") or "") for f in strong)

    # Sync is inline in record_education_grade (no silent swallow)
    ops_src = inspect.getsource(
        __import__(
            "src.infrastructure.memory.repositories.education_mastery_ops",
            fromlist=["record_education_grade"],
        ).record_education_grade
    )
    assert "record_learner_from_grade" in ops_src
    assert "except Exception" not in ops_src or "pass" not in ops_src.split("record_learner_from_grade")[-1][:200]


def test_record_learner_from_grade_still_callable_directly(tmp_path: Path):
    """Helper remains available; grade path owns auto-sync (no second tutor runtime)."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    repo.upsert_education_mastery(
        item_id="edu_316_direct",
        topic="Direct",
        wiki_path="notes/direct.md",
        prompt="Direct?",
        expected_answer="ok",
        grade="unseen",
    )
    # Grade without relying solely on helper import in test body for the miss row
    row = repo.record_education_grade(item_id="edu_316_direct", correct=False)
    # Calling again is idempotent enough for pattern/weakness upsert
    facts = record_learner_from_grade(repo, item=row, correct=False)
    assert facts.get("weakness_fact_id")
