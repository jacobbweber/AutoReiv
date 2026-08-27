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

    # Core 2 agents present
    profiles = agent_reg.list_profiles()
    assert len(profiles) == 2

    # Check tools bound for each agent
    assistant_tools = tool_reg.get_tools_for_agent(agent_reg.get_profile("assistant"))
    assert len(assistant_tools) >= 5

    autoreiv_tools = tool_reg.get_tools_for_agent(agent_reg.get_profile("autoreiv"))
    assert len(autoreiv_tools) >= 8



def test_system_agent_diagnostic_tools(store, collector, skill):
    # 1. Record error span
    collector.record_turn_span(
        agent_id="librarian",
        session_id="sess_lib_1",
        model="ollama/qwen2.5:7b",
        duration_ms=120.0,
        success=False,
        error_message="Gateway network timeout 192.168.1.29",
    )

    # 2. Test get_recent_errors
    errors = skill.get_recent_errors(agent_id="librarian")
    assert len(errors) == 1
    assert "timeout" in errors[0]["error_message"]
    assert errors[0]["agent_id"] == "librarian"

    # 3. Create session messages & test transcript retrieval
    from src.domain.gateway.models import ChatMessage, Role

    store.create_session(agent_id="librarian", title="Test chat", session_id="sess_lib_1")
    store.save_message("sess_lib_1", "librarian", ChatMessage(role=Role.USER, content="Clean inbox"))
    store.save_message("sess_lib_1", "librarian", ChatMessage(role=Role.ASSISTANT, content="Starting audit..."))

    transcript = skill.get_session_transcript(session_id="sess_lib_1")
    assert transcript["success"] is True
    assert len(transcript["messages"]) == 2
    assert transcript["messages"][0]["content"] == "Clean inbox"

    # 4. Test get_agent_sessions
    sessions = skill.get_agent_sessions(agent_id="librarian")
    assert len(sessions) == 1
    assert sessions[0]["id"] == "sess_lib_1"

    # 5. Test get_system_logs
    from src.application.observability.log_buffer import SystemLogBuffer

    buf = SystemLogBuffer.get_instance()
    buf.add_entry(level="ERROR", message="Sample diagnostic error log", logger_name="kernel")

    logs = skill.get_system_logs(level="ERROR")
    assert any("Sample diagnostic error log" in log_item["message"] for log_item in logs)
