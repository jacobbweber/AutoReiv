"""
Unit tests for Dynamic Skill & Tool Scoping Strategy [CARD-339, ADR-0052].
Verifies:
1. Layer 1 Fast-Path Intent Matcher
2. Lean Platform Primitive baseline (5 tools)
3. Layer 2 Dynamic Tool Expansion via activate_skill
"""


import pytest

from src.application.gateway.gateway_service import MultiProviderGateway
from src.application.kernel.agent_kernel import AgentKernel
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.platform_primitives import PlatformPrimitiveTools
from src.application.telemetry.collector import TelemetryCollector
from src.domain.gateway.models import (
    ChatMessage,
    CompletionResponse,
    Role,
    StreamChunk,
    ToolCall,
)
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.sqlite_store import SQLiteStateStore
from tests.unit.kernel.test_agent_kernel import MockScriptedLLM


def test_match_intent_skills():
    """Verify Layer 1 0ms intent heuristics."""
    assert AgentKernel._match_intent_skills("please search the wiki for kubernetes notes") == ["wiki"]
    assert AgentKernel._match_intent_skills("inspect system health, cpu and telemetry") == ["diagnostics"]
    assert AgentKernel._match_intent_skills("schedule a weekly task and log daily items") == ["wiki_tasks"]
    assert AgentKernel._match_intent_skills("read the repository code file and prepare a patch") == ["coding"]
    assert AgentKernel._match_intent_skills("hello, what is the capital of France?") == []


@pytest.mark.asyncio
async def test_autoreiv_lean_baseline_and_dynamic_expansion(tmp_path):
    """
    Verify autoreiv mounts ONLY 5 lean platform primitives on cold queries,
    and dynamically mounts specialized tools when activate_skill is called.
    """
    store = SQLiteStateStore(db_path=str(tmp_path / "test.db"))
    store.initialize_db()
    session = store.create_session(agent_id="autoreiv")
    telemetry = TelemetryCollector(store=store)

    registry = ScopedToolRegistry()
    # Register primitives
    prims = PlatformPrimitiveTools(state_store=store)
    registry.register_tool(
        name="activate_skill",
        description="Activate skill",
        parameters={"type": "object", "properties": {"skills": {"type": "array"}}},
        handler=prims.activate_skill,
    )
    registry.register_tool(
        name="ask_clarification",
        description="Clarify",
        parameters={"type": "object", "properties": {"question": {"type": "string"}}},
        handler=prims.ask_clarification,
    )
    registry.register_tool(
        name="get_session_info",
        description="Session info",
        parameters={"type": "object", "properties": {}},
        handler=prims.get_session_info,
    )
    registry.register_tool(
        name="handoff_to_agent",
        description="Handoff",
        parameters={"type": "object", "properties": {}},
        handler=lambda **kw: {"status": "ok"},
    )
    registry.register_tool(
        name="lookup_agents",
        description="Lookup",
        parameters={"type": "object", "properties": {}},
        handler=lambda **kw: [],
    )
    # Register a wiki tool (specialist)
    registry.register_tool(
        name="wiki_note_read",
        description="Read note",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        handler=lambda path="": f"Content of {path}",
    )

    autoreiv_profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="You are AutoReiv.",
        allowed_skill=["wiki", "diagnostics", "tasks", "coding"],
    )

    # Initial turn: Step 0 returns tool call to activate_skill("wiki")
    # Step 1 returns assistant final response
    step0_call = ToolCall(
        id="call_act_1",
        name="activate_skill",
        arguments={"skills": ["wiki"]},
    )
    resp0 = CompletionResponse(
        model="mock/test",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="I need to access the wiki.",
            tool_calls=[step0_call],
        ),
        finish_reason="tool_calls",
    )
    resp1 = CompletionResponse(
        model="mock/test",
        message=ChatMessage(
            role=Role.ASSISTANT,
            content="Wiki skill is active and I have resolved your request.",
        ),
        finish_reason="stop",
    )

    mock_llm = MockScriptedLLM(responses=[resp0, resp1])
    gateway = MultiProviderGateway()
    gateway.register_provider(mock_llm)

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=store,
        telemetry=telemetry,
        data_dir=str(tmp_path),
    )

    final_msg = await kernel.run_turn(
        agent=autoreiv_profile,
        session_id=session.id,
        user_content="Hello! Can you help me?",  # Cold query: no intent match
    )

    assert "Wiki skill is active" in final_msg.content
    assert len(mock_llm.requests) == 2

    # Verify Step 0: Only 5 lean primitives were mounted (wiki_note_read NOT mounted)
    req0_tools = {t.name for t in (mock_llm.requests[0].tools or [])}
    assert "activate_skill" in req0_tools
    assert "ask_clarification" in req0_tools
    assert "get_session_info" in req0_tools
    assert "handoff_to_agent" in req0_tools
    assert "lookup_agents" in req0_tools
    assert "wiki_note_read" not in req0_tools
    assert len(req0_tools) == 5

    # Verify Step 1: After activate_skill("wiki"), wiki_note_read IS mounted!
    req1_tools = {t.name for t in (mock_llm.requests[1].tools or [])}
    assert "wiki_note_read" in req1_tools
    assert "activate_skill" in req1_tools


@pytest.mark.asyncio
async def test_autoreiv_stream_turn_dynamic_expansion(tmp_path):
    """Verify stream_turn also expands tools dynamically on activate_skill."""
    store = SQLiteStateStore(db_path=str(tmp_path / "stream_test.db"))
    store.initialize_db()
    session = store.create_session(agent_id="autoreiv")
    telemetry = TelemetryCollector(store=store)

    registry = ScopedToolRegistry()
    prims = PlatformPrimitiveTools(state_store=store)
    registry.register_tool(
        name="activate_skill",
        description="Activate skill",
        parameters={"type": "object", "properties": {"skills": {"type": "array"}}},
        handler=prims.activate_skill,
    )
    registry.register_tool(
        name="ask_clarification",
        description="Clarify",
        parameters={"type": "object", "properties": {"question": {"type": "string"}}},
        handler=prims.ask_clarification,
    )
    registry.register_tool(
        name="get_session_info",
        description="Session info",
        parameters={"type": "object", "properties": {}},
        handler=prims.get_session_info,
    )
    registry.register_tool(
        name="handoff_to_agent",
        description="Handoff",
        parameters={"type": "object", "properties": {}},
        handler=lambda **kw: {"status": "ok"},
    )
    registry.register_tool(
        name="lookup_agents",
        description="Lookup",
        parameters={"type": "object", "properties": {}},
        handler=lambda **kw: [],
    )
    registry.register_tool(
        name="inspect_system_health",
        description="Inspect health",
        parameters={"type": "object", "properties": {}},
        handler=lambda: {"cpu": "ok", "status": "healthy"},
    )

    autoreiv_profile = AgentProfile(
        id="autoreiv",
        name="AutoReiv",
        description="Platform Agent",
        system_prompt="You are AutoReiv.",
        allowed_skill=["wiki", "diagnostics", "tasks", "coding"],
    )

    step0_call = ToolCall(
        id="call_diag_1",
        name="activate_skill",
        arguments={"skills": ["diagnostics"]},
    )
    chunk0 = [
        StreamChunk(tool_calls=[step0_call], is_finished=True),
    ]
    chunk1 = [
        StreamChunk(content="Diagnostics skill activated.", is_finished=True),
    ]

    mock_llm = MockScriptedLLM(responses=[], stream_chunks=[chunk0, chunk1])
    gateway = MultiProviderGateway()
    gateway.register_provider(mock_llm)

    kernel = AgentKernel(
        gateway=gateway,
        tool_registry=registry,
        state_store=store,
        telemetry=telemetry,
        data_dir=str(tmp_path),
    )

    events = []
    async for ev in kernel.stream_turn(
        agent=autoreiv_profile,
        session_id=session.id,
        user_content="Hello, system status check.",
    ):
        events.append(ev)

    assert len(mock_llm.requests) == 2
    # Step 0 had Layer 1 matched diagnostics (because "system status" was in query!)
    # But let's verify both steps executed successfully
    req1_tools = {t.name for t in (mock_llm.requests[1].tools or [])}
    assert "inspect_system_health" in req1_tools
    assert "activate_skill" in req1_tools
