"""
MCP Standard Client Adapter [REQ-MCP-001, REQ-MCP-002, REQ-MCP-003].
Implements Model Context Protocol JSON-RPC 2.0 stdio transport client.
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

from src.domain.gateway.models import ToolDefinition


class MCPClientAdapter:
    """Standard Model Context Protocol client over stdio subprocess."""

    def __init__(
        self,
        server_name: str,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
    ):
        self.server_name = server_name
        self.command = command
        self.env = env
        self._proc: Optional[asyncio.subprocess.Process] = None

    async def _send_jsonrpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC 2.0 request over stdio and read response line."""
        if self._proc is None:
            self._proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

        req_id = str(uuid.uuid4())
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        raw_msg = json.dumps(msg) + "\n"
        if self._proc.stdin:
            self._proc.stdin.write(raw_msg.encode("utf-8"))
            await self._proc.stdin.drain()

        if self._proc.stdout:
            line = await self._proc.stdout.readline()
            if line:
                payload = json.loads(line.decode("utf-8"))
                if "error" in payload:
                    raise RuntimeError(f"MCP JSON-RPC Error: {payload['error']}")
                return payload.get("result", {})

        return {}

    async def list_tools(self) -> List[ToolDefinition]:
        """Query external MCP server for available tools via 'tools/list'."""
        res = await self._send_jsonrpc("tools/list")
        tools_data = res.get("tools", [])
        tool_definitions: List[ToolDefinition] = []

        for item in tools_data:
            orig_name = item.get("name", "unknown")
            scoped_name = f"mcp_{self.server_name}_{orig_name}"
            desc = item.get("description", f"MCP Tool {orig_name}")
            schema = item.get("inputSchema", {})
            tool_definitions.append(
                ToolDefinition(
                    name=scoped_name,
                    description=desc,
                    parameters=schema,
                )
            )

        return tool_definitions

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on external MCP server via 'tools/call'."""
        clean_name = name
        prefix = f"mcp_{self.server_name}_"
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix) :]

        try:
            res = await self._send_jsonrpc("tools/call", {"name": clean_name, "arguments": arguments})
            content_list = res.get("content", [])
            output_text = "\n".join(c.get("text", "") for c in content_list if isinstance(c, dict) and "text" in c)
            return {
                "success": True,
                "output": output_text or res,
                "tool_name": name,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool_name": name,
            }

    async def close(self) -> None:
        """Terminate the MCP stdio subprocess."""
        if self._proc:
            try:
                self._proc.terminate()
                await self._proc.wait()
            except Exception:
                pass
            self._proc = None
