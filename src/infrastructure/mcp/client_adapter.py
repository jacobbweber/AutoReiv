"""
MCP Standard Client Adapter & Client Manager [REQ-MCP-001, REQ-MCP-002, REQ-MCP-003].
Implements Model Context Protocol JSON-RPC 2.0 stdio transport client and lifecycle manager.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.domain.gateway.models import ToolDefinition

logger = logging.getLogger(__name__)


class MCPClientAdapter:
    """Standard Model Context Protocol client over stdio subprocess."""

    def __init__(
        self,
        server_name: str,
        command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
        transport: str = "stdio",
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        _http_transport: Optional[Any] = None,
    ):
        self.server_name = server_name
        self.command = command or []
        self.env = env
        self.timeout_seconds = timeout_seconds
        self.transport = (transport or "stdio").lower()
        self.url = url
        self.headers = headers or {}
        self._http_transport = _http_transport
        self._proc: Optional[subprocess.Popen] = None
        self._lock = asyncio.Lock()

    async def _send_jsonrpc_remote(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC 2.0 request over HTTP/SSE endpoint."""
        import httpx

        req_id = str(uuid.uuid4())
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        client_kwargs: Dict[str, Any] = {"timeout": self.timeout_seconds}
        if self._http_transport is not None:
            client_kwargs["transport"] = self._http_transport

        merged_headers = {"Content-Type": "application/json", **self.headers}
        target_url = self.url or ""
        if not target_url:
            raise RuntimeError(f"Remote MCP server '{self.server_name}' has no URL configured.")

        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.post(target_url, json=msg, headers=merged_headers)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Remote MCP server '{self.server_name}' returned status {resp.status_code}: {resp.text}"
                )
            payload = resp.json()
            if "error" in payload:
                raise RuntimeError(f"MCP JSON-RPC Error: {payload['error']}")
            return payload.get("result", {})

    def _sync_exchange(self, raw_msg: str) -> str:
        """Synchronously write JSON-RPC request to stdin and read response from stdout."""
        if self._proc is None:
            raise RuntimeError(f"MCP server '{self.server_name}' process is not running.")
        if self._proc.poll() is not None:
            err = self._proc.stderr.read() if self._proc.stderr else ""
            raise RuntimeError(f"MCP server '{self.server_name}' exited with code {self._proc.returncode}: {err}")

        self._proc.stdin.write(raw_msg)
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        if not line and self._proc.poll() is not None:
            err = self._proc.stderr.read() if self._proc.stderr else ""
            raise RuntimeError(f"MCP server '{self.server_name}' process terminated unexpectedly: {err}")
        return line

    async def _send_jsonrpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send JSON-RPC 2.0 request over remote transport or stdio subprocess."""
        if self.transport == "sse" or (self.url and not self.command):
            return await self._send_jsonrpc_remote(method, params)

        async with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                merged_env = {**os.environ, **(self.env or {})} if self.env else None
                self._proc = subprocess.Popen(
                    self.command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env=merged_env,
                    bufsize=1,
                )

            req_id = str(uuid.uuid4())
            msg = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params or {},
            }
            raw_msg = json.dumps(msg) + "\n"
            loop = asyncio.get_running_loop()
            line = await loop.run_in_executor(None, self._sync_exchange, raw_msg)
            if line:
                payload = json.loads(line)
                if "error" in payload:
                    raise RuntimeError(f"MCP JSON-RPC Error: {payload['error']}")
                return payload.get("result", {})

            return {}

    def get_stderr(self) -> str:
        """Read standard error from the subprocess if available."""
        if self._proc and self._proc.stderr:
            try:
                return self._proc.stderr.read() or ""
            except Exception:
                return ""
        return ""

    async def list_tools(self) -> List[ToolDefinition]:
        """Query external MCP server for available tools via 'tools/list'."""
        try:
            res = await asyncio.wait_for(
                self._send_jsonrpc("tools/list"),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            logger.warning(f"MCP server '{self.server_name}' tools/list failed: {exc}")
            return []

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
            if res.get("isError"):
                return {
                    "success": False,
                    "error": output_text or f"MCP tool {name} returned error status.",
                    "tool_name": name,
                }
            return {
                "success": True,
                "output": output_text or res,
                "tool_name": name,
            }
        except asyncio.TimeoutError:
            await self.close()
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
            proc = self._proc
            self._proc = None
            try:
                proc.terminate()
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._sync_close, proc)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    @staticmethod
    def _sync_close(proc: subprocess.Popen) -> None:
        try:
            proc.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1.0)
        except Exception:
            pass


class MCPClientManager:
    """Manages active MCP server connections and dynamic tool mounting."""

    def __init__(self, tool_registry: ScopedToolRegistry):
        self.tool_registry = tool_registry
        self._adapters: Dict[str, MCPClientAdapter] = {}
        self._mounted_tools: Dict[str, List[str]] = {}

    async def mount_server(
        self,
        name: str,
        command: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
        transport: str = "stdio",
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        _http_transport: Optional[Any] = None,
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
            transport=transport,
            url=url,
            headers=headers,
            _http_transport=_http_transport,
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
                "transport": adapter.transport,
                "url": adapter.url,
                "command": adapter.command,
                "tool_count": len(self._mounted_tools.get(name, [])),
                "tools": self._mounted_tools.get(name, []),
            }
            for name, adapter in self._adapters.items()
        }

    async def mount_agent_pack_server(
        self,
        agent_id: str,
        pack_dir: Union[str, Path],
        timeout_seconds: float = 30.0,
    ) -> List[ToolDefinition]:
        """Mount an agent-scoped MCP server from packs/<agent_id>/ [CARD-176, CARD-183, REQ-DELIV-004]."""
        p_dir = Path(pack_dir)
        mcp_script = p_dir / "mcp" / "server.py"
        pack_json_file = p_dir / "pack.json"

        mounted_tools: List[ToolDefinition] = []

        if pack_json_file.is_file():
            try:
                data = json.loads(pack_json_file.read_text(encoding="utf-8"))
                # Support both mcp_servers list and single mcp_server config
                cfg_list: List[dict] = []
                if isinstance(data.get("mcp_servers"), list):
                    cfg_list.extend(data["mcp_servers"])
                if isinstance(data.get("mcp_server"), dict):
                    single = data["mcp_server"]
                    if not any(c.get("name") == single.get("name") for c in cfg_list):
                        cfg_list.append(single)

                for idx, server_cfg in enumerate(cfg_list):
                    if server_cfg.get("enabled") is False:
                        continue
                    srv_name = server_cfg.get("name") or f"pack_{agent_id}"
                    if idx > 0 and srv_name == f"pack_{agent_id}":
                        srv_name = f"pack_{agent_id}_{idx}"

                    transport = server_cfg.get("transport", "stdio")
                    url = server_cfg.get("url")
                    headers = server_cfg.get("headers")
                    env = {**os.environ, "PYTHONPATH": str(Path.cwd()), **(server_cfg.get("env") or {})}

                    cmd: Optional[List[str]] = None
                    if transport != "sse" and not url:
                        custom_script = p_dir / (server_cfg.get("entrypoint") or "mcp/server.py")
                        script_to_run = custom_script if custom_script.is_file() else mcp_script
                        if not script_to_run.is_file():
                            continue
                        cmd = list(server_cfg.get("command") or [sys.executable, "-u", str(script_to_run)])

                    tools = await self.mount_server(
                        name=srv_name,
                        command=cmd,
                        env=env,
                        timeout_seconds=timeout_seconds,
                        transport=transport,
                        url=url,
                        headers=headers,
                    )
                    mounted_tools.extend(tools)
                return mounted_tools
            except Exception as e:
                logger.warning(f"Failed to read mcp_server config in {pack_json_file}: {e}")

        # Fallback to local mcp/server.py if no pack.json or unconfigured
        if mcp_script.is_file():
            server_name = f"pack_{agent_id}"
            command = [sys.executable, "-u", str(mcp_script)]
            env = {**os.environ, "PYTHONPATH": str(Path.cwd())}
            return await self.mount_server(
                name=server_name,
                command=command,
                env=env,
                timeout_seconds=timeout_seconds,
            )
        return []

    async def unmount_agent_pack_server(self, agent_id: str) -> None:
        """Unmount an agent-scoped MCP server [CARD-176]."""
        await self.unmount_server(f"pack_{agent_id}")

    async def shutdown_all(self) -> None:
        """Shutdown all active MCP subprocesses."""
        names = list(self._adapters.keys())
        for name in names:
            await self.unmount_server(name)
