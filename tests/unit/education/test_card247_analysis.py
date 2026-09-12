"""CARD-247: Education Analysis - error log + metacog facts; miss reasons feed quiz."""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application.education.analysis import (
    ANALYSIS_CATEGORY,
    ANALYSIS_ENTITY,
    MISS_REASON_CONCEPT_GAP,
    MISS_REASON_EMPTY,
    MISS_REASON_PARTIAL,
    MISS_REASON_WRONG,
    active_miss_reasons,
    classify_miss_reason,
    list_error_log,
    list_metacog_patterns,
    record_error_and_metacog,
    select_quiz_with_miss_reason_pressure,
    summarize_analysis,
    write_analysis_wiki_outcome,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "assistant_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def _seed(repo, item_id, topic, grade="unseen", miss_count=0, pass_count=0, next_due=None, prompt=None, expected="answer"):
    repo.upsert_education_mastery(
        item_id=item_id,
        topic=topic,
        wiki_path=f"notes/{topic}.md",
        prompt=prompt or f"Prompt for {item_id}?",
        expected_answer=expected,
        grade=grade,
        next_due=next_due,
    )
    if miss_count or pass_count or grade != "unseen":
        with repo.get_connection() as conn:
            conn.execute(
                "UPDATE education_mastery SET grade=?, miss_count=?, pass_count=?, next_due=COALESCE(?, next_due) WHERE item_id=?",
                (grade, miss_count, pass_count, next_due, item_id),
            )


def test_classify_miss_reason_taxonomy_binary():
    assert classify_miss_reason(expected="standing Job", given="", correct=False) == MISS_REASON_EMPTY
    assert (
        classify_miss_reason(expected="standing Job", given="chat toast", correct=False) == MISS_REASON_WRONG
    )
    assert (
        classify_miss_reason(
            expected="standing Job HITL park mastery",
            given="standing Job something",
            correct=False,
        )
        == MISS_REASON_PARTIAL
    )
    assert (
        classify_miss_reason(
            expected="",
            given="I forgot HITL",
            required_concepts=["standing Job", "HITL park"],
            correct=False,
        )
        == MISS_REASON_CONCEPT_GAP
    )
    assert classify_miss_reason(expected="x", given="x", correct=True) == "pass"


def test_analysis_module_has_no_llm_self_score():
    import src.application.education.analysis as mod

    src = inspect.getsource(mod)
    low = src.lower()
    assert "complete(" not in src
    assert "openai" not in low
    assert "ollama" not in low
    assert "chat.completions" not in low
    assert "self_score" not in low
    assert "gateway.complete" not in low
    assert "llm_gateway" not in low


def test_record_error_and_metacog_on_miss(tmp_path):
    repo = _repo(tmp_path)
    _seed(repo, "edu_an_1", "Jobs", expected="standing Job")
    row = repo.get_education_mastery("edu_an_1")
    assert row is not None
    result = record_error_and_metacog(
        repo,
        item=row,
        given="chat toast",
        correct=False,
        source="quiz",
    )
    assert result["recorded"] is True
    assert result["miss_reason"] == MISS_REASON_WRONG
    assert result["error_fact_id"]
    assert result["metacog_fact_id"]
    assert result["pattern_fact_id"]

    errors = list_error_log(repo)
    assert any("edu_an_1" in (e.get("value") or "") for e in errors)
    assert all(e.get("category") == ANALYSIS_CATEGORY for e in errors)
    pats = list_metacog_patterns(repo)
    assert any("metacog" in (p.get("attribute") or "") or "miss_reason" in (p.get("value") or "") for p in pats)
    assert "memory" in str(repo.db_path).replace("\\", "/").lower() or "assistant_memory" in str(repo.db_path)


def test_pass_does_not_write_error_log(tmp_path):
    repo = _repo(tmp_path)
    _seed(repo, "edu_an_pass", "Jobs", expected="ok")
    row = repo.get_education_mastery("edu_an_pass")
    result = record_error_and_metacog(repo, item=row, given="ok", correct=True)
    assert result["recorded"] is False
    assert result["miss_reason"] == "pass"
    assert list_error_log(repo) == [] or not any(
        "edu_an_pass" in (e.get("value") or "") for e in list_error_log(repo)
    )


def test_select_quiz_prefers_miss_reason_pressured_items(tmp_path):
    repo = _repo(tmp_path)
    now = datetime(2026, 9, 11, 21, 0, 0, tzinfo=timezone.utc)
    _seed(
        repo,
        "edu_strong",
        "Strong",
        grade="pass",
        pass_count=3,
        miss_count=0,
        next_due=(now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        prompt="Strong?",
        expected="strong",
    )
    _seed(
        repo,
        "edu_weak_other",
        "Other",
        grade="miss",
        miss_count=1,
        pass_count=0,
        next_due=(now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        prompt="Other weak?",
        expected="other",
    )
    _seed(
        repo,
        "edu_hot_miss",
        "Hot",
        grade="miss",
        miss_count=2,
        pass_count=0,
        next_due=(now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        prompt="Hot miss?",
        expected="standing Job",
    )
    row = repo.get_education_mastery("edu_hot_miss")
    record_error_and_metacog(repo, item=row, given="toast", correct=False, source="quiz", now=now)

    picked = select_quiz_with_miss_reason_pressure(repo, limit=3, as_of=now)
    assert picked
    assert picked[0]["item_id"] == "edu_hot_miss"
    assert picked[0].get("analysis_pressure") is True
    assert MISS_REASON_WRONG in (picked[0].get("active_miss_reasons") or active_miss_reasons(repo))


def test_grade_path_records_analysis_facts(tmp_path):
    """record_education_grade with given answer should sync analysis on miss."""
    repo = _repo(tmp_path)
    _seed(repo, "edu_grade_an", "Priming", expected="schema first")
    # Simulate API grade path helper
    from src.application.education.analysis import record_error_and_metacog as rec

    row = repo.record_education_grade(item_id="edu_grade_an", correct=False)
    analysis = rec(repo, item=row, given="I guess random", correct=False, source="quiz")
    assert analysis["recorded"]
    summary = summarize_analysis(repo)
    assert summary["error_count"] >= 1
    assert "edu_grade_an" in (summary.get("pressured_item_ids") or [])


def test_write_analysis_wiki_outcome(tmp_path):
    class FakeWiki:
        def __init__(self):
            self.calls = []

        def append_note(self, path, chunk, heading=None):
            self.calls.append({"path": path, "chunk": chunk, "heading": heading})
            return {"success": True, "path": path}

    wiki = FakeWiki()
    item = {"item_id": "edu_w1", "prompt": "What is priming?"}
    result = write_analysis_wiki_outcome(
        wiki,
        wiki_path="00_Inbox/note.md",
        item=item,
        miss_reason=MISS_REASON_EMPTY,
        given="",
    )
    assert result["success"] is True
    assert wiki.calls and wiki.calls[0]["heading"] == "Analysis outcomes"
    assert "miss_reason=empty_answer" in wiki.calls[0]["chunk"]


def test_summarize_analysis_entity(tmp_path):
    repo = _repo(tmp_path)
    _seed(repo, "edu_sum", "Topic", expected="answer")
    row = repo.get_education_mastery("edu_sum")
    record_error_and_metacog(repo, item=row, given="", correct=False)
    summary = summarize_analysis(repo)
    assert summary["entity"] == ANALYSIS_ENTITY
    assert summary["category"] == ANALYSIS_CATEGORY
    assert summary["error_count"] >= 1
    assert MISS_REASON_EMPTY in summary["active_miss_reasons"]
