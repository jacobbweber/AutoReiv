"""Checkout-jailed repo tools [CARD-262 read / CARD-264 write HITL].

List/read/write/patch/rollback files under AutoReiv checkout with path sandbox.
Writes are catalog tools + CARD-221 REQUIRE_CONFIRM (HITL). No FS escape.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError, detect_autoreiv_root, jail_join

READ_EXCERPT_CHARS = 24000

# Default deny: secrets / agent DBs / env - still under jail, but refused.
_DEFAULT_DENY_GLOBS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "**/*credential*",
    "**/*secret*",
    "**/*.pem",
    "**/*.key",
    "**/id_rsa*",
    "**/*memory.db*",
    "**/*storage.db*",
    "**/*.p12",
    "**/*.pfx",
)


def resolve_checkout_root(
    checkout_root: Optional[str] = None,
    default_root: Optional[Path] = None,
) -> Path:
    """Resolve checkout root from arg, constructor default, env, or detect.

    Explicit default_root (tests / injected jail) beats AUTOREIV_CHECKOUT_ROOT so
    unit jails are not silently rewritten to the live checkout.
    """
    if checkout_root:
        return Path(checkout_root).expanduser().resolve()
    if default_root is not None:
        return Path(default_root).resolve()
    env = (os.environ.get("AUTOREIV_CHECKOUT_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return detect_autoreiv_root()


def _normalize_rel(path: str | None) -> str:
    p = (path or "").strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/") or "."


def is_denied_path(rel: str, deny_globs: Sequence[str] | None = None) -> bool:
    rel_n = _normalize_rel(rel)
    if rel_n == ".":
        return False
    globs = tuple(deny_globs) if deny_globs is not None else _DEFAULT_DENY_GLOBS
    name = Path(rel_n).name
    for pat in globs:
        if fnmatch.fnmatch(rel_n, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False


class RepoCheckoutTools:
    """List/read/write under checkout root. Writes HITL-gated. No FS escape."""

    def __init__(
        self,
        default_checkout_root: Optional[str] = None,
        root_resolver: Optional[Callable[[Optional[str]], Path]] = None,
        deny_globs: Optional[Sequence[str]] = None,
        allow_prefixes: Optional[Sequence[str]] = None,
    ):
        self._default_root = (
            Path(default_checkout_root).resolve() if default_checkout_root else None
        )
        self._root_resolver = root_resolver
        self._deny_globs = (
            tuple(deny_globs) if deny_globs is not None else _DEFAULT_DENY_GLOBS
        )
        env_allow = (os.environ.get("AUTOREIV_REPO_ALLOWLIST") or "").strip()
        if allow_prefixes is not None:
            self._allow_prefixes = tuple(
                p.strip().replace("\\", "/").strip("/")
                for p in allow_prefixes
                if str(p).strip()
            )
        elif env_allow:
            self._allow_prefixes = tuple(
                p.strip().replace("\\", "/").strip("/")
                for p in env_allow.split(",")
                if p.strip()
            )
        else:
            self._allow_prefixes = ()

    def _root(self, checkout_root: Optional[str] = None) -> Path:
        if self._root_resolver is not None:
            return Path(self._root_resolver(checkout_root)).resolve()
        return resolve_checkout_root(checkout_root, default_root=self._default_root)

    def _check_allow(self, rel: str) -> Optional[str]:
        rel_n = _normalize_rel(rel)
        if is_denied_path(rel_n, self._deny_globs):
            return f"Path denied by sandbox policy: {rel_n}"
        if not self._allow_prefixes:
            return None
        if rel_n == ".":
            return None
        for pref in self._allow_prefixes:
            if pref == "*":
                return None
            if rel_n == pref or rel_n.startswith(pref.rstrip("/") + "/"):
                return None
        return f"Path not in checkout allowlist: {rel_n}"

    def list_repo_dir(
        self,
        path: str = ".",
        checkout_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            root = self._root(checkout_root)
            target = jail_join(root, path or ".")
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        rel = (
            str(target.relative_to(root)).replace("\\", "/")
            if target != root
            else "."
        )
        deny_err = self._check_allow(rel)
        if deny_err:
            return {"success": False, "error": deny_err}
        if not target.exists():
            return {"success": False, "error": f"Path not found: {rel}"}
        if not target.is_dir():
            return {"success": False, "error": f"Not a directory: {rel}"}
        entries: List[Dict[str, Any]] = []
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            child_rel = str(child.relative_to(root)).replace("\\", "/")
            if is_denied_path(child_rel, self._deny_globs):
                continue
            entries.append(
                {
                    "name": child.name,
                    "path": child_rel,
                    "type": "dir" if child.is_dir() else "file",
                }
            )
        return {
            "success": True,
            "checkout_root": str(root),
            "path": rel,
            "entries": entries,
            "tool": "repo_file_list",
        }

    def read_repo_file(
        self,
        path: str,
        checkout_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not path:
            return {
                "success": False,
                "error": "path is required",
                "tool": "repo_file_read",
            }
        try:
            root = self._root(checkout_root)
            target = jail_join(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc), "tool": "repo_file_read"}
        rel = str(target.relative_to(root)).replace("\\", "/")
        deny_err = self._check_allow(rel)
        if deny_err:
            return {
                "success": False,
                "error": deny_err,
                "path": rel,
                "tool": "repo_file_read",
            }
        if not target.is_file():
            return {
                "success": False,
                "error": f"File not found: {rel}",
                "path": rel,
                "tool": "repo_file_read",
            }
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return {
                "success": False,
                "error": f"Not a UTF-8 text file: {rel}",
                "path": rel,
                "tool": "repo_file_read",
            }
        return {
            "success": True,
            "checkout_root": str(root),
            "path": rel,
            "content": text[:READ_EXCERPT_CHARS],
            "truncated": len(text) > READ_EXCERPT_CHARS,
            "chars": len(text),
            "tool": "repo_file_read",
        }

    def repo_file_list(
        self,
        path: str = ".",
        checkout_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.list_repo_dir(path=path, checkout_root=checkout_root)

    def repo_file_read(
        self,
        path: str,
        checkout_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.read_repo_file(path=path, checkout_root=checkout_root)


    def _snapshot_key(self, root: Path, rel: str) -> str:
        return str((root / rel).resolve())

    def _ensure_snapshots(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        snaps = getattr(self, "_write_snapshots", None)
        if snaps is None:
            snaps = {}
            setattr(self, "_write_snapshots", snaps)
        return snaps

    def _record_snapshot(self, root: Path, rel: str, target: Path) -> None:
        snaps = self._ensure_snapshots()
        key = self._snapshot_key(root, rel)
        if key not in snaps:
            if target.is_file():
                try:
                    prior = target.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    prior = None
                snaps[key] = (True, prior)
            else:
                snaps[key] = (False, None)

    def repo_file_write(
        self,
        path: str,
        content: str,
        checkout_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create or overwrite a UTF-8 file under checkout. HITL REQUIRE_CONFIRM."""
        if not path:
            return {"success": False, "error": "path is required", "tool": "repo_file_write"}
        try:
            root = self._root(checkout_root)
            target = jail_join(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc), "tool": "repo_file_write"}
        rel = str(target.relative_to(root)).replace("\\", "/")
        deny_err = self._check_allow(rel)
        if deny_err:
            return {"success": False, "error": deny_err, "path": rel, "tool": "repo_file_write"}
        if target.exists() and target.is_dir():
            return {
                "success": False,
                "error": f"Refusing to overwrite a directory: {rel}",
                "path": rel,
                "tool": "repo_file_write",
            }
        created = not target.is_file()
        self._record_snapshot(root, rel, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        text = content if content is not None else ""
        target.write_text(text, encoding="utf-8")
        return {
            "success": True,
            "checkout_root": str(root),
            "path": rel,
            "chars": len(text),
            "created": created,
            "tool": "repo_file_write",
        }

    def repo_file_patch(
        self,
        path: str,
        content: str,
        checkout_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Overwrite an existing UTF-8 file (fail if missing). HITL REQUIRE_CONFIRM."""
        if not path:
            return {"success": False, "error": "path is required", "tool": "repo_file_patch"}
        try:
            root = self._root(checkout_root)
            target = jail_join(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc), "tool": "repo_file_patch"}
        rel = str(target.relative_to(root)).replace("\\", "/")
        deny_err = self._check_allow(rel)
        if deny_err:
            return {"success": False, "error": deny_err, "path": rel, "tool": "repo_file_patch"}
        if not target.is_file():
            return {
                "success": False,
                "error": f"File not found for patch: {rel}",
                "path": rel,
                "tool": "repo_file_patch",
            }
        self._record_snapshot(root, rel, target)
        text = content if content is not None else ""
        target.write_text(text, encoding="utf-8")
        return {
            "success": True,
            "checkout_root": str(root),
            "path": rel,
            "chars": len(text),
            "created": False,
            "tool": "repo_file_patch",
        }

    def repo_file_rollback(
        self,
        path: str,
        checkout_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore last pre-write snapshot for path (delete if write created it)."""
        if not path:
            return {"success": False, "error": "path is required", "tool": "repo_file_rollback"}
        try:
            root = self._root(checkout_root)
            target = jail_join(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc), "tool": "repo_file_rollback"}
        rel = str(target.relative_to(root)).replace("\\", "/")
        deny_err = self._check_allow(rel)
        if deny_err:
            return {"success": False, "error": deny_err, "path": rel, "tool": "repo_file_rollback"}
        snaps = self._ensure_snapshots()
        key = self._snapshot_key(root, rel)
        if key not in snaps:
            return {
                "success": False,
                "error": f"No write snapshot to rollback: {rel}",
                "path": rel,
                "tool": "repo_file_rollback",
            }
        existed, prior = snaps.pop(key)
        if not existed:
            if target.is_file():
                target.unlink()
            return {
                "success": True,
                "path": rel,
                "deleted": True,
                "tool": "repo_file_rollback",
            }
        if prior is None:
            return {
                "success": False,
                "error": f"Prior content unavailable (non-UTF8?): {rel}",
                "path": rel,
                "tool": "repo_file_rollback",
            }
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(prior, encoding="utf-8")
        return {
            "success": True,
            "path": rel,
            "deleted": False,
            "chars": len(prior),
            "tool": "repo_file_rollback",
        }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="repo_file_list",
            description=(
                "List one directory under the configured AutoReiv checkout root. "
                "Paths cannot escape the checkout; sensitive paths are denied. Read-only."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory under checkout (default .)",
                    },
                    "checkout_root": {
                        "type": "string",
                        "description": (
                            "Optional override; default AUTOREIV_CHECKOUT_ROOT "
                            "or detected AutoReiv root"
                        ),
                    },
                },
            },
            handler=self.repo_file_list,
        )
        registry.register_tool(
            name="repo_file_read",
            description=(
                "Read a UTF-8 file under the configured AutoReiv checkout root. "
                "Rejects path escapes and sensitive files. Read-only — claim only "
                "what this tool returns."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path (e.g. AGENTS.md)",
                    },
                    "checkout_root": {
                        "type": "string",
                        "description": (
                            "Optional override; default AUTOREIV_CHECKOUT_ROOT "
                            "or detected AutoReiv root"
                        ),
                    },
                },
                "required": ["path"],
            },
            handler=self.repo_file_read,
        )
        registry.register_tool(
            name="repo_file_write",
            description=(
                "Create or overwrite a UTF-8 file under the AutoReiv checkout root. "
                "Sandboxed; sensitive paths denied. REQUIRE_CONFIRM / HITL before execute."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path under checkout",
                    },
                    "content": {
                        "type": "string",
                        "description": "Full UTF-8 file contents",
                    },
                    "checkout_root": {
                        "type": "string",
                        "description": (
                            "Optional override; default AUTOREIV_CHECKOUT_ROOT "
                            "or detected AutoReiv root"
                        ),
                    },
                },
                "required": ["path", "content"],
            },
            handler=self.repo_file_write,
        )
        registry.register_tool(
            name="repo_file_patch",
            description=(
                "Overwrite an existing UTF-8 file under checkout (fails if missing). "
                "Sandboxed; REQUIRE_CONFIRM / HITL before execute."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative existing file path",
                    },
                    "content": {
                        "type": "string",
                        "description": "Replacement UTF-8 contents",
                    },
                    "checkout_root": {
                        "type": "string",
                        "description": (
                            "Optional override; default AUTOREIV_CHECKOUT_ROOT "
                            "or detected AutoReiv root"
                        ),
                    },
                },
                "required": ["path", "content"],
            },
            handler=self.repo_file_patch,
        )
        registry.register_tool(
            name="repo_file_rollback",
            description=(
                "Rollback the last repo_file_write/patch for a path to its pre-write "
                "snapshot (deletes the file if the write created it). REQUIRE_CONFIRM."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path to restore",
                    },
                    "checkout_root": {
                        "type": "string",
                        "description": (
                            "Optional override; default AUTOREIV_CHECKOUT_ROOT "
                            "or detected AutoReiv root"
                        ),
                    },
                },
                "required": ["path"],
            },
            handler=self.repo_file_rollback,
        )
