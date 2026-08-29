"""
Builtin Conductor allowlist [REQ-SDLC-030, REQ-SDLC-034].
"""

import pytest

from src.application.orchestration.directory_service import AgentDirectoryService
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.mark.asyncio
async def test_conductor_deny_execute_code_and_cli(store):
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store, telemetry=TelemetryCollector(store=store)
    )
    conductor = agent_reg.get_agent("conductor")
    assert conductor is not None
    assert "execute_code" not in conductor.allowed_tool_names
    assert "cli_exec" not in conductor.allowed_tool_names
    assert "write_project_file" not in conductor.allowed_tool_names
    deny = await tool_reg.execute(
        ToolCall(id="c1", name="execute_code", arguments={"code": "print(1)"}),
        conductor,
    )
    assert deny.success is False
    assert "not authorized" in (deny.error or "").lower()


def test_lookup_agents_lists_conductor(store):
    agent_reg, _ = BuiltinAgentRegistry.bootstrap(
        store=store, telemetry=TelemetryCollector(store=store)
    )
    directory = AgentDirectoryService(agent_registry=agent_reg, state_store=store)
    cards = directory.search_agents("conductor scrum product", limit=5)
    assert "conductor" in [c.id for c in cards]
