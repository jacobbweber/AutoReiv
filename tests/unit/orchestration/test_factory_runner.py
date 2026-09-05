"""
Unit tests for Autonomous Factory Runner [REQ-FACT-016, REQ-FACT-017, REQ-FACT-018].
"""

import asyncio

import pytest

from src.application.orchestration.capability_graph import CapabilityGraphEngine
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
async def test_factory_runner_advances_queued_job_to_waiting_approval(store, repo, tmp_path):
    from src.application.orchestration.factory_runner import FactoryRunner

    engine = CapabilityGraphEngine(repo)
    runner = FactoryRunner(
        repo=repo,
        engine=engine,
        store=store,
        data_dir=tmp_path / "data",
    )

    # 1. Create a queued job
    job = FactoryJob(
        id="fjob_hyperv_test",
        target_agent_id="hyperv",
        session_id="sess_autoreiv_supervisor",
        status="queued",
        seed_intent="Manage Hyper-V virtual machines on Windows",
        current_node_id="discovery_probe",
    )
    repo.save_job(job)

    # 2. Run runner step-by-step or full tick loop
    max_steps = 15
    steps = 0
    while steps < max_steps:
        stepped = await runner.step_job("fjob_hyperv_test")
        if not stepped:
            break
        steps += 1
        updated = repo.get_job("fjob_hyperv_test")
        if updated.status == "waiting_approval":
            break

    # 3. Verify final state is waiting_approval at hitl_deploy_gate_node
    final_job = repo.get_job("fjob_hyperv_test")
    assert final_job is not None
    assert final_job.status == "waiting_approval"
    assert final_job.current_node_id == "hitl_deploy_gate_node"

    # Verify environment manifest grounded on agent purpose [REQ-FACT-032]
    import json

    manifest = json.loads(final_job.environment_manifest_json)
    assert manifest["target_medium"] == "cli"
    assert "Hyper-V" in manifest["discovered_modules"]
    assert manifest["namespace_isolation"]["cmdlet_prefix"] == "Hyper-V\\"

    # 4. Verify structured packets exist for all roles
    packets = repo.list_packets("fjob_hyperv_test")
    roles = {p.sender_role for p in packets}
    assert "inspector" in roles
    assert "conductor" in roles
    assert "coder" in roles
    assert "sandbox_runner" in roles
    assert "critic" in roles

    # 5. Verify eval runs exist
    evals = repo.list_eval_runs("fjob_hyperv_test")
    assert len(evals) >= 1
    assert evals[0].stage_1_functional is True
    assert evals[0].stage_2_safety is True
    assert evals[0].stage_3_idempotency is True
    assert evals[0].stage_4_critic is True

    # 6. Verify AutoReiv platform session received the certification message [REQ-FACT-018]
    messages = store.get_messages(final_job.session_id)
    assert len(messages) >= 1
    assert "Autonomous Lab Certification Complete" in messages[-1].content
    assert "hyperv" in messages[-1].content.lower()


@pytest.mark.asyncio
async def test_factory_runner_start_stop_lifecycle(store, repo, tmp_path):
    from src.application.orchestration.factory_runner import FactoryRunner

    engine = CapabilityGraphEngine(repo)
    runner = FactoryRunner(
        repo=repo,
        engine=engine,
        store=store,
        data_dir=tmp_path / "data",
        poll_interval=0.05,
    )

    task = asyncio.create_task(runner.start())
    await asyncio.sleep(0.1)
    assert runner.is_running is True

    await runner.stop()
    await task
    assert runner.is_running is False


@pytest.mark.asyncio
async def test_coder_authors_functional_powershell_tool_for_system_agents(store, repo, tmp_path):
    from src.application.orchestration.factory_runner import FactoryRunner

    engine = CapabilityGraphEngine(repo)
    runner = FactoryRunner(
        repo=repo,
        engine=engine,
        store=store,
        data_dir=tmp_path / "data",
    )

    job = FactoryJob(
        id="fjob_hyperv_real",
        target_agent_id="hyperv",
        session_id="sess_123",
        status="running",
        current_node_id="coder_node",
        seed_intent="Create and configure virtual machines with RAM, vCPU, and VHDX virtual hard disks on Hyper-V",
    )
    repo.save_job(job)

    stepped = await runner.step_job("fjob_hyperv_real")
    assert stepped is True

    packets = repo.list_packets("fjob_hyperv_real")
    coder_pkts = [p for p in packets if p.sender_role == "coder"]
    assert len(coder_pkts) >= 1
    files_map = coder_pkts[0].payload.get("files_map", {})
    tool_code = files_map.get("tools/manage_hyperv.py", "")

    # Invariant: Code must NOT be a fake static dummy dictionary return!
    assert 'return {"success": True, "action": action, "agent": "hyperv", "details": kwargs}' not in tool_code

    # Invariant: Code must invoke PowerShell via subprocess with cmdlets or parameter handling
    assert "subprocess" in tool_code or "powershell" in tool_code.lower()
    assert "New-VM" in tool_code or "Get-VM" in tool_code or "-Command" in tool_code

