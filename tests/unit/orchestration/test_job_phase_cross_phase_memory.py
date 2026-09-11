"""CARD-226 Job/Phase cross-phase memory.db recall [REQ-JPMEM-001..005].

Strict TDD: phase N writes fact to <agent>_memory.db; kill/resume; phase N+1 recalls it.
Never <agent>_storage.db.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.application.orchestration.chat_job_binding import phase_assignment_prompt
from src.application.orchestration.job_phase_memory import (
    JobPhaseMemoryBridge,
    assert_memory_db_path,
    prior_lines_from_job_memory,
)
from src.application.orchestration.job_phase_orchestrator import JobPhaseOrchestrator
from src.domain.orchestration.models import HandoffPacket, PhaseStatus
from src.infrastructure.data.resolver import (
    resolve_agent_memory_path,
    resolve_agent_storage_path,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


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


def _packet(goal: str = "g", facts=None) -> HandoffPacket:
    return HandoffPacket(
        goal=goal,
        facts=list(facts or ["ok"]),
        constraints=[],
        done_when="done",
        budget={},
    )


def test_req_jpmem_001_memory_path_never_storage(data_dir):
    """Cognitive path is *_memory.db only [REQ-JPMEM-001]."""
    mem = resolve_agent_memory_path("assistant", data_dir=data_dir)
    stor = resolve_agent_storage_path("assistant", data_dir=data_dir)
    assert mem.name.endswith("_memory.db")
    assert stor.name.endswith("_storage.db")
    assert mem != stor
    assert_memory_db_path(mem)
    with pytest.raises(ValueError):
        assert_memory_db_path(stor)


def test_req_jpmem_002_phase_complete_persists_facts_to_memory_db(orch, store, data_dir):
    """Phase complete writes reflections into agent memory.db + checkpoint refs [REQ-JPMEM-002]."""
    job = orch.create_job_with_phases(
        goal="remember across phases",
        session_id="sess_jpmem",
        agent_id="assistant",
        phase_specs=[
            {"name": "Research", "success_rule": "notes"},
            {"name": "Execute", "success_rule": "ship"},
        ],
    )
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    orch.complete_phase(
        phases[0].id,
        _packet("remember", ["secret_token_alpha=42", "region=lab-east"]),
    )

    mem_path = resolve_agent_memory_path("assistant", data_dir=data_dir)
    stor_path = resolve_agent_storage_path("assistant", data_dir=data_dir)
    assert mem_path.exists()
    assert not stor_path.exists()

    repo = AgentMemoryRepository(db_path=mem_path)
    repo.initialize_schema()
    facts = repo.list_facts_for_entity(f"job:{job.id}")
    values = " ".join(f.get("value", "") for f in facts)
    assert "secret_token_alpha=42" in values
    assert "region=lab-east" in values

    cp = orch.get_latest_checkpoint(job.id)
    assert cp is not None
    assert cp.memory_fact_ids
    assert all(isinstance(x, str) and x for x in cp.memory_fact_ids)


def test_req_jpmem_003_kill_resume_phase_n_plus_1_recalls_fact(orch, store, data_dir, temp_db_path):
    """Phase N writes; kill; new process recalls for phase N+1 [REQ-JPMEM-003]."""
    job = orch.create_job_with_phases(
        goal="cross phase recall",
        session_id="sess_resume_mem",
        agent_id="assistant",
        phase_specs=[
            {"name": "Research", "success_rule": "notes"},
            {"name": "Build", "success_rule": "built"},
        ],
    )
    phases = store.list_phases_for_job(job.id)
    orch.start_phase(phases[0].id)
    orch.complete_phase(
        phases[0].id,
        _packet("cross", ["durable_fact_gamma=ship-it"]),
    )
    # Start phase 1 then crash while RUNNING
    orch.start_phase(phases[1].id)
    assert store.get_phase(phases[1].id).status == PhaseStatus.RUNNING
    job_id = job.id

    # New process
    store2 = SQLiteStateStore(db_path=temp_db_path)
    orch2 = JobPhaseOrchestrator(store2, data_dir=data_dir)
    resume = orch2.resume_after_crash(job_id)
    assert resume.resumed_from_checkpoint is True

    recalled = prior_lines_from_job_memory(
        agent_id="assistant",
        job_id=job_id,
        data_dir=data_dir,
    )
    blob = "\\n".join(recalled)
    assert "durable_fact_gamma=ship-it" in blob

    # Phase N+1 assignment must include recalled durable fact (not empty prior theatre)
    nxt = store2.get_phase(phases[1].id)
    prompt = phase_assignment_prompt(job, nxt, 2, recalled)
    assert "durable_fact_gamma=ship-it" in prompt


def test_req_jpmem_004_bridge_uses_card116_repo_not_storage(data_dir):
    """Bridge writes through AgentMemoryRepository path only [REQ-JPMEM-004]."""
    bridge = JobPhaseMemoryBridge(agent_id="assistant", data_dir=data_dir)
    assert str(bridge.db_path).endswith("_memory.db")
    assert "_storage.db" not in str(bridge.db_path)
    refs = bridge.persist_phase_facts(
        job_id="job_demo",
        phase_index=0,
        phase_name="Research",
        facts=["prefer_memory_db=yes"],
    )
    assert refs
    stor = resolve_agent_storage_path("assistant", data_dir=data_dir)
    assert not stor.exists()
    recalled = bridge.recall_job_facts(job_id="job_demo")
    assert any("prefer_memory_db=yes" in (f.get("value") or "") for f in recalled)


def test_req_jpmem_005_checkpoint_as_dict_exposes_memory_refs(orch, store, data_dir):
    """Checkpoint / observability surface memory_fact_ids [REQ-JPMEM-005]."""
    job = orch.create_job_with_phases(
        goal="obs memory",
        session_id="sess_obs_mem",
        agent_id="assistant",
        phase_specs=[{"name": "Only", "success_rule": "ok"}],
    )
    phase = store.list_phases_for_job(job.id)[0]
    orch.start_phase(phase.id)
    orch.complete_phase(phase.id, _packet("obs", ["visible_ref=1"]))
    cp = orch.get_latest_checkpoint(job.id)
    d = cp.as_dict()
    assert "memory_fact_ids" in d
    assert d["memory_fact_ids"]
