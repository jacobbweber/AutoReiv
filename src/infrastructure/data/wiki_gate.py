"""Deployment-mode wiki path gate [ADR-0056 / CARD-414].

Local Windows/Linux: explicit path required; no suggested path; no silent fallback vault.
Docker/daemon: AUTOREIV_WIKI_PATH (or documented deploy path) required; hard-fail start if missing.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ENV_WIKI_PATH = "AUTOREIV_WIKI_PATH"
ENV_DEPLOY_MODE = "AUTOREIV_DEPLOY_MODE"
WIKI_PATH_SETTING_KEY = "wiki_path"
WIKI_SCAFFOLD_CONFIRMED_KEY = "wiki_scaffold_confirmed"


class WikiPathConfigurationError(RuntimeError):
    """Wiki path missing/unreadable in a mode that requires hard-fail."""


@dataclass(frozen=True)
class WikiPathStatus:
    path: Optional[Path]
    configured: bool
    exists: bool
    readable: bool
    deploy_mode: str
    status: str  # configured|missing|unreadable|unset|docker_required
    message: str


def is_docker_runtime() -> bool:
    return Path("/.dockerenv").exists()


def resolve_deploy_mode(*, in_docker: Optional[bool] = None) -> str:
    """Return docker|daemon|local. AUTOREIV_DEPLOY_MODE wins; else /.dockerenv → docker."""
    raw = (os.environ.get(ENV_DEPLOY_MODE) or "").strip().lower()
    if raw in ("docker", "daemon", "local"):
        return raw
    docker = is_docker_runtime() if in_docker is None else in_docker
    if docker:
        return "docker"
    return "local"


def is_hard_fail_deploy_mode(mode: Optional[str] = None) -> bool:
    m = mode or resolve_deploy_mode()
    return m in ("docker", "daemon")


def configured_wiki_path(
    *,
    setting_wiki_path: Optional[str] = None,
    env_wiki_path: Optional[str] = None,
) -> Optional[Path]:
    """Explicit wiki path from env (preferred) or durable setting. No default suggestion."""
    raw = env_wiki_path
    if raw is None:
        raw = os.environ.get(ENV_WIKI_PATH)
    if raw is not None and str(raw).strip():
        return Path(str(raw).strip()).expanduser()
    if setting_wiki_path is not None and str(setting_wiki_path).strip():
        return Path(str(setting_wiki_path).strip()).expanduser()
    return None


def inspect_wiki_path(
    path: Optional[Path],
    *,
    deploy_mode: Optional[str] = None,
) -> WikiPathStatus:
    mode = deploy_mode or resolve_deploy_mode()
    if path is None:
        if is_hard_fail_deploy_mode(mode):
            return WikiPathStatus(
                path=None,
                configured=False,
                exists=False,
                readable=False,
                deploy_mode=mode,
                status="docker_required",
                message=(
                    f"Wiki path required for {mode} deploy. Set {ENV_WIKI_PATH} "
                    "and mount a volume (see docker-compose.yml)."
                ),
            )
        return WikiPathStatus(
            path=None,
            configured=False,
            exists=False,
            readable=False,
            deploy_mode=mode,
            status="unset",
            message="Wiki path not configured. Choose an explicit folder in Settings (no default).",
        )
    exists = path.exists()
    readable = False
    if exists:
        try:
            readable = path.is_dir() and os.access(path, os.R_OK)
        except OSError:
            readable = False
    if not exists:
        status = "missing"
        message = f"Configured wiki path is missing: {path}"
    elif not readable:
        status = "unreadable"
        message = f"Configured wiki path is unreadable: {path}"
    else:
        status = "configured"
        message = f"Wiki path OK: {path}"
    return WikiPathStatus(
        path=path,
        configured=True,
        exists=exists,
        readable=readable,
        deploy_mode=mode,
        status=status,
        message=message,
    )


def enforce_wiki_path_for_boot(
    *,
    setting_wiki_path: Optional[str] = None,
    in_docker: Optional[bool] = None,
    allow_unset_local: bool = True,
) -> WikiPathStatus:
    """Gate wiki for process start.

    Docker/daemon: raise WikiPathConfigurationError if unset/missing/unreadable.
    Local: return status; unset is allowed (wiki fail-closed) when allow_unset_local.
    """
    mode = resolve_deploy_mode(in_docker=in_docker)
    path = configured_wiki_path(setting_wiki_path=setting_wiki_path)
    status = inspect_wiki_path(path, deploy_mode=mode)
    if is_hard_fail_deploy_mode(mode):
        if status.status != "configured":
            raise WikiPathConfigurationError(status.message)
        return status
    if not allow_unset_local and status.status == "unset":
        raise WikiPathConfigurationError(status.message)
    if status.configured and status.status in ("missing", "unreadable"):
        # Local fail-visible: do not hard-crash entire app, but callers must not mkdir elsewhere.
        logger.error("Wiki path fail-visible: %s", status.message)
    return status


def should_scaffold_wiki(paths_wiki: Optional[Path], *, confirmed: bool) -> bool:
    """Scaffold numbered vault only after explicit operator confirm [ADR-0056]."""
    return bool(confirmed) and paths_wiki is not None
