"""CARD-655: in the CARD-654 live check Spark wrote an application criterion that invented a fact
the note never states ("The follower responds with an AppendEntries response indicating success").
The criterion named note terms (follower, AppendEntries) so it passed the old list check, and the
grader then required "responds, indicating, success". The journey submission covered everything the
note says and still failed. Criteria that aren't supported by the notes are now dropped when the
lab is written; a reply left with fewer than two grounded criteria is refused."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.education.grounded_steps import compose_step_content
from src.application.education.labs import criterion_in_notes, grade_lab_submission
from src.domain.wiki.frontmatter import FrontmatterParser
from tests.unit.education._grounded_fixtures import TOPIC, FakeGateway, USER_NOTE, add_note, make_env

# Live Spark criterion that failed a correct submission (CARD-654 live check, 2026-10-06 11:40 ET).
LIVE_INVENTED = "The follower responds with an AppendEntries response indicating success."
LIVE_GROUNDED = [
    "The follower's log contains an entry at the previous index with the same term.",
    "The new entry's term matches the leader's current term.",
    "The new entry's index follows the previous index in the follower's log.",
]
JOURNEY_SUBMISSION = (
    "My Raft log replication lab: the leader appends each client command to its log with the current term and sends "
    "AppendEntries with the previous log index and term to every follower. A follower rejects entries when its log has "
    "no entry at the previous index with the same term, and the leader retries with an earlier index. When a majority "
    "of servers stored the entry, the leader advances the commit index and applies it to its state machine; followers "
    "learn the commit index from the next heartbeat and apply entries in log order."
)
LAB = {
    "objective": "Verify that a follower's log meets the term and index condition before accepting new entries.",
    "tasks": [
        "Start with the leader's log containing a new entry at an index with the current term.",
        "Send an AppendEntries message to a follower with the previous index and term.",
        "Check that the follower's log has an entry at the previous index with the same term; if not, reject.",
        "If the condition is met, the follower accepts the new entry.",
    ],
    "question": "What must a follower's log contain at the previous index?",
    "answer": "An entry with the same term",
}


@pytest.fixture
def env(tmp_path: Path):
    return make_env(tmp_path)


def _compose(tools, wiki_root, criteria, step="application"):
    add_note(wiki_root)
    reply = {**LAB, "criteria": criteria}
    return asyncio.run(compose_step_content(FakeGateway(reply), tools, TOPIC, step))


def test_the_live_invented_criterion_is_not_supported_by_the_note():
    from src.application.education.grounded import source_vocab

    vocab = source_vocab([{"title": TOPIC, "text": USER_NOTE, "path": "n.md"}])
    assert criterion_in_notes(LIVE_INVENTED, vocab) is False
    assert all(criterion_in_notes(c, vocab) for c in LIVE_GROUNDED)


def test_an_invented_criterion_is_dropped_and_the_rest_are_kept(env):
    _, tools, wiki_root = env
    composed = _compose(tools, wiki_root, LIVE_GROUNDED + [LIVE_INVENTED])
    assert composed["ok"] is True, composed
    assert LIVE_INVENTED not in composed["criteria"]
    assert composed["criteria"] == LIVE_GROUNDED


def test_a_reply_left_with_fewer_than_two_grounded_criteria_is_refused(env):
    _, tools, wiki_root = env
    composed = _compose(tools, wiki_root, [LIVE_GROUNDED[0], LIVE_INVENTED])
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid"
    assert "criteria" in (composed.get("skip_detail") or composed.get("detail") or "criteria")


def test_the_journey_submission_passes_once_the_invented_criterion_is_gone(env):
    repo, tools, wiki_root = env
    composed = _compose(tools, wiki_root, LIVE_GROUNDED + [LIVE_INVENTED])
    assert composed["ok"] is True and LIVE_INVENTED not in composed["criteria"]
    # Against the raw Spark criteria (including the invented one) the journey submission fails.
    raw = grade_lab_submission(topic=TOPIC, step="application", submission=JOURNEY_SUBMISSION,
                               expected_invariants=LIVE_GROUNDED + [LIVE_INVENTED])
    assert raw["passed"] is False and LIVE_INVENTED in raw["failed_invariants"]
    cid = start_or_resume_course(repo, topic_id=TOPIC, steps=["application", "analysis"])["course_id"]
    done = complete_course_step(
        repo, course_id=cid, wiki_tools_or_store=tools, lab_submission=JOURNEY_SUBMISSION, composed=composed,
    )
    assert done["passed"] is True and done["graded"] is True
    body = (wiki_root / done["wiki_path"]).read_text(encoding="utf-8")
    assert LIVE_INVENTED not in body
    assert LIVE_GROUNDED[0] in body


def test_a_submission_that_skips_a_note_fact_a_criterion_names_still_fails(env):
    # Keep grader generous but not trivial: dropping invented criteria must not make labs free.
    thin = (
        "I wrote about Raft. The leader and the followers talk. AppendEntries is used somehow. "
        "There is a commit index somewhere."
    )
    res = grade_lab_submission(topic=TOPIC, step="application", submission=thin, expected_invariants=LIVE_GROUNDED)
    assert res["passed"] is False
