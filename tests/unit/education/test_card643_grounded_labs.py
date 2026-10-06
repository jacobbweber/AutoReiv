"""CARD-643: construction and application labs are built from the learner's notes via one model call
(objective, tasks, criteria, quiz) and a submission is graded against those grounded criteria. The
fixed per-topic lab (same objective, tasks, invariants, a test command for a file that does not exist)
and the made-up "baseline" submission that graded itself are gone."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.education.course import complete_course_step, start_or_resume_course
from src.application.education.grounded_steps import compose_step_content
from src.application.education.labs import grade_lab_submission
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
    "objective": "Model how a leader replicates log entries to followers with AppendEntries",
    "tasks": [
        "Write the leader's log as a list of entries with index and term",
        "Send AppendEntries with the previous index and term to each follower",
        "Advance the commit index once a majority has stored the entry",
    ],
    "criteria": [
        "Follower rejects entries when the previous index and term do not match",
        "Commit index advances only after a majority stored the entry",
    ],
    "question": "What must match before a follower appends entries?",
    "answer": "The previous index and term",
}
OLD_TEMPLATE = {
    "objective": f"Construct the foundational data model, core schemas, and boundary handling for {TOPIC}.",
    "tasks": [
        f"1. Define state representation, data structures, and core interfaces for {TOPIC}.",
        "2. Implement deterministic state transition logic and explicit edge-case boundary checks.",
        "3. Validate invariant constraints against unexpected inputs or state regressions.",
    ],
    "criteria": [
        f"Invariant 1: Structural consistency and boundary condition handling for {TOPIC}.",
        "Invariant 2: Deterministic state progression and minimal disturbance under reconfiguration.",
    ],
    "question": f"Perform construction lab for {TOPIC} with verified invariants.",
    "answer": "Structural consistency",
}
GOOD_SUBMISSION = (
    "My Raft lab: the leader keeps entries with index and term. A follower rejects AppendEntries when the previous "
    "index and term do not match, and the leader advances the commit index after a majority stored the entry."
)


@pytest.fixture
def env(tmp_path: Path):
    return make_env(tmp_path)


def _course_on(repo, step: str) -> str:
    nxt = "application" if step == "construction" else "analysis"
    return start_or_resume_course(repo, topic_id=TOPIC, steps=[step, nxt])["course_id"]


def _composed(tools, wiki_root, step="construction", reply=GROUNDED):
    add_note(wiki_root)
    return asyncio.run(compose_step_content(FakeGateway(reply), tools, TOPIC, step))


def test_template_lab_is_gone():
    import src.application.education.labs as labs_mod

    assert not hasattr(labs_mod, "build_lab_specification")
    text = Path(labs_mod.__file__).read_text(encoding="utf-8")
    for phrase in ("Structural consistency", "Deterministic state progression", "test_command", "pytest tests/unit"):
        assert phrase not in text
    course_text = (Path(labs_mod.__file__).parent / "course.py").read_text(encoding="utf-8")
    assert "Course baseline specification" not in course_text
    assert "with verified invariants" not in course_text


@pytest.mark.parametrize("step", ["construction", "application"])
def test_no_notes_and_no_submission_writes_nothing(env, step):
    repo, tools, wiki_root = env
    before = md_files(wiki_root)
    done = complete_course_step(repo, course_id=_course_on(repo, step), wiki_tools_or_store=tools)
    assert md_files(wiki_root) == before
    assert done["skip_reason"] and done["item_ids"] == [] and not done["wiki_path"]
    assert mastery(repo) == []
    assert [f for f in repo.list_semantic_facts() if step in (f.get("attribute") or "")] == []
    assert done["course"]["current_step"] != step


@pytest.mark.parametrize("reply", [OLD_TEMPLATE, {**GROUNDED, "criteria": ["Quantum flux", "Warp drive calibration"]}, "nope"])
def test_template_or_ungrounded_lab_is_refused(env, reply):
    repo, tools, wiki_root = env
    composed = _composed(tools, wiki_root, reply=reply)
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid", composed


def test_grounded_lab_grades_a_submission_against_its_criteria(env):
    repo, tools, wiki_root = env
    composed = _composed(tools, wiki_root)
    assert composed["ok"] is True, composed
    done = complete_course_step(
        repo, course_id=_course_on(repo, "construction"), wiki_tools_or_store=tools,
        lab_submission=GOOD_SUBMISSION, composed=composed,
    )
    assert done["passed"] is True and done["course"]["current_step"] == "application"
    meta, body = FrontmatterParser.parse((wiki_root / done["wiki_path"]).read_text(encoding="utf-8"))
    assert GROUNDED["objective"] in body and GROUNDED["criteria"][0] in body
    assert GOOD_SUBMISSION in body
    assert "[[00_Inbox/raft-log-replication" in body
    assert "Structural consistency" not in body and "pytest" not in body
    assert [(r["prompt"], r["expected_answer"]) for r in mastery(repo)] == [(GROUNDED["question"], GROUNDED["answer"])]


def test_grounded_lab_failing_submission_halts_the_course(env):
    repo, tools, wiki_root = env
    composed = _composed(tools, wiki_root)
    done = complete_course_step(
        repo, course_id=_course_on(repo, "construction"), wiki_tools_or_store=tools,
        lab_submission="I wrote something about databases and caching layers instead.", composed=composed,
    )
    assert done["passed"] is False and done["course"]["current_step"] == "construction"
    assert done["grade_result"]["failed_invariants"]
    facts = [f for f in repo.list_semantic_facts() if f["attribute"] == "course_step_construction_miss"]
    assert facts


def test_grounded_lab_without_submission_writes_the_assignment_and_grades_nothing(env):
    repo, tools, wiki_root = env
    composed = _composed(tools, wiki_root, step="application")
    done = complete_course_step(repo, course_id=_course_on(repo, "application"), wiki_tools_or_store=tools, composed=composed)
    meta, body = FrontmatterParser.parse((wiki_root / done["wiki_path"]).read_text(encoding="utf-8"))
    assert GROUNDED["tasks"][0] in body
    assert "Passed" not in body and done["grade_result"] == {}
    assert done["course"]["current_step"] == "analysis"


def test_submission_without_grounded_lab_is_kept_ungraded(env):
    repo, tools, wiki_root = env
    done = complete_course_step(
        repo, course_id=_course_on(repo, "construction"), wiki_tools_or_store=tools, lab_submission=GOOD_SUBMISSION
    )
    meta, body = FrontmatterParser.parse((wiki_root / done["wiki_path"]).read_text(encoding="utf-8"))
    assert GOOD_SUBMISSION in body
    assert "Passed" not in body and done["grade_result"] == {}
    assert done["item_ids"] == [] and mastery(repo) == []
    assert done["course"]["current_step"] == "application"


def test_grader_needs_criteria_and_does_not_pass_on_the_word_invariant():
    res = grade_lab_submission(topic=TOPIC, submission="Invariant invariant invariant, all invariants hold here fine.")
    assert res["passed"] is False
    res2 = grade_lab_submission(
        topic=TOPIC,
        submission="Invariant invariant invariant, all invariants hold here fine.",
        expected_invariants=["Follower rejects mismatched previous index"],
    )
    assert res2["passed"] is False


def test_lab_preview_api_never_returns_a_template():
    from src.web.app import app

    with TestClient(app) as client:
        res = client.post("/api/education/course/lab/preview", json={"topic": "Zebra quokka 643", "step": "construction"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False and body["skip_reason"] in ("no_wiki_notes", "model_unavailable")
    assert "test_command" not in body and "invariants" not in body
