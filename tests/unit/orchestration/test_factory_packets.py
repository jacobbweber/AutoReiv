"""
Unit tests for Autonomous Agent Pack Factory typed packets and durable SQLite store [REQ-FACT-003, REQ-FACT-012].
"""

import os
import tempfile

import pytest

from src.domain.orchestration.factory_packets import (
    EvalPacket,
    FactoryEvalRun,
    FactoryJob,
    FactoryPacket,
    GapPacket,
    PromotePacket,
    WorkPacket,
)
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
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
def factory_repo(temp_db_path):
    store = SQLiteStateStore(db_path=temp_db_path)
    return FactoryPacketRepository(store)


def test_work_packet_serialization():
    packet = WorkPacket(
        goal="Manage game server lifecycle",
        target_agent_id="game-agent",
        facts=["Ubuntu 22.04 LTS", "systemd service palworld.service"],
        constraints=["Do not mutate /etc/systemd directly", "Require HITL for restart"],
        done_when="Service status returns active, stop stops process, restart safely completes",
        budget={"max_turns": 10, "max_tokens": 16000},
        target_host="192.168.1.150",
    )
    data = packet.model_dump()
    assert data["goal"] == "Manage game server lifecycle"
    assert data["target_agent_id"] == "game-agent"
    assert len(data["facts"]) == 2

    # Round-trip JSON
    json_str = packet.model_dump_json()
    reconstructed = WorkPacket.model_validate_json(json_str)
    assert reconstructed.goal == packet.goal
    assert reconstructed.facts == packet.facts


def test_gap_packet_validation():
    packet = GapPacket(
        kind="tool",
        justification="No tool exists to restart systemd service via user scope",
        evidence="attempt_phase exit 127: systemctl not permitted without sudo",
        suggested_signature="def restart_service(name: str, scope: str = 'user') -> dict",
        target_agent_id="game-agent",
    )
    assert packet.kind == "tool"
    assert "restart_service" in packet.suggested_signature


def test_eval_packet_battery_scoring():
    eval_p = EvalPacket(
        checks_executed=["stage_1_functional", "stage_2_safety", "stage_3_idempotency", "stage_4_critic"],
        passed=True,
        stage_1_functional=True,
        stage_2_safety=True,
        stage_3_idempotency=True,
        stage_4_critic=True,
        stdout="All 3 trial runs passed with code 0",
        critic_notes="AST cleanly typed; no unbounded regex",
        duration_ms=452.1,
    )
    assert eval_p.passed is True
    assert eval_p.stage_2_safety is True


def test_promote_packet_structure():
    promote = PromotePacket(
        target_agent_id="game-agent",
        modified_files=["tools/palworld_service.py", "skills/server_ops/SKILL.md"],
        test_scores={"functional": 1.0, "safety": 1.0, "idempotency": 1.0, "critic": 1.0},
        critic_verdict="approved",
        hitl_approval_id="appr_019283",
    )
    assert promote.critic_verdict == "approved"
    assert len(promote.modified_files) == 2


def test_factory_job_and_packet_persistence(factory_repo):
    # 1. Create a factory job
    job = FactoryJob(
        id="fjob_001",
        target_agent_id="game-agent",
        session_id="sess_training_01",
        status="queued",
        seed_intent="Build a dedicated game server management agent",
        target_host="192.168.1.150",
        active_graph_id="graph_standard_factory_v1",
        current_node_id="socratic_handshake",
    )
    factory_repo.save_job(job)

    fetched_job = factory_repo.get_job("fjob_001")
    assert fetched_job is not None
    assert fetched_job.id == "fjob_001"
    assert fetched_job.status == "queued"
    assert fetched_job.target_agent_id == "game-agent"

    # Update job status
    factory_repo.update_job_status("fjob_001", "running", current_node_id="discovery_probe", cycles_consumed=1)
    updated_job = factory_repo.get_job("fjob_001")
    assert updated_job.status == "running"
    assert updated_job.current_node_id == "discovery_probe"
    assert updated_job.cycles_consumed == 1

    # 2. Persist a typed packet
    work_pkt = WorkPacket(
        goal="Discover target host file layout",
        target_agent_id="game-agent",
        done_when="Manifest compiled",
    )
    envelope = FactoryPacket(
        id="fpkt_001",
        job_id="fjob_001",
        packet_type="work",
        sender_role="conductor",
        recipient_role="inspector",
        node_id="discovery_probe",
        payload=work_pkt.model_dump(),
    )
    factory_repo.save_packet(envelope)

    packets = factory_repo.list_packets("fjob_001")
    assert len(packets) == 1
    assert packets[0].id == "fpkt_001"
    assert packets[0].packet_type == "work"
    assert packets[0].sender_role == "conductor"

    # 3. Persist an evaluation run
    eval_run = FactoryEvalRun(
        id="feval_001",
        job_id="fjob_001",
        tool_name="palworld_service",
        stage_1_functional=True,
        stage_2_safety=True,
        stage_3_idempotency=True,
        stage_4_critic=True,
        stdout_log="Tests passed",
        stderr_log="",
        critic_notes="Clean AST",
        duration_ms=250.0,
        overall_passed=True,
    )
    factory_repo.save_eval_run(eval_run)

    eval_runs = factory_repo.list_eval_runs("fjob_001")
    assert len(eval_runs) == 1
    assert eval_runs[0].id == "feval_001"
    assert eval_runs[0].overall_passed is True
    assert eval_runs[0].tool_name == "palworld_service"
