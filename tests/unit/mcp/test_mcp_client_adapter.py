"""
Unit tests for MCPClientAdapter [REQ-MCP-001, REQ-MCP-002, REQ-MCP-003].
"""

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.mcp.client_adapter import MCPClientAdapter


@pytest.mark.asyncio
async def test_mcp_client_adapter_list_and_call_tools():
    adapter = MCPClientAdapter(server_name="git-mcp", command=["mock-mcp-server"])

    # Mock jsonrpc response for tools/list
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
            {
                "content": [{"type": "text", "text": "On branch main. Clean working tree."}]
            },
        ]
    )

    tools = await adapter.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mcp_git-mcp_git_status"
    assert tools[0].description == "Show working tree status"

    result = await adapter.call_tool("git_status", {})
    assert result["success"] is True
    assert "Clean working tree" in result["output"]
