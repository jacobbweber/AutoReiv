"""CARD-441: Progress you can trust on non-Studio Tutor surface.

REQ-441-001..004: course/mastery/due from Learning OS without #view-education;
refresh reflects durable grades; API failure is honest (no fake mastery %);
Education Studio progress chrome retained.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.education.progress_summary import (
    build_progress_summary,
    summarize_mastery_rows,
)
from src.application.skills.education_tools import EducationTools
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


PROGRESS_TOOL_NAMES = (
    "education_progress_summary",
    "education_progress_courses",
    "education_progress_mastery",
    "education_mastery_due",
)


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "tutor_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _tools(repo: AgentMemoryRepository, **kwargs) -> EducationTools:
    return EducationTools(repository=repo, default_agent_id="tutor", **kwargs)


def _seed_course_and_grades(repo: AgentMemoryRepository) -> str:
    cid = repo.upsert_education_course(
        topic_id="CARD-441 Progress",
        steps=["priming", "retrieval", "elaboration"],
        current_step="retrieval",
        status="active",
    )
    mid = repo.upsert_education_mastery(
        item_id="edu_card441_a",
        topic="CARD-441 Progress",
        wiki_path="01_Notes/card441.md",
        prompt="What owns trustable progress?",
        expected_answer="Learning OS",
        grade="unseen",
    )
    past = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    repo.record_education_grade(item_id=mid, correct=True, now=past)
    mid2 = repo.upsert_education_mastery(
        item_id="edu_card441_b",
        topic="CARD-441 Progress",
        wiki_path="01_Notes/card441.md",
        prompt="Studio required for progress?",
        expected_answer="No",
        grade="unseen",
    )
    repo.record_education_grade(item_id=mid2, correct=False, now=past)
    with repo.get_connection() as conn:
        conn.execute(
            "UPDATE education_mastery SET next_due = ? WHERE item_id = ?",
            ("2026-09-11T12:00:00Z", mid2),
        )
    return cid


def test_progress_tools_register_on_registry():
    registry = ScopedToolRegistry()
    EducationTools().register_tools(registry)
    for name in PROGRESS_TOOL_NAMES:
        assert name in registry._tools
        assert registry.get_tool_origin(name) == "platform"


def test_summarize_mastery_rows_no_fake_pct_when_empty():
    """[REQ-441-003] Empty ledger => mastery_pct None, not 100."""
    summary = summarize_mastery_rows([])
    assert summary["empty"] is True
    assert summary["mastery_pct"] is None
    assert summary["item_count"] == 0


def test_progress_summary_empty_state_honest(tmp_path: Path):
    repo = _repo(tmp_path)
    out = build_progress_summary(repo, agent_id="tutor")
    assert out["success"] is True
    assert out["empty"] is True
    assert out["mastery"]["mastery_pct"] is None
    assert out["studio_required"] is False
    assert out["studio_chrome_retained"] is True
    assert out["http_contract"] == "GET /api/education/progress"
    assert out["skill_hint"] == "progress-summary"


def test_progress_summary_sourced_from_learning_os(tmp_path: Path):
    """[REQ-441-001] Course + mastery + due from durable Learning OS stores."""
    repo = _repo(tmp_path)
    cid = _seed_course_and_grades(repo)
    out = build_progress_summary(
        repo, agent_id="tutor", topic_id="CARD-441 Progress", course_id=cid
    )
    assert out["success"] is True
    assert out["empty"] is False
    assert out["studio_required"] is False
    assert out["course"]["count"] >= 1
    assert out["current_course"]["course_id"] == cid
    assert out["mastery"]["pass_count"] == 1
    assert out["mastery"]["miss_count"] == 1
    assert out["mastery"]["mastery_pct"] == 50.0
    assert out["due"]["count"] >= 1
    assert out["http_contract"] == "GET /api/education/progress"


def test_progress_reflects_new_grade_after_refresh(tmp_path: Path):
    """[REQ-441-002] Durable grade lands; summary reflects it on re-read."""
    repo = _repo(tmp_path)
    tools = _tools(repo)
    _seed_course_and_grades(repo)
    before = tools.education_progress_summary(topic_id="CARD-441 Progress")
    assert before["success"] is True
    before_pass = int(before["mastery"]["pass_count"])

    mid3 = repo.upsert_education_mastery(
        item_id="edu_card441_c",
        topic="CARD-441 Progress",
        wiki_path="01_Notes/card441.md",
        prompt="Progress skill id?",
        expected_answer="progress-summary",
        grade="unseen",
    )
    now = datetime(2026, 9, 23, 15, 0, 0, tzinfo=timezone.utc)
    repo.record_education_grade(item_id=mid3, correct=True, now=now)

    after = tools.education_progress_summary(topic_id="CARD-441 Progress")
    assert after["success"] is True
    assert int(after["mastery"]["pass_count"]) == before_pass + 1


def test_progress_tool_failure_path_no_fake_pct():
    """[REQ-441-003] Failure => success=false, mastery_pct None."""

    class BoomRepo:
        def list_education_courses(self, limit=50):
            raise RuntimeError("db down")

        def list_education_mastery(self, limit=200, topic=None):
            raise RuntimeError("db down")

        def list_due_education_mastery(self, limit=50, as_of=None):
            raise RuntimeError("db down")

    out = build_progress_summary(BoomRepo(), agent_id="tutor")
    assert out["success"] is False
    assert out["mastery"]["mastery_pct"] is None
    assert out["empty"] is True


def test_progress_courses_and_mastery_tools(tmp_path: Path):
    repo = _repo(tmp_path)
    tools = _tools(repo)
    _seed_course_and_grades(repo)
    courses = tools.education_progress_courses()
    assert courses["success"] is True
    assert courses["count"] >= 1
    mastery = tools.education_progress_mastery(topic="CARD-441 Progress")
    assert mastery["success"] is True
    assert mastery["mastery_pct"] == 50.0
    assert mastery["http_contract"] == "GET /api/education/mastery"


def test_studio_chrome_not_removed_by_card_441():
    """[REQ-441-004] Studio progress chrome markers remain."""
    index = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    assert 'id="tab-education"' in index
    assert 'id="view-education"' in index
    assert 'id="educationCourseChrome"' in index
    assert 'id="chatEducationModeProgressBtn"' in index
    assert 'id="chatEducationModeProgressPanel"' in index

    edu_js = Path("src/web/static/modules/studios/education.js").read_text(encoding="utf-8")
    assert "renderEducationCourseChrome" in edu_js

    study_js = Path("src/web/static/modules/studios/study_entry.js").read_text(encoding="utf-8")
    assert "progress-summary" in study_js
    assert "/api/education/progress" in study_js
    assert "education_progress_summary" in study_js


def test_tutor_pack_progress_summary_skill_names_tools():
    """progress-summary skill + pack_tool_names list CARD-441 tools."""
    pack = json.loads(Path("platform-packs/tutor/pack.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in pack["skills"]}
    progress_tools = set(by_id["progress-summary"]["tools"])
    pack_tools = set(pack.get("pack_tool_names") or [])

    for name in (
        "education_progress_summary",
        "education_progress_courses",
        "education_progress_mastery",
        "education_mastery_due",
    ):
        assert name in progress_tools, name
        assert name in pack_tools, name

    skill_md = Path("platform-packs/tutor/skills/progress-summary/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "education_progress_summary" in skill_md
    assert "CARD-441" in skill_md
    assert "GET /api/education/progress" in skill_md
    assert "No `education_progress_*` agent tool yet" not in skill_md
