"""
Project-scoped file tools jailed under project_root [REQ-SDLC-021, REQ-SDLC-022].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError, jail_join, resolve_project_root

READ_EXCERPT_CHARS = 20000


class ProjectFileSkill:
    """List / read / write files inside a project root. No host-wide access."""

    def __init__(
        self,
        default_project_root: Optional[str] = None,
        root_resolver: Optional[Callable[[Optional[str]], Path]] = None,
    ):
        self._default_root = Path(default_project_root).resolve() if default_project_root else None
        self._root_resolver = root_resolver

    def _root(self, project_root: Optional[str] = None) -> Path:
        if self._root_resolver is not None:
            return Path(self._root_resolver(project_root)).resolve()
        return resolve_project_root(project_root, default_root=self._default_root)

    def _safe(self, root: Path, relative: str) -> Path:
        return jail_join(root, relative or ".")

    def list_project_dir(
        self,
        path: str = ".",
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            root = self._root(project_root)
            target = self._safe(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        if not target.exists():
            return {"success": False, "error": f"Path not found: {path}"}
        if not target.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}
        entries: List[Dict[str, Any]] = []
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            rel = str(child.relative_to(root)).replace("\\", "/")
            entries.append(
                {
                    "name": child.name,
                    "path": rel,
                    "type": "dir" if child.is_dir() else "file",
                }
            )
        return {
            "success": True,
            "project_root": str(root),
            "path": str(target.relative_to(root)).replace("\\", "/") if target != root else ".",
            "entries": entries,
        }

    def read_project_file(
        self,
        path: str,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not path:
            return {"success": False, "error": "path is required"}
        try:
            root = self._root(project_root)
            target = self._safe(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        if not target.is_file():
            return {"success": False, "error": f"File not found: {path}"}
        text = target.read_text(encoding="utf-8")
        return {
            "success": True,
            "project_root": str(root),
            "path": str(target.relative_to(root)).replace("\\", "/"),
            "content": text[:READ_EXCERPT_CHARS],
            "truncated": len(text) > READ_EXCERPT_CHARS,
            "chars": len(text),
        }

    def write_project_file(
        self,
        path: str,
        content: str,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not path:
            return {"success": False, "error": "path is required"}
        try:
            root = self._root(project_root)
            target = self._safe(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        if target.exists() and target.is_dir():
            return {"success": False, "error": f"Refusing to overwrite a directory: {path}"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if content is not None else "", encoding="utf-8")
        return {
            "success": True,
            "project_root": str(root),
            "path": str(target.relative_to(root)).replace("\\", "/"),
            "chars": len(content or ""),
        }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="list_project_dir",
            description="List one directory under project_root. Paths cannot escape the root.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory (default .)"},
                    "project_root": {"type": "string"},
                },
            },
            handler=self.list_project_dir,
        )
        registry.register_tool(
            name="read_project_file",
            description="Read a UTF-8 file under project_root. Rejects path escapes.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "project_root": {"type": "string"},
                },
                "required": ["path"],
            },
            handler=self.read_project_file,
        )
        registry.register_tool(
            name="write_project_file",
            description="Write a UTF-8 file under project_root. Rejects path escapes. HITL in ask mode.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "project_root": {"type": "string"},
                },
                "required": ["path"],
            },
            handler=self.write_project_file,
        )
