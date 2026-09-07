"""
Unit and integration tests for PackMCPServer micro-framework [REQ-DELIV-002].
"""

import json
import sys
from pathlib import Path

import pytest

from src.infrastructure.mcp.client_adapter import MCPClientAdapter
from src.infrastructure.mcp.pack_server import PackMCPServer


def test_pack_mcp_server_tool_registration():
    server = PackMCPServer(name="test-server", version="1.0.0")

    @server.tool(name="echo_test", description="Test echo tool")
    def echo(message: str, count: int = 1) -> dict:
        return {"echo": message * count}

    tools = server.list_tool_definitions()
    assert len(tools) == 1
    t = tools[0]
    assert t["name"] == "echo_test"
    assert t["description"] == "Test echo tool"
    props = t["inputSchema"]["properties"]
    assert "message" in props
    assert "count" in props


@pytest.mark.asyncio
async def test_pack_mcp_server_dispatch_requests():
    server = PackMCPServer(name="dispatch-server", version="1.0.0")

    @server.tool(name="calc_add", description="Add two numbers")
    def add(a: int, b: int) -> dict:
        return {"sum": a + b}

    # 1. initialize
    init_res = await server.handle_request_async(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert init_res.get("result", {}).get("serverInfo", {}).get("name") == "dispatch-server"
    assert "tools" in init_res.get("result", {}).get("capabilities", {})

    # 2. tools/list
    list_res = await server.handle_request_async(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    tools = list_res.get("result", {}).get("tools", [])
    assert len(tools) == 1
    assert tools[0]["name"] == "calc_add"

    # 3. tools/call success
    call_res = await server.handle_request_async(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "calc_add", "arguments": {"a": 3, "b": 7}},
        }
    )
    content = call_res.get("result", {}).get("content", [])
    assert len(content) > 0
    parsed = json.loads(content[0]["text"])
    assert parsed.get("sum") == 10

    # 4. tools/call unknown tool error
    call_err = await server.handle_request_async(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "non_existent", "arguments": {}},
        }
    )
    assert "error" in call_err
    assert call_err["error"]["code"] == -32601

    # 5. unknown method
    method_err = await server.handle_request_async(
        {"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}}
    )
    assert "error" in method_err


@pytest.mark.asyncio
async def test_pack_mcp_server_subprocess_client_integration(tmp_path: Path):
    """End-to-end integration: Run PackMCPServer in a child process and query via MCPClientAdapter."""
    script_path = tmp_path / "server_entry.py"
    script_code = '''
import sys
from src.infrastructure.mcp.pack_server import PackMCPServer

server = PackMCPServer(name="integration-server")

@server.tool(name="ping", description="Ping test")
def ping(payload: str = "pong") -> dict:
    return {"status": "ok", "reply": payload}

if __name__ == "__main__":
    server.run_stdio()
'''
    script_path.write_text(script_code, encoding="utf-8")

    import os
    env = {**os.environ, "PYTHONPATH": str(Path.cwd())}
    adapter = MCPClientAdapter(
        server_name="integration",
        command=[sys.executable, "-u", str(script_path)],
        env=env,
        timeout_seconds=5.0,
    )

    try:
        tools = await adapter.list_tools()
        if not tools and adapter._proc and adapter._proc.stderr:
            err = await adapter._proc.stderr.read()
            print("SUBPROCESS STDERR:", err.decode("utf-8", errors="replace"))
        assert len(tools) == 1
        assert tools[0].name == "mcp_integration_ping"

        result = await adapter.call_tool("ping", {"payload": "hello-world"})
        assert result["success"] is True
        output = result["output"]
        assert "hello-world" in output
        assert "status" in output
    finally:
        await adapter.close()
