"""CARD-654: in the course-filler-3 live check Spark asked the priming question again in every later
grounded step, so the CARD-650 dedupe dropped five quiz items and the course kept one. A read-only
probe (10 of 10 replies) showed the avoid list does reach the prompt and Spark ignores it, while a
follow-up turn naming the repeat got a new question 4 of 6 times. So a step whose question repeats an
earlier one asks once more, naming the repeat; if the second question repeats too (or the second
reply is unusable), the step keeps its first grounded content and saves no quiz item."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.education.grounded_steps import compose_course_step
from tests.unit.education._grounded_fixtures import TOPIC, add_note, make_env, mastery

ASKED = ("What condition must a follower's log meet to accept an AppendEntries message?",
         "The follower's log must have an entry at the previous index with the same term")
NEW = ("How do followers learn the commit index?", "From the next AppendEntries heartbeat")
ENV = {
    "practice": ["Trace one client command to a majority of followers", "Watch the leader advance the commit index"],
}
DUAL = {
    "prose": "In Raft the leader appends each client command to its log, replicates it to followers with AppendEntries, and commits it once a majority has stored it.",
    "mermaid": "flowchart TD\n  A[Client command] --> B[Leader appends to log]\n  B --> C[AppendEntries to followers]\n  C --> D[Majority stored]",
    "steps": ["Leader appends the command", "AppendEntries goes to every follower", "A majority stores it and the leader commits"],
}


def _reply(base, qa):
    return "```json\n" + json.dumps({**base, "question": qa[0], "answer": qa[1]}) + "\n```"


class SeqGateway:
    default_model_id = "fake-model"

    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []

    async def complete(self, request):
        self.requests.append(request)
        return SimpleNamespace(text=self.replies.pop(0) if self.replies else "")


@pytest.fixture
def env(tmp_path: Path):
    repo, tools, wiki_root = make_env(tmp_path)
    add_note(wiki_root)
    return repo, tools, wiki_root


def _compose(gateway, tools, step="environment"):
    return asyncio.run(compose_course_step(gateway, tools, TOPIC, step, avoid_questions=[ASKED[0]]))


def test_the_router_shows_the_model_the_priming_question_already_saved(env):
    # Verification the card asked for: the earlier ledger question reaches the step prompt.
    from src.web.routers.education import _compose_current_step

    repo, tools, _ = env
    repo.upsert_education_mastery(item_id="edu_priming1", topic=TOPIC, prompt=ASKED[0], expected_answer=ASKED[1], grade="unseen")
    cid = start_or_resume_course(repo, topic_id=TOPIC, steps=["environment", "retention"])["course_id"]
    gateway = SeqGateway(_reply(ENV, NEW))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(gateway=gateway)))
    out = asyncio.run(_compose_current_step(request, repo, cid, tools))
    assert out["ok"] and ASKED[0] in gateway.requests[0].messages[-1].content


def test_a_repeated_question_is_asked_again_naming_the_repeat(env):
    _, tools, _ = env
    gateway = SeqGateway(_reply(ENV, ASKED), _reply(ENV, NEW))
    out = _compose(gateway, tools)
    assert len(gateway.requests) == 2
    retry = gateway.requests[1].messages
    assert [getattr(m.role, "value", m.role) for m in retry][-2:] == ["assistant", "user"]
    assert ASKED[0] in retry[-1].content and "different" in retry[-1].content.lower()
    assert out["ok"] and out["question"] == NEW[0] and out["answer"] == NEW[1]
    assert out["quiz_retry"] == "new_question"


def test_a_distinct_question_is_not_asked_again(env):
    _, tools, _ = env
    gateway = SeqGateway(_reply(ENV, NEW))
    out = _compose(gateway, tools)
    assert len(gateway.requests) == 1 and out["question"] == NEW[0] and not out.get("quiz_retry")


def test_dual_coding_asks_again_too(env):
    _, tools, _ = env
    gateway = SeqGateway(_reply(DUAL, ASKED), _reply(DUAL, NEW))
    out = _compose(gateway, tools, "dual_coding")
    assert len(gateway.requests) == 2 and out["question"] == NEW[0] and out["quiz_retry"] == "new_question"


def test_a_second_repeat_saves_the_note_without_a_quiz_item(env):
    repo, tools, wiki_root = env
    repo.upsert_education_mastery(item_id="edu_priming1", topic=TOPIC, prompt=ASKED[0], expected_answer=ASKED[1], grade="unseen")
    again = (ASKED[0].replace("meet", "satisfy"), ASKED[1])
    gateway = SeqGateway(_reply(ENV, ASKED), _reply(ENV, again))
    composed = _compose(gateway, tools)
    assert len(gateway.requests) == 2 and composed["quiz_retry"] == "repeated"
    cid = start_or_resume_course(repo, topic_id=TOPIC, steps=["environment", "retention"])["course_id"]
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools, composed=composed)
    assert done["wiki_path"] and done["quiz_skip_reason"] == "duplicate_question"
    assert done["quiz_retry"] == "repeated"
    assert "## Quiz" not in (wiki_root / done["wiki_path"]).read_text(encoding="utf-8")
    assert [r["item_id"] for r in mastery(repo)] == ["edu_priming1"]


def test_an_unusable_second_reply_keeps_the_first_content_without_its_quiz_item(env):
    repo, tools, _ = env
    repo.upsert_education_mastery(item_id="edu_priming1", topic=TOPIC, prompt=ASKED[0], expected_answer=ASKED[1], grade="unseen")
    gateway = SeqGateway(_reply(ENV, ASKED), "not json at all")
    composed = _compose(gateway, tools)
    assert composed["ok"] and composed["practice"] == ENV["practice"] and composed["quiz_retry"] == "refused"
    cid = start_or_resume_course(repo, topic_id=TOPIC, steps=["environment", "retention"])["course_id"]
    done = complete_course_step(repo, course_id=cid, wiki_tools_or_store=tools, composed=composed)
    assert done["wiki_path"] and done["quiz_skip_reason"] == "duplicate_question" and len(mastery(repo)) == 1


def test_only_one_extra_call_per_step(env):
    _, tools, _ = env
    gateway = SeqGateway(_reply(ENV, ASKED), _reply(ENV, ASKED), _reply(ENV, NEW))
    _compose(gateway, tools)
    assert len(gateway.requests) == 2
