"""CARD-619: later job steps see Jacob's answer to an earlier step's question."""

from __future__ import annotations

from src.application.orchestration.operator_answer import (
    format_operator_answer_note,
    question_from_assistant_reply,
)
from src.application.orchestration.working_set_context import (
    build_phase_working_set,
    format_phase_working_set_prompt,
)
from src.domain.orchestration.models import Job, JobStatus, Phase, PhaseStatus


def test_format_operator_answer_note_keeps_question_and_answer():
    note = format_operator_answer_note(
        "Which vegetables are you growing?",
        "Tomatoes, peppers and garlic; about 100 words; do not save it",
    )
    assert note.startswith("Jacob answered Which vegetables are you growing?:")
    assert "Tomatoes, peppers and garlic" in note
    assert "do not save it" in note


def test_format_operator_answer_note_negative_empty_answer():
    assert format_operator_answer_note("Q?", "") == ""
    assert format_operator_answer_note("", "only answer") == "Jacob answered: only answer"


def test_question_from_assistant_reply_takes_the_last_question():
    text = (
        "I can draft a garden plan.\n\n"
        "Which vegetables are you growing?\n\n"
        "The job is waiting for your answer. Reply here and the step continues."
    )
    assert question_from_assistant_reply(text) == "Which vegetables are you growing?"


def test_later_phase_assignment_includes_the_answer_note():
    job = Job(id="j1", session_id="s", agent_id="autoreiv", goal="write a note; ask me which vegetables first", status=JobStatus.RUNNING)
    phase = Phase(id="p2", job_id="j1", index=1, name="Execute", assigned_agent_id="developer", status=PhaseStatus.RUNNING, success_rule="write the note")
    note = format_operator_answer_note(
        "Which vegetables are you growing?",
        "Tomatoes, peppers and garlic; about 100 words; do not save it",
    )
    # prior durable notes: answer first, then a distilled Formulate note
    prior = [note, "Phase 1 (Formulate): asked which vegetables."]
    ws = build_phase_working_set(job=job, phase=phase, phase_count=2, prior_phase_notes=prior)
    prompt = format_phase_working_set_prompt(ws)
    assert "Jacob answered Which vegetables are you growing?:" in prompt
    assert "do not save it" in prompt
    assert prompt.index("Jacob answered") < prompt.index("Phase 1 (Formulate)")


def test_job_with_no_question_has_no_answer_line():
    job = Job(id="j2", session_id="s", agent_id="autoreiv", goal="summarize the wiki", status=JobStatus.RUNNING)
    phase = Phase(id="p1", job_id="j2", index=0, name="Execute", assigned_agent_id="autoreiv", status=PhaseStatus.RUNNING, success_rule="summarize")
    ws = build_phase_working_set(job=job, phase=phase, phase_count=1, prior_phase_notes=[])
    prompt = format_phase_working_set_prompt(ws)
    assert "Jacob answered" not in prompt
