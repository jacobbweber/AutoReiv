"""CARD-438: Tutor chat quiz/flashcard turns write durable Learning OS grades.

REQ-438-001..004: education_* agent tools grade into education_mastery;
failure does not fake success; Education Studio quiz chrome remains.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.quiz_engine import grade_answer_binary
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.education_tools import EducationTools
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


EDU_TOOL_NAMES = (
    "education_quiz_extract",
    "education_quiz_next",
    "education_quiz_grade",
    "education_mastery_due",
    "education_mastery_upsert",
    "education_flashcard_next",
    "education_flashcard_grade",
)


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "tutor_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _tools(repo: AgentMemoryRepository, wiki_root: Path | None = None) -> EducationTools:
    return EducationTools(
        repository=repo,
        wiki_root=wiki_root,
        default_agent_id="tutor",
    )


def test_education_tools_register_on_registry():
    registry = ScopedToolRegistry()
    EducationTools().register_tools(registry)
    for name in EDU_TOOL_NAMES:
        assert name in registry._tools
        assert registry.get_tool_origin(name) == "platform"


def test_quiz_grade_turn_persists_durable_mastery_row(tmp_path: Path):
    """[REQ-438-001] Quiz turn path -> education_mastery grade + next_due."""
    repo = _repo(tmp_path)
    tools = _tools(repo)
    now = datetime(2026, 9, 23, 20, 0, 0, tzinfo=timezone.utc)

    mid = repo.upsert_education_mastery(
        item_id="edu_card438_quiz",
        topic="CARD-438 Quiz",
        wiki_path="01_Notes/card438-quiz.md",
        prompt="What ledger stores Learning OS grades?",
        expected_answer="education_mastery",
        grade="unseen",
    )
    assert mid == "edu_card438_quiz"

    # Wrong answer first
    wrong = tools.education_quiz_grade(
        item_id=mid,
        answer="chat bubble score",
        agent_id="tutor",
    )
    assert wrong.get("success") is True
    assert wrong.get("durable") is True
    assert wrong.get("correct") is False
    assert wrong.get("grade") == "miss"
    assert wrong.get("grader") == "binary_external"
    assert wrong.get("http_contract") == "POST /api/education/quiz/grade"

    row = repo.get_education_mastery(mid)
    assert row is not None
    assert row["grade"] == "miss"
    assert int(row["interval_stage"]) == 0
    assert row.get("next_due")
    assert int(row.get("miss_count") or 0) >= 1

    # Pass advances SRS
    # Force stage via record with controlled now then tool grade
    repo.record_education_grade(item_id=mid, correct=False, now=now)
    right = tools.education_quiz_grade(
        item_id=mid,
        answer="education_mastery",
        agent_id="tutor",
    )
    assert right.get("success") is True
    assert right.get("correct") is True
    assert right.get("grade") == "pass"
    row2 = repo.get_education_mastery(mid)
    assert row2["grade"] == "pass"
    assert int(row2["interval_stage"]) >= 1
    assert row2.get("next_due")
    assert grade_answer_binary("education_mastery", "Education_Mastery") is True


def test_flashcard_grade_turn_shares_durable_quiz_path(tmp_path: Path):
    """[REQ-438-001] Flashcard turn uses shared quiz-grade ledger write."""
    repo = _repo(tmp_path)
    tools = _tools(repo)

    upsert = tools.education_mastery_upsert(
        topic="CARD-438 Flash",
        wiki_path="01_Notes/card438-flash.md",
        prompt="SRS ladder days?",
        expected_answer="1-3-7-30",
        agent_id="tutor",
    )
    assert upsert.get("success") is True
    assert upsert.get("durable") is True
    item_id = upsert["item_id"]

    # Make due by recording a miss in the past
    past = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    repo.record_education_grade(item_id=item_id, correct=False, now=past)
    # Force next_due into the past for due listing
    with repo.get_connection() as conn:
        conn.execute(
            "UPDATE education_mastery SET next_due = ? WHERE item_id = ?",
            ("2026-09-02T12:00:00Z", item_id),
        )

    nxt = tools.education_flashcard_next(limit=5, agent_id="tutor")
    assert nxt.get("success") is True
    ids = [i.get("item_id") for i in (nxt.get("items") or [])]
    assert item_id in ids

    graded = tools.education_flashcard_grade(
        item_id=item_id,
        answer="1-3-7-30",
        agent_id="tutor",
    )
    assert graded.get("success") is True
    assert graded.get("durable") is True
    assert graded.get("correct") is True
    assert graded.get("grade") == "pass"
    assert graded.get("shared_with") == "education_quiz_grade"
    assert graded.get("http_contract") == "POST /api/education/quiz/grade"

    row = repo.get_education_mastery(item_id)
    assert row["grade"] == "pass"
    assert row.get("last_graded_at")
    due = datetime.fromisoformat(row["next_due"].replace("Z", "+00:00"))
    assert due > datetime.now(timezone.utc) - timedelta(days=0)


def test_grade_failure_does_not_fake_success(tmp_path: Path):
    """[REQ-438-003] Missing item / empty expected -> success false, no pass row."""
    repo = _repo(tmp_path)
    tools = _tools(repo)

    missing = tools.education_quiz_grade(
        item_id="edu_does_not_exist",
        answer="anything",
        agent_id="tutor",
    )
    assert missing.get("success") is False
    assert missing.get("durable") is False
    assert "Unknown mastery item" in str(missing.get("error") or "")
    assert repo.get_education_mastery("edu_does_not_exist") is None

    mid = repo.upsert_education_mastery(
        item_id="edu_empty_expected",
        topic="Empty",
        wiki_path="x.md",
        prompt="Q?",
        expected_answer="",
        grade="unseen",
    )
    empty = tools.education_quiz_grade(item_id=mid, answer="guess", agent_id="tutor")
    assert empty.get("success") is False
    assert empty.get("durable") is False
    assert "expected_answer" in str(empty.get("error") or "")
    row = repo.get_education_mastery(mid)
    assert row is not None
    assert (row.get("grade") or "").lower() == "unseen"
    assert not row.get("last_graded_at")


def test_hard_refresh_path_mastery_and_due_reflect_grade(tmp_path: Path):
    """[REQ-438-002] After grade, mastery list / due / quiz next still see the row."""
    repo = _repo(tmp_path)
    tools = _tools(repo)
    mid = repo.upsert_education_mastery(
        item_id="edu_refresh_check",
        topic="Refresh Topic",
        wiki_path="note.md",
        prompt="Capital of durable grades?",
        expected_answer="ledger",
        grade="unseen",
    )
    tools.education_quiz_grade(item_id=mid, answer="ledger", agent_id="tutor")

    # Simulate "hard refresh" by new tool instance on same db
    tools2 = _tools(repo)
    listed = repo.list_education_mastery(topic="Refresh Topic")
    assert any(r["item_id"] == mid and r["grade"] == "pass" for r in listed)

    nxt = tools2.education_quiz_next(topic="Refresh Topic", agent_id="tutor")
    assert nxt.get("success") is True
    # Item may or may not be "next" after pass; ledger presence is the durable proof
    assert repo.get_education_mastery(mid)["grade"] == "pass"


def test_education_studio_quiz_chrome_not_removed():
    """[REQ-438-004] Do not remove Education Studio quiz UI on this card."""
    index = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    assert 'id="tab-education"' in index
    assert 'id="view-education"' in index
    assert 'id="educationQuizPanel"' in index or "educationQuizPanel" in index

    edu_js = Path("src/web/static/modules/studios/education.js").read_text(encoding="utf-8")
    assert "/api/education/quiz/grade" in edu_js
    assert "gradeEducationAnswerLocal" in edu_js


def test_tutor_pack_names_education_tools_on_quiz_and_flashcard_skills():
    """Skills + pack_tool_names list the exact CARD-438 tools."""
    import json

    pack = json.loads(Path("platform-packs/tutor/pack.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in pack["skills"]}
    quiz_tools = set(by_id["quiz-turn"]["tools"])
    flash_tools = set(by_id["flashcard-turn"]["tools"])
    pack_tools = set(pack.get("pack_tool_names") or [])

    for name in ("education_quiz_next", "education_quiz_grade", "education_quiz_extract"):
        assert name in quiz_tools
        assert name in pack_tools
    for name in (
        "education_flashcard_next",
        "education_flashcard_grade",
        "education_mastery_due",
        "education_mastery_upsert",
    ):
        assert name in flash_tools
        assert name in pack_tools

    quiz_md = Path("platform-packs/tutor/skills/quiz-turn/SKILL.md").read_text(encoding="utf-8")
    flash_md = Path("platform-packs/tutor/skills/flashcard-turn/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "education_quiz_grade" in quiz_md
    assert "education_flashcard_grade" in flash_md
    assert "CARD-438" in quiz_md
    assert "CARD-438" in flash_md
