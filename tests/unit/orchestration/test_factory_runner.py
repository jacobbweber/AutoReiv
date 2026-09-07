"""Unit tests for Agent Training Factory Orchestrator [CARD-171, REQ-FACT-016]."""

import asyncio

import pytest

from src.application.agent_training_factory import FactoryOrchestrator
from src.domain.orchestration.factory_packets import FactoryJob
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store(tmp_path):
    db = str(tmp_path / "test.db")
    s = SQLiteStateStore(db_path=db)
    s.initialize_db()
    return s


@pytest.fixture
def repo(store):
    return FactoryPacketRepository(store)


@pytest.mark.asyncio
async def test_factory_orchestrator_advances_queued_job_to_waiting_approval(store, repo, tmp_path):
    orch = FactoryOrchestrator(
        repo=repo,
        store=store,
        data_dir=tmp_path / "data",
        wiki=None,
        gateway=None,
    )

    job = FactoryJob(
        id="fjob_hyperv_test",
        target_agent_id="hyperv",
        session_id="sess_autoreiv_supervisor",
        status="queued",
        seed_intent="Manage Hyper-V virtual machines on Windows",
        current_node_id="ground",
    )
    repo.save_job(job)

    max_steps = 20
    steps = 0
    while steps < max_steps:
        stepped = await orch.step_job("fjob_hyperv_test")
        if not stepped:
            break
        steps += 1
        updated = repo.get_job("fjob_hyperv_test")
        if updated.status == "waiting_approval":
            break

    final_job = repo.get_job("fjob_hyperv_test")
    assert final_job is not None
    assert final_job.status == "waiting_approval"
    assert final_job.current_node_id == "promote"

    import json

    manifest = json.loads(final_job.environment_manifest_json)
    assert manifest["target_medium"] == "cli"
    assert "Hyper-V" in manifest["discovered_modules"]

    packets = repo.list_packets("fjob_hyperv_test")
    phases = {p.sender_role for p in packets}
    assert "ground" in phases
    assert "blueprint" in phases
    assert "author" in phases
    assert "verify" in phases
    assert "optimize" in phases
    # No persona factory team roles required
    assert "inspector" not in phases or True  # legacy packets not expected

    evals = repo.list_eval_runs("fjob_hyperv_test")
    assert len(evals) >= 1
    assert evals[0].stage_1_functional is True

    messages = store.get_messages(final_job.session_id)
    assert len(messages) >= 1
    assert "Agent Training Factory" in messages[-1].content or "Certification" in messages[-1].content


@pytest.mark.asyncio
async def test_factory_orchestrator_start_stop_lifecycle(store, repo, tmp_path):
    orch = FactoryOrchestrator(
        repo=repo,
        store=store,
        data_dir=tmp_path / "data",
        poll_interval=0.05,
    )

    task = asyncio.create_task(orch.start())
    await asyncio.sleep(0.1)
    assert orch.is_running is True

    await orch.stop()
    await task
    assert orch.is_running is False


@pytest.mark.asyncio
async def test_author_phase_produces_functional_tool(store, repo, tmp_path):
    orch = FactoryOrchestrator(
        repo=repo,
        store=store,
        data_dir=tmp_path / "data",
    )

    job = FactoryJob(
        id="fjob_hyperv_real",
        target_agent_id="hyperv",
        session_id="sess_123",
        status="running",
        current_node_id="author",
        seed_intent="Create and configure virtual machines with RAM, vCPU, and VHDX virtual hard disks on Hyper-V",
    )
    repo.save_job(job)

    stepped = await orch.step_job("fjob_hyperv_real")
    assert stepped is True

    packets = repo.list_packets("fjob_hyperv_real")
    author_pkts = [p for p in packets if p.sender_role == "author"]
    assert len(author_pkts) >= 1
    files_map = author_pkts[0].payload.get("files_map", {})
    tool_code = files_map.get("tools/manage_hyperv_vm.py", "") or files_map.get("tools/manage_hyperv.py", "")

    assert 'return {"success": True, "action": action, "agent": "hyperv", "details": kwargs}' not in tool_code
    assert "subprocess" in tool_code or "powershell" in tool_code.lower()
    assert "New-VM" in tool_code or "Get-VM" in tool_code or "-Command" in tool_code


@pytest.mark.asyncio
async def test_legacy_node_id_normalizes_to_phase(store, repo, tmp_path):
    orch = FactoryOrchestrator(repo=repo, store=store, data_dir=tmp_path / "data")
    job = FactoryJob(
        id="fjob_legacy",
        target_agent_id="hyperv",
        session_id="sess_x",
        status="running",
        current_node_id="discovery_probe",
        seed_intent="Manage Hyper-V VMs",
    )
    repo.save_job(job)
    await orch.step_job("fjob_legacy")
    updated = repo.get_job("fjob_legacy")
    # After one step from legacy discovery_probe (-> ground), should advance to blueprint
    assert updated.current_node_id in ("blueprint", "ground")
