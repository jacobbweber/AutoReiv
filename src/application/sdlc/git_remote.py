"""Git remote access for project tools [CARD-730, ADR-0067].

GitHub HTTPS auth comes from env ``GITHUB_TOKEN`` and rides in the git process environment (``GIT_CONFIG_*``), so it
is never written to ``.git/config``, never on the command line and never in tool output.
"""

from __future__ import annotations

import base64
import os
import re
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlsplit

GITHUB_HOSTS = frozenset({"github.com", "www.github.com"})
REMOTE_TIMEOUT_S = 600
_SCP_LIKE = re.compile(r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[^/\\].*$")  # git@github.com:owner/repo.git


def _token() -> str:
    return (os.environ.get("GITHUB_TOKEN") or "").strip()


def remote_env(url: str) -> Dict[str, str]:
    """Environment for a git command that talks to ``url``: no prompts, safe protocols, GitHub token when it applies."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ALLOW_PROTOCOL"] = "https:ssh:file"
    token = _token()
    host = (urlsplit(url).hostname or "").lower() if "://" in url else ""
    if token and host in GITHUB_HOSTS:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {basic}"
    return env


def scrub(text: str) -> str:
    """Remove the token (raw or as the basic-auth header) from git output."""
    token = _token()
    if not token or not text:
        return text or ""
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    return text.replace(basic, "***").replace(token, "***")


def check_remote_url(url: str, projects_dir: Path) -> Optional[str]:
    """Why ``url`` may not be cloned, or None. Network URLs: https, ssh, git@host:path. Local repos: only inside the
    projects folder (never the running AutoReiv checkout or other host folders)."""
    text = (url or "").strip()
    if not text or text.startswith("-") or "::" in text or any(c in text for c in "\r\n\0"):
        return "Give a repository URL such as https://github.com/owner/repo.git."
    if "://" in text:
        parts = urlsplit(text)
        scheme = parts.scheme.lower()
        if scheme in ("https", "ssh"):
            if parts.password is not None:
                return "Do not put a password or token in the URL; set GITHUB_TOKEN for the serve instead."
            return None
        if scheme == "file":
            return _check_local(Path(parts.path), projects_dir)
        return f"URL scheme '{scheme}' is not allowed. Use https:// or ssh://."
    if _SCP_LIKE.match(text):
        return None
    return _check_local(Path(text), projects_dir)


def _check_local(path: Path, projects_dir: Path) -> Optional[str]:
    from src.application.sdlc.projects_service import touches_running_checkout

    target = path.expanduser().resolve()
    root = projects_dir.resolve()
    if touches_running_checkout(target):
        return "The running AutoReiv code cannot be cloned from here. Clone it from its git remote instead."
    if target == root or root not in target.parents:
        return f"Local repositories can only be cloned from inside the projects folder: {root}"
    return None
