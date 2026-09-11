"""CARD-229 Phase-scoped working-set context [REQ-WSCTX-001..006].

Each phase turn: goal + matched metadata + bound skill body only + this-phase memory facts.
Prior phases -> short durable notes (not raw tool dumps / unbound skill bodies).
Proof: phase N+1 excludes unbound bodies and prior tool dumps.
AGENTS.md: ticked tools still listed every Chat turn (orthogonal to working set).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.application.orchestration.chat_job_binding import phase_assignment_prompt
from src.application.orchestration.working_set_context import (
    DURABLE_NOTE_MAX_CHARS,
    M12_MAX_TOOL_CHARS,
    PhaseWorkingSet,
    build_phase_working_set,
    distill_durable_note,
    format_phase_working_set_prompt,
    strip_tool_dumps,
)
from src.domain.orchestration.models import PhaseSpec
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

UNBOUND_BODY_MARKER = "UNBOUND_SKILL_BODY_MARKER_MUST_NOT_LEAK_TO_NPLUS1"
TOOL_DUMP_MARKER = "RAW_TOOL_DUMP_MARKER_MUST_NOT_LEAK"
BOUND_BODY_MARKER = "BOUND_SKILL_BODY_FOR_THIS_PHASE_ONLY"


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    yield path
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.fixture
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


def _job_and_phases(store: SQLiteStateStore):
    from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator

    orch = JobPhaseOrchestrator(store)
    job = orch.create_job_with_phases(
        goal="Investigate host health and report",
        session_id="sess-wsctx",
        agent_id="assistant",
        phase_specs=[
            PhaseSpec(name="Research", success_rule="Gather signals", assigned_agent_id="assistant"),
            PhaseSpec(name="Execute", success_rule="Act on findings", assigned_agent_id="assistant"),
        ],
    )
    phases = store.list_phases_for_job(job.id)
    return orch, job, phases


def test_strip_tool_dumps_removes_tool_payloads():
    raw = (
        "Summary: host is fine.\n"
        f"[Tool Output: host_health]: {TOOL_DUMP_MARKER}\n"
        '{"tool_call": {"name": "bash", "result": "' + TOOL_DUMP_MARKER + '"}}\n'
        "Done."
    )
    cleaned = strip_tool_dumps(raw)
    assert TOOL_DUMP_MARKER not in cleaned
    assert "host is fine" in cleaned or "Done" in cleaned


def test_distill_durable_note_is_short_and_dump_free():
    raw = (
        "Phase completed successfully with findings A B C.\n"
        f"[Tool Output: shell]: {'X' * 5000}{TOOL_DUMP_MARKER}\n"
        + ("Y" * 2000)
    )
    note = distill_durable_note(phase_name="Research", phase_index=0, raw_output=raw)
    assert TOOL_DUMP_MARKER not in note
    assert len(note) <= DURABLE_NOTE_MAX_CHARS + 80  # allow prefix
    assert "Research" in note
    assert M12_MAX_TOOL_CHARS == 8000  # aligned with ContextCompactor default


def test_phase_nplus1_excludes_unbound_skill_body_and_prior_tool_dumps(store):
    orch, job, phases = _job_and_phases(store)
    p0, p1 = phases[0], phases[1]

    matched_metadata = [
        {
            "id": "skill.platform-health",
            "title": "platform-health",
            "risk": "medium",
            "requires_hitl": False,
            "metadata_only": True,
            "body_loaded": False,
        },
        {
            "id": "skill.other-runbook",
            "title": "other-runbook",
            "risk": "low",
            "requires_hitl": False,
            "metadata_only": True,
            "body_loaded": False,
        },
    ]

    # Phase 0 working set may include its own bound body.
    ws0 = build_phase_working_set(
        job=job,
        phase=p0,
        phase_count=2,
        matched_metadata=matched_metadata,
        bound_skill_id="skill.platform-health",
        bound_skill_body=f"## Overview\n{BOUND_BODY_MARKER}\nUse host_health.\n",
        this_phase_memory_facts=["phase_0_research_0: cpu ok"],
        prior_phase_notes=[],
    )
    prompt0 = format_phase_working_set_prompt(ws0)
    assert BOUND_BODY_MARKER in prompt0
    assert "Investigate host health" in prompt0
    assert "cpu ok" in prompt0
    assert UNBOUND_BODY_MARKER not in prompt0

    # After phase 0: durable note only (tool dump stripped); unbound body never enters notes.
    prior_raw = (
        f"Findings: disk 12% free.\n[Tool Output: df]: {TOOL_DUMP_MARKER}\n"
        f"Bound skill skill.platform-health (platform-health):\n{UNBOUND_BODY_MARKER}\n"
        + ("Z" * 3000)
    )
    note0 = distill_durable_note(phase_name=p0.name, phase_index=p0.index, raw_output=prior_raw)

    # Phase 1 binds a *different* skill; must not see phase-0 body or tool dump.
    ws1 = build_phase_working_set(
        job=job,
        phase=p1,
        phase_count=2,
        matched_metadata=matched_metadata,
        bound_skill_id="skill.other-runbook",
        bound_skill_body="## Overview\nPHASE1_BOUND_ONLY\n",
        this_phase_memory_facts=["phase_1_execute_0: act now"],
        prior_phase_notes=[note0],
    )
    prompt1 = format_phase_working_set_prompt(ws1)

    assert "PHASE1_BOUND_ONLY" in prompt1
    assert UNBOUND_BODY_MARKER not in prompt1
    assert BOUND_BODY_MARKER not in prompt1  # prior bound body must not leak
    assert TOOL_DUMP_MARKER not in prompt1
    assert "Research" in prompt1 or "disk" in prompt1.lower() or "Phase 1" in prompt1
    # Matched metadata present without bodies
    assert "skill.platform-health" in prompt1
    assert "metadata" in prompt1.lower() or "Matched capabilities" in prompt1
    assert "FULL_RUNBOOK" not in prompt1

    # Compatibility: phase_assignment_prompt still works but standing path should prefer working set.
    legacy = phase_assignment_prompt(job, p1, 2, [note0])
    assert TOOL_DUMP_MARKER not in legacy


def test_working_set_fields_cover_done_bar(store):
    _, job, phases = _job_and_phases(store)
    ws = build_phase_working_set(
        job=job,
        phase=phases[0],
        phase_count=2,
        matched_metadata=[{"id": "skill.x", "title": "x", "metadata_only": True}],
        bound_skill_id="skill.x",
        bound_skill_body="BODY",
        this_phase_memory_facts=["fact-a"],
        prior_phase_notes=["Phase 0 note"],
    )
    assert isinstance(ws, PhaseWorkingSet)
    assert ws.phase_goal
    assert ws.matched_metadata
    assert ws.bound_skill_body == "BODY"
    assert ws.this_phase_memory_facts == ["fact-a"]
    assert ws.prior_phase_notes == ["Phase 0 note"]


def test_agents_md_tools_invariant_not_owned_by_working_set():
    """Working-set formatter must not claim to replace Chat ticked tool schemas."""
    from src.application.orchestration import working_set_context as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "ticked tools" in src.lower() or "AGENTS.md" in src
    # No API that strips Chat tools from working set module.
    assert not hasattr(mod, "hide_chat_tools")
    assert not hasattr(mod, "omit_ticked_tools")
