"""
Comprehensive unit tests for MCPClientAdapter & MCPClientManager [REQ-MCP-001, REQ-MCP-002, REQ-MCP-003].
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.kernel.models import AgentProfile
from src.infrastructure.mcp.client_adapter import MCPClientAdapter, MCPClientManager


@pytest.mark.asyncio
async def test_mcp_client_adapter_list_and_call_tools():
    adapter = MCPClientAdapter(server_name="git-mcp", command=["mock-mcp-server"])

    adapter._send_jsonrpc = AsyncMock(
        side_effect=[
            # tools/list response
            {
                "tools": [
                    {
                        "name": "git_status",
                        "description": "Show working tree status",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            },
            # tools/call response
            {"content": [{"type": "text", "text": "On branch main. Clean working tree."}]},
        ]
    )

    tools = await adapter.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mcp_git-mcp_git_status"
    assert tools[0].description == "Show working tree status"

    result = await adapter.call_tool("git_status", {})
    assert result["success"] is True
    assert "Clean working tree" in result["output"]


@pytest.mark.asyncio
async def test_mcp_client_adapter_timeout_handling():
    """Verify tool execution respects execution timeout cleanly [REQ-MCP-003]."""
    adapter = MCPClientAdapter(server_name="slow-mcp", command=["mock-slow-server"], timeout_seconds=0.1)

    async def slow_jsonrpc(*args, **kwargs):
        await asyncio.sleep(0.5)
        return {}

    adapter._send_jsonrpc = slow_jsonrpc

    result = await adapter.call_tool("slow_op", {})
    assert result["success"] is False
    assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()


@pytest.mark.asyncio
async def test_mcp_client_adapter_close():
    """Verify adapter terminates underlying subprocess on close [REQ-MCP-001]."""
    adapter = MCPClientAdapter(server_name="test-server", command=["mock-cmd"])
    from unittest.mock import MagicMock

    mock_proc = MagicMock()
    mock_proc.returncode = None
    mock_proc.terminate = MagicMock()
    mock_proc.wait = AsyncMock()
    adapter._proc = mock_proc

    await adapter.close()
    mock_proc.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_client_manager_mount_and_unmount():
    """Verify MCPClientManager mounts tools into ScopedToolRegistry with RBAC [REQ-MCP-002]."""
    registry = ScopedToolRegistry()
    manager = MCPClientManager(tool_registry=registry)

    # Mock client adapter creation
    with patch("src.infrastructure.mcp.client_adapter.MCPClientAdapter") as mock_cls:
        mock_instance = AsyncMock()
        mock_instance.list_tools.return_value = [MCPClientAdapter(server_name="sqlite", command=[]).list_tools]
        from src.domain.gateway.models import ToolDefinition

        mock_instance.list_tools = AsyncMock(
            return_value=[
                ToolDefinition(
                    name="mcp_sqlite_query",
                    description="Run SQL query",
                    parameters={"type": "object", "properties": {"sql": {"type": "string"}}},
                )
            ]
        )
        mock_instance.call_tool = AsyncMock(return_value={"success": True, "output": "Query executed: 5 rows"})
        mock_cls.return_value = mock_instance

        # Mount server
        mounted_tools = await manager.mount_server(
            name="sqlite",
            command=["uvx", "mcp-server-sqlite"],
            env={},
        )
        assert len(mounted_tools) == 1
        assert mounted_tools[0].name == "mcp_sqlite_query"

        # Verify registry contains tool
        tool_def = registry.get_tool_definition("mcp_sqlite_query")
        assert tool_def is not None

        # Verify agent RBAC allows execution
        agent = AgentProfile(
            id="sre-agent",
            name="SRE",
            description="Site Reliability Engineer",
            system_prompt="You diagnose systems.",
            allowed_tool_names=["mcp_sqlite_query"],
        )
        from src.domain.gateway.models import ToolCall

        call = ToolCall(id="call_1", name="mcp_sqlite_query", arguments={"sql": "SELECT 1"})
        res = await registry.execute(call, agent)
        assert res.success is True

        # Unmount server
        await manager.unmount_server("sqlite")
        assert registry.get_tool_definition("mcp_sqlite_query") is None


@pytest.mark.asyncio
async def test_mcp_client_adapter_env_injection():
    """Verify environment variables are merged with host env and passed to subprocess [REQ-MCP-007]."""
    custom_env = {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_mock_12345", "API_SECRET": "secret_abc"}
    adapter = MCPClientAdapter(server_name="github", command=["mock-github-mcp"], env=custom_env)

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        from unittest.mock import MagicMock

        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        mock_proc.stdin.drain = AsyncMock()
        mock_proc.stdout = AsyncMock()
        mock_proc.stdout.readline.return_value = b'{"jsonrpc": "2.0", "id": "1", "result": {"tools": []}}\n'
        mock_exec.return_value = mock_proc

        await adapter.list_tools()

        assert mock_exec.called
        call_kwargs = mock_exec.call_args[1]
        passed_env = call_kwargs.get("env", {})
        assert passed_env["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_mock_12345"
        assert passed_env["API_SECRET"] == "secret_abc"
        # Ensure host PATH is also preserved
        import os

        if "PATH" in os.environ:
            assert passed_env.get("PATH") == os.environ["PATH"]
