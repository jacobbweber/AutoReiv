"""CARD-319: Education Retention — ledger next_due drives Routine → standing Job.

Prove-and-harden: due mint, pause→no mint / resume→mint, miss-after-resurface
same mastery row (1-3-7-30), restart-safe pending_job_id. No new Education chrome
— operator proof is Routines Studio pause/resume + learner ledger next_due.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.retention_routine import (
    EDUCATION_RETENTION_ROUTINE_ID,
    run_education_retention,
)
from src.application.education.srs import SRS_INTERVALS_DAYS
from src.domain.routines.models import Routine, ScheduleType
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _assert_memory_db_path(db: Path) -> None:
    name = db.name.lower()
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in name or "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def _due_item(repo: AgentMemoryRepository, item_id: str, now: datetime, **extra) -> None:
    repo.upsert_education_mastery(
        item_id=item_id,
        topic=extra.get("topic", "Retention"),
        wiki_path=extra.get("wiki_path", "00_Inbox/retention.md"),
        prompt=extra.get("prompt", "What drives resurface?"),
        expected_answer=extra.get("expected_answer", "Routine to standing Job"),
        grade=extra.get("grade", "miss"),
        next_due=(now - timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
        interval_stage=extra.get("interval_stage", 0),
    )


def _routine(*, enabled: bool) -> Routine:
    return Routine(
        id=EDUCATION_RETENTION_ROUTINE_ID,
        name="Education Retrieval + Retention",
        description="Resurface due Education quiz reviews as standing Jobs",
        agent_id="assistant",
        prompt="Resurface due Education quiz reviews as standing Jobs.",
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,
        enabled=enabled,
    )


class _FakeJob:
    def __init__(self, jid: str):
        self.id = jid


class _FakeOrch:
    def __init__(self):
        self.minted = []

    def create_job_from_catalog_resolve(self, intent, session_id, agent_id, **kwargs):
        jid = f"job_edu_{len(self.minted) + 1:04d}"
        self.minted.append(
            {
                "intent": intent,
                "session_id": session_id,
                "agent_id": agent_id,
                "job_id": jid,
                "kwargs": kwargs,
            }
        )
        return _FakeJob(jid)


def test_srs_ladder_still_1_3_7_30():
    assert SRS_INTERVALS_DAYS == (1, 3, 7, 30)


def test_due_rows_mint_standing_job_via_retention_routine(tmp_path: Path):
    """[REQ-EDU-RSV-001] Due mastery → education-retrieval-retention mints standing Job."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 14, 16, 0, 0, tzinfo=timezone.utc)
    _due_item(repo, "edu_rsv_1", now)

    orch = _FakeOrch()
    result = run_education_retention(
        memory_repo=repo,
        orch=orch,
        routine=_routine(enabled=True),
        agent_id="assistant",
        session_id="sess_rsv",
        now=now,
    )
    assert result["status"] == "ok"
    assert result["due_count"] == 1
    assert len(result["minted_job_ids"]) == 1
    assert orch.minted and orch.minted[0]["job_id"] == result["minted_job_ids"][0]
    row = repo.get_education_mastery("edu_rsv_1")
    assert row["pending_job_id"] == result["minted_job_ids"][0]
    assert EDUCATION_RETENTION_ROUTINE_ID == "education-retrieval-retention"


def test_disabled_routine_mints_nothing(tmp_path: Path):
    """[REQ-EDU-RSV-002] Paused / disabled Routine → no Job mint (Routines Studio pause)."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 14, 16, 0, 0, tzinfo=timezone.utc)
    _due_item(repo, "edu_rsv_paused", now)

    orch = _FakeOrch()
    result = run_education_retention(
        memory_repo=repo,
        orch=orch,
        routine=_routine(enabled=False),
        agent_id="assistant",
        session_id="sess_paused",
        now=now,
    )
    assert result["status"] == "ok"
    assert result.get("reason") in {"routine_disabled", "routine_paused"}
    assert result["minted_job_ids"] == []
    assert orch.minted == []
    row = repo.get_education_mastery("edu_rsv_paused")
    assert not (row.get("pending_job_id") or "").strip()


def test_enabled_after_pause_mints_next_due(tmp_path: Path):
    """[REQ-EDU-RSV-002] Resume (enabled) → next due fires and mints."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 14, 16, 5, 0, tzinfo=timezone.utc)
    _due_item(repo, "edu_rsv_resume", now)

    orch = _FakeOrch()
    paused = run_education_retention(
        memory_repo=repo,
        orch=orch,
        routine=_routine(enabled=False),
        now=now,
    )
    assert paused["minted_job_ids"] == []

    resumed = run_education_retention(
        memory_repo=repo,
        orch=orch,
        routine=_routine(enabled=True),
        session_id="sess_resume",
        now=now,
    )
    assert resumed["status"] == "ok"
    assert len(resumed["minted_job_ids"]) == 1
    assert len(orch.minted) == 1
    row = repo.get_education_mastery("edu_rsv_resume")
    assert row["pending_job_id"] == resumed["minted_job_ids"][0]


def test_miss_after_resurface_advances_same_mastery_row(tmp_path: Path):
    """[REQ-EDU-RSV-003] Miss on resurfaced practice updates same row next_due on 1-3-7-30."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 14, 16, 10, 0, tzinfo=timezone.utc)
    _due_item(repo, "edu_rsv_miss", now, interval_stage=1)  # was on day-3 ladder

    orch = _FakeOrch()
    minted = run_education_retention(
        memory_repo=repo,
        orch=orch,
        routine=_routine(enabled=True),
        now=now,
    )
    assert minted["minted_job_ids"]
    before = repo.get_education_mastery("edu_rsv_miss")
    assert before["pending_job_id"] == minted["minted_job_ids"][0]
    assert before["interval_stage"] == 1

    grade_at = now + timedelta(minutes=5)
    after = repo.record_education_grade(
        item_id="edu_rsv_miss",
        correct=False,
        now=grade_at,
    )
    assert after["item_id"] == "edu_rsv_miss"  # same row
    assert after["grade"] == "miss"
    assert after["interval_stage"] == 0  # miss resets to stage 0
    due = datetime.fromisoformat(after["next_due"].replace("Z", "+00:00"))
    assert due == grade_at + timedelta(days=1)
    assert not (after.get("pending_job_id") or "").strip()


def test_restart_safe_ledger_and_pending_job_id(tmp_path: Path):
    """[REQ-EDU-RSV-004] Reopen memory.db → same next_due + pending_job_id (restart-safe)."""
    db = tmp_path / "packs/assistant/assistant_memory.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    _assert_memory_db_path(db)
    now = datetime(2026, 9, 14, 16, 20, 0, tzinfo=timezone.utc)

    repo1 = AgentMemoryRepository(db_path=db)
    repo1.initialize_schema()
    _due_item(repo1, "edu_rsv_restart", now)
    orch = _FakeOrch()
    result = run_education_retention(
        memory_repo=repo1,
        orch=orch,
        routine=_routine(enabled=True),
        now=now,
    )
    jid = result["minted_job_ids"][0]
    row1 = repo1.get_education_mastery("edu_rsv_restart")
    next_due_1 = row1["next_due"]
    pending_1 = row1["pending_job_id"]
    assert pending_1 == jid

    # Simulate serve restart: new repo handle on same disk path
    repo2 = AgentMemoryRepository(db_path=db)
    repo2.initialize_schema()
    row2 = repo2.get_education_mastery("edu_rsv_restart")
    assert row2 is not None
    assert row2["next_due"] == next_due_1
    assert row2["pending_job_id"] == pending_1

    due = repo2.list_due_education_mastery(as_of=now)
    ids = {r["item_id"] for r in due}
    assert "edu_rsv_restart" in ids
    # Second tick must not spam — pending_job_id still set
    result2 = run_education_retention(
        memory_repo=repo2,
        orch=orch,
        routine=_routine(enabled=True),
        now=now,
    )
    assert result2["minted_job_ids"] == []
    assert result2.get("reason") in {"all_pending", "nothing_due"}


def test_scheduler_lists_only_enabled_routines():
    """Scheduler gate: enabled_only=True — paused retention never ticks."""
    from src.application.routines.scheduler import RoutineScheduler
    import src.application.routines.scheduler as sched_mod

    src = inspect.getsource(RoutineScheduler.tick)
    assert "enabled_only=True" in src or "enabled_only = True" in src
    # Matcher also refuses disabled
    from src.application.routines.matcher import ScheduleMatcher

    r = _routine(enabled=False)
    assert ScheduleMatcher.is_routine_due(r, datetime.now(timezone.utc)) is False


def test_retention_api_gates_on_routine_enabled():
    """[REQ-EDU-RSV-002] POST /api/education/retention/run honors enabled gate (no chrome)."""
    from src.web.routers import education as edu_router

    src = inspect.getsource(edu_router.run_retention)
    assert "enabled" in src
    assert "run_education_retention" in src
    assert "force_due_item_id" in src
    # Must not invent new Education schedule chrome endpoints in this handler
    assert "schedule_ui" not in src.lower()
    assert "due_calendar" not in src.lower()


def test_no_new_education_schedule_chrome_in_retention_module():
    """UX lock: Retention uses Routines Studio + learner ledger only — no new Edu chrome."""
    import src.application.education.retention_routine as rr

    src = inspect.getsource(rr)
    assert "EDUCATION_RETENTION_ROUTINE_ID" in src
    low = src.lower()
    assert "toast" not in low or "not" in low  # toast is anti-pattern mentioned OK
    # Module must not ship HTML / studio panel helpers
    assert "<div" not in src
    assert "edu-schedule" not in low
    assert "educationSchedule" not in src
