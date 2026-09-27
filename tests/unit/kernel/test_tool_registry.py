"""
Unit tests for Scoped Tool Registry & RBAC Permissions [REQ-KERNEL-002].
"""

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.gateway.models import ToolCall
from src.domain.kernel.models import AgentProfile


def sample_sync_calculator(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


async def sample_async_fetcher(item_id: str) -> dict:
    """Fetch item details asynchronously."""
    return {"id": item_id, "status": "active"}


def sample_failing_tool():
    raise ValueError("Database connection lost")


@pytest.fixture
def registry():
    reg = ScopedToolRegistry()
    reg.register_tool(
        name="calculator",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
        handler=sample_sync_calculator,
    )
    reg.register_tool(
        name="fetcher",
        description="Fetch item",
        parameters={
            "type": "object",
            "properties": {"item_id": {"type": "string"}},
            "required": ["item_id"],
        },
        handler=sample_async_fetcher,
    )
    reg.register_tool(
        name="failing_tool",
        description="A tool that errors",
        parameters={"type": "object"},
        handler=sample_failing_tool,
    )
    return reg


@pytest.mark.asyncio
async def test_scoped_tool_listing_for_agent(registry, bind_skills):
    profile = AgentProfile(
        id="calc-agent",
        name="Calculator Agent",
        description="Math agent",
        system_prompt="Math helper",
        allowed_skill=bind_skills({"skill-calculator": ["calculator"]}),
    )
    tools = registry.get_tools_for_agent(profile)
    assert len(tools) == 1
    assert tools[0].name == "calculator"


@pytest.mark.asyncio
async def test_tool_execution_authorized_sync(registry, bind_skills):
    profile = AgentProfile(
        id="math-bot",
        name="Math Bot",
        description="Math",
        system_prompt="Do math",
        allowed_skill=bind_skills({"skill-calculator": ["calculator"]}),
    )
    call = ToolCall(id="call_1", name="calculator", arguments={"a": 5, "b": 7})
    result = await registry.execute(call, profile)

    assert result.success is True
    assert result.output == 12
    assert result.error is None
    assert result.duration_ms > 0


@pytest.mark.asyncio
async def test_tool_execution_authorized_async(registry, bind_skills):
    profile = AgentProfile(
        id="fetch-bot",
        name="Fetch Bot",
        description="Fetch",
        system_prompt="Fetch items",
        allowed_skill=bind_skills({"skill-fetcher": ["fetcher"]}),
    )
    call = ToolCall(id="call_2", name="fetcher", arguments={"item_id": "item_99"})
    result = await registry.execute(call, profile)

    assert result.success is True
    assert result.output == {"id": "item_99", "status": "active"}


@pytest.mark.asyncio
async def test_tool_execution_denied_unauthorized(registry):
    profile = AgentProfile(
        id="guest-agent",
        name="Guest",
        description="Guest with no tools",
        system_prompt="Guest",
        allowed_tool_names=[],  # No tools allowed
    )
    call = ToolCall(id="call_3", name="calculator", arguments={"a": 1, "b": 2})
    result = await registry.execute(call, profile)

    assert result.success is False
    assert "not authorized" in result.error.lower()
    assert result.output is None


@pytest.mark.asyncio
async def test_tool_execution_unknown_tool(registry, bind_skills):
    profile = AgentProfile(
        id="admin",
        name="Admin",
        description="Admin",
        system_prompt="Admin",
        allowed_skill=bind_skills({"skill-non_existent": ["non_existent"]}),
    )
    call = ToolCall(id="call_4", name="non_existent", arguments={})
    result = await registry.execute(call, profile)

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_tool_execution_exception_handled_gracefully(registry, bind_skills):
    profile = AgentProfile(
        id="tester",
        name="Tester",
        description="Tester",
        system_prompt="Test",
        allowed_skill=bind_skills({"skill-failing_tool": ["failing_tool"]}),
    )
    call = ToolCall(id="call_5", name="failing_tool", arguments={})
    result = await registry.execute(call, profile)

    assert result.success is False
    assert "Database connection lost" in result.error


@pytest.mark.asyncio
async def test_read_document_file_auto_authorized_when_registered(registry, bind_skills):
    registry.register_tool(
        name="read_document_file",
        description="Read doc",
        parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        handler=lambda path: f"content of {path}",
    )
    # Agent does NOT explicitly list read_document_file in allowed_tool_names
    profile = AgentProfile(
        id="custom-agent",
        name="Custom Agent",
        description="Custom",
        system_prompt="Custom",
        allowed_skill=bind_skills({"skill-calculator": ["calculator"]}),
    )
    tools = registry.get_tools_for_agent(profile)
    tool_names = {t.name for t in tools}
    assert "read_document_file" in tool_names
    assert "calculator" in tool_names

    call = ToolCall(id="call_doc", name="read_document_file", arguments={"path": "test.csv"})
    result = await registry.execute(call, profile)
    assert result.success is True
    assert result.output == "content of test.csv"


@pytest.mark.asyncio
async def test_wiki_tool_reaches_agent_only_through_a_ticked_skill(registry, bind_skills):
    """CARD-539 D3: allow_wiki_access retired; untick the wiki skill instead."""
    registry.register_tool(
        name="wiki_note_create",
        description="Create note",
        parameters={"type": "object", "properties": {"title": {"type": "string"}}},
        handler=lambda title: f"created {title}",
    )
    profile_blocked = AgentProfile(
        id="blocked-agent", name="Blocked Agent", description="No wiki", system_prompt="Agent", allowed_skill=[]
    )
    assert "wiki_note_create" not in {t.name for t in registry.get_tools_for_agent(profile_blocked)}
    call = ToolCall(id="call_wiki", name="wiki_note_create", arguments={"title": "Test"})
    res = await registry.execute(call, profile_blocked)
    assert res.success is False
    assert "not authorized" in res.error

    profile_allowed = AgentProfile(
        id="allowed-agent",
        name="Allowed Agent",
        description="Wiki allowed",
        system_prompt="Agent",
        allowed_skill=bind_skills({"wiki-notes": ["wiki_note_create"]}),
    )
    assert "wiki_note_create" in {t.name for t in registry.get_tools_for_agent(profile_allowed)}
    res_allowed = await registry.execute(call, profile_allowed)
    assert res_allowed.success is True
    assert res_allowed.output == "created Test"
