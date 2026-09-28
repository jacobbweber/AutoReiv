"""
Project root detection and path jail for SDLC tools [REQ-SDLC-012, REQ-SDLC-021].
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Optional


class ProjectPathError(ValueError):
    """Path is outside the project root or otherwise rejected."""


# CARD-555: folders no file-writing tool may touch (os.pathsep-separated). The live QA serve sets this to the real
# checkout, so an approved write in a throwaway env cannot land in Jacob's working tree. Unset means no extra guard.
PROTECTED_WRITE_ROOTS_ENV = "AUTOREIV_PROTECTED_WRITE_ROOTS"


def protected_write_roots(env: Optional[Mapping[str, str]] = None) -> list[Path]:
    raw = str((os.environ if env is None else env).get(PROTECTED_WRITE_ROOTS_ENV) or "")
    return [Path(p).expanduser() for p in raw.split(os.pathsep) if p.strip()]


def _resolved(path: Path) -> Path:
    try:
        return Path(path).resolve()
    except OSError:
        return Path(os.path.abspath(path))


def protected_write_error(target: Path | str, env: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """An error message when ``target`` is inside a protected write root, else None."""
    t = _resolved(Path(target))
    e = os.environ if env is None else env
    # CARD-556: the serve's own data root stays writable (live QA keeps its throwaway data, and so the no-project
    # scratch folder, in the gitignored <real checkout>/scratch/live_qa_data).
    data_raw = str(e.get("AUTOREIV_DATA_DIR") or "").strip()
    if data_raw:
        d = _resolved(Path(data_raw).expanduser())
        if t == d or d in t.parents:
            return None
    for root in protected_write_roots(env):
        r = _resolved(root)
        if t == r or r in t.parents:
            return f"Refusing to write under a protected folder ({r}); this environment may not change it."
    return None


def detect_autoreiv_root(start: Optional[Path] = None) -> Path:
    """Walk upward for an AutoReiv checkout (`.agents/cards` or a legacy cards folder + `AGENTS.md`)."""
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
            has_cards = (
                (cur / ".agents" / "cards").is_dir()
                or (cur / "docs" / "cards").is_dir()
                or (cur / ".github" / "cards").is_dir()
            )
            if has_cards and (cur / "AGENTS.md").is_file():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
    return Path.cwd().resolve()


def _is_checkout_dir(cur: Path) -> bool:
    has_cards = (
        (cur / ".agents" / "cards").is_dir()
        or (cur / "docs" / "cards").is_dir()
        or (cur / ".github" / "cards").is_dir()
    )
    return has_cards and (cur / "AGENTS.md").is_file()


def autoreiv_checkout_roots(env: Optional[Mapping[str, str]] = None) -> list[Path]:
    """Every folder that is the AutoReiv checkout for this process [CARD-556].

    `AUTOREIV_CHECKOUT_ROOT` when set, plus a real checkout found upward from the cwd or this module
    (`AGENTS.md` + cards). Unlike `detect_autoreiv_root`, there is no cwd fallback: a folder that is not a
    checkout is never reported, so an installed build does not treat the user's home as the checkout.
    """
    found: list[Path] = []
    raw = str((os.environ if env is None else env).get("AUTOREIV_CHECKOUT_ROOT") or "").strip()
    if raw:
        found.append(_resolved(Path(raw).expanduser()))
    for seed in (Path.cwd(), Path(__file__).resolve().parent):
        cur = _resolved(seed)
        for _ in range(12):
            if _is_checkout_dir(cur):
                found.append(cur)
                break
            if cur.parent == cur:
                break
            cur = cur.parent
    out: list[Path] = []
    for p in found:
        if p not in out:
            out.append(p)
    return out


def inside_checkout(target: Path | str, env: Optional[Mapping[str, str]] = None) -> Optional[Path]:
    """The checkout root that contains ``target``, else None [CARD-556]."""
    t = _resolved(Path(target))
    for root in autoreiv_checkout_roots(env):
        if t == root or root in t.parents:
            return root
    return None


def default_scratch_root() -> Path:
    """`<OS temp>/autoreiv-scratch`: throwaway files never land in a project or the checkout [CARD-556, CARD-562]."""
    import tempfile

    return _resolved(Path(tempfile.gettempdir()) / "autoreiv-scratch")


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
