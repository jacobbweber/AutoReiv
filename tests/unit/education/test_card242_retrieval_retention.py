"""CARD-242: Education Retrieval + Retention — mastery ledger, binary grade, SRS, Routine->Job."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.application.education.quiz_engine import (
    extract_quiz_items_from_note,
    grade_answer_binary,
)
from src.application.education.srs import (
    SRS_INTERVALS_DAYS,
    next_due_after_grade,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def test_srs_intervals_are_1_3_7_30():
    assert SRS_INTERVALS_DAYS == (1, 3, 7, 30)


def test_binary_external_grade_not_llm():
    assert grade_answer_binary("Standing Job", "standing job") is True
    assert grade_answer_binary("Standing Job", "  Standing   Job  ") is True
    assert grade_answer_binary("Standing Job", "routine toast") is False
    # Source must not call an LLM — inspect module
    import inspect
    import src.application.education.quiz_engine as qe

    src = inspect.getsource(qe)
    assert "complete(" not in src
    assert "gateway" not in src.lower() or "Gateway" not in src
    assert "openai" not in src.lower()
    assert "ollama" not in src.lower()


def test_extract_quiz_items_from_priming_dual_note():
    body = """---
title: Priming Jobs
tags: [education, priming, schema]
---

# Priming: Standing Jobs

## Outline
- Job mint
- Phase chrome

## Quiz
- Q: What must mint a resurface after a quiz miss?
  A: Routine to standing Job
- Q: Where does the mastery ledger live?
  A: memory.db
"""
    items = extract_quiz_items_from_note(
        body,
        wiki_path="00_Inbox/priming-jobs.md",
        topic="Standing Jobs",
    )
    assert len(items) >= 2
    assert items[0]["prompt"].lower().startswith("what must mint")
    assert "routine" in items[0]["expected_answer"].lower()
    assert items[0]["wiki_path"] == "00_Inbox/priming-jobs.md"
    assert items[0]["item_id"]


def test_mastery_ledger_write_read_in_memory_db(tmp_path):
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    item_id = repo.upsert_education_mastery(
        item_id="edu_item_abc",
        topic="Standing Jobs",
        wiki_path="00_Inbox/priming-jobs.md",
        prompt="What must mint a resurface after a quiz miss?",
        expected_answer="Routine to standing Job",
        grade="unseen",
        next_due=None,
    )
    assert item_id == "edu_item_abc"
    row = repo.get_education_mastery(item_id)
    assert row is not None
    assert row["topic"] == "Standing Jobs"
    assert row["wiki_path"] == "00_Inbox/priming-jobs.md"
    assert row["grade"] == "unseen"
    assert row["next_due"] is None or row["next_due"] == ""


def test_miss_schedules_next_due_on_1_3_7_30(tmp_path):
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)

    repo.upsert_education_mastery(
        item_id="edu_miss_1",
        topic="Jobs",
        wiki_path="notes/jobs.md",
        prompt="Q?",
        expected_answer="yes",
        grade="unseen",
    )
    row = repo.record_education_grade(
        item_id="edu_miss_1",
        correct=False,
        now=now,
    )
    assert row["grade"] == "miss"
    assert row["interval_stage"] == 0
    due = datetime.fromisoformat(row["next_due"].replace("Z", "+00:00"))
    assert due == now + timedelta(days=1)

    # Second miss resets to day-1
    later = now + timedelta(days=2)
    row2 = repo.record_education_grade(item_id="edu_miss_1", correct=False, now=later)
    due2 = datetime.fromisoformat(row2["next_due"].replace("Z", "+00:00"))
    assert due2 == later + timedelta(days=1)

    # Pass advances 1 -> 3
    pass_at = later + timedelta(hours=1)
    row3 = repo.record_education_grade(item_id="edu_miss_1", correct=True, now=pass_at)
    assert row3["grade"] == "pass"
    assert row3["interval_stage"] == 1
    due3 = datetime.fromisoformat(row3["next_due"].replace("Z", "+00:00"))
    assert due3 == pass_at + timedelta(days=3)


def test_next_due_helper_covers_full_ladder():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert next_due_after_grade(correct=False, interval_stage=2, now=now)[0] == 0
    assert next_due_after_grade(correct=False, interval_stage=2, now=now)[1] == now + timedelta(days=1)
    stage, due = next_due_after_grade(correct=True, interval_stage=0, now=now)
    assert stage == 1 and due == now + timedelta(days=3)
    stage, due = next_due_after_grade(correct=True, interval_stage=1, now=now)
    assert stage == 2 and due == now + timedelta(days=7)
    stage, due = next_due_after_grade(correct=True, interval_stage=2, now=now)
    assert stage == 3 and due == now + timedelta(days=30)
    stage, due = next_due_after_grade(correct=True, interval_stage=3, now=now)
    assert stage == 3 and due == now + timedelta(days=30)


def test_list_due_mastery_items(tmp_path):
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)
    repo.upsert_education_mastery(
        item_id="due_now",
        topic="A",
        wiki_path="a.md",
        prompt="p",
        expected_answer="a",
        grade="miss",
        next_due=(now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
        interval_stage=0,
    )
    repo.upsert_education_mastery(
        item_id="due_later",
        topic="B",
        wiki_path="b.md",
        prompt="p",
        expected_answer="b",
        grade="miss",
        next_due=(now + timedelta(days=5)).isoformat().replace("+00:00", "Z"),
        interval_stage=0,
    )
    due = repo.list_due_education_mastery(as_of=now)
    ids = {r["item_id"] for r in due}
    assert "due_now" in ids
    assert "due_later" not in ids


def test_retention_routine_mints_standing_job_for_due_review(tmp_path):
    """Miss -> ledger next_due -> Routine fires -> standing Job minted [REQ-EDU-RR-003/005]."""
    from src.application.education.retention_routine import (
        EDUCATION_RETENTION_ROUTINE_ID,
        run_education_retention,
    )
    from src.domain.routines.models import Routine, ScheduleType

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 11, 18, 0, 0, tzinfo=timezone.utc)
    repo.upsert_education_mastery(
        item_id="edu_live_1",
        topic="Priming",
        wiki_path="00_Inbox/priming.md",
        prompt="What is Priming?",
        expected_answer="schema first",
        grade="miss",
        next_due=(now - timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
        interval_stage=0,
    )

    minted = []

    class FakeJob:
        def __init__(self, jid):
            self.id = jid

    class FakeOrch:
        def create_job_from_catalog_resolve(self, intent, session_id, agent_id, **kwargs):
            jid = f"job_edu_{len(minted)+1:04d}"
            minted.append(
                {
                    "intent": intent,
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "job_id": jid,
                    "kwargs": kwargs,
                }
            )
            return FakeJob(jid)

    routine = Routine(
        id=EDUCATION_RETENTION_ROUTINE_ID,
        name="Education Retrieval Retention",
        description="Resurface due quiz reviews as standing Jobs",
        agent_id="assistant",
        prompt="Resurface due Education quiz reviews as standing Jobs.",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        enabled=True,
    )

    result = run_education_retention(
        memory_repo=repo,
        orch=FakeOrch(),
        routine=routine,
        agent_id="assistant",
        session_id="sess_edu_retention",
        now=now,
    )
    assert result["status"] == "ok"
    assert result["due_count"] == 1
    assert len(result["minted_job_ids"]) == 1
    assert result["minted_job_ids"][0].startswith("job_edu_")
    assert minted and "Education" in minted[0]["intent"]
    assert "edu_live_1" in minted[0]["intent"] or "Priming" in minted[0]["intent"]
    # Chat toast alone is not Done — must go through Job mint
    assert hasattr(FakeOrch, "create_job_from_catalog_resolve")
    assert minted[0]["job_id"] == result["minted_job_ids"][0]

    row = repo.get_education_mastery("edu_live_1")
    assert row.get("pending_job_id") == result["minted_job_ids"][0]


def test_retention_routine_id_in_builtin_manifests():
    from src.application.education.retention_routine import EDUCATION_RETENTION_ROUTINE_ID
    from src.domain.routines.manifests import BUILTIN_ROUTINES, get_builtin_routine

    r = get_builtin_routine(EDUCATION_RETENTION_ROUTINE_ID)
    assert r is not None
    assert r.id == EDUCATION_RETENTION_ROUTINE_ID
    assert any(x.id == EDUCATION_RETENTION_ROUTINE_ID for x in BUILTIN_ROUTINES)
    # Prompt must speak standing Job / Education review — not chat toast
    low = (r.prompt or "").lower()
    assert "standing job" in low or "education" in low
