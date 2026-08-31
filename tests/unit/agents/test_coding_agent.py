"""
Coding pack and sandboxed execute_code grant [REQ-AGENTS-010, REQ-AGENTS-011].
"""

import pytest

from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.agent_packs.catalog import import_sdlc_packs


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def collector(store):
    return TelemetryCollector(store=store)


def _ready(store, collector, tmp_path):
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(
        store=store,
        telemetry=collector,
        wiki_root=str(tmp_path / "wiki"),
        skills_dir=str(tmp_path / "skills"),
    )
    import_sdlc_packs(tmp_path, agent_reg, tool_reg)
    return agent_reg, tool_reg


@pytest.mark.asyncio
async def test_bootstrap_registers_execute_code_for_coding_only(store, collector, tmp_path):
    agent_reg, tool_reg = _ready(store, collector, tmp_path)

    assert tool_reg.get_tool_definition("execute_code") is not None

    coding = agent_reg.get_agent("coding")
    assistant = agent_reg.get_agent("assistant")
    autoreiv = agent_reg.get_agent("autoreiv")
    assert coding is not None
    assert coding.is_builtin is False
    assert "execute_code" in coding.allowed_tool_names
    assert "execute_code" not in assistant.allowed_tool_names
    assert "execute_code" not in autoreiv.allowed_tool_names

    call = ToolCall(id="call_code", name="execute_code", arguments={"code": "print(1 + 1)"})
    coding_res = await tool_reg.execute(call, coding)
    assert coding_res.success is True
    assert "2" in str(coding_res.output.get("stdout", ""))

    deny = await tool_reg.execute(call, assistant)
    assert deny.success is False
    assert "not authorized" in (deny.error or "").lower()

    deny_auto = await tool_reg.execute(call, autoreiv)
    assert deny_auto.success is False
    assert "not authorized" in (deny_auto.error or "").lower()


def test_lookup_agents_lists_coding(store, collector, tmp_path):
    agent_reg, _ = _ready(store, collector, tmp_path)
    from src.application.orchestration.directory_service import AgentDirectoryService

    directory = AgentDirectoryService(agent_registry=agent_reg, state_store=store)
    cards = directory.search_agents("python coding", limit=5)
    ids = [c.id for c in cards]
    assert "coding" in ids
