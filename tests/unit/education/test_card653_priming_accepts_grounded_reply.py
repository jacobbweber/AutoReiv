"""CARD-653: in the live course run the priming step refused the real model's reply on a topic with a
note. A read-only Spark probe (4 replies to the course priming prompt) showed why: the key ideas,
question and answer were grounded every time, but in 2 of 4 replies the "prerequisites" (things the
notes rely on, which by definition are often not in the notes, e.g. "Understanding of distributed
consensus concepts") failed the grounding check, and that refused the whole reply. Prerequisites that
are not taken from the notes are now dropped instead; the reply is still refused when its key ideas,
question or answer are not grounded. The refusal detail is also returned and logged."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.education.grounded_steps import compose_step_content
from tests.unit.education._grounded_fixtures import TOPIC, FakeGateway, add_note, make_env, mastery

# One of the replies Spark (nemotron-3.5-lightning) gave in the CARD-653 probe, refused before this card.
SPARK_REPLY = {
    "outline": [
        "Leader appends client commands to its log with current term",
        "AppendEntries messages sent with new entries, previous log index and term",
        "Follower accepts entries only if log has matching entry at previous index",
        "Majority of servers must store entry before leader advances commit index",
        "Followers apply committed entries in log order via heartbeat",
    ],
    "prerequisites": [
        "Understanding of distributed consensus concepts",
        "Familiarity with leader-follower architecture",
        "Knowledge of log-based replication mechanisms",
    ],
    "question": "What condition must a follower's log meet to accept new entries?",
    "answer": "It must match the leader's previous index and term",
}


@pytest.fixture
def env(tmp_path: Path):
    return make_env(tmp_path)


def _compose(tools, reply):
    return asyncio.run(compose_step_content(FakeGateway(reply), tools, TOPIC, "priming"))


def test_grounded_reply_with_outside_prerequisites_is_accepted_without_them(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    composed = _compose(tools, SPARK_REPLY)
    assert composed["ok"] is True, composed
    assert "Understanding of distributed consensus concepts" not in composed["prerequisites"]
    assert "Knowledge of log-based replication mechanisms" not in composed["prerequisites"]
    assert composed["outline"] == SPARK_REPLY["outline"]


def test_course_priming_writes_the_grounded_reply(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    composed = _compose(tools, {**SPARK_REPLY, "prerequisites": ["Understanding of distributed consensus concepts"]})
    course_id = start_or_resume_course(repo, topic_id=TOPIC, steps=["priming", "dual_coding"])["course_id"]
    done = complete_course_step(repo, course_id=course_id, wiki_tools_or_store=tools, composed=composed)
    assert done["wiki_path"], done
    body = (wiki_root / done["wiki_path"]).read_text(encoding="utf-8")
    assert "## Key ideas" in body and SPARK_REPLY["outline"][0] in body
    assert "## Before you start" not in body and "distributed consensus" not in body
    assert [r["prompt"] for r in mastery(repo)] == [SPARK_REPLY["question"]]


def test_ungrounded_key_ideas_are_still_refused(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    reply = {**SPARK_REPLY, "outline": ["Bake bread at home", "Paint a fence blue", "Plant tulips in spring"]}
    composed = _compose(tools, reply)
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid"
    assert "outline" in composed["detail"]


def test_refusal_detail_is_returned_and_logged(env, caplog):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    with caplog.at_level(logging.INFO, logger="src.application.education.grounded_steps"):
        composed = _compose(tools, {**SPARK_REPLY, "answer": "Bananas"})
    assert composed["ok"] is False and "answer" in composed["detail"]
    assert any("priming" in r.getMessage() and "answer" in r.getMessage() for r in caplog.records)
    course_id = start_or_resume_course(repo, topic_id=TOPIC, steps=["priming", "dual_coding"])["course_id"]
    done = complete_course_step(repo, course_id=course_id, wiki_tools_or_store=tools, composed=composed)
    assert done["skip_reason"] == "model_output_invalid" and "answer" in done["skip_detail"]
