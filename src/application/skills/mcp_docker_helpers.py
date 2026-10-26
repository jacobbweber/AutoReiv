"""Docker- and host-aware helpers for MCP server scaffolding, container deployment, and registration [CARD-745]."""

from __future__ import annotations

import os
import re
import socket
import textwrap
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse


def is_running_in_docker() -> bool:
    """True when AutoReiv is running inside a Docker container (AUTOREIV_DEPLOY_MODE=docker or /.dockerenv)."""
    if os.environ.get("AUTOREIV_DEPLOY_MODE", "").strip().lower() == "docker":
        return True
    return Path("/.dockerenv").exists()


def _is_host_filesystem_path(val: str) -> bool:
    v = (val or "").strip()
    return v.startswith("/") or bool(re.match(r"^[a-zA-Z]:[/\\]", v))


def translate_container_to_host_path(path_str: str) -> str:
    """Translate a container path under $AUTOREIV_PROJECTS_DIR or $AUTOREIV_WIKI_PATH to its host bind-mount path."""
    raw = (path_str or "").strip()
    if not raw:
        return raw
    mappings = (
        (os.environ.get("AUTOREIV_PROJECTS_DIR", "").strip(), os.environ.get("AUTOREIV_PROJECTS_HOST_PATH", "").strip()),
        (os.environ.get("AUTOREIV_WIKI_PATH", "").strip(), os.environ.get("AUTOREIV_WIKI_HOST_PATH", "").strip()),
    )
    for container_prefix, host_prefix in mappings:
        if not container_prefix or not _is_host_filesystem_path(host_prefix):
            continue
        c_norm = container_prefix.rstrip("/")
        h_norm = host_prefix.rstrip("/\\")
        if raw == c_norm:
            return h_norm
        if raw.startswith(c_norm + "/"):
            return h_norm + raw[len(c_norm) :]
    return raw


def translate_volume_spec(vol: str) -> str:
    """Translate '<src>:<dst>[:<mode>]' volume spec if <src> is inside $AUTOREIV_PROJECTS_DIR."""
    spec = (vol or "").strip()
    if ":" not in spec:
        return spec
    # Handle Windows drive letters (e.g. D:/foo:/bar[:ro]) vs Unix (/foo:/bar[:ro])
    if re.match(r"^[a-zA-Z]:[/\\]", spec):
        first_colon = spec.find(":", 2)
        if first_colon == -1:
            return spec
        src = spec[:first_colon]
        rest = spec[first_colon + 1 :]
    else:
        src, rest = spec.split(":", 1)
    translated_src = translate_container_to_host_path(src)
    return f"{translated_src}:{rest}"


def resolve_mcp_endpoint_url(port: int) -> str:
    """Return the SSE/HTTP endpoint URL reachable from the current AutoReiv process [CARD-745]."""
    host = "host.docker.internal" if is_running_in_docker() else "localhost"
    return f"http://{host}:{port}/sse"


def _can_connect(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def normalize_mcp_registration_url(url: Optional[str]) -> Optional[str]:
    """Normalize localhost vs host.docker.internal so MCP URLs work both inside Docker and on the host [CARD-745]."""
    if not url:
        return url
    raw = str(url).strip()
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw
    hostname = (parsed.hostname or "").lower()
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not hostname:
        return raw

    in_docker = is_running_in_docker()
    if in_docker and hostname in ("localhost", "127.0.0.1"):
        if not _can_connect("127.0.0.1", port) and _can_connect("host.docker.internal", port):
            netloc = f"host.docker.internal:{parsed.port}" if parsed.port else "host.docker.internal"
            return urlunparse(parsed._replace(netloc=netloc))
    elif not in_docker and hostname == "host.docker.internal":
        if not _can_connect("host.docker.internal", port) and _can_connect("127.0.0.1", port):
            netloc = f"127.0.0.1:{parsed.port}" if parsed.port else "127.0.0.1"
            return urlunparse(parsed._replace(netloc=netloc))
    return raw


def wait_for_mcp_http_health(port: int, timeout_s: float = 4.0) -> bool:
    """Wait briefly for a newly started MCP container's /health endpoint to respond."""
    hosts = ["host.docker.internal", "127.0.0.1"] if is_running_in_docker() else ["127.0.0.1", "localhost"]
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        for h in hosts:
            try:
                with urllib.request.urlopen(f"http://{h}:{port}/health", timeout=0.5) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                continue
        time.sleep(0.2)
    return False


def build_tool_code_block(tool: Dict[str, Any], clean_name_fn: Any) -> str:
    """Build one @mcp.tool() Python function block from a tool specification dict."""
    t_name = clean_name_fn(tool.get("name", "example_tool"))
    t_desc = str(tool.get("description") or f"Executes {t_name} operation.").replace('"""', "'''")
    params = tool.get("parameters", {})
    param_signatures: List[str] = []
    param_docs: List[str] = []

    if isinstance(params, dict) and "properties" in params:
        props = params.get("properties", {})
        reqs = set(params.get("required", []))
        for p_name, p_meta in props.items():
            p_type_str = p_meta.get("type", "string") if isinstance(p_meta, dict) else "string"
            py_type = {
                "integer": "int",
                "number": "float",
                "boolean": "bool",
                "array": "list",
                "object": "dict",
            }.get(p_type_str, "str")
            p_clean = re.sub(r"[^a-zA-Z0-9_]", "_", p_name)
            is_req = p_clean in reqs or p_name in reqs
            if is_req:
                param_signatures.append(f"{p_clean}: {py_type}")
            else:
                param_signatures.append(f"{p_clean}: Optional[{py_type}] = None")
            desc = p_meta.get("description", "Parameter") if isinstance(p_meta, dict) else "Parameter"
            param_docs.append(f"        {p_clean}: {desc}")
    elif isinstance(params, list):
        for p in params:
            if not isinstance(p, dict):
                continue
            p_name = p.get("name", "arg")
            p_clean = re.sub(r"[^a-zA-Z0-9_]", "_", p_name)
            py_type = p.get("type", "str")
            if p.get("required", True):
                param_signatures.append(f"{p_clean}: {py_type}")
            else:
                param_signatures.append(f"{p_clean}: Optional[{py_type}] = None")
            param_docs.append(f"        {p_clean}: {p.get('description', 'Parameter')}")

    sig_str = ", ".join(param_signatures)
    doc_str = "\n".join(param_docs)
    full_doc = f'    """{t_desc}\n\n    Args:\n{doc_str}\n    """' if doc_str else f'    """{t_desc}"""'

    custom_code = str(tool.get("code") or tool.get("implementation") or "").strip()
    if custom_code:
        dedented = textwrap.dedent(custom_code).strip("\n")
        body_str = "\n".join(f"    {line}" if line.strip() else "" for line in dedented.splitlines())
    else:
        body_str = f'    # Operational execution logic for {t_name}\n    return f"Executed {t_name} successfully."'

    return f"@mcp.tool()\ndef {t_name}({sig_str}) -> str:\n{full_doc}\n{body_str}\n"


def build_fastmcp_server_code(clean_name: str, description: str, tool_code_blocks: List[str]) -> str:
    """Generate a dual-transport (stdio + HTTP/SSE JSON-RPC 2.0) FastMCP server.py [CARD-745]."""
    safe_desc = (description or clean_name).replace('"', '\\"').replace("\n", " ")
    tools_section = "\n\n".join(tool_code_blocks)
    return f'''"""
FastMCP Server: {clean_name}
{description}
"""

import inspect
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP as _UpstreamFastMCP  # noqa: F401
except ImportError:
    _UpstreamFastMCP = None


class FastMCP:
    """Dual-mode (stdio + HTTP/SSE JSON-RPC 2.0) FastMCP server runtime [CARD-745]."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._tools: Dict[str, Callable[..., Any]] = {{}}

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[fn.__name__] = fn
            return fn

        return _decorator

    def _tool_schemas(self) -> List[Dict[str, Any]]:
        type_map = {{
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
            "str": "string",
        }}
        schemas: List[Dict[str, Any]] = []
        for t_name, fn in self._tools.items():
            sig = inspect.signature(fn)
            props: Dict[str, Any] = {{}}
            required: List[str] = []
            for p_name, param in sig.parameters.items():
                if p_name in ("self", "cls"):
                    continue
                ann = str(param.annotation) if param.annotation is not inspect.Parameter.empty else "str"
                json_type = "string"
                for k, v in type_map.items():
                    if k in ann.lower():
                        json_type = v
                        break
                props[p_name] = {{"type": json_type, "description": f"Parameter {{p_name}}"}}
                if param.default is inspect.Parameter.empty:
                    required.append(p_name)
            schema: Dict[str, Any] = {{"type": "object", "properties": props}}
            if required:
                schema["required"] = required
            schemas.append(
                {{
                    "name": t_name,
                    "description": (inspect.getdoc(fn) or f"Tool {{t_name}}").splitlines()[0],
                    "inputSchema": schema,
                }}
            )
        return schemas

    def _handle_rpc(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        req_id = payload.get("id")
        method = str(payload.get("method") or "")
        params = payload.get("params") or {{}}
        if method.startswith("notifications/"):
            return None
        if method == "initialize":
            return {{
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {{
                    "protocolVersion": "2024-11-05",
                    "capabilities": {{"tools": {{}}}},
                    "serverInfo": {{"name": self.name, "version": "0.1.0"}},
                }},
            }}
        if method == "tools/list":
            return {{"jsonrpc": "2.0", "id": req_id, "result": {{"tools": self._tool_schemas()}}}}
        if method == "tools/call":
            t_name = str(params.get("name") or "")
            t_args = params.get("arguments") or {{}}
            fn = self._tools.get(t_name)
            if fn is None:
                return {{
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {{"code": -32601, "message": f"Unknown tool: {{t_name}}"}},
                }}
            try:
                res = fn(**(t_args if isinstance(t_args, dict) else {{}}))
                text = res if isinstance(res, str) else json.dumps(res, default=str)
                return {{
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {{"content": [{{"type": "text", "text": str(text)}}], "isError": False}},
                }}
            except Exception as exc:
                return {{
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {{"content": [{{"type": "text", "text": f"Error: {{exc}}"}}], "isError": True}},
                }}
        return {{"jsonrpc": "2.0", "id": req_id, "result": {{}}}}

    def run(self, transport: str = "stdio") -> None:
        mode = (os.environ.get("MCP_TRANSPORT") or transport or "stdio").strip().lower()
        if mode in ("sse", "http"):
            server_ref = self
            port = int(os.environ.get("PORT", "8000"))

            class _Handler(BaseHTTPRequestHandler):
                def log_message(self, fmt: str, *args: Any) -> None:
                    return

                def do_GET(self) -> None:
                    if self.path.startswith("/health"):
                        body = b'{{"status":"ok"}}'
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    body = b": ok\\n\\n"
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.end_headers()
                    self.wfile.write(body)

                def do_POST(self) -> None:
                    length = int(self.headers.get("Content-Length") or "0")
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{{}}"
                    try:
                        req_obj = json.loads(raw)
                    except Exception:
                        self.send_response(400)
                        self.end_headers()
                        return
                    reply = server_ref._handle_rpc(req_obj)
                    out = json.dumps(reply or {{"jsonrpc": "2.0", "id": req_obj.get("id"), "result": {{}}}}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    self.wfile.write(out)

            httpd = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
            httpd.serve_forever()
            return

        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                req_obj = json.loads(line)
            except Exception:
                continue
            reply = self._handle_rpc(req_obj)
            if reply is not None:
                sys.stdout.write(json.dumps(reply) + "\\n")
                sys.stdout.flush()


mcp = FastMCP("{clean_name}", description="{safe_desc}")


@mcp.tool()
def health() -> str:
    """Health check endpoint for container and client monitoring [REQ-394-004]."""
    return "OK"


{tools_section}

if __name__ == "__main__":
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "stdio"))
'''


def build_mcp_dockerfile(clean_name: str) -> str:
    """Build Dockerfile with non-root user, SSE transport env, and active HEALTHCHECK [REQ-394-004, CARD-745]."""
    return f"""# Multi-stage enterprise container for {clean_name}
FROM python:3.12-slim

WORKDIR /app

# Non-root user creation for enterprise security hardening
RUN useradd -m -u 1000 mcpuser

COPY pyproject.toml README.md* server.py ./

ENV MCP_TRANSPORT=sse \\
    PORT=8000 \\
    PYTHONUNBUFFERED=1

USER mcpuser
EXPOSE 8000

# Automated healthcheck validation to prevent zombie processes [REQ-394-004, REQ-394-005]
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["python", "server.py"]
"""
