"""
Zero-dependency Python Model Context Protocol (MCP) Server micro-framework [REQ-DELIV-002].
Standard JSON-RPC 2.0 stdio server for Agent Pack process isolation.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional, get_type_hints


def _python_type_to_json_schema(py_type: Any) -> Dict[str, Any]:
    if py_type in (int, float):
        return {"type": "number" if py_type is float else "integer"}
    if py_type is bool:
        return {"type": "boolean"}
    if py_type is str:
        return {"type": "string"}
    if py_type in (list, List):
        return {"type": "array"}
    if py_type in (dict, Dict):
        return {"type": "object"}
    return {"type": "string"}


def derive_input_schema(fn: Callable[..., Any]) -> Dict[str, Any]:
    """Derive JSON schema from callable signature and type annotations."""
    sig = inspect.signature(fn)
    hints = {}
    try:
        hints = get_type_hints(fn)
    except Exception:
        pass

    properties: Dict[str, Any] = {}
    required: List[str] = []

    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        py_type = hints.get(name, str)
        schema = _python_type_to_json_schema(py_type)
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            schema["default"] = param.default
        properties[name] = schema

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


class PackMCPServer:
    """
    Lightweight, dependency-free MCP server base class.
    Executes in a dedicated child process, isolating host commands from AutoReiv.
    """

    def __init__(self, name: str, version: str = "1.0.0", protocol_version: str = "2024-11-05"):
        self.name = name
        self.version = version
        self.protocol_version = protocol_version
        self._tools: Dict[str, Dict[str, Any]] = {}

    def tool(
        self,
        name: Optional[str] = None,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a function as an MCP tool."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or fn.__name__
            desc = description or (inspect.getdoc(fn) or f"Tool {tool_name}").split("\n\n")[0].strip()
            schema = input_schema or derive_input_schema(fn)
            self.register_tool(name=tool_name, handler=fn, description=desc, input_schema=schema)
            return fn

        return decorator

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a tool handler function."""
        schema = input_schema or derive_input_schema(handler)
        self._tools[name] = {
            "name": name,
            "description": description or f"Tool {name}",
            "inputSchema": schema,
            "handler": handler,
        }

    def list_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return MCP tools/list definitions."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in self._tools.values()
        ]

    async def handle_request_async(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single JSON-RPC 2.0 request."""
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        if not method or not isinstance(method, str):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: missing method"},
            }

        # 1. initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": self.version},
                },
            }

        # 2. notifications/initialized or ping
        if method in ("notifications/initialized", "initialized"):
            return {}  # Notifications do not return responses
        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        # 3. tools/list
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.list_tool_definitions()},
            }

        # 4. tools/call
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}

            if tool_name not in self._tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
                }

            handler = self._tools[tool_name]["handler"]
            try:
                if inspect.iscoroutinefunction(handler):
                    output = await handler(**arguments)
                else:
                    output = handler(**arguments)

                # Format output as standard MCP text content
                if isinstance(output, str):
                    text_content = output
                else:
                    try:
                        text_content = json.dumps(output, indent=2)
                    except Exception:
                        text_content = str(output)

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": text_content}]},
                }
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": err_msg}],
                        "isError": True,
                    },
                }

        # Unknown method
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for handle_request_async."""
        return asyncio.run(self.handle_request_async(req))

    def run_stdio(self) -> None:
        """Run standard stdio loop reading JSON-RPC lines from sys.stdin."""
        # Ensure UTF-8 IO
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                req = json.loads(line)
                resp = self.handle_request(req)
                if resp:  # Do not respond to notifications
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except KeyboardInterrupt:
                break
            except Exception as e:
                sys.stderr.write(f"PackMCPServer Error: {e}\n")
                sys.stderr.flush()
