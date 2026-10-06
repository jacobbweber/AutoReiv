"""CARD-647: the analysis course step writes no quiz item about its own pass rate.

The scorecard note and the retention handoff stay; the mastery ledger gets no item whose
question is the app's own numbers (that answer goes stale as soon as another item is graded).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

NOW = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)


def _setup(tmp_path: Path):
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    tools = WikiTools(wiki_root=wiki_root)
    repo = AgentMemoryRepository(db_path=tmp_path / "assistant_memory.db")
    repo.initialize_schema()
    return wiki_root, tools, repo


def test_analysis_step_writes_no_quiz_item(tmp_path: Path):
    wiki_root, tools, repo = _setup(tmp_path)
    topic = "Raft consensus"
    repo.upsert_education_mastery(
        item_id="learner_raft_1",
        topic=topic,
        wiki_path="00_Inbox/raft.md",
        prompt="What does a Raft follower do when its election timeout fires?",
        expected_answer="It becomes a candidate and requests votes",
        grade="unseen",
    )
    course = start_or_resume_course(repo, topic_id=topic, steps=["analysis", "environment"])

    result = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools, now=NOW)

    assert result["completed_step"] == "analysis"
    assert result["item_ids"] == []
    prompts = [r.get("prompt") or "" for r in repo.list_education_mastery(topic=topic)]
    assert not any("pass rate" in p.lower() for p in prompts), prompts
    assert not any((r.get("item_id") or "").endswith("_analysis") for r in repo.list_education_mastery(topic=topic))
    # The learner's own item is untouched apart from the retention schedule.
    assert len(prompts) == 1


def test_analysis_step_keeps_scorecard_note_and_retention_handoff(tmp_path: Path):
    wiki_root, tools, repo = _setup(tmp_path)
    topic = "Raft consensus"
    repo.upsert_education_mastery(
        item_id="learner_raft_1",
        topic=topic,
        wiki_path="00_Inbox/raft.md",
        prompt="What does a Raft follower do when its election timeout fires?",
        expected_answer="It becomes a candidate and requests votes",
        grade="unseen",
    )
    course = start_or_resume_course(repo, topic_id=topic, steps=["analysis", "environment"])

    result = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools, now=NOW)

    assert result["success"] is True
    path = result["wiki_path"]
    assert path and (wiki_root / path).exists()
    assert "Scorecard" in (wiki_root / path).read_text(encoding="utf-8")
    handoff = (result.get("ledger") or {}).get("handoff") or {}
    assert handoff, result.get("ledger")
    item = repo.get_education_mastery("learner_raft_1")
    assert item.get("next_due")
    assert result["course"]["current_step"] == "environment"