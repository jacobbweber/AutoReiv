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
async def test_scoped_tool_listing_for_agent(registry):
    profile = AgentProfile(
        id="calc-agent",
        name="Calculator Agent",
        description="Math agent",
        system_prompt="Math helper",
        allowed_tool_names=["calculator"],
    )
    tools = registry.get_tools_for_agent(profile)
    assert len(tools) == 1
    assert tools[0].name == "calculator"


@pytest.mark.asyncio
async def test_tool_execution_authorized_sync(registry):
    profile = AgentProfile(
        id="math-bot",
        name="Math Bot",
        description="Math",
        system_prompt="Do math",
        allowed_tool_names=["calculator"],
    )
    call = ToolCall(id="call_1", name="calculator", arguments={"a": 5, "b": 7})
    result = await registry.execute(call, profile)

    assert result.success is True
    assert result.output == 12
    assert result.error is None
    assert result.duration_ms > 0


@pytest.mark.asyncio
async def test_tool_execution_authorized_async(registry):
    profile = AgentProfile(
        id="fetch-bot",
        name="Fetch Bot",
        description="Fetch",
        system_prompt="Fetch items",
        allowed_tool_names=["fetcher"],
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
async def test_tool_execution_unknown_tool(registry):
    profile = AgentProfile(
        id="admin",
        name="Admin",
        description="Admin",
        system_prompt="Admin",
        allowed_tool_names=["non_existent"],
    )
    call = ToolCall(id="call_4", name="non_existent", arguments={})
    result = await registry.execute(call, profile)

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_tool_execution_exception_handled_gracefully(registry):
    profile = AgentProfile(
        id="tester",
        name="Tester",
        description="Tester",
        system_prompt="Test",
        allowed_tool_names=["failing_tool"],
    )
    call = ToolCall(id="call_5", name="failing_tool", arguments={})
    result = await registry.execute(call, profile)

    assert result.success is False
    assert "Database connection lost" in result.error


@pytest.mark.asyncio
async def test_read_document_file_auto_authorized_when_registered(registry):
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
        allowed_tool_names=["calculator"],
    )
    tools = registry.get_tools_for_agent(profile)
    tool_names = {t.name for t in tools}
    assert "read_document_file" in tool_names
    assert "calculator" in tool_names

    call = ToolCall(id="call_doc", name="read_document_file", arguments={"path": "test.csv"})
    result = await registry.execute(call, profile)
    assert result.success is True
    assert result.output == "content of test.csv"
