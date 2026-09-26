"""
Integration Dogfooding Test Suite: Capability Gap Closed Loop Lifecycle [CARD-374].

Validates the capability gap journey that outlives the Factory:
1. Kernel in-flight detection: When an agent response admits a missing capability,
   a structured gap record is created and persisted to SQLite with session context.
2. Backlog surfacing: the Agent backlog API surfaces the pending gap
   with agent ID, intent, and suggested tool details.

The Factory train / promote / fail steps were deleted with the Factory [CARD-497].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import AgentProfile
from src.domain.gateway.models import (
    ChatMessage,
    CompletionResponse,
    Role,
)
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.connection import SQLiteConnectionManager
from src.infrastructure.memory.repositories.capability_gaps import GAP_PENDING, CapabilityGapRepository
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
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
    app.state.store = store
    app.state.state_store = store
    app.state.capability_gap_repo = gap_repo
    app.state.data_dir_paths = data_dir_paths
    app.state.registry = registry
    app.state.gateway = gateway

    return {
        "tmp_path": tmp_path,
        "data_dir": data_dir,
        "store": store,
        "gap_repo": gap_repo,
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
    """Verify that /api/agents/gaps surfaces pending gaps with metadata; the Factory backlog route is gone [REQ-FACT-027, CARD-497]."""
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

        # 2. The retired Factory backlog route is not mounted
        r2 = await client.get("/api/agent_training_factory/gaps?status=pending")
        assert r2.status_code == 404

        # Verify full metadata in backlog response
        matching_gap = next(g for g in body1["gaps"] if g["id"] == gap1.id)
        assert matching_gap["agent_id"] == "sec-ops"
        assert matching_gap["session_id"] == "sess_sec_01"
        assert matching_gap["suggested_tool_name"] == "port_scanner"
        assert matching_gap["identified_capability"] == "Port Scanner"
        assert matching_gap["status"] == "pending"
