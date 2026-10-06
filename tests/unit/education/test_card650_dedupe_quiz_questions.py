"""CARD-650: every grounded course step asked the model for one quiz question from the same notes
without seeing the questions already written, so one course filled the ledger with near-identical
items (the live run wrote five variants of "What condition must a follower's log meet ..."). Now the
model is shown the questions already in the ledger, and a step whose question still nearly repeats
an existing item keeps its note but writes no quiz item."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.education.grounded import is_near_duplicate
from src.application.education.grounded_steps import compose_course_step
from src.domain.wiki.frontmatter import FrontmatterParser
from tests.unit.education._grounded_fixtures import (
    GROUNDED_PRIMING,
    TOPIC,
    FakeGateway,
    add_note,
    make_env,
    mastery,
)

# Questions and answers the live Spark run wrote for one course (CARD-642 live check).
LIVE = [
    ("What condition must a follower's log satisfy for it to accept an AppendEntries message?",
     "The follower's log must have an entry at the previous index with the same term as the previous_log_term in the message."),
    ("What condition must a follower's log meet for it to accept an AppendEntries message from the leader?",
     "The follower's log must have an entry at the previous index with the same term as specified in the message."),
    ("What must a follower's log contain at the previous index for it to accept new entries?",
     "an entry at the previous index with the same term"),
    ("What must a follower check before accepting an AppendEntries message?",
     "Its log has an entry at the previous index with the same term"),
]
DISTINCT = ("How do followers learn the commit index?", "From the next AppendEntries heartbeat")
ENV = {
    "ok": True, "step": "environment", "skip_reason": None,
    "practice": ["Trace one client command to a majority of followers", "Watch the commit index advance"],
    "sources": [{"path": "00_Inbox/raft-log-replication.md", "title": "Raft log replication"}],
}


@pytest.fixture
def env(tmp_path: Path):
    return make_env(tmp_path)


def _seed(repo, q, a, item_id="course_raft_log_replication_dual_coding", topic=TOPIC):
    repo.upsert_education_mastery(item_id=item_id, topic=topic, prompt=q, expected_answer=a, grade="unseen")


def _course(repo, step="environment"):
    return start_or_resume_course(repo, topic_id=TOPIC, steps=[step, "retention"])["course_id"]


@pytest.mark.parametrize("i", [1, 2, 3])
def test_live_variants_are_near_duplicates(i):
    assert is_near_duplicate(LIVE[0][0], LIVE[0][1], LIVE[i][0], LIVE[i][1])


def test_a_different_question_is_not_a_duplicate():
    assert not is_near_duplicate(LIVE[0][0], LIVE[0][1], *DISTINCT)
    assert not is_near_duplicate(GROUNDED_PRIMING["question"], GROUNDED_PRIMING["answer"], *DISTINCT)


def test_duplicate_question_keeps_the_note_but_writes_no_quiz_item(env):
    repo, tools, wiki_root = env
    _seed(repo, *LIVE[0])
    done = complete_course_step(
        repo, course_id=_course(repo), wiki_tools_or_store=tools,
        composed={**ENV, "question": LIVE[1][0], "answer": LIVE[1][1]},
    )
    _meta, body = FrontmatterParser.parse((wiki_root / done["wiki_path"]).read_text(encoding="utf-8"))
    assert "Trace one client command" in body
    assert "## Quiz" not in body and LIVE[1][0] not in body
    assert done["item_ids"] == [] and done["quiz_skip_reason"] == "duplicate_question"
    assert [r["prompt"] for r in mastery(repo)] == [LIVE[0][0]]
    assert done["course"]["current_step"] == "retention"


def test_distinct_question_is_written(env):
    repo, tools, wiki_root = env
    _seed(repo, *LIVE[0])
    done = complete_course_step(
        repo, course_id=_course(repo), wiki_tools_or_store=tools, composed={**ENV, "question": DISTINCT[0], "answer": DISTINCT[1]},
    )
    assert sorted(r["prompt"] for r in mastery(repo)) == sorted([LIVE[0][0], DISTINCT[0]])
    assert done["quiz_skip_reason"] is None


def test_rerunning_a_step_replaces_its_own_item(env):
    repo, tools, wiki_root = env
    _seed(repo, *LIVE[0], item_id="course_raft_log_replication_environment")
    done = complete_course_step(
        repo, course_id=_course(repo), wiki_tools_or_store=tools, composed={**ENV, "question": LIVE[1][0], "answer": LIVE[1][1]},
    )
    assert [r["prompt"] for r in mastery(repo)] == [LIVE[1][0]]
    assert done["quiz_skip_reason"] is None


def test_duplicate_of_an_item_on_another_topic_is_skipped_too(env):
    repo, tools, wiki_root = env
    _seed(repo, *LIVE[0], item_id="raft_consensus_q1", topic="Raft consensus")
    done = complete_course_step(
        repo, course_id=_course(repo), wiki_tools_or_store=tools, composed={**ENV, "question": LIVE[3][0], "answer": LIVE[3][1]},
    )
    assert done["quiz_skip_reason"] == "duplicate_question"
    assert len(mastery(repo)) == 1


def test_priming_duplicate_question_writes_the_note_without_a_quiz_item(env):
    repo, tools, wiki_root = env
    _seed(repo, GROUNDED_PRIMING["question"].replace("When does", "At what point does"), GROUNDED_PRIMING["answer"])
    done = complete_course_step(repo, course_id=_course(repo, "priming"), wiki_tools_or_store=tools, composed=GROUNDED_PRIMING)
    assert done["wiki_path"]
    body = (wiki_root / done["wiki_path"]).read_text(encoding="utf-8")
    assert "## Key ideas" in body and "## Quiz" not in body
    assert len(mastery(repo)) == 1 and done["quiz_skip_reason"] == "duplicate_question"


def test_model_is_shown_the_questions_already_asked(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    gateway = FakeGateway({**ENV, "question": DISTINCT[0], "answer": DISTINCT[1]})
    asyncio.run(compose_course_step(gateway, tools, TOPIC, "environment", avoid_questions=[LIVE[0][0], LIVE[2][0]]))
    user = gateway.requests[0].messages[-1].content
    assert LIVE[0][0] in user and LIVE[2][0] in user
    assert "different" in user.lower()


def test_result_says_which_question_was_dropped_and_what_it_repeats(env):
    # Follow-up from the course-filler-3 live check: the dropped question was invisible, so a reviewer
    # could not tell a real repeat from an over-eager match.
    repo, tools, wiki_root = env
    _seed(repo, *LIVE[0])
    done = complete_course_step(
        repo, course_id=_course(repo), wiki_tools_or_store=tools,
        composed={**ENV, "question": LIVE[1][0], "answer": LIVE[1][1]},
    )
    assert done["quiz_duplicate"] == {"question": LIVE[1][0], "duplicate_of": LIVE[0][0]}
