"""CARD-253 Long-run context: working-set holds N->N+1 + kill/resume [REQ-LRCTX-001..004].

Prove phase-scoped working set retention across phases; kill/resume rebuilds from
ledger/memory facts; full transcript dump must NOT masquerade as memory.
Extends CARD-228/229 (+226); AGENTS.md tools stay orthogonal.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.application.orchestration.job_phase_memory import (
    JobPhaseMemoryBridge,
    prior_lines_from_job_memory,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.application.orchestration.working_set_context import (
    MEMORY_FACT_MAX_CHARS,
    TRANSCRIPT_DUMP_MARKER,
    assert_not_transcript_memory,
    build_phase_working_set,
    format_phase_working_set_prompt,
    looks_like_transcript_dump,
    rebuild_working_set_after_resume,
    sanitize_memory_fact,
)
from src.domain.orchestration.models import HandoffPacket, PhaseSpec, PhaseStatus
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

LEDGER_FACT = "ledger_token=CARD253-N0-OK"
TRANSCRIPT_DUMP = (
    "Chat transcript\n"
    "system: You are AutoReiv.\n"
    "user: do the long job\n"
    "assistant: starting phase 1 with tools...\n"
    "tool: {\"tool_call\": {\"name\": \"bash\", \"result\": \"ok\"}}\n"
    "user: continue\n"
    "assistant: more chatter that must not be memory\n"
    "user: still going\n"
    "assistant: dump dump dump\n"
) + ("X" * 800)


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
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def store(temp_db_path):
    return SQLiteStateStore(db_path=temp_db_path)


@pytest.fixture
def orch(store, data_dir):
    return JobPhaseOrchestrator(store, data_dir=data_dir)


def _packet(facts):
    return HandoffPacket(
        goal="g",
        facts=list(facts),
        constraints=[],
        done_when="done",
        budget={},
    )


def test_req_lrctx_003_transcript_dump_detected_and_rejected():
    assert looks_like_transcript_dump(TRANSCRIPT_DUMP) is True
    assert sanitize_memory_fact(TRANSCRIPT_DUMP) is None
    with pytest.raises(ValueError, match=TRANSCRIPT_DUMP_MARKER):
        assert_not_transcript_memory(TRANSCRIPT_DUMP)
    # Short ledger facts still ok.
    ok = sanitize_memory_fact(LEDGER_FACT)
    assert ok is not None
    assert LEDGER_FACT in ok
    assert len(ok) <= MEMORY_FACT_MAX_CHARS + 80


def test_req_lrctx_003_persist_rejects_transcript_as_memory(data_dir):
    bridge = JobPhaseMemoryBridge(agent_id="assistant", data_dir=data_dir)
    refs = bridge.persist_phase_facts(
        job_id="job_tx_reject",
        phase_index=0,
        phase_name="Research",
        facts=[TRANSCRIPT_DUMP, LEDGER_FACT],
    )
    # Transcript rejected; ledger kept.
    assert refs
    recalled = bridge.recall_lines(job_id="job_tx_reject")
    blob = "\n".join(recalled)
    assert LEDGER_FACT in blob
    assert "dump dump dump" not in blob
    assert "You are AutoReiv" not in blob


def test_req_lrctx_001_working_set_holds_across_n_to_nplus1(orch, store, data_dir):
    """N->N+1 working set keeps ledger facts + progressive bind; no prior body dump."""
    job = orch.create_job_with_phases(
        goal="long-run context under qwen",
        session_id="sess-lrctx-n",
        agent_id="assistant",
        phase_specs=[
            PhaseSpec(name="Research", success_rule="Gather", assigned_agent_id="assistant"),
            PhaseSpec(name="Execute", success_rule="Act", assigned_agent_id="assistant"),
        ],
    )
    phases = store.list_phases_for_job(job.id)
    p0, p1 = phases[0], phases[1]
    meta = [
        {
            "id": "skill.demo",
            "title": "demo",
            "risk": "low",
            "requires_hitl": False,
            "metadata_only": True,
            "body_loaded": False,
        }
    ]
    orch.start_phase(p0.id)
    orch.complete_phase(p0.id, _packet([LEDGER_FACT, "region=jarvis-lab"]))

    memory_facts = prior_lines_from_job_memory(
        agent_id="assistant", job_id=job.id, data_dir=data_dir
    )
    assert any(LEDGER_FACT in f for f in memory_facts)

    ws1 = build_phase_working_set(
        job=job,
        phase=p1,
        phase_count=2,
        matched_metadata=meta,
        bound_skill_id="skill.demo",
        bound_skill_body="## Overview\nPHASE1_BOUND_ONLY\n",
        all_memory_facts=memory_facts,
    )
    prompt1 = format_phase_working_set_prompt(ws1)
    assert LEDGER_FACT in prompt1 or any(LEDGER_FACT in n for n in ws1.prior_phase_notes)
    assert "PHASE1_BOUND_ONLY" in prompt1
    assert "You are AutoReiv" not in prompt1
    assert TRANSCRIPT_DUMP_MARKER not in prompt1


def test_req_lrctx_002_kill_resume_rebuilds_from_memory_not_transcript(
    orch, store, data_dir, temp_db_path
):
    """Kill/resume: N+1 working set from ledger/memory; transcript seed fails."""
    job = orch.create_job_with_phases(
        goal="survive kill resume",
        session_id="sess-lrctx-resume",
        agent_id="assistant",
        phase_specs=[
            PhaseSpec(name="Research", success_rule="notes"),
            PhaseSpec(name="Build", success_rule="built"),
        ],
    )
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    orch.complete_phase(phases[0].id, _packet([LEDGER_FACT]))
    orch.start_phase(phases[1].id)
    assert store.get_phase(phases[1].id).status == PhaseStatus.RUNNING
    job_id = job.id

    # New process (kill/resume)
    store2 = SQLiteStateStore(db_path=temp_db_path)
    orch2 = JobPhaseOrchestrator(store2, data_dir=data_dir)
    resume = orch2.resume_after_crash(job_id)
    assert resume.resumed_from_checkpoint is True

    recalled = prior_lines_from_job_memory(
        agent_id="assistant", job_id=job_id, data_dir=data_dir
    )
    assert any(LEDGER_FACT in f for f in recalled)

    phase1 = store2.get_phase(phases[1].id)
    ws = rebuild_working_set_after_resume(
        job=job,
        phase=phase1,
        phase_count=2,
        all_memory_facts=recalled,
        matched_metadata=[{"id": "skill.x", "title": "x", "metadata_only": True}],
        bound_skill_id="skill.x",
        bound_skill_body="## Bound for resumed phase\n",
        session_transcript=None,
    )
    prompt = format_phase_working_set_prompt(ws)
    assert LEDGER_FACT in prompt or any(LEDGER_FACT in n for n in ws.prior_phase_notes)
    assert "Bound for resumed phase" in prompt or ws.has_bound_skill_body

    # Feeding a full transcript must fail closed (not masquerade as memory).
    with pytest.raises(ValueError, match=TRANSCRIPT_DUMP_MARKER):
        rebuild_working_set_after_resume(
            job=job,
            phase=phase1,
            phase_count=2,
            all_memory_facts=recalled,
            session_transcript=TRANSCRIPT_DUMP,
        )


def test_req_lrctx_004_agents_md_and_no_second_context_product():
    from src.application.orchestration import working_set_context as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "CARD-253" in src or "REQ-LRCTX" in src or "transcript" in src.lower()
    assert "ticked tools" in src.lower() or "AGENTS.md" in src
    assert not hasattr(mod, "hide_chat_tools")
    # Chat resume wires rebuild helper.
    chat_src = Path("src/web/routers/chat.py").read_text(encoding="utf-8")
    assert "rebuild_working_set_after_resume" in chat_src
