"""
Dogfooding the 8-Stage Agent Training Factory pipeline for the Homelab Fleet [CARD-198, CARD-197, REQ-FLEET-007].
"""

import os
import tempfile

import pytest

from src.application.agent_training_factory import FactoryOrchestrator
from src.domain.orchestration.factory_packets import FactoryJob
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def clean_store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
        path = handle.name
    store = SQLiteStateStore(db_path=path)
    store.initialize_db()
    yield store, FactoryPacketRepository(store)
    for suffix in ("", "-wal", "-shm"):
        candidate = path + suffix
        if os.path.exists(candidate):
            try:
                os.remove(candidate)
            except OSError:
                pass


@pytest.mark.asyncio
async def test_dogfood_training_homelab_fleet_engineer(clean_store, tmp_path):
    """
    Dogfood: Exercise AutoReiv's 8-stage Training Factory pipeline on homelab-engineer.
    Verifies CARD-197 refinements:
    - Phase duration tracking
    - Matt Pocock 5-section SKILL.md structure
    - HITL deliverable inspection at waiting_approval gate
    - OpenTofu / Hyper-V tool synthesis envelope
    """
    store, repo = clean_store
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    orch = FactoryOrchestrator(
        repo=repo,
        store=store,
        data_dir=data_dir,
    )

    job_id = "fjob_homelab_engineer_dogfood"
    job = FactoryJob(
        id=job_id,
        target_agent_id="homelab-engineer",
        session_id="sess_homelab_dogfood",
        status="queued",
        current_node_id="ground",
        seed_intent="Author declarative OpenTofu configurations and manage Hyper-V virtual machine lifecycle",
    )
    repo.save_job(job)

    # Step through pipeline until waiting_approval or step limit
    max_steps = 25
    steps = 0
    while steps < max_steps:
        stepped = await orch.step_job(job_id)
        if not stepped:
            break
        steps += 1
        updated = repo.get_job(job_id)
        if updated.status == "waiting_approval":
            break

    final_job = repo.get_job(job_id)
    assert final_job is not None
    assert final_job.status == "waiting_approval"
    assert final_job.current_node_id == "promote"

    # Verify packets generated across the 8-stage pipeline
    packets = repo.list_packets(job_id)
    assert len(packets) >= 5

    phases_seen = {p.sender_role for p in packets}
    assert "ground" in phases_seen
    assert "blueprint" in phases_seen
    assert "author" in phases_seen

    # Verify duration tracking on packets (CARD-197 refinement)
    for p in packets:
        # Each phase packet should have duration_ms tracked in payload or packet
        payload = p.payload or {}
        assert "duration_ms" in payload or "phase_duration_ms" in payload or hasattr(p, "duration_ms")

    # Verify author phase produced Matt Pocock compliant runbook
    author_packets = [p for p in packets if p.sender_role == "author"]
    assert len(author_packets) >= 1
    files_map = author_packets[0].payload.get("files_map", {})
    assert len(files_map) > 0

    # Locate generated SKILL.md
    skill_files = [k for k in files_map.keys() if k.endswith("SKILL.md")]
    assert len(skill_files) >= 1

    for s_path in skill_files:
        skill_content = files_map[s_path]
        assert "## Overview" in skill_content
        assert "## Tools" in skill_content
        assert "## Order" in skill_content
        assert "## Pitfalls" in skill_content
        assert "## Done-when" in skill_content

    # Verify generated tools follow functional envelope (not empty stubs)
    tool_files = [k for k in files_map.keys() if k.startswith("tools/") and k.endswith(".py")]
    for t_path in tool_files:
        tool_code = files_map[t_path]
        assert "def " in tool_code
        assert "return " in tool_code
        # Must not be an empty fake stub
        assert 'return {"success": True, "action": action, "agent": "hyperv", "details": kwargs}' not in tool_code
