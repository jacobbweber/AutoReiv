"""
Integration Dogfooding Test Suite: Capability Gap Closed Loop Lifecycle [CARD-374].

Validates the complete closed-loop capability gap journey:
1. Kernel in-flight detection: When an agent response admits a missing capability,
   a structured gap record is created and persisted to SQLite with session context.
2. Backlog surfacing: Factory and Agent backlog APIs surface the pending gap
   with agent ID, intent, and suggested tool details.
3. Seeding & Linkage: Seeding a factory job via either the gap train endpoint or
   direct job intake with capability_gap_id links the gap and transitions status to 'training'.
4. Promotion & Resolution: Completing and approving the job writes the user pack,
   registers the agent in BuiltinAgentRegistry, and transitions the gap to 'trained'.
5. Honest Failure & Dismissal: Rejecting or failing promotion updates the gap to
   'failed' or 'cant' honestly without dangling or corrupting references.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.agent_training_factory.gap_link import (
    GAP_CANT,
    GAP_DISMISSED,
    GAP_FAILED,
    GAP_PENDING,
    GAP_TRAINED,
    GAP_TRAINING,
    encode_gap_id_objective,
    gap_id_from_job,
)
from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import AgentProfile
from src.domain.gateway.models import (
    ChatMessage,
    CompletionResponse,
    Role,
)
from src.domain.kernel.models import AgentOrigin
from src.domain.orchestration.factory_packets import FactoryJob, FactoryPacket
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.connection import SQLiteConnectionManager
from src.infrastructure.memory.repositories.capability_gaps import CapabilityGapRepository
from src.infrastructure.memory.repositories.factory_packets import FactoryPacketRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from src.web.routers import agent_training_factory as atf_mod
from src.web.routers import gaps as gaps_mod


class MockGapDeterministicProvider:
    """Mock LLM provider returning predetermined text responses."""

    provider_id: str = "default"

    def __init__(self):
        self.provider_id = "default"
        self.next_response = "I don't have the tool to inspect DNS records for that domain."

    async def complete(self, request: Any) -> CompletionResponse:
        return CompletionResponse(
            model=getattr(request, "model", "default"),
            message=ChatMessage(role=Role.ASSISTANT, content=self.next_response),
        )


@pytest.fixture
def gap_test_env(tmp_path: Path, monkeypatch):
    """Setup isolated SQLite store, repositories, gateway, and kernel."""
    data_dir = tmp_path / "user_data"
    data_dir.mkdir(parents=True)
    packs_dir = data_dir / "packs"
    packs_dir.mkdir(parents=True)
    skills_dir = data_dir / "skills"
    skills_dir.mkdir(parents=True)
    wiki_path = tmp_path / "wiki"
    wiki_path.mkdir(parents=True)

    db_path = data_dir / "autoreiv.db"
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(data_dir))
    monkeypatch.setenv("AUTOREIV_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTOREIV_WIKI_PATH", str(wiki_path))

    store = SQLiteStateStore(db_path=str(db_path))
    store.initialize_db()
    conn_mgr = SQLiteConnectionManager(db_path=str(db_path))

    gap_repo = CapabilityGapRepository(connection_manager=conn_mgr)
    factory_repo = FactoryPacketRepository(connection_manager=conn_mgr)

    gateway = MultiProviderGateway()
    mock_provider = MockGapDeterministicProvider()
    gateway.register_provider(mock_provider)

    telemetry = TelemetryCollector(store=store)
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=telemetry,
        wiki_root=str(wiki_path),
        skills_dir=str(skills_dir),
    )

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=tool_reg,
        state_store=store,
        telemetry=telemetry,
        data_dir=str(data_dir),
    )

    from src.infrastructure.data.resolver import DataDirResolver

    data_dir_paths = DataDirResolver().resolve()

    # Setup web application
    app = FastAPI()
    app.include_router(gaps_mod.router)
    app.include_router(atf_mod.router)
    app.state.store = store
    app.state.state_store = store
    app.state.capability_gap_repo = gap_repo
    app.state.factory_repo = factory_repo
    app.state.data_dir_paths = data_dir_paths
    app.state.registry = registry
    app.state.gateway = gateway

    return {
        "tmp_path": tmp_path,
        "data_dir": data_dir,
        "store": store,
        "gap_repo": gap_repo,
        "factory_repo": factory_repo,
        "gateway": gateway,
        "mock_provider": mock_provider,
        "kernel": kernel,
        "registry": registry,
        "app": app,
    }


@pytest.mark.asyncio
async def test_dogfood_kernel_detects_gap_and_records_to_sqlite(gap_test_env):
    """Simulate a chat turn where the agent lacks tools, verifying automatic gap logging to SQLite [REQ-PRUNE-AUTO-002]."""
    kernel: AgentKernel = gap_test_env["kernel"]
    store: SQLiteStateStore = gap_test_env["store"]
    gap_repo: CapabilityGapRepository = gap_test_env["gap_repo"]
    mock_provider: MockGapDeterministicProvider = gap_test_env["mock_provider"]

    agent = AgentProfile(
        id="network-ops",
        name="Network Operations Specialist",
        description="Handles network diagnostics",
        system_prompt="You are a network ops assistant.",
    )

    session = store.create_session(agent_id=agent.id, title="DNS Debug Session")

    # Configure provider response indicating missing capability
    mock_provider.next_response = "I cannot directly inspect DNS records without a tool."

    user_prompt = "Can you inspect DNS records for example.com?"
    response = await kernel.run_turn(
        agent=agent,
        session_id=session.id,
        user_content=user_prompt,
    )

    assert response is not None
    assert "cannot directly inspect DNS records" in response.content

    # Assert structured gap is persisted in SQLite
    gaps = gap_repo.list_gaps(agent_id=agent.id, status=GAP_PENDING)
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap.agent_id == agent.id
    assert gap.session_id == session.id
    assert gap.status == GAP_PENDING
    assert "inspect DNS records" in gap.identified_capability or "inspect DNS records" in gap.turn_text
    assert gap.suggested_tool_name is not None
    assert gap.suggested_tool_name != ""


@pytest.mark.asyncio
async def test_dogfood_backlog_api_surfaces_pending_gaps(gap_test_env):
    """Verify that both /api/agents/gaps and /api/agent_training_factory/gaps surface pending gaps with metadata [REQ-FACT-027]."""
    app: FastAPI = gap_test_env["app"]
    gap_repo: CapabilityGapRepository = gap_test_env["gap_repo"]

    # Seed 2 pending gaps
    gap1 = gap_repo.create_gap(
        agent_id="sec-ops",
        turn_text="Scan open ports on subnet 10.0.0.0/24",
        identified_capability="Port Scanner",
        suggested_tool_name="port_scanner",
        session_id="sess_sec_01",
    )
    gap2 = gap_repo.create_gap(
        agent_id="db-admin",
        turn_text="Analyze slow queries from postgres logs",
        identified_capability="Query Analyzer",
        suggested_tool_name="analyze_slow_queries",
        session_id="sess_db_01",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Query agent gaps endpoint
        r1 = await client.get("/api/agents/gaps?status=pending")
        assert r1.status_code == 200
        body1 = r1.json()
        assert body1["success"] is True
        gap_ids1 = [g["id"] for g in body1["gaps"]]
        assert gap1.id in gap_ids1
        assert gap2.id in gap_ids1

        # 2. Query factory backlog endpoint
        r2 = await client.get("/api/agent_training_factory/gaps?status=pending")
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2["success"] is True
        gap_ids2 = [g["id"] for g in body2["gaps"]]
        assert gap1.id in gap_ids2
        assert gap2.id in gap_ids2

        # Verify full metadata in backlog response
        matching_gap = next(g for g in body2["gaps"] if g["id"] == gap1.id)
        assert matching_gap["agent_id"] == "sec-ops"
        assert matching_gap["session_id"] == "sess_sec_01"
        assert matching_gap["suggested_tool_name"] == "port_scanner"
        assert matching_gap["identified_capability"] == "Port Scanner"
        assert matching_gap["status"] == "pending"


@pytest.mark.asyncio
async def test_dogfood_train_gap_creates_linked_factory_job(gap_test_env):
    """Test seeding factory training job from gap via both train endpoint and direct job intake [REQ-FACT-028]."""
    app: FastAPI = gap_test_env["app"]
    gap_repo: CapabilityGapRepository = gap_test_env["gap_repo"]
    factory_repo: FactoryPacketRepository = gap_test_env["factory_repo"]

    # 1. Test via POST /api/agents/{agent_id}/gaps/{gap_id}/train
    gap_train = gap_repo.create_gap(
        agent_id="infra-bot",
        turn_text="Deploy Terraform template to Hyper-V cluster",
        identified_capability="Terraform Provisioner",
        suggested_tool_name="deploy_terraform",
        session_id="sess_infra_01",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_train = await client.post(f"/api/agents/infra-bot/gaps/{gap_train.id}/train")
        assert r_train.status_code == 200
        train_body = r_train.json()
        assert train_body["success"] is True
        assert train_body["status"] == GAP_TRAINING

        # Verify gap status updated to training in SQLite
        refreshed_gap = gap_repo.get_gap(gap_train.id)
        assert refreshed_gap.status == GAP_TRAINING

        # Verify factory job linked to gap
        job = factory_repo.get_job(train_body["job_id"])
        assert job is not None
        assert gap_id_from_job(job) == gap_train.id

        # 2. Test via POST /api/agent_training_factory/jobs with capability_gap_id
        gap_intake = gap_repo.create_gap(
            agent_id="log-parser",
            turn_text="Parse journald logs for auth failures",
            identified_capability="Journald Log Parser",
            suggested_tool_name="parse_journald",
            session_id="sess_log_01",
        )

        r_intake = await client.post(
            "/api/agent_training_factory/jobs",
            json={
                "target_agent_id": "log-parser",
                "seed_intent": "Parse journald logs for authentication failures",
                "objectives": ["Extract SSH failed logins", "Aggregate by IP"],
                "capability_gap_id": gap_intake.id,
            },
        )
        assert r_intake.status_code == 200
        intake_body = r_intake.json()
        assert intake_body["success"] is True
        assert intake_body["capability_gap_id"] == gap_intake.id

        # Verify gap status transitioned to training
        refreshed_intake_gap = gap_repo.get_gap(gap_intake.id)
        assert refreshed_intake_gap.status == GAP_TRAINING

        # Verify factory job has encoded gap_id in objectives
        intake_job = factory_repo.get_job(intake_body["job_id"])
        assert intake_job is not None
        assert gap_id_from_job(intake_job) == gap_intake.id


@pytest.mark.asyncio
async def test_dogfood_promote_resolves_gap_and_links_agent_pack(gap_test_env):
    """Verify that approving promote resolves the gap (status='trained') and registers custom agent pack [CARD-374]."""
    app: FastAPI = gap_test_env["app"]
    gap_repo: CapabilityGapRepository = gap_test_env["gap_repo"]
    factory_repo: FactoryPacketRepository = gap_test_env["factory_repo"]
    registry: BuiltinAgentRegistry = gap_test_env["registry"]
    data_dir: Path = gap_test_env["data_dir"]

    target_agent = "disk-auditor"
    gap = gap_repo.create_gap(
        agent_id=target_agent,
        turn_text="Inspect disk inode usage and report high-consumption directories",
        identified_capability="Inode Usage Auditor",
        suggested_tool_name="audit_disk_inodes",
        session_id="sess_disk_01",
    )
    gap_repo.update_gap_status(gap.id, GAP_TRAINING)

    job_id = "fjob_disk_auditor_01"
    job = FactoryJob(
        id=job_id,
        target_agent_id=target_agent,
        session_id="sess_disk_01",
        status="waiting_approval",
        seed_intent="Inspect disk inode usage",
        objectives=[encode_gap_id_objective(gap.id), "Audit inode distribution across mount points"],
        current_node_id="promote",
    )
    factory_repo.save_job(job)

    # Deliver authored sandbox-verified pack files
    tool_code = '''"""Disk inode auditing tool."""
from typing import Dict, Any

def audit_disk_inodes(action: str = "audit", path: str = "/") -> Dict[str, Any]:
    """Audit inode distribution."""
    return {"status": "success", "action": action, "inodes_used": 152000}
'''
    skill_md = """---
name: disk-auditor
description: Audit disk inodes
requires_tools:
  - audit_disk_inodes
---

# Disk Inode Auditor

## Overview
Audits filesystem inodes.

## Tools
- `audit_disk_inodes`

## Order (Standard Operating Procedure)
1. Inspect directory.

## Pitfalls
- Permissions.

## Done-when
Verify audit returns status success.
"""

    work_packet = FactoryPacket(
        id="fpkt_disk_work",
        job_id=job_id,
        packet_type="work",
        sender_role="author",
        recipient_role="verify",
        node_id="author",
        payload={
            "tool_name": "audit_disk_inodes",
            "files_map": {
                "tools/audit_disk_inodes.py": tool_code,
                "skills/disk_auditor/SKILL.md": skill_md,
            },
        },
    )
    factory_repo.save_packet(work_packet)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Promote the job with approval
        r_promote = await client.post(
            f"/api/agent_training_factory/jobs/{job_id}/promote",
            json={"decision": "approved"},
        )
        assert r_promote.status_code == 200, r_promote.text
        promote_body = r_promote.json()
        assert promote_body["success"] is True

        # 1. Verify gap status transitioned to 'trained' (resolved)
        refreshed_gap = gap_repo.get_gap(gap.id)
        assert refreshed_gap.status == GAP_TRAINED
        assert refreshed_gap.status != GAP_PENDING

        # Pending backlog query no longer includes this gap
        pending_gaps = gap_repo.list_gaps(agent_id=target_agent, status=GAP_PENDING)
        assert len(pending_gaps) == 0

        # 2. Verify agent pack on disk in user data
        pack_dir = data_dir / "packs" / target_agent
        assert pack_dir.exists()
        assert (pack_dir / "pack.json").exists()
        assert (pack_dir / "tools" / "audit_disk_inodes.py").exists()

        # 3. Verify registry recognizes newly promoted agent pack
        promoted_profile = registry.get_agent(target_agent)
        assert promoted_profile is not None
        assert promoted_profile.origin == AgentOrigin.PACK


@pytest.mark.asyncio
async def test_dogfood_fail_or_reject_job_updates_gap_honestly(gap_test_env):
    """Verify that rejecting a job sets 'failed' and unverified promotion sets 'cant' without dangling state [CARD-270]."""
    app: FastAPI = gap_test_env["app"]
    gap_repo: CapabilityGapRepository = gap_test_env["gap_repo"]
    factory_repo: FactoryPacketRepository = gap_test_env["factory_repo"]

    # 1. Test Rejection -> GAP_FAILED
    gap_reject = gap_repo.create_gap(
        agent_id="backup-bot",
        turn_text="Backup etcd cluster to S3",
        identified_capability="Etcd S3 Backup",
        suggested_tool_name="backup_etcd",
        session_id="sess_backup_01",
    )
    gap_repo.update_gap_status(gap_reject.id, GAP_TRAINING)

    job_reject = FactoryJob(
        id="fjob_rej_01",
        target_agent_id="backup-bot",
        session_id="sess_backup_01",
        status="waiting_approval",
        seed_intent="Backup etcd cluster to S3",
        objectives=[encode_gap_id_objective(gap_reject.id)],
        current_node_id="promote",
    )
    factory_repo.save_job(job_reject)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_rej = await client.post(
            f"/api/agent_training_factory/jobs/{job_reject.id}/promote",
            json={"decision": "rejected"},
        )
        assert r_rej.status_code == 200
        refreshed_rej = gap_repo.get_gap(gap_reject.id)
        assert refreshed_rej.status == GAP_FAILED

        # 2. Test Unverified Promotion -> GAP_CANT (HTTP 422 refused theatre)
        gap_empty = gap_repo.create_gap(
            agent_id="ghost-bot",
            turn_text="Ghost capability with zero files",
            identified_capability="Ghost Tool",
            suggested_tool_name="ghost_tool",
            session_id="sess_ghost_01",
        )
        gap_repo.update_gap_status(gap_empty.id, GAP_TRAINING)

        job_empty = FactoryJob(
            id="fjob_empty_01",
            target_agent_id="ghost-bot",
            session_id="sess_ghost_01",
            status="waiting_approval",
            seed_intent="Ghost capability",
            objectives=[encode_gap_id_objective(gap_empty.id)],
            current_node_id="promote",
        )
        factory_repo.save_job(job_empty)

        r_empty = await client.post(
            f"/api/agent_training_factory/jobs/{job_empty.id}/promote",
            json={"decision": "approved"},
        )
        assert r_empty.status_code == 422
        refreshed_empty = gap_repo.get_gap(gap_empty.id)
        assert refreshed_empty.status == GAP_CANT

        # 3. Test Dismissal -> GAP_DISMISSED
        gap_dismiss = gap_repo.create_gap(
            agent_id="obsolete-bot",
            turn_text="Obsolete request",
            identified_capability="Obsolete",
            suggested_tool_name="obsolete_tool",
        )

        r_del = await client.delete(f"/api/agents/obsolete-bot/gaps/{gap_dismiss.id}")
        assert r_del.status_code == 200
        refreshed_del = gap_repo.get_gap(gap_dismiss.id)
        assert refreshed_del.status == GAP_DISMISSED
