"""
Injectable serve restarter for post-update restart [CARD-451 REQ-451-006, REQ-451-012].

Tests inject a no-op / recording restarter so nothing is ever restarted.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class ServeRestarter(Protocol):
    def schedule_restart(self, *, host: str, port: int, repo_root: Path) -> bool:
        """Schedule a process restart after the current HTTP response returns."""
        ...


class NoOpRestarter:
    """Test double — never restarts anything."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def schedule_restart(self, *, host: str, port: int, repo_root: Path) -> bool:
        self.calls.append({"host": host, "port": port, "repo_root": str(repo_root)})
        return True


class DetachedScriptRestarter:
    """Spawn scripts/restart_serve.ps1 (Windows) or restart_serve.py detached."""

    def schedule_restart(self, *, host: str, port: int, repo_root: Path) -> bool:
        root = Path(repo_root)
        try:
            if sys.platform.startswith("win"):
                ps1 = root / "scripts" / "restart_serve.ps1"
                if not ps1.is_file():
                    logger.error("restart_serve.ps1 missing at %s", ps1)
                    return False
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1),
                    "-HostAddr",
                    str(host),
                    "-Port",
                    str(port),
                ]
                creation = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) | getattr(
                    subprocess, "DETACHED_PROCESS", 0x00000008
                )
                subprocess.Popen(
                    cmd,
                    cwd=str(root),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creation,
                    close_fds=True,
                )
            else:
                py = root / "scripts" / "restart_serve.py"
                cmd = [
                    sys.executable,
                    str(py),
                    "--host",
                    str(host),
                    "--port",
                    str(port),
                ]
                subprocess.Popen(
                    cmd,
                    cwd=str(root),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )
            logger.info("Scheduled serve restart host=%s port=%s", host, port)
            return True
        except Exception as exc:
            logger.error("Failed to schedule serve restart: %s", exc, exc_info=True)
            return False


def resolve_serve_bind(default_host: str = "0.0.0.0", default_port: int = 8000) -> tuple[str, int]:
    """Read current serve bind from env set by CLI serve."""
    host = (os.environ.get("AUTOREIV_SERVE_HOST") or default_host).strip() or default_host
    try:
        port = int(os.environ.get("AUTOREIV_SERVE_PORT") or default_port)
    except ValueError:
        port = default_port
    return host, port
