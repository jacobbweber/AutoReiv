"""CARD-320: Education Course + Mastery model — durable course in agent memory.db.

Fails if REQ-EDU-COURSE-001..006 regress: education_course table, Wiki+ledger on
step complete, binary external mastery gate, restart-safe course+step, course
pipeline DEFAULT (mode-picker = jump-to-step), no Dual Coding chrome / storage.db.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _assert_memory_db_path(db: Path) -> None:
    name = db.name.lower()
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in name or "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_default_course_steps_exclude_dual_coding_chrome():
    """[REQ-EDU-COURSE-005/006] Default pipeline has ordered Learning OS steps; no Dual Coding chrome."""
    from src.application.education.course import COURSE_KIND, DEFAULT_COURSE_STEPS

    assert COURSE_KIND == "education_course"
    assert isinstance(DEFAULT_COURSE_STEPS, (list, tuple))
    assert len(DEFAULT_COURSE_STEPS) >= 4
    assert DEFAULT_COURSE_STEPS[0] == "priming"
    assert "retrieval" in DEFAULT_COURSE_STEPS
    assert "retention" in DEFAULT_COURSE_STEPS
    assert "dual_coding" not in DEFAULT_COURSE_STEPS


def test_education_course_table_created_in_agent_memory_db(tmp_path: Path):
    """[REQ-EDU-COURSE-001] Durable education_course beside education_mastery in *_memory.db."""
    from src.infrastructure.memory.repositories.education_course_ops import (
        ensure_education_course_schema,
    )

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    with repo.get_connection() as conn:
        ensure_education_course_schema(conn)
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "education_course" in tables
    assert "education_mastery" in tables
    assert "storage.db" not in str(db)


def test_start_course_persists_ordered_steps_and_current(tmp_path: Path):
    """[REQ-EDU-COURSE-001] topic_id + steps JSON + current_step + status + timestamps."""
    from src.application.education.course import DEFAULT_COURSE_STEPS, start_or_resume_course

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(repo, topic_id="Standing Jobs")
    assert course["topic_id"] == "Standing Jobs"
    assert course["course_id"]
    assert course["status"] == "active"
    assert course["current_step"] == DEFAULT_COURSE_STEPS[0]
    steps = course["steps"]
    assert steps == list(DEFAULT_COURSE_STEPS)
    assert course.get("created_at")
    assert course.get("updated_at")

    again = start_or_resume_course(repo, topic_id="Standing Jobs")
    assert again["course_id"] == course["course_id"]
    assert again["current_step"] == course["current_step"]


def test_reopen_memory_db_preserves_course_and_step(tmp_path: Path):
    """[REQ-EDU-COURSE-004] Restart-safe: reopen memory.db → same course + current_step."""
    from src.application.education.course import (
        DEFAULT_COURSE_STEPS,
        complete_course_step,
        get_course,
        start_or_resume_course,
    )

    wiki = WikiTools(wiki_root=tmp_path / "wiki")
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)

    repo1 = AgentMemoryRepository(db_path=db)
    repo1.initialize_schema()
    c0 = start_or_resume_course(repo1, topic_id="Restart Course")
    assert c0["current_step"] == "priming"

    done = complete_course_step(
        repo1,
        course_id=c0["course_id"],
        wiki_tools_or_store=wiki,
        teach_style="schema first",
    )
    assert done["success"] is True
    assert done["course"]["current_step"] == DEFAULT_COURSE_STEPS[1]

    repo2 = AgentMemoryRepository(db_path=db)
    repo2.initialize_schema()
    c1 = get_course(repo2, course_id=c0["course_id"])
    assert c1 is not None
    assert c1["topic_id"] == "Restart Course"
    assert c1["current_step"] == DEFAULT_COURSE_STEPS[1]
    assert c1["status"] == "active"

    resumed = start_or_resume_course(repo2, topic_id="Restart Course")
    assert resumed["course_id"] == c0["course_id"]
    assert resumed["current_step"] == DEFAULT_COURSE_STEPS[1]


def test_complete_step_writes_wiki_and_ledger_anchors(tmp_path: Path):
    """[REQ-EDU-COURSE-002] Each completed step → Wiki artifact + ledger anchors."""
    from src.application.education.course import complete_course_step, start_or_resume_course

    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(repo, topic_id="CARD320 Wiki Ledger")
    assert course["current_step"] == "priming"

    result = complete_course_step(
        repo,
        course_id=course["course_id"],
        wiki_tools_or_store=tools,
        teach_style="schema first",
    )
    assert result["success"] is True
    assert result.get("wiki_path") or (result.get("artifact") or {}).get("path")
    path = (result.get("wiki_path") or result["artifact"]["path"]).replace("\\", "/")
    assert path.startswith("00_Inbox/")

    ledger = result.get("ledger") or {}
    assert ledger.get("success") is True or ledger.get("count", 0) >= 1 or result.get("item_ids")
    rows = repo.list_education_mastery()
    assert any("CARD320" in (r.get("topic") or "") or "Wiki Ledger" in (r.get("topic") or "") for r in rows)


def test_mastery_gate_binary_external_miss_sets_next_due(tmp_path: Path):
    """[REQ-EDU-COURSE-003] Mastery = binary external only; miss → Retention next_due."""
    from src.application.education import course as course_mod
    from src.application.education.course import (
        complete_course_step,
        grade_course_mastery,
        start_or_resume_course,
    )

    src = inspect.getsource(course_mod)
    assert "grade_answer_binary" in src
    assert "openai" not in src.lower()
    assert "ollama" not in src.lower()

    wiki = WikiTools(wiki_root=tmp_path / "wiki")
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(repo, topic_id="Binary Gate")
    priming = complete_course_step(
        repo, course_id=course["course_id"], wiki_tools_or_store=wiki
    )
    assert priming["success"] is True

    rows = repo.list_education_mastery()
    assert rows
    item = next(r for r in rows if (r.get("expected_answer") or "").strip())
    now = datetime(2026, 9, 14, 20, 0, 0, tzinfo=timezone.utc)

    graded = grade_course_mastery(
        repo,
        item_id=item["item_id"],
        answer="totally wrong not matching",
        now=now,
    )
    assert graded["grader"] == "binary_external"
    assert graded["correct"] is False
    assert graded["item"]["grade"] == "miss"
    assert graded["item"]["interval_stage"] == 0
    due = datetime.fromisoformat(graded["item"]["next_due"].replace("Z", "+00:00"))
    assert due == now + timedelta(days=1)

    pass_g = grade_course_mastery(
        repo,
        item_id=item["item_id"],
        answer=item["expected_answer"],
        now=now + timedelta(days=1),
    )
    assert pass_g["grader"] == "binary_external"
    assert pass_g["correct"] is True
    assert pass_g["item"]["grade"] == "pass"


def test_jump_to_step_is_secondary_mode_picker(tmp_path: Path):
    """[REQ-EDU-COURSE-005] Mode-picker jumps to step; does not replace durable course."""
    from src.application.education.course import (
        DEFAULT_COURSE_STEPS,
        jump_to_course_step,
        start_or_resume_course,
    )

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(repo, topic_id="Jump Topic")
    assert course["current_step"] == "priming"

    jumped = jump_to_course_step(repo, course_id=course["course_id"], step="retrieval")
    assert jumped["current_step"] == "retrieval"
    assert jumped["steps"] == list(DEFAULT_COURSE_STEPS)

    jumped2 = jump_to_course_step(repo, course_id=course["course_id"], step="elaboration")
    assert jumped2["current_step"] == "elaboration"


def test_course_pipeline_is_default_ask_path():
    """[REQ-EDU-COURSE-005] Course pipeline is DEFAULT; custom/mode is secondary."""
    from src.application.education.course import is_course_pipeline_default

    assert is_course_pipeline_default() is True

    js_path = Path(__file__).resolve().parents[3] / "src/web/static/modules/studios/education.js"
    js = js_path.read_text(encoding="utf-8")
    assert "COURSE_PIPELINE" in js or "coursePipeline" in js or "educationCourse" in js
    assert "jumpToStep" in js or "jump_to_step" in js or "Jump to step" in js or "jump-to-step" in js
    assert "DualCodingPlayer" not in js
    assert "dual-coding-player" not in js.lower()


def test_router_course_endpoints_exist():
    """API surface for course start/get/complete/jump wired on education router."""
    from src.web.routers import education as edu_router

    src = inspect.getsource(edu_router)
    assert "/api/education/course" in src
    assert "complete" in src.lower() or "complete_step" in src or "complete-step" in src
    assert "jump" in src.lower()
    assert "grade_answer_binary" in src


def test_agent_memory_initialize_includes_course_schema(tmp_path: Path):
    """Schema init installs education_course alongside education_mastery."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    with repo.get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='education_course'"
        ).fetchone()
    assert row is not None


def test_complete_advances_through_pipeline_until_done(tmp_path: Path):
    """Completing last step marks course completed."""
    from src.application.education.course import (
        DEFAULT_COURSE_STEPS,
        complete_course_step,
        jump_to_course_step,
        start_or_resume_course,
    )

    wiki = WikiTools(wiki_root=tmp_path / "wiki")
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    course = start_or_resume_course(repo, topic_id="Finish Line")
    last = DEFAULT_COURSE_STEPS[-1]
    jump_to_course_step(repo, course_id=course["course_id"], step=last)
    result = complete_course_step(
        repo, course_id=course["course_id"], wiki_tools_or_store=wiki
    )
    assert result["success"] is True
    assert result["course"]["status"] == "completed"
    assert result["course"]["current_step"] == last
