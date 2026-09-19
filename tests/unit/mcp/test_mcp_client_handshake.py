"""
Unit tests for standard MCP lifecycle handshake (initialize -> notifications/initialized -> tools/list)
[REQ-MCP-HANDSHAKE-001, REQ-MCP-HANDSHAKE-002].
"""

import json
from unittest.mock import MagicMock

import pytest

from src.infrastructure.mcp.client_adapter import MCPClientAdapter


@pytest.mark.asyncio
async def test_mcp_client_handshake_stdio():
    """Verify MCPClientAdapter performs initialize and notifications/initialized before tools/list."""
    adapter = MCPClientAdapter(server_name="test-server", command=["mock-server"])

    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    mock_proc.stderr = MagicMock()

    sent_messages = []

    def fake_sync_exchange(raw_msg: str) -> str:
        msg = json.loads(raw_msg.strip())
        sent_messages.append(msg)
        if msg.get("method") == "initialize":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mock-mcp", "version": "1.0.0"},
                },
            }) + "\n"
        elif msg.get("method") == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {
                    "tools": [
                        {
                            "name": "sample_tool",
                            "description": "Sample description",
                            "inputSchema": {"type": "object", "properties": {}},
                        }
                    ]
                },
            }) + "\n"
        return "{}\n"

    adapter._proc = mock_proc
    adapter._sync_exchange = fake_sync_exchange

    tools = await adapter.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "mcp_test-server_sample_tool"

    # Verify order of sent messages
    methods_sent = [m.get("method") for m in sent_messages]
    assert "initialize" in methods_sent
    assert "tools/list" in methods_sent
    assert methods_sent.index("initialize") < methods_sent.index("tools/list")

    # Verify notification was written to stdin
    # Either via _sync_write_notification or in sent_messages
    stdin_writes = "".join(call[0][0] for call in mock_proc.stdin.write.call_args_list)
    assert "notifications/initialized" in stdin_writes or any(
        m.get("method") == "notifications/initialized" for m in sent_messages
    )


@pytest.mark.asyncio
async def test_mcp_client_handshake_fallback_on_legacy_server():
    """Verify graceful fallback if legacy server rejects initialize with method not found."""
    adapter = MCPClientAdapter(server_name="legacy-server", command=["mock-server"])

    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    mock_proc.stderr = MagicMock()

    sent_messages = []

    def fake_sync_exchange(raw_msg: str) -> str:
        msg = json.loads(raw_msg.strip())
        sent_messages.append(msg)
        if msg.get("method") == "initialize":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "error": {"code": -32601, "message": "Method not found"},
            }) + "\n"
        elif msg.get("method") == "tools/list":
            return json.dumps({
                "jsonrpc": "2.0",
                "id": msg["id"],
                "result": {
                    "tools": [
                        {
                            "name": "legacy_tool",
                            "description": "Legacy tool desc",
                            "inputSchema": {},
                        }
                    ]
                },
            }) + "\n"
        return "{}\n"

    adapter._proc = mock_proc
    adapter._sync_exchange = fake_sync_exchange

    tools = await adapter.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mcp_legacy-server_legacy_tool"


@pytest.mark.asyncio
async def test_mcp_client_handshake_remote_http():
    """Verify remote HTTP/SSE transport also sends initialize before tools/list."""
    import httpx

    posted_requests = []

    def mock_app(request: httpx.Request):
        data = json.loads(request.content.decode("utf-8"))
        posted_requests.append(data)
        if data.get("method") == "initialize":
            return httpx.Response(200, json={
                "jsonrpc": "2.0",
                "id": data["id"],
                "result": {"protocolVersion": "2024-11-05", "capabilities": {}},
            })
        elif data.get("method") == "notifications/initialized":
            return httpx.Response(200, json={})
        elif data.get("method") == "tools/list":
            return httpx.Response(200, json={
                "jsonrpc": "2.0",
                "id": data["id"],
                "result": {"tools": [{"name": "remote_tool", "description": "desc"}]},
            })
        return httpx.Response(400, json={"error": "unsupported"})

    transport = httpx.MockTransport(mock_app)
    adapter = MCPClientAdapter(
        server_name="remote-server",
        transport="sse",
        url="http://localhost:9000/sse",
        _http_transport=transport,
    )

    tools = await adapter.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mcp_remote-server_remote_tool"

    methods_called = [r.get("method") for r in posted_requests]
    assert "initialize" in methods_called
    assert "tools/list" in methods_called
    assert methods_called.index("initialize") < methods_called.index("tools/list")
