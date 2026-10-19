"""
Unit tests for Remote HTTP/SSE MCPClientAdapter [CARD-183].
[REQ-MCP-AGENT-002]
"""

import json

import httpx
import pytest

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.infrastructure.mcp.client_adapter import MCPClientAdapter, MCPClientManager


@pytest.mark.asyncio
async def test_remote_mcp_adapter_list_tools():
    target_url = "http://remote-mcp.internal:8080/sse"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == target_url
        assert request.headers.get("authorization") == "Bearer test-key"
        body = json.loads(request.content)
        assert body["method"] == "tools/list"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "tools": [
                        {
                            "name": "manage_hyperv_vm",
                            "description": "Manage virtual machines on Hyper-V host",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"action": {"type": "string"}},
                            },
                        },
                        {
                            "name": "manage_hyperv_network",
                            "description": "Manage Hyper-V virtual switches",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"action": {"type": "string"}},
                            },
                        },
                    ]
                },
            },
        )

    adapter = MCPClientAdapter(
        server_name="hyperv-remote",
        transport="sse",
        url=target_url,
        headers={"Authorization": "Bearer test-key"},
        _http_transport=httpx.MockTransport(handler),
    )

    tools = await adapter.list_tools()
    assert len(tools) == 2
    names = [t.name for t in tools]
    assert "mcp_hyperv-remote_manage_hyperv_vm" in names
    assert "mcp_hyperv-remote_manage_hyperv_network" in names


@pytest.mark.asyncio
async def test_remote_mcp_adapter_call_tool():
    target_url = "http://remote-mcp.internal:8080/sse"

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["method"] == "tools/call"
        assert body["params"]["name"] == "manage_hyperv_vm"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "content": [{"type": "text", "text": "VM Web01 running"}],
                    "isError": False,
                },
            },
        )

    adapter = MCPClientAdapter(
        server_name="hyperv-remote",
        transport="sse",
        url=target_url,
        _http_transport=httpx.MockTransport(handler),
    )

    res = await adapter.call_tool("manage_hyperv_vm", {"action": "status", "vm_name": "Web01"})
    assert res["success"] is True
    assert "VM Web01 running" in str(res["output"])


@pytest.mark.asyncio
async def test_mcp_client_manager_mount_remote_server():
    registry = ScopedToolRegistry()
    manager = MCPClientManager(tool_registry=registry)

    target_url = "http://remote-docker:9000/sse"

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {
                    "tools": [
                        {
                            "name": "container_status",
                            "description": "Check Docker container status",
                            "inputSchema": {"type": "object"},
                        }
                    ]
                },
            },
        )

    tools = await manager.mount_server(
        name="docker-node",
        transport="sse",
        url=target_url,
        _http_transport=httpx.MockTransport(handler),
    )

    assert len(tools) == 1
    assert "mcp_docker-node_container_status" in registry

    # Unmount
    await manager.unmount_server("docker-node")
    assert "mcp_docker-node_container_status" not in registry


@pytest.mark.asyncio
async def test_remote_adapter_speaks_streamable_http_like_the_github_mcp_server():
    """CARD-730: Streamable HTTP servers (e.g. https://api.githubcopilot.com/mcp/) need Accept for JSON and SSE,
    may answer as an SSE frame, and hand out an Mcp-Session-Id that later requests must send back."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        accept = request.headers.get("accept", "")
        if "application/json" not in accept or "text/event-stream" not in accept:
            return httpx.Response(406, text="Not Acceptable")
        body = json.loads(request.content)
        seen.append((body["method"], request.headers.get("mcp-session-id")))
        if "id" not in body:
            return httpx.Response(202)
        if body["method"] == "initialize":
            result = {"protocolVersion": "2025-03-26", "capabilities": {}, "serverInfo": {"name": "gh"}}
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result},
                                  headers={"Mcp-Session-Id": "sess-1"})
        frame = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": {"tools": [
            {"name": "get_me", "description": "Who am I", "inputSchema": {"type": "object", "properties": {}}}]}})
        return httpx.Response(200, text=f"event: message\ndata: {frame}\n\n",
                              headers={"Content-Type": "text/event-stream"})

    adapter = MCPClientAdapter(
        server_name="github",
        transport="sse",
        url="https://api.githubcopilot.com/mcp/",
        headers={"Authorization": "Bearer pat"},
        _http_transport=httpx.MockTransport(handler),
    )
    tools = await adapter.list_tools()
    assert [t.name for t in tools] == ["mcp_github_get_me"]
    assert seen[0] == ("initialize", None)
    assert ("tools/list", "sess-1") in seen
