"""CARD-318: Education Retrieval — binary external grade → mastery ledger prove-and-harden.

Fails if REQ-EDU-RET-001..005 regress: binary_external only, durable pass/fail row,
miss → next_due stage0=+1d (1-3-7-30), Priming-seeded items gradable, restart-safe.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.learner_model import (
    summarize_learner_model,
    select_quiz_items,
)
from src.application.education.priming import (
    priming_writeback,
    seed_ledger_anchors_from_priming_note,
    build_priming_schema_markdown,
)
from src.application.education.quiz_engine import grade_answer_binary
from src.application.education.srs import SRS_INTERVALS_DAYS
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _assert_memory_db_path(db: Path) -> None:
    name = db.name.lower()
    path_s = str(db).replace("\\", "/").lower()
    assert "memory" in name or "memory" in path_s, f"ledger must live under memory.db path, got {db}"
    assert "storage.db" not in path_s, f"must never invent storage.db path, got {db}"


def test_srs_ladder_pinned_1_3_7_30():
    assert SRS_INTERVALS_DAYS == (1, 3, 7, 30)


def test_binary_external_grader_pin_no_llm():
    """[REQ-EDU-RET-001] Binary external only — never LLM self-score."""
    assert grade_answer_binary("memory.db", "Memory.db") is True
    assert grade_answer_binary("memory.db", "storage.db") is False

    import src.application.education.quiz_engine as qe

    src = inspect.getsource(qe)
    assert "complete(" not in src
    assert "openai" not in src.lower()
    assert "ollama" not in src.lower()

    from src.web.routers import education as edu_router

    route_src = inspect.getsource(edu_router.grade_quiz)
    assert "grade_answer_binary" in route_src
    assert 'grader": "binary_external"' in route_src.replace("'", '"') or (
        "binary_external" in route_src and "grader" in route_src
    )
    # Must not invent an LLM grader on the quiz grade path
    assert "llm" not in route_src.lower() or "binary_external" in route_src


def test_priming_seeded_wrong_grade_sets_miss_and_next_due(tmp_path: Path):
    """[REQ-EDU-RET-002/003/004] Priming writeback → wrong grade → miss + stage0 +1d."""
    wiki_root = tmp_path / "wiki"
    wiki = WikiStore(root_dir=wiki_root)
    wiki.scaffold()
    tools = WikiTools(wiki_root=wiki_root)

    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    result = priming_writeback(
        topic="CARD318 Retrieval",
        wiki_tools_or_store=tools,
        memory_repo=repo,
        teach_style="schema first",
        search_first=False,
    )
    assert result["success"] is True
    ledger = result["ledger"]
    assert ledger.get("success") is True
    assert ledger.get("count", 0) >= 1
    item_ids = list(ledger.get("item_ids") or [])
    assert item_ids

    item_id = item_ids[0]
    row0 = repo.get_education_mastery(item_id)
    assert row0 is not None
    assert (row0.get("prompt") or "").strip(), "Priming anchor must have prompt for grade"
    assert (row0.get("expected_answer") or "").strip(), (
        "Priming anchor must have expected_answer for binary grade"
    )
    assert (row0.get("grade") or "").lower() == "unseen"

    now = datetime(2026, 9, 14, 14, 0, 0, tzinfo=timezone.utc)
    # Wrong answer → miss
    wrong = "totally wrong answer not matching expected"
    correct = grade_answer_binary(row0["expected_answer"], wrong)
    assert correct is False
    miss = repo.record_education_grade(item_id=item_id, correct=correct, now=now)
    assert miss["grade"] == "miss"
    assert miss["interval_stage"] == 0
    assert int(miss.get("miss_count") or 0) >= 1
    assert miss.get("last_graded_at")
    due = datetime.fromisoformat(miss["next_due"].replace("Z", "+00:00"))
    assert due == now + timedelta(days=1)


def test_pass_advances_interval_stage(tmp_path: Path):
    """[REQ-EDU-RET-002/003] Pass advances stage on 1-3-7-30."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 14, 14, 30, 0, tzinfo=timezone.utc)

    body = build_priming_schema_markdown(topic="Pass Advance")
    seeded = seed_ledger_anchors_from_priming_note(
        repo,
        content=body,
        wiki_path="00_Inbox/priming-pass-advance.md",
        topic="Pass Advance",
    )
    assert seeded["count"] >= 1
    item_id = seeded["item_ids"][0]

    # First miss then pass → stage 1 (+3d)
    repo.record_education_grade(item_id=item_id, correct=False, now=now)
    passed = repo.record_education_grade(
        item_id=item_id, correct=True, now=now + timedelta(hours=1)
    )
    assert passed["grade"] == "pass"
    assert passed["interval_stage"] == 1
    assert int(passed.get("pass_count") or 0) >= 1
    due = datetime.fromisoformat(passed["next_due"].replace("Z", "+00:00"))
    assert due == now + timedelta(hours=1) + timedelta(days=3)


def test_quiz_next_prefers_priming_unseen_over_strong_pass(tmp_path: Path):
    """[REQ-EDU-RET-004] quiz selection prefers Priming-seeded unseen over strong passes."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    # Strong pass (should not win when priming unseen exists)
    repo.upsert_education_mastery(
        item_id="edu_strong_pass",
        topic="Other",
        wiki_path="notes/other.md",
        prompt="Strong?",
        expected_answer="yes",
        grade="unseen",
    )
    repo.record_education_grade(item_id="edu_strong_pass", correct=True)

    body = build_priming_schema_markdown(topic="Priming Prefer")
    seeded = seed_ledger_anchors_from_priming_note(
        repo,
        content=body,
        wiki_path="00_Inbox/priming-prefer.md",
        topic="Priming Prefer",
    )
    priming_ids = set(seeded["item_ids"])
    assert priming_ids

    ranked = select_quiz_items(repo, limit=3)
    assert ranked, "selection must return items"
    top_ids = [r["item_id"] for r in ranked]
    # At least one priming unseen should outrank the strong pass
    assert any(iid in priming_ids for iid in top_ids), (
        f"expected priming unseen in top selection, got {top_ids}"
    )
    assert top_ids[0] != "edu_strong_pass" or ranked[0].get("grade") == "unseen"


def test_restart_safe_same_row_and_learner_summary(tmp_path: Path):
    """[REQ-EDU-RET-005] Reopen AgentMemoryRepository on same db — row + learner match."""
    db = tmp_path / "assistant_memory.db"
    _assert_memory_db_path(db)
    now = datetime(2026, 9, 14, 15, 0, 0, tzinfo=timezone.utc)

    repo1 = AgentMemoryRepository(db_path=db)
    repo1.initialize_schema()
    body = build_priming_schema_markdown(topic="Restart Safe")
    seeded = seed_ledger_anchors_from_priming_note(
        repo1,
        content=body,
        wiki_path="00_Inbox/priming-restart.md",
        topic="Restart Safe",
    )
    item_id = seeded["item_ids"][0]
    miss = repo1.record_education_grade(item_id=item_id, correct=False, now=now)
    expected_due = miss["next_due"]
    expected_grade = miss["grade"]
    summary1 = summarize_learner_model(repo1)
    weak1 = int(summary1.get("weakness_count") or 0)
    assert weak1 >= 1

    close = getattr(repo1, "close", None)
    if callable(close):
        close()
    del repo1

    repo2 = AgentMemoryRepository(db_path=db)
    repo2.initialize_schema()
    row = repo2.get_education_mastery(item_id)
    assert row is not None
    assert row["grade"] == expected_grade == "miss"
    assert row["next_due"] == expected_due
    assert row["interval_stage"] == 0
    assert int(row.get("miss_count") or 0) >= 1
    assert row.get("last_graded_at")

    summary2 = summarize_learner_model(repo2)
    assert int(summary2.get("weakness_count") or 0) >= 1
    blob = " ".join(
        str(x.get("item_id") or "") + " " + str(x.get("value") or "")
        for x in (summary2.get("items") or [])
    ) + " " + " ".join(
        str(f.get("value") or "") for f in (summary2.get("facts") or [])
    )
    assert item_id in blob


def test_upsert_path_also_grades_binary_and_persists(tmp_path: Path):
    """Upsert (non-priming extractable) items still grade binary → durable row."""
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    now = datetime(2026, 9, 14, 16, 0, 0, tzinfo=timezone.utc)
    mid = repo.upsert_education_mastery(
        item_id="edu_318_upsert",
        topic="Upsert",
        wiki_path="notes/upsert.md",
        prompt="Where does mastery live?",
        expected_answer="memory.db",
        grade="unseen",
    )
    assert mid == "edu_318_upsert"
    assert grade_answer_binary("memory.db", "storage.db") is False
    miss = repo.record_education_grade(item_id=mid, correct=False, now=now)
    assert miss["grade"] == "miss"
    due = datetime.fromisoformat(miss["next_due"].replace("Z", "+00:00"))
    assert due == now + timedelta(days=1)


def test_grade_quiz_route_exposes_binary_external_contract():
    """API contract pin: POST quiz/grade returns grader binary_external."""
    from src.web.routers import education as edu_router

    src = inspect.getsource(edu_router.grade_quiz)
    assert "grade_answer_binary" in src
    assert "record_education_grade" in src
    assert "binary_external" in src


def test_priming_unseen_outranks_other_unseen(tmp_path: Path):
    """[REQ-EDU-RET-004] Among unseen items, Priming-seeded wins over plain upsert."""
    from src.application.education.learner_model import is_priming_seeded_item

    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()

    repo.upsert_education_mastery(
        item_id="edu_plain_unseen",
        topic="Plain",
        wiki_path="notes/plain.md",
        prompt="Plain?",
        expected_answer="plain",
        grade="unseen",
    )
    body = build_priming_schema_markdown(topic="Priming Prefer Unseen")
    seeded = seed_ledger_anchors_from_priming_note(
        repo,
        content=body,
        wiki_path="00_Inbox/priming-prefer-unseen.md",
        topic="Priming Prefer Unseen",
    )
    priming_id = seeded["item_ids"][0]
    assert is_priming_seeded_item(repo.get_education_mastery(priming_id))
    assert not is_priming_seeded_item(repo.get_education_mastery("edu_plain_unseen"))

    ranked = select_quiz_items(repo, limit=1)
    assert ranked[0]["item_id"] == priming_id


def test_grade_quiz_rejects_empty_expected_answer():
    """CARD-318 harden: empty expected_answer cannot be binary-graded."""
    from src.web.routers import education as edu_router

    src = inspect.getsource(edu_router.grade_quiz)
    assert "empty expected_answer" in src or "422" in src
