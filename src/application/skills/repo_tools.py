"""Checkout-jailed read-only repo tools [CARD-262 / REQ-REPO-001].

List/read files under a configured AutoReiv checkout root with path sandbox.
No write/destructive tools in this card. Prefer catalog + CARD-221 HITL SAFE.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

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
    """Resolve checkout root from arg, AUTOREIV_CHECKOUT_ROOT, or detect."""
    if checkout_root:
        return Path(checkout_root).expanduser().resolve()
    env = (os.environ.get("AUTOREIV_CHECKOUT_ROOT") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if default_root is not None:
        return Path(default_root).resolve()
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
    """Read-only list/read under checkout root. No FS escape; sensitive deny."""

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
