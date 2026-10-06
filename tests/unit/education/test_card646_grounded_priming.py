"""CARD-646: priming is built from the learner's wiki notes on the topic via one model call, or
writes nothing. The fixed outline and the two template quiz items ("In one sentence, what is X?"
answered "X is a durable concept learned via Priming schema...", and "Where should Priming write
durable knowledge for X?") are gone."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.education.grounded_steps import compose_step_content
from src.application.education.priming_seed import seed_ledger_anchors_from_priming_note
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
    "outline": [
        "The leader appends client commands to its log",
        "AppendEntries carries entries to every follower",
        "A follower accepts entries only when its log matches the previous index and term",
        "An entry commits once a majority has stored it",
    ],
    "prerequisites": ["Leader election with votes from a majority"],
    "question": "When does the leader advance the commit index?",
    "answer": "When a majority of followers have stored the entry",
}

OLD_TEMPLATE = {
    "outline": [f"What is {TOPIC}?", "Why it matters (AutoReiv / your vault)", "Key parts / moving pieces", "Prerequisites and priors"],
    "prerequisites": ["Ability to open Wiki notes in Education Studio"],
    "question": f"In one sentence, what is {TOPIC}?",
    "answer": f"{TOPIC} is a durable concept learned via Priming schema (outline + prerequisites + goals) before deep detail.",
}


@pytest.fixture
def env(tmp_path: Path):
    return make_env(tmp_path)


def _course_on_priming(repo) -> str:
    return start_or_resume_course(repo, topic_id=TOPIC, steps=["priming", "dual_coding"])["course_id"]


def test_template_builder_is_gone():
    import src.application.education.priming_schema as schema_mod

    assert not hasattr(schema_mod, "build_priming_schema_markdown")
    for mod in ("priming_schema", "priming_seed", "priming_ledger"):
        text = (Path(schema_mod.__file__).parent / f"{mod}.py").read_text(encoding="utf-8")
        assert "durable concept learned via Priming" not in text
        assert "Where should Priming write durable knowledge" not in text
        assert "What is the Priming schema outline" not in text


def test_no_notes_skips(env):
    repo, tools, wiki_root = env
    composed = asyncio.run(compose_step_content(FakeGateway(GROUNDED), tools, TOPIC, "priming"))
    assert composed["ok"] is False and composed["skip_reason"] == "no_wiki_notes"


@pytest.mark.parametrize("gateway", [None, FakeGateway(error=RuntimeError("spark down"))])
def test_no_model_is_a_skip(env, gateway):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    composed = asyncio.run(compose_step_content(gateway, tools, TOPIC, "priming"))
    assert composed["ok"] is False and composed["skip_reason"] == "model_unavailable"


@pytest.mark.parametrize("reply", [OLD_TEMPLATE, "Sure! Here is an outline.", {**GROUNDED, "answer": "Quantum flux capacitors"}])
def test_template_or_ungrounded_reply_is_refused(env, reply):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    composed = asyncio.run(compose_step_content(FakeGateway(reply), tools, TOPIC, "priming"))
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid", composed


def test_grounded_priming_is_written_with_sources_and_its_own_quiz_item(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    gw = FakeGateway(GROUNDED)
    composed = asyncio.run(compose_step_content(gw, tools, TOPIC, "priming"))
    assert composed["ok"] is True, composed
    assert len(gw.requests) == 1 and gw.requests[0].think is False
    assert "AppendEntries" in gw.requests[0].messages[1].content

    done = complete_course_step(repo, course_id=_course_on_priming(repo), wiki_tools_or_store=tools, composed=composed)
    assert done["course"]["current_step"] == "dual_coding"
    path = done["wiki_path"]
    meta, body = FrontmatterParser.parse((wiki_root / path).read_text(encoding="utf-8"))
    assert "A follower accepts entries only when its log matches" in body
    assert "[[00_Inbox/raft-log-replication" in body
    assert "durable concept" not in body and "Where should Priming" not in body
    prompts = sorted(r["prompt"] for r in mastery(repo))
    assert prompts == ["When does the leader advance the commit index?"], prompts


def test_priming_without_grounded_content_writes_nothing(env):
    repo, tools, wiki_root = env
    before = md_files(wiki_root)
    done = complete_course_step(repo, course_id=_course_on_priming(repo), wiki_tools_or_store=tools)
    assert md_files(wiki_root) == before
    assert done["item_ids"] == [] and not done["wiki_path"]
    assert done["skip_reason"]
    assert mastery(repo) == []
    assert [f for f in repo.list_semantic_facts() if "priming" in (f.get("attribute") or "")] == []
    assert done["course"]["current_step"] == "dual_coding"


def test_priming_note_without_quiz_seeds_no_template_item(env):
    repo, tools, wiki_root = env
    res = seed_ledger_anchors_from_priming_note(
        repo, content="# Priming: Raft\n\nSome outline with no quiz.", wiki_path="00_Inbox/p.md", topic=TOPIC
    )
    assert res["item_ids"] == []
    assert mastery(repo) == []


def test_priming_writeback_api_never_writes_the_template():
    from src.web.app import app

    with TestClient(app) as client:
        res = client.post(
            "/api/education/priming/writeback",
            json={"agent_id": "tutor", "topic": "Zebra crossing quokka semantics 646"},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is False
    assert body["skip_reason"] in ("no_wiki_notes", "model_unavailable")
    assert not body.get("path")
