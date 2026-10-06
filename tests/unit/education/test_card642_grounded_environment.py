"""CARD-642: the environment step writes only content about the topic from the learner's notes (where
and how to practise it) plus the learner's real delivery profile, or records progress only. The
generic framing note (the same "single-brain memory.db" constraints for every topic) and the quiz item
"What delivery profile and runtime constraints frame learning for X?" are gone."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.education.environment import select_delivery_profile
from src.application.education.grounded_steps import compose_step_content
from src.domain.wiki.frontmatter import FrontmatterParser
from tests.unit.education._grounded_fixtures import (
    TOPIC,
    FakeGateway,
    add_note,
    make_env,
    mastery,
    md_files,
)

GROUNDED = {
    "practice": [
        "Trace one client command from the leader's log to a majority of followers",
        "Find a case where a follower rejects AppendEntries because the previous term differs",
        "Watch the commit index advance on the next heartbeat",
    ],
    "question": "How do followers learn the commit index?",
    "answer": "From the next AppendEntries heartbeat",
}
OLD_TEMPLATE = {
    "practice": [
        "Single-brain persistence anchored in assistant_memory.db (never secondary storage).",
        "Tool authorization strictly scoped to catalog allowlist (wiki_note_* only; no wiki_overview).",
    ],
    "question": f"What delivery profile and runtime constraints frame learning for {TOPIC}?",
    "answer": "Calm Focus profile with single-brain memory.db invariants",
}


@pytest.fixture
def env(tmp_path: Path):
    return make_env(tmp_path)


def _course_on_environment(repo) -> str:
    return start_or_resume_course(repo, topic_id=TOPIC, steps=["environment", "retention"])["course_id"]


def test_template_framing_is_gone():
    import src.application.education.environment as env_mod

    assert not hasattr(env_mod, "build_environment_framing")
    for name in ("environment.py", "course.py"):
        text = (Path(env_mod.__file__).parent / name).read_text(encoding="utf-8")
        assert "Single-brain persistence" not in text
        assert "single-brain memory.db invariants" not in text
        assert "runtime constraints frame learning" not in text


def test_without_grounded_content_records_progress_only(env):
    repo, tools, wiki_root = env
    before = md_files(wiki_root)
    done = complete_course_step(repo, course_id=_course_on_environment(repo), wiki_tools_or_store=tools)
    assert md_files(wiki_root) == before
    assert done["skip_reason"] and done["item_ids"] == [] and not done["wiki_path"]
    assert mastery(repo) == []
    assert [f for f in repo.list_semantic_facts() if f.get("attribute") == "course_step_environment"] == []
    assert done["course"]["current_step"] == "retention"


@pytest.mark.parametrize("reply", [OLD_TEMPLATE, {**GROUNDED, "practice": ["Bake bread", "Paint a fence"]}, "nope"])
def test_template_or_ungrounded_reply_is_refused(env, reply):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    composed = asyncio.run(compose_step_content(FakeGateway(reply), tools, TOPIC, "environment"))
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid", composed


def test_grounded_environment_note_has_practice_profile_and_its_own_quiz_item(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    select_delivery_profile(repo, "calm_focus")
    composed = asyncio.run(compose_step_content(FakeGateway(GROUNDED), tools, TOPIC, "environment"))
    assert composed["ok"] is True, composed
    done = complete_course_step(
        repo, course_id=_course_on_environment(repo), wiki_tools_or_store=tools, composed=composed
    )
    meta, body = FrontmatterParser.parse((wiki_root / done["wiki_path"]).read_text(encoding="utf-8"))
    assert GROUNDED["practice"][1] in body
    assert "Calm" in body
    assert "[[00_Inbox/raft-log-replication" in body
    assert "memory.db" not in body and "wiki_overview" not in body
    assert [(r["prompt"], r["expected_answer"]) for r in mastery(repo)] == [(GROUNDED["question"], GROUNDED["answer"])]
    assert done["course"]["current_step"] == "retention"


def test_environment_preview_api_has_no_template():
    from src.web.app import app

    with TestClient(app) as client:
        res = client.post("/api/education/course/environment/preview", json={"topic": "Zebra quokka 642"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False and body["skip_reason"] in ("no_wiki_notes", "model_unavailable")
    assert "constraints" not in body and "framing_markdown" not in body
    assert body["profile"]["id"]
