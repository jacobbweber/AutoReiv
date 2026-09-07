"""
Remote SSH Platform Tools [CARD-160].
"""

import io
import time
from typing import Any, Dict, Optional, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry, get_tool_context
from src.application.skills.command_filter import DangerousCommandFilter
from src.domain.remote.models import RemoteHost


class RemoteTools:
    """Platform tools for managing and inspecting remote servers over SSH."""

    def __init__(self, store: Optional[Any] = None):
        self._store = store

    def _resolve_host_and_secret(self, host_id: str) -> Tuple[RemoteHost, str]:
        if not self._store:
            raise ValueError("State store not configured for RemoteTools.")
        host = self._store.get_remote_host(host_id)
        if not host:
            raise ValueError(f"Remote host '{host_id}' not found.")

        ctx = get_tool_context()
        agent_id = ctx.get("agent_id")
        if agent_id and host.credential_id:
            allowed_creds = set(ctx.get("allowed_credentials") or [])
            resolved_creds = ctx.get("credentials") or {}
            if host.credential_id not in allowed_creds and host.credential_id not in resolved_creds:
                raise PermissionError(
                    f"Agent '{agent_id}' is not authorized to access credential '{host.credential_id}' required for host '{host.id}'."
                )

        secret = ""
        if host.credential_id:
            resolved_creds = ctx.get("credentials") or {}
            if host.credential_id in resolved_creds:
                secret = resolved_creds[host.credential_id]
            else:
                cred = self._store.get_credential(host.credential_id)
                if cred and cred.secret:
                    secret = cred.secret

        return host, secret

    def _create_ssh_client(self, host: RemoteHost, secret: str, timeout: float = 15.0):
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if host.auth_type == "key" or (secret and "-----BEGIN" in secret):
            pkey = None
            key_f = io.StringIO(secret)
            for key_cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey):
                try:
                    key_f.seek(0)
                    pkey = key_cls.from_private_key(key_f)
                    break
                except Exception:
                    continue
            client.connect(
                hostname=host.host,
                port=host.port or 22,
                username=host.username,
                pkey=pkey,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        else:
            client.connect(
                hostname=host.host,
                port=host.port or 22,
                username=host.username,
                password=secret or None,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        return client

    async def ssh_exec_command(
        self,
        host_id: str,
        command: str,
        cwd: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Execute a shell command on a remote host over SSH."""
        start_time = time.perf_counter()

        is_bad, reason = DangerousCommandFilter.is_dangerous(command)
        if is_bad:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": reason or "Prohibited dangerous command",
                "error": reason or "Prohibited dangerous command",
                "duration_ms": 0.0,
            }

        try:
            host, secret = self._resolve_host_and_secret(host_id)
        except PermissionError as pe:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(pe),
                "error": str(pe),
                "duration_ms": 0.0,
            }
        except Exception as exc:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
                "error": str(exc),
                "duration_ms": 0.0,
            }

        cmd_to_run = f"cd {cwd} && {command}" if cwd else command

        try:
            client = self._create_ssh_client(host, secret, timeout=min(timeout, 15.0))
            try:
                _stdin, stdout, stderr = client.exec_command(cmd_to_run, timeout=timeout)
                out_bytes = stdout.read()
                err_bytes = stderr.read()
                exit_code = stdout.channel.recv_exit_status()

                dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "exit_code": exit_code,
                    "stdout": out_bytes.decode("utf-8", errors="replace"),
                    "stderr": err_bytes.decode("utf-8", errors="replace"),
                    "error": None,
                    "duration_ms": dur_ms,
                }
            finally:
                client.close()
        except Exception as exc:
            dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(exc),
                "error": str(exc),
                "duration_ms": dur_ms,
            }

    async def ssh_read_file(self, host_id: str, file_path: str) -> Dict[str, Any]:
        """Safely read the content of a file on a remote host via SFTP."""
        start_time = time.perf_counter()
        try:
            host, secret = self._resolve_host_and_secret(host_id)
        except PermissionError as pe:
            return {
                "success": False,
                "file_path": file_path,
                "content": "",
                "error": str(pe),
                "duration_ms": 0.0,
            }
        except Exception as exc:
            return {
                "success": False,
                "file_path": file_path,
                "content": "",
                "error": str(exc),
                "duration_ms": 0.0,
            }

        try:
            client = self._create_ssh_client(host, secret, timeout=15.0)
            try:
                sftp = client.open_sftp()
                try:
                    with sftp.open(file_path, "r") as f:
                        data = f.read()
                    content_str = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
                    dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return {
                        "success": True,
                        "file_path": file_path,
                        "content": content_str,
                        "size_bytes": len(content_str),
                        "error": None,
                        "duration_ms": dur_ms,
                    }
                finally:
                    sftp.close()
            finally:
                client.close()
        except Exception as exc:
            dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "file_path": file_path,
                "content": "",
                "error": str(exc),
                "duration_ms": dur_ms,
            }

    async def ssh_inspect_environment(self, host_id: str) -> Dict[str, Any]:
        """Perform a read-only environment probe on a remote host."""
        start_time = time.perf_counter()
        try:
            host, secret = self._resolve_host_and_secret(host_id)
        except PermissionError as pe:
            return {
                "success": False,
                "host_id": host_id,
                "error": str(pe),
                "duration_ms": 0.0,
            }
        except Exception as exc:
            return {
                "success": False,
                "host_id": host_id,
                "error": str(exc),
                "duration_ms": 0.0,
            }

        try:
            client = self._create_ssh_client(host, secret, timeout=15.0)
            try:
                def run_cmd(c):
                    _, stdout, stderr = client.exec_command(c, timeout=10.0)
                    out = stdout.read().decode("utf-8", errors="replace").strip()
                    return out

                os_info = run_cmd("uname -srm || ver")
                uptime_info = run_cmd("uptime || net statistics server")
                disk_info = run_cmd("df -h / || wmic logicaldisk get caption,freespace,size")

                dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "success": True,
                    "host_id": host_id,
                    "label": host.label,
                    "os": os_info,
                    "uptime": uptime_info,
                    "disk_usage": disk_info,
                    "error": None,
                    "duration_ms": dur_ms,
                }
            finally:
                client.close()
        except Exception as exc:
            dur_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "host_id": host_id,
                "error": str(exc),
                "duration_ms": dur_ms,
            }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register remote host tools in the scoped registry."""
        registry.register_tool(
            name="ssh_exec_command",
            description="Execute a shell command on a configured remote host over SSH. Target host must be configured in Settings Studio, and the calling agent must have permission to the host's credential.",
            parameters={
                "type": "object",
                "properties": {
                    "host_id": {"type": "string", "description": "Identifier of the remote host (e.g. 'game-server')"},
                    "command": {"type": "string", "description": "Shell command to execute on the remote host"},
                    "cwd": {"type": "string", "description": "Optional working directory on the remote host"},
                    "timeout": {"type": "number", "description": "Command timeout in seconds (default 30)", "default": 30.0},
                },
                "required": ["host_id", "command"],
            },
            handler=self.ssh_exec_command,
        )

        registry.register_tool(
            name="ssh_read_file",
            description="Safely read the content of a remote file over SFTP without running arbitrary scripts.",
            parameters={
                "type": "object",
                "properties": {
                    "host_id": {"type": "string", "description": "Identifier of the remote host"},
                    "file_path": {"type": "string", "description": "Full remote file path (e.g. '/var/log/syslog')"},
                },
                "required": ["host_id", "file_path"],
            },
            handler=self.ssh_read_file,
        )

        registry.register_tool(
            name="ssh_inspect_environment",
            description="Run a non-mutating system probe on a remote host to discover OS, uptime, and disk usage.",
            parameters={
                "type": "object",
                "properties": {
                    "host_id": {"type": "string", "description": "Identifier of the remote host"},
                },
                "required": ["host_id"],
            },
            handler=self.ssh_inspect_environment,
        )
