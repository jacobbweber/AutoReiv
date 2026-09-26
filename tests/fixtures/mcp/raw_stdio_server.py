"""Minimal stdio JSON-RPC MCP server for CARD-511 tests. Needs no mcp SDK.

Usage: raw_stdio_server.py <mode>
  good      lists lookup + ping; tools/call echoes the tool name and arguments
  crash     lists the same tools; tools/call raises and the process exits
  empty     lists no tools
  iserror   tools/call returns isError with "city not found"
  badschema lists a tool with an invalid name and a non-object inputSchema
"""

import json
import sys

MODE = sys.argv[1] if len(sys.argv) > 1 else "good"
TOOLS = [
    {
        "name": "lookup",
        "description": "Look up a city",
        "inputSchema": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
    {"name": "ping", "description": "Ping", "inputSchema": {"type": "object", "properties": {}}},
]


def _reply(mid, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    if mid is None:
        continue
    if method == "initialize":
        _reply(mid, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "c511", "version": "0"}})
    elif method == "tools/list":
        if MODE == "empty":
            _reply(mid, {"tools": []})
        elif MODE == "badschema":
            _reply(mid, {"tools": [{"name": "bad name", "description": "x", "inputSchema": "nope"}]})
        else:
            _reply(mid, {"tools": TOOLS})
    elif method == "tools/call":
        if MODE == "crash":
            raise RuntimeError("c511 deliberate failure inside MCP tool")
        if MODE == "iserror":
            _reply(mid, {"content": [{"type": "text", "text": "city not found"}], "isError": True})
        else:
            text = json.dumps({"tool": params.get("name"), "arguments": params.get("arguments")})
            _reply(mid, {"content": [{"type": "text", "text": text}]})
    else:
        _reply(mid, {})
