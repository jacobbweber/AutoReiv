"""
Project-scoped file tools jailed under project_root [REQ-SDLC-021, REQ-SDLC-022].
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import (
    ProjectPathError,
    default_scratch_root,
    inside_checkout,
    jail_join,
    protected_write_error,
    resolve_project_root,
)

READ_EXCERPT_CHARS = 20000


class ProjectFileTools:
    """List / read / write files inside a project root. No host-wide access."""

    def __init__(
        self,
        default_project_root: Optional[str] = None,
        root_resolver: Optional[Callable[[Optional[str]], Path]] = None,
        project_resolver: Optional[Callable[[Optional[str]], Optional[Path]]] = None,
        scratch_root: Optional[str | Path] = None,
    ):
        self._default_root = Path(default_project_root).resolve() if default_project_root else None
        self._root_resolver = root_resolver
        # CARD-556 D1: explicit/selected project, else <data root>/scratch; never the AutoReiv checkout.
        self._project_resolver = project_resolver
        self._scratch_root = Path(scratch_root).expanduser().resolve() if scratch_root else None

    def scratch_root(self) -> Path:
        return self._scratch_root or default_scratch_root()

    def _write_root(self, project_root: Optional[str] = None) -> tuple[Path, str]:
        """(root, "project" | "scratch") for write_project_file [CARD-556]."""
        if project_root:
            return Path(project_root).expanduser().resolve(), "project"
        if self._project_resolver is not None:
            selected = self._project_resolver(None)
            if selected:
                return Path(selected).resolve(), "project"
        elif self._root_resolver is not None:
            # Legacy resolvers fall back to the checkout when nothing is selected; that case goes to scratch.
            resolved = Path(self._root_resolver(None)).resolve()
            if inside_checkout(resolved) is None:
                return resolved, "project"
        elif self._default_root is not None:
            return self._default_root, "project"
        return self.scratch_root(), "scratch"

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
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return {"success": False, "error": f"Failed to read file: {exc}"}
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
            root, location = self._write_root(project_root)
            target = self._safe(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        checkout = inside_checkout(target)
        if checkout is not None:
            # CARD-556 D1: never write into the AutoReiv checkout from this tool.
            return {
                "success": False,
                "error": (
                    f"Refusing to write into the AutoReiv checkout ({checkout}). write_project_file never changes "
                    "the checkout; use repo_file_write or repo_file_patch for checkout changes, or select another "
                    "project in Projects Studio."
                ),
            }
        blocked = protected_write_error(target)
        if blocked:
            return {"success": False, "error": blocked}
        from src.application.skills.card_tools import cards_folder_refusal

        cards_refused = cards_folder_refusal(root, target)
        if cards_refused:
            return {"success": False, "error": cards_refused}
        if target.exists() and target.is_dir():
            return {"success": False, "error": f"Refusing to overwrite a directory: {path}"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if content is not None else "", encoding="utf-8")
        out: Dict[str, Any] = {
            "success": True,
            "location": location,
            "project_root": str(root),
            "path": str(target.relative_to(root)).replace("\\", "/"),
            "full_path": str(target),
            "chars": len(content or ""),
        }
        if location == "scratch":
            out["note"] = (
                f"No project is selected in Projects Studio, so the file was written to the AutoReiv scratch folder "
                f"{root}, not to the AutoReiv checkout. Full path: {target}. To read it back pass "
                f"project_root={root}. To change the AutoReiv checkout use repo_file_write; to write into a "
                "project, select it in Projects Studio or pass project_root."
            )
        return out

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="list_project_dir",
            description="List one directory under project_root. Paths cannot escape the root.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory (default .)"},
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
                },
                "required": ["path"],
            },
            handler=self.read_project_file,
        )
        registry.register_tool(
            name="write_project_file",
            description=(
                "Write a UTF-8 file under the project selected in Projects Studio (or project_root). With no "
                f"project selected it writes to the AutoReiv scratch folder {self.scratch_root()}, never to the "
                "AutoReiv checkout; the result gives the full path. Use repo_file_write to change the AutoReiv "
                "checkout. Rejects path escapes. HITL in ask mode."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path"],
            },
            handler=self.write_project_file,
        )
