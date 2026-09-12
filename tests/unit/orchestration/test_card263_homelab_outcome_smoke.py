"""CARD-263: Homelab-class outcome smoke bars (Wiki + repo + same job_id + DONE)."""
from __future__ import annotations

from src.application.orchestration.homelab_outcome_smoke import (
    evaluate_fixture_pack,
    evaluate_homelab_outcome,
)


JOB = "job_aabbccddeeff"


def _pass_events():
    return [
        {"event": "job_created", "data": {"job_id": JOB}},
        {"event": "plan_formulated", "data": {"job_id": JOB, "phase": "Formulate"}},
        {"event": "phase_start", "data": {"job_id": JOB, "phase": "Formulate"}},
        {"event": "phase_start", "data": {"job_id": JOB, "phase": "Execute"}},
        {
            "event": "tool_output",
            "data": {
                "name": "repo_file_list",
                "success": True,
                "path": ".",
                "entries": ["AGENTS.md"],
            },
        },
        {
            "event": "tool_output",
            "data": {
                "name": "repo_file_read",
                "success": True,
                "path": "AGENTS.md",
                "content": "Cards stay Ready until build. Three Beats.",
            },
        },
        {
            "event": "tool_output",
            "data": {
                "name": "wiki_note_create",
                "success": True,
                "path": "00_Inbox/agents-card-rule.md",
            },
        },
        {
            "event": "tool_output",
            "data": {
                "name": "wiki_note_read",
                "success": True,
                "path": "00_Inbox/agents-card-rule.md",
            },
        },
        {"event": "turn_done", "data": {"content": "Wrote 00_Inbox/agents-card-rule.md from AGENTS.md."}},
    ]


def _journey_done():
    return {
        "ok": True,
        "job_id": JOB,
        "job": {"id": JOB, "status": "done"},
        "phases": [
            {"name": "Formulate", "status": "done"},
            {"name": "Execute", "status": "done"},
        ],
    }


def test_pass_wiki_plus_repo_same_job_done():
    result = evaluate_homelab_outcome(
        events=_pass_events(),
        job={"id": JOB, "status": "done"},
        journey=_journey_done(),
        turn_text="Wrote 00_Inbox/agents-card-rule.md from AGENTS.md card rule.",
        expected_job_id=JOB,
    )
    assert result["ok"] is True
    assert result["same_job_id"] is True
    assert result["wiki_provenanced"] is True
    assert result["repo_provenanced"] is True
    assert result["formulate_then_execute"] is True
    assert result["journey_done"] is True
    assert result["observe_job_id"] == JOB
    assert result["invented_paths"] == []


def test_fail_wiki_only_no_repo():
    events = [
        e
        for e in _pass_events()
        if "repo_file" not in str(e.get("data", {}).get("name", ""))
    ]
    result = evaluate_homelab_outcome(
        events=events,
        job={"id": JOB, "status": "done"},
        journey=_journey_done(),
        turn_text="Wrote 00_Inbox/agents-card-rule.md",
        expected_job_id=JOB,
    )
    assert result["ok"] is False
    assert result["repo_provenanced"] is False


def test_fail_repo_only_no_wiki():
    events = [
        e
        for e in _pass_events()
        if "wiki_note" not in str(e.get("data", {}).get("name", ""))
    ]
    result = evaluate_homelab_outcome(
        events=events,
        job={"id": JOB, "status": "done"},
        journey=_journey_done(),
        turn_text="AGENTS.md says cards stay Ready.",
        expected_job_id=JOB,
    )
    assert result["ok"] is False
    assert result["wiki_provenanced"] is False


def test_fail_observe_different_job_id():
    journey = dict(_journey_done())
    journey["job_id"] = "job_deadbeef0001"
    journey["job"] = {"id": "job_deadbeef0001", "status": "done"}
    result = evaluate_homelab_outcome(
        events=_pass_events(),
        job={"id": JOB, "status": "done"},
        journey=journey,
        turn_text="Wrote 00_Inbox/agents-card-rule.md from AGENTS.md.",
        expected_job_id=JOB,
    )
    assert result["ok"] is False
    assert result["same_job_id"] is False


def test_fail_invented_wiki_path():
    result = evaluate_homelab_outcome(
        events=_pass_events(),
        job={"id": JOB, "status": "done"},
        journey=_journey_done(),
        turn_text="Also see 00_Inbox/totally-fake-okta.md for the card rule.",
        expected_job_id=JOB,
    )
    assert result["ok"] is False
    assert result["invented_paths"]
    assert any("totally-fake-okta.md" in p for p in result["invented_paths"])


def test_fail_journey_not_done():
    journey = {
        "ok": True,
        "job_id": JOB,
        "job": {"id": JOB, "status": "running"},
        "phases": [
            {"name": "Formulate", "status": "done"},
            {"name": "Execute", "status": "running"},
        ],
    }
    result = evaluate_homelab_outcome(
        events=_pass_events(),
        job={"id": JOB, "status": "running"},
        journey=journey,
        turn_text="Working on 00_Inbox/agents-card-rule.md from AGENTS.md.",
        expected_job_id=JOB,
    )
    assert result["ok"] is False
    assert result["journey_done"] is False


def test_fail_missing_formulate_execute():
    events = [e for e in _pass_events() if e.get("event") not in {"plan_formulated", "phase_start"}]
    result = evaluate_homelab_outcome(
        events=events,
        job={"id": JOB, "status": "done"},
        journey={"ok": True, "job_id": JOB, "job": {"id": JOB, "status": "done"}, "phases": []},
        turn_text="Wrote 00_Inbox/agents-card-rule.md from AGENTS.md.",
        expected_job_id=JOB,
    )
    assert result["ok"] is False
    assert result["formulate_then_execute"] is False


def test_fixture_pack_red_and_green():
    pack = evaluate_fixture_pack(
        [
            {
                "id": "fx_pass",
                "expect_ok": True,
                "events": _pass_events(),
                "job": {"id": JOB, "status": "done"},
                "journey": _journey_done(),
                "turn_text": "Wrote 00_Inbox/agents-card-rule.md from AGENTS.md.",
                "expected_job_id": JOB,
            },
            {
                "id": "fx_no_repo",
                "expect_ok": False,
                "events": [e for e in _pass_events() if "repo_file" not in str(e)],
                "job": {"id": JOB, "status": "done"},
                "journey": _journey_done(),
                "turn_text": "Wrote 00_Inbox/agents-card-rule.md",
                "expected_job_id": JOB,
            },
        ]
    )
    assert pack["ok"] is True
