"""
MCP Standard Client Adapter & Client Manager [REQ-MCP-001, REQ-MCP-002, REQ-MCP-003].
Implements Model Context Protocol JSON-RPC 2.0 stdio transport client and lifecycle manager.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.gateway.models import ToolDefinition

logger = logging.getLogger(__name__)


class MCPClientAdapter:
    """Standard Model Context Protocol client over stdio subprocess."""

    def __init__(
        self,
        server_name: str,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
    ):
        self.server_name = server_name
        self.command = command
        self.env = env
        self.timeout_seconds = timeout_seconds
        self._proc: Optional[asyncio.subprocess.Process] = None

    async def _send_jsonrpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC 2.0 request over stdio and read response line."""
        if self._proc is None:
            merged_env = {**os.environ, **(self.env or {})} if self.env else None
            self._proc = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=merged_env,
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
        """Execute tool on external MCP server via 'tools/call' with timeout enforcement."""
        clean_name = name
        prefix = f"mcp_{self.server_name}_"
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix) :]

        try:
            res = await asyncio.wait_for(
                self._send_jsonrpc("tools/call", {"name": clean_name, "arguments": arguments}),
                timeout=self.timeout_seconds,
            )
            content_list = res.get("content", [])
            output_text = "\n".join(c.get("text", "") for c in content_list if isinstance(c, dict) and "text" in c)
            return {
                "success": True,
                "output": output_text or res,
                "tool_name": name,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"MCP Tool '{name}' execution timed out after {self.timeout_seconds} seconds.",
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


class MCPClientManager:
    """Manages active MCP server connections and dynamic tool mounting."""

    def __init__(self, tool_registry: ScopedToolRegistry):
        self.tool_registry = tool_registry
        self._adapters: Dict[str, MCPClientAdapter] = {}
        self._mounted_tools: Dict[str, List[str]] = {}

    async def mount_server(
        self,
        name: str,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
    ) -> List[ToolDefinition]:
        """Mount an MCP server and register its discovered tools into ScopedToolRegistry."""
        # Close existing adapter if remounting
        if name in self._adapters:
            await self.unmount_server(name)

        adapter = MCPClientAdapter(
            server_name=name,
            command=command,
            env=env,
            timeout_seconds=timeout_seconds,
        )
        tools = await adapter.list_tools()
        self._adapters[name] = adapter
        self._mounted_tools[name] = [t.name for t in tools]

        # Register each tool into ScopedToolRegistry with dispatch closure
        for tool_def in tools:

            def make_handler(adp: MCPClientAdapter, tool_name: str):
                async def _mcp_dispatch_handler(**kwargs):
                    return await adp.call_tool(tool_name, kwargs)

                return _mcp_dispatch_handler

            self.tool_registry.mount_mcp_tool(
                definition=tool_def,
                handler=make_handler(adapter, tool_def.name),
            )

        logger.info(f"Mounted MCP server '{name}' with {len(tools)} tools.")
        return tools

    async def unmount_server(self, name: str) -> None:
        """Unmount an MCP server and remove its tools from ScopedToolRegistry."""
        adapter = self._adapters.pop(name, None)
        if adapter:
            await adapter.close()

        tool_names = self._mounted_tools.pop(name, [])
        for tool_name in tool_names:
            self.tool_registry.unmount_tool(tool_name)

        logger.info(f"Unmounted MCP server '{name}'.")

    def get_mounted_servers(self) -> Dict[str, Dict[str, Any]]:
        """List all active mounted MCP servers and tool counts."""
        return {
            name: {
                "server_name": name,
                "command": adapter.command,
                "tool_count": len(self._mounted_tools.get(name, [])),
                "tools": self._mounted_tools.get(name, []),
            }
            for name, adapter in self._adapters.items()
        }

    async def shutdown_all(self) -> None:
        """Shutdown all active MCP subprocesses."""
        names = list(self._adapters.keys())
        for name in names:
            await self.unmount_server(name)
