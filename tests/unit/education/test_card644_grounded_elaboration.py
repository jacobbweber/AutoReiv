"""CARD-644: the elaboration step writes nothing without a learner explanation. With one, the note
holds the explanation, and follow-up questions and a quiz item are added only when the model's reply
is grounded in what the learner wrote (and their notes). The placeholder note, the template probes,
analogy and edge-case sections and the topic-name answer are gone."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.application.education.course import complete_course_step, start_or_resume_course
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

EXPLANATION = (
    "The leader appends a command to its log and sends AppendEntries to the followers. A follower only "
    "accepts when its previous index and term match, and the entry commits once a majority stored it."
)
GROUNDED = {
    "probes": [
        "What does a follower do when its previous index and term do not match?",
        "Why does the leader wait for a majority before it commits an entry?",
    ],
    "question": "When does an entry commit?",
    "answer": "Once a majority of followers stored it",
}
OFF_EXPLANATION = {**GROUNDED, "answer": "Quantum flux capacitors calibrate the warp drive"}
OLD_TEMPLATE = {
    "probes": [f"What is an intuitive real-world analogy for {TOPIC}, and what is a non-example?"],
    "question": f"How would you summarize the core invariant of {TOPIC}?",
    "answer": f"{TOPIC} guarantees correct state progression through disciplined coordination.",
}


@pytest.fixture
def env(tmp_path: Path):
    return make_env(tmp_path)


def _course_on_elaboration(repo) -> str:
    return start_or_resume_course(repo, topic_id=TOPIC, steps=["elaboration", "construction"])["course_id"]


def test_template_text_is_gone():
    import src.application.education.course as course_mod
    import src.application.education.elaboration as elab_mod

    for mod in (course_mod, elab_mod):
        text = Path(mod.__file__).read_text(encoding="utf-8")
        assert "Learner self-explanation to be added" not in text
        assert "guarantees correct state progression" not in text
        assert "Intuitive mental model illustrating" not in text
        assert "explain the core mechanism of" not in text


def test_no_explanation_writes_nothing(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    before = md_files(wiki_root)
    done = complete_course_step(repo, course_id=_course_on_elaboration(repo), wiki_tools_or_store=tools)
    assert md_files(wiki_root) == before
    assert done["skip_reason"] == "no_learner_explanation"
    assert done["item_ids"] == [] and not done["wiki_path"]
    assert mastery(repo) == []
    assert [f for f in repo.list_semantic_facts() if "elaboration" in (f.get("attribute") or "")] == []
    assert done["course"]["current_step"] == "construction"


def test_compose_needs_an_explanation(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    composed = asyncio.run(compose_step_content(FakeGateway(GROUNDED), tools, TOPIC, "elaboration"))
    assert composed["ok"] is False and composed["skip_reason"] == "no_learner_explanation"


def test_grounded_reply_adds_probes_and_a_quiz_item_from_the_explanation(env):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    gw = FakeGateway(GROUNDED)
    composed = asyncio.run(compose_step_content(gw, tools, TOPIC, "elaboration", learner_text=EXPLANATION))
    assert composed["ok"] is True, composed
    assert EXPLANATION in gw.requests[0].messages[1].content

    done = complete_course_step(
        repo, course_id=_course_on_elaboration(repo), wiki_tools_or_store=tools,
        learner_explanation=EXPLANATION, composed=composed,
    )
    meta, body = FrontmatterParser.parse((wiki_root / done["wiki_path"]).read_text(encoding="utf-8"))
    assert EXPLANATION in body
    assert "Why does the leader wait for a majority" in body
    assert "analogy" not in body.lower() and "Edge Cases" not in body
    rows = mastery(repo)
    assert [(r["prompt"], r["expected_answer"]) for r in rows] == [(GROUNDED["question"], GROUNDED["answer"])]


def test_explanation_without_notes_can_still_ground_in_the_explanation(env):
    repo, tools, wiki_root = env
    composed = asyncio.run(
        compose_step_content(FakeGateway(GROUNDED), tools, TOPIC, "elaboration", learner_text=EXPLANATION)
    )
    assert composed["ok"] is True, composed
    assert composed["sources"] == []


@pytest.mark.parametrize("reply", [OFF_EXPLANATION, OLD_TEMPLATE, "no json here"])
def test_answer_not_from_the_explanation_or_template_is_refused(env, reply):
    repo, tools, wiki_root = env
    add_note(wiki_root)
    composed = asyncio.run(
        compose_step_content(FakeGateway(reply), tools, TOPIC, "elaboration", learner_text=EXPLANATION)
    )
    assert composed["ok"] is False and composed["skip_reason"] == "model_output_invalid", composed


def test_explanation_without_grounded_reply_keeps_only_the_explanation(env):
    repo, tools, wiki_root = env
    done = complete_course_step(
        repo, course_id=_course_on_elaboration(repo), wiki_tools_or_store=tools, learner_explanation=EXPLANATION
    )
    meta, body = FrontmatterParser.parse((wiki_root / done["wiki_path"]).read_text(encoding="utf-8"))
    assert EXPLANATION in body
    assert "## Quiz" not in body and "Q:" not in body
    assert done["item_ids"] == [] and mastery(repo) == []
    assert done["course"]["current_step"] == "construction"


def test_preview_api_has_no_template_probes():
    from src.web.app import app

    with TestClient(app) as client:
        res = client.post("/api/education/course/elaboration/preview", json={"topic": "Zebra quokka 644"})
    assert res.status_code == 200
    body = res.json()
    assert body["probing_questions"] == []
    assert body["skip_reason"] == "no_learner_explanation"
