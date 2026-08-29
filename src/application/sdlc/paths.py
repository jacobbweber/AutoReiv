"""
Project root detection and path jail for SDLC tools [REQ-SDLC-012, REQ-SDLC-021].
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


class ProjectPathError(ValueError):
    """Path is outside the project root or otherwise rejected."""


def detect_autoreiv_root(start: Optional[Path] = None) -> Path:
    """Walk upward for an AutoReiv checkout (`.github/cards` + `AGENTS.md`)."""
    seeds = []
    if start is not None:
        seeds.append(Path(start))
    seeds.append(Path.cwd())
    seeds.append(Path(__file__).resolve())
    seen = set()
    for seed in seeds:
        cur = seed.resolve() if seed.exists() or seed.parent.exists() else Path.cwd()
        if not cur.is_dir():
            cur = cur.parent
        for _ in range(10):
            key = str(cur)
            if key in seen:
                break
            seen.add(key)
            if (cur / ".github" / "cards").is_dir() and (cur / "AGENTS.md").is_file():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
    return Path.cwd().resolve()


def resolve_project_root(project_root: Optional[str] = None, default_root: Optional[Path] = None) -> Path:
    if project_root:
        return Path(project_root).expanduser().resolve()
    if default_root is not None:
        return Path(default_root).resolve()
    return detect_autoreiv_root()


def jail_join(root: Path, relative: str) -> Path:
    """Join `relative` under `root`. Reject `..` and absolute escapes."""
    root_r = Path(root).resolve()
    rel = (relative or "").strip()
    if not rel or rel in (".", "./"):
        return root_r
    raw = Path(rel)
    if raw.is_absolute():
        target = raw.resolve()
        try:
            target.relative_to(root_r)
            return target
        except ValueError as exc:
            raise ProjectPathError("Path escapes project_root") from exc
    if ".." in raw.parts:
        raise ProjectPathError("Path escapes project_root")
    target = (root_r / rel).resolve()
    try:
        target.relative_to(root_r)
    except ValueError as exc:
        raise ProjectPathError("Path escapes project_root") from exc
    return target
