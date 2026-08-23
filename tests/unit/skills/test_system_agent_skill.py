"""
Unit tests for System Agent Skill & Builtin Registry [REQ-AGENTS-006].
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.system_agent_skill import SystemAgentSkill
from src.application.telemetry.collector import TelemetryCollector
from src.domain.agents.profiles import SYSTEM_AGENT_PROFILE
from src.domain.gateway.models import ToolCall
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


@pytest.fixture
def store():
    s = SQLiteStateStore(db_path=":memory:")
    s.initialize_db()
    return s


@pytest.fixture
def collector(store):
    return TelemetryCollector(store=store)


@pytest.fixture
def skill(store, collector):
    return SystemAgentSkill(store=store, telemetry=collector)


def test_system_health_inspection(collector, skill):
    collector.record_turn_span(
        agent_id="general-assistant",
        session_id="s1",
        model="ollama/qwen2.5:7b",
        duration_ms=100.0,
        prompt_tokens=50,
        completion_tokens=25,
        success=True,
    )

    health = skill.inspect_system_health()
    assert health["database_status"] == "healthy"
    assert health["total_turns"] == 1
    assert health["total_tokens"] == 75
    assert health["global_error_rate"] == 0.0


def test_agent_usage_summary(collector, skill):
    collector.record_turn_span(
        agent_id="linux-sysadmin",
        session_id="s2",
        model="ollama/qwen2.5:7b",
        duration_ms=80.0,
        prompt_tokens=40,
        completion_tokens=20,
        success=True,
    )

    usage = skill.get_agent_usage_summary(agent_id="linux-sysadmin")
    assert usage["turn_count"] == 1
    assert usage["total_tokens"] == 60


def test_tool_health_matrix(collector, skill):
    collector.record_tool_span(
        agent_id="linux-sysadmin",
        session_id="s2",
        tool_name="cli_exec",
        duration_ms=10.0,
        success=True,
    )

    matrix = skill.get_tool_health_matrix()
    assert "cli_exec" in matrix
    assert matrix["cli_exec"]["call_count"] == 1
    assert matrix["cli_exec"]["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_system_agent_registered_tool_execution(store, collector, skill):
    registry = ScopedToolRegistry()
    skill.register_tools(registry)

    call = ToolCall(id="call_sys", name="inspect_system_health", arguments={})
    res = await registry.execute(call, SYSTEM_AGENT_PROFILE)

    assert res.success is True
    assert res.output["database_status"] == "healthy"


def test_builtin_agent_registry_bootstrapping(store, collector):
    agent_reg, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=collector)

    # All 4 agents present
    profiles = agent_reg.list_profiles()
    assert len(profiles) == 4

    # Check tools bound for each agent
    ga_tools = tool_reg.get_tools_for_agent(agent_reg.get_profile("general-assistant"))
    assert len(ga_tools) >= 4

    sa_tools = tool_reg.get_tools_for_agent(agent_reg.get_profile("linux-sysadmin"))
    assert len(sa_tools) >= 2

    lib_tools = tool_reg.get_tools_for_agent(agent_reg.get_profile("librarian"))
    assert len(lib_tools) >= 4

    sys_tools = tool_reg.get_tools_for_agent(agent_reg.get_profile("system-agent"))
    assert len(sys_tools) >= 3
