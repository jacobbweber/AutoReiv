"""CARD-439: Due reviews in Tutor education mode (SRS / retention from Study).

REQ-439-001..004: due list from Learning OS mastery/due; complete persists
grade/SRS and shifts due queue; empty state is honest; delivery profiles
must not replace ledger/SRS. Education Studio due chrome stays.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.education_tools import EducationTools
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


DUE_REVIEW_TOOL_NAMES = (
    "education_mastery_due",
    "education_due_review_list",
    "education_due_review_complete",
    "education_retention_run",
    "education_quiz_grade",
    "education_flashcard_grade",
)


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "tutor_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _tools(repo: AgentMemoryRepository, **kwargs) -> EducationTools:
    return EducationTools(
        repository=repo,
        default_agent_id="tutor",
        **kwargs,
    )


def _seed_due(repo: AgentMemoryRepository, item_id: str, *, prompt: str, expected: str) -> str:
    mid = repo.upsert_education_mastery(
        item_id=item_id,
        topic="CARD-439 Due",
        wiki_path="01_Notes/card439-due.md",
        prompt=prompt,
        expected_answer=expected,
        grade="unseen",
    )
    past = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    repo.record_education_grade(item_id=mid, correct=False, now=past)
    with repo.get_connection() as conn:
        conn.execute(
            "UPDATE education_mastery SET next_due = ? WHERE item_id = ?",
            ("2026-09-02T12:00:00Z", mid),
        )
    return mid


def test_due_review_tools_register_on_registry():
    registry = ScopedToolRegistry()
    EducationTools().register_tools(registry)
    for name in DUE_REVIEW_TOOL_NAMES:
        assert name in registry._tools
        assert registry.get_tool_origin(name) == "platform"


def test_due_review_list_sourced_from_mastery_due_api_contract(tmp_path: Path):
    """[REQ-439-001] Due list comes from education_mastery due ledger, not client fiction."""
    repo = _repo(tmp_path)
    tools = _tools(repo)
    mid = _seed_due(repo, "edu_card439_due_a", prompt="What owns due reviews?", expected="Learning OS")

    listed = tools.education_due_review_list(agent_id="tutor", limit=20)
    assert listed.get("success") is True
    assert listed.get("empty") is False
    assert listed.get("http_contract") == "GET /api/education/mastery/due"
    assert listed.get("skill_hint") == "due-review"
    ids = [i.get("item_id") for i in (listed.get("items") or [])]
    assert mid in ids
    # Twin: mastery_due must agree
    twin = tools.education_mastery_due(agent_id="tutor", limit=20)
    assert twin.get("success") is True
    twin_ids = [i.get("item_id") for i in (twin.get("items") or [])]
    assert mid in twin_ids


def test_due_review_empty_state_when_nothing_due(tmp_path: Path):
    """[REQ-439-003] Empty due queue is an explicit empty state, not fake items."""
    repo = _repo(tmp_path)
    tools = _tools(repo)

    listed = tools.education_due_review_list(agent_id="tutor")
    assert listed.get("success") is True
    assert listed.get("empty") is True
    assert listed.get("count") == 0
    assert listed.get("items") == []
    assert "No due reviews" in str(listed.get("empty_state") or "")
    # mastery_due also surfaces empty honestly
    due = tools.education_mastery_due(agent_id="tutor")
    assert due.get("success") is True
    assert due.get("empty") is True
    assert due.get("count") == 0


def test_due_review_complete_persists_and_shifts_due_list(tmp_path: Path):
    """[REQ-439-002] Complete writes durable grade/SRS; item leaves or reschedules due."""
    repo = _repo(tmp_path)
    tools = _tools(repo)
    mid = _seed_due(
        repo,
        "edu_card439_complete",
        prompt="SRS ladder?",
        expected="1-3-7-30",
    )

    before = tools.education_due_review_list(agent_id="tutor")
    assert mid in [i.get("item_id") for i in (before.get("items") or [])]

    done = tools.education_due_review_complete(
        item_id=mid,
        answer="1-3-7-30",
        agent_id="tutor",
    )
    assert done.get("success") is True
    assert done.get("durable") is True
    assert done.get("correct") is True
    assert done.get("grade") == "pass"
    assert done.get("http_contract") == "POST /api/education/quiz/grade"
    assert done.get("skill_hint") == "due-review"
    assert done.get("left_due_queue") is True or done.get("still_due") is False

    row = repo.get_education_mastery(mid)
    assert row is not None
    assert row["grade"] == "pass"
    assert row.get("next_due")
    due_at = datetime.fromisoformat(row["next_due"].replace("Z", "+00:00"))
    assert due_at > datetime.now(timezone.utc) - timedelta(minutes=1)

    after = tools.education_due_review_list(agent_id="tutor")
    after_ids = [i.get("item_id") for i in (after.get("items") or [])]
    assert mid not in after_ids


def test_due_review_complete_failure_does_not_fake_success(tmp_path: Path):
    """Failures must not claim durable success (anti-theatre)."""
    repo = _repo(tmp_path)
    tools = _tools(repo)

    missing = tools.education_due_review_complete(
        item_id="edu_missing_439",
        answer="x",
        agent_id="tutor",
    )
    assert missing.get("success") is False
    assert missing.get("durable") is False
    assert "Unknown mastery item" in str(missing.get("error") or "")
    assert missing.get("left_due_queue") is not True


def test_retention_run_nothing_due_is_honest_empty(tmp_path: Path):
    """Retention with nothing due returns honest empty / nothing_due (no fake mint)."""
    repo = _repo(tmp_path)
    tools = _tools(repo)
    result = tools.education_retention_run(agent_id="tutor")
    assert result.get("success") is True
    assert result.get("http_contract") == "POST /api/education/retention/run"
    inner = result.get("result") or {}
    assert inner.get("status") == "ok"
    assert int(inner.get("due_count") or 0) == 0
    assert inner.get("reason") in ("nothing_due", "all_pending")
    assert (inner.get("minted_job_ids") or []) == []


def test_retention_run_without_orch_does_not_fake_mint(tmp_path: Path):
    """With due items but no orchestrator, retention fails closed (no fake job ids)."""
    repo = _repo(tmp_path)
    tools = _tools(repo)  # no orch
    mid = _seed_due(repo, "edu_card439_ret", prompt="Retention?", expected="standing job")
    result = tools.education_retention_run(agent_id="tutor", max_items=3)
    # Honest failure or explicit no_orchestrator - never fake minted jobs
    inner = result.get("result") or {}
    minted = list(inner.get("minted_job_ids") or result.get("minted_job_ids") or [])
    assert minted == []
    if result.get("success") is True:
        assert inner.get("reason") == "no_orchestrator" or inner.get("status") == "failed"
    else:
        assert result.get("durable") is not True or "orchestrator" in str(result.get("error") or "").lower()
    # Due item still present (not silently cleared)
    assert repo.get_education_mastery(mid) is not None


def test_education_studio_due_chrome_not_removed():
    """Studio due/quiz panels remain (ADR-0059 / REQ keep Studio)."""
    index = Path("src/web/templates/index.html").read_text(encoding="utf-8")
    assert 'id="tab-education"' in index
    assert 'id="view-education"' in index
    assert 'id="educationDueList"' in index
    assert 'id="educationRefreshDueBtn"' in index
    assert 'id="educationRunRetentionBtn"' in index
    # Tutor education-mode due affordance present
    assert 'id="chatEducationModeDueBtn"' in index
    assert 'id="chatEducationModeDuePanel"' in index

    edu_js = Path("src/web/static/modules/studios/education.js").read_text(encoding="utf-8")
    assert "/api/education/mastery/due" in edu_js
    assert "/api/education/retention/run" in edu_js

    study_js = Path("src/web/static/modules/studios/study_entry.js").read_text(encoding="utf-8")
    assert "due-review" in study_js
    assert "/api/education/mastery/due" in study_js
    assert "No due reviews" in study_js
    # Must not claim delivery profiles replace SRS
    assert "delivery profile" not in study_js.lower() or "not replace" in study_js.lower()


def test_tutor_pack_due_review_skill_names_tools():
    """due-review skill + pack_tool_names list CARD-439 tools."""
    import json

    pack = json.loads(Path("platform-packs/tutor/pack.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in pack["skills"]}
    due_tools = set(by_id["due-review"]["tools"])
    pack_tools = set(pack.get("pack_tool_names") or [])

    for name in (
        "education_due_review_list",
        "education_due_review_complete",
        "education_mastery_due",
        "education_retention_run",
        "education_quiz_grade",
        "education_flashcard_grade",
    ):
        assert name in due_tools, name
        assert name in pack_tools, name

    skill_md = Path("platform-packs/tutor/skills/due-review/SKILL.md").read_text(encoding="utf-8")
    assert "education_due_review_list" in skill_md
    assert "education_due_review_complete" in skill_md
    assert "CARD-439" in skill_md
    assert "education_retention_run" in skill_md
    # No fake retention tool disclaimer left as blocker
    assert "No `education_retention_*` agent tool yet" not in skill_md
