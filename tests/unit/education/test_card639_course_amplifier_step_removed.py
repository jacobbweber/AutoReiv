"""CARD-639: the course "amplifiers" step is retired. Courses skip it and nothing writes its filler
wiki note ("Course Visual Amplifiers: ...") or filler quiz item ("How does the visual amplifier model...")."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.education.course import (
    DEFAULT_COURSE_STEPS,
    JUMPABLE_STEPS,
    ORDERED_COURSE_STEPS,
    complete_course_step,
    course_chrome_snapshot,
    jump_to_course_step,
    start_or_resume_course,
)
from src.application.skills.wiki_tools import WikiTools
from src.domain.wiki.store import WikiStore
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

LEGACY_STEPS = ["priming", "retrieval", "elaboration", "construction", "application", "analysis", "environment", "amplifiers", "retention"]


@pytest.fixture
def env(tmp_path: Path):
    repo = AgentMemoryRepository(db_path=tmp_path / "tutor_memory.db")
    repo.initialize_schema()
    wiki_root = tmp_path / "wiki"
    WikiStore(root_dir=wiki_root).scaffold()
    return repo, WikiTools(wiki_root=wiki_root), wiki_root


def _legacy_course(repo, current_step: str) -> str:
    """A course stored before CARD-639, whose step list still names "amplifiers"."""
    return repo.upsert_education_course(topic_id="TCP handshake", steps=LEGACY_STEPS, current_step=current_step, status="active")


def _assert_no_filler(repo, wiki_root: Path) -> None:
    notes = [p for p in wiki_root.rglob("*.md") if "Amplifier" in p.name or "amplifier" in p.read_text(encoding="utf-8", errors="ignore").lower()]
    assert notes == [], f"filler amplifier notes written: {notes}"
    items = [r for r in repo.list_education_mastery(limit=500) if "amplifier" in (r.get("prompt") or "").lower() or str(r.get("item_id") or "").endswith("_amplifiers")]
    assert items == [], f"filler amplifier quiz items written: {items}"
    assert repo.get_semantic_fact("edu_course_tcp_handshake_amplifiers") is None


def test_amplifiers_is_not_a_course_step():
    assert "amplifiers" not in DEFAULT_COURSE_STEPS
    assert "amplifiers" not in ORDERED_COURSE_STEPS
    assert "amplifiers" not in JUMPABLE_STEPS
    assert DEFAULT_COURSE_STEPS[-2:] == ("environment", "retention")


def test_new_course_goes_from_environment_to_retention(env):
    repo, tools, wiki_root = env
    course = start_or_resume_course(repo, topic_id="TCP handshake", steps=LEGACY_STEPS)
    assert "amplifiers" not in course["steps"]
    repo.update_education_course_step(course_id=course["course_id"], current_step="environment", status="active")
    done = complete_course_step(repo, course_id=course["course_id"], wiki_tools_or_store=tools)
    assert done["completed_step"] == "environment"
    assert done["course"]["current_step"] == "retention"
    _assert_no_filler(repo, wiki_root)


def test_stored_course_on_the_retired_step_moves_on_without_writing(env):
    repo, tools, wiki_root = env
    cid = _legacy_course(repo, "amplifiers")
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools)
    assert done["completed_step"] == "amplifiers"
    assert done["skipped"] is True
    assert done["course"]["current_step"] == "retention"
    assert done["item_ids"] == [] and not done["wiki_path"]
    _assert_no_filler(repo, wiki_root)


def test_stored_step_list_skips_the_retired_step_after_environment(env):
    repo, tools, wiki_root = env
    cid = _legacy_course(repo, "environment")
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools)
    assert done["course"]["current_step"] == "retention"
    _assert_no_filler(repo, wiki_root)


def test_jumping_to_the_retired_step_is_refused(env):
    repo, _tools, _root = env
    cid = _legacy_course(repo, "priming")
    with pytest.raises(ValueError):
        jump_to_course_step(repo, course_id=cid, step="amplifiers")


def test_chrome_snapshot_hides_the_retired_step(env):
    repo, _tools, _root = env
    _legacy_course(repo, "environment")
    snap = course_chrome_snapshot(repo, topic_id="TCP handshake")
    assert "amplifiers" not in snap["steps"]
    assert "amplifiers" not in snap["default_steps"]


def test_course_module_no_longer_uses_lumina():
    src = Path("src/application/education/course.py").read_text(encoding="utf-8")
    assert "lumina" not in src.lower()
    assert "build_visual_amplifier_for_course" not in src
