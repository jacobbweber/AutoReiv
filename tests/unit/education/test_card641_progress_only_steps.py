"""CARD-641: course steps without their own writer (retrieval, retention, custom, any other name)
record progress only: the course moves on and no wiki note, quiz item or memory fact is written."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.education.course import complete_course_step, jump_to_course_step
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

TOPIC = "Consistent hashing"


@pytest.fixture
def env(tmp_path: Path):
    repo = AgentMemoryRepository(db_path=tmp_path / "tutor_memory.db")
    repo.initialize_schema()
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    return repo, WikiTools(wiki_root=wiki_root), wiki_root


def _md(wiki_root: Path) -> set:
    return {str(p.relative_to(wiki_root)) for p in wiki_root.rglob("*.md")}


def _assert_progress_only(repo, wiki_root: Path, before: set, done: dict, step: str) -> None:
    assert done["success"] is True
    assert done["completed_step"] == step
    assert done["skip_reason"] == "no_writer"
    assert not done["wiki_path"] and done["item_ids"] == [] and done["tools_used"] == []
    assert _md(wiki_root) == before, "a wiki note was written"
    rows = repo.list_education_mastery(limit=500)
    assert [r for r in rows if r["item_id"].endswith(f"_{step}")] == []
    assert [r for r in rows if "learning os step" in (r.get("prompt") or "").lower()] == []
    assert [f for f in repo.list_semantic_facts() if (f.get("attribute") or "") == f"course_step_{step}"] == []


@pytest.mark.parametrize(("step", "nxt"), [("retrieval", "elaboration"), ("custom", None), ("portfolio", "retention")])
def test_step_without_writer_records_progress_only(env, step, nxt):
    repo, tools, wiki_root = env
    steps = ["priming", "retrieval", "elaboration", "portfolio", "retention", "custom"]
    cid = repo.upsert_education_course(topic_id=TOPIC, steps=steps, current_step="priming", status="active")
    jump_to_course_step(repo, course_id=cid, step=step)
    before = _md(wiki_root)
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools)
    _assert_progress_only(repo, wiki_root, before, done, step)
    if nxt:
        assert done["course"]["current_step"] == nxt and done["course"]["status"] == "active"
    else:
        assert done["course"]["status"] == "completed"


def test_retention_finishes_the_course_without_writing(env):
    repo, tools, wiki_root = env
    cid = repo.upsert_education_course(topic_id=TOPIC, steps=["environment", "retention"], current_step="retention", status="active")
    before = _md(wiki_root)
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools)
    _assert_progress_only(repo, wiki_root, before, done, "retention")
    assert done["course"]["status"] == "completed"


def test_generic_writer_is_gone():
    src = Path("src/application/education/course.py").read_text(encoding="utf-8")
    assert "What Learning OS step did you just complete" not in src
    assert 'f"Course {step_name.title()}: {topic_clean}"' not in src
