"""
Projects root, listing, create/delete jail, and selected project [REQ-SDLC-050..052].
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.sdlc.paths import ProjectPathError, detect_autoreiv_root, jail_join
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")
PROJECTS_ROOT_KEY = "projects_root"
SELECTED_PROJECT_KEY = "selected_project"

REQUIRED_SCAFFOLD = (
    "AGENTS.md",
    "CHANGELOG.md",
    "VERSION",
    "CONTRIBUTING.md",
    "README.md",
    "docs/specs/.gitkeep",
    ".github/cards/.gitkeep",
    "tests/.gitkeep",
)


def default_template_dir() -> Path:
    here = Path(__file__).resolve()
    repo = here.parents[3] if len(here.parents) >= 4 else Path.cwd()
    candidate = repo / "templates" / "sdlc-project"
    if candidate.is_dir():
        return candidate
    cwd = Path.cwd() / "templates" / "sdlc-project"
    return cwd


class ProjectsService:
    """Filesystem projects under a configured root. Not the wiki."""

    def __init__(self, store: Optional[SQLiteStateStore] = None, default_checkout: Optional[Path] = None):
        if store is None:
            store = SQLiteStateStore(db_path=":memory:")
            store.initialize_db()
        self.store = store
        self.default_checkout = Path(default_checkout).resolve() if default_checkout else detect_autoreiv_root()

    def get_projects_root(self) -> str:
        raw = self.store.get_setting(PROJECTS_ROOT_KEY)
        if isinstance(raw, dict):
            return str(raw.get("path") or "")
        return str(raw or "")

    def set_projects_root(self, path: str) -> Dict[str, Any]:
        value = (path or "").strip()
        self.store.set_setting(PROJECTS_ROOT_KEY, value)
        return {"success": True, "projects_root": value}

    def resolve_root(self, project_root: Optional[str] = None) -> Path:
        if project_root:
            return Path(project_root).expanduser().resolve()
        selected = self.get_selected()
        path = (selected or {}).get("path") if isinstance(selected, dict) else None
        if path:
            return Path(path).expanduser().resolve()
        return Path(self.default_checkout).resolve()

    def get_selected(self) -> Dict[str, Any]:
        raw = self.store.get_setting(SELECTED_PROJECT_KEY)
        return raw if isinstance(raw, dict) else {}

    def set_selected(self, slug: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
        if path:
            target = Path(path).expanduser().resolve()
            payload = {"slug": slug or target.name, "path": str(target)}
        elif slug:
            listed = self.list_projects()
            match = next((p for p in listed.get("projects", []) if p["slug"] == slug), None)
            if not match:
                return {"success": False, "error": f"Project '{slug}' not found"}
            payload = {"slug": match["slug"], "path": match["path"]}
        else:
            self.store.set_setting(SELECTED_PROJECT_KEY, {})
            return {"success": True, "selected": {}}
        self.store.set_setting(SELECTED_PROJECT_KEY, payload)
        return {"success": True, "selected": payload}

    def _require_root(self) -> Path:
        raw = self.get_projects_root()
        if not raw:
            raise ProjectPathError("projects_root is not set")
        root = Path(raw).expanduser().resolve()
        if not root.exists():
            raise ProjectPathError(f"projects_root does not exist: {root}")
        if not root.is_dir():
            raise ProjectPathError(f"projects_root is not a directory: {root}")
        return root

    def list_projects(self) -> Dict[str, Any]:
        raw = self.get_projects_root()
        if not raw:
            return {"success": True, "projects_root": "", "projects": [], "selected": self.get_selected()}
        root = Path(raw).expanduser()
        if not root.is_dir():
            return {
                "success": True,
                "projects_root": str(root),
                "projects": [],
                "selected": self.get_selected(),
                "warning": "projects_root is not a directory",
            }
        root = root.resolve()
        projects: List[Dict[str, Any]] = []
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            if child.name.startswith("."):
                continue
            projects.append({"slug": child.name, "name": child.name, "path": str(child.resolve())})
        return {
            "success": True,
            "projects_root": str(root),
            "projects": projects,
            "selected": self.get_selected(),
        }

    def create_project(self, slug: str, name: Optional[str] = None) -> Dict[str, Any]:
        clean = (slug or "").strip()
        if not SLUG_RE.match(clean):
            return {"success": False, "error": "Invalid slug. Use letters, numbers, dot, underscore, hyphen."}
        try:
            root = self._require_root()
            target = jail_join(root, clean)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        if target.exists():
            return {"success": False, "error": f"Project already exists: {clean}"}
        template = default_template_dir()
        if template.is_dir():
            shutil.copytree(template, target)
        else:
            target.mkdir(parents=True, exist_ok=False)
        files = []
        for rel in REQUIRED_SCAFFOLD:
            if (target / rel).exists():
                files.append(rel)
        return {
            "success": True,
            "slug": clean,
            "name": name or clean,
            "path": str(target),
            "scaffold": files,
        }

    def delete_project(self, slug: str, confirm: bool = False) -> Dict[str, Any]:
        if not confirm:
            return {"success": False, "error": "delete requires confirm=true"}
        clean = (slug or "").strip()
        if not SLUG_RE.match(clean):
            return {"success": False, "error": "Invalid slug"}
        try:
            root = self._require_root()
            target = jail_join(root, clean)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        if not target.exists():
            return {"success": False, "error": f"Project not found: {clean}"}
        if not target.is_dir():
            return {"success": False, "error": f"Not a project directory: {clean}"}
        selected = self.get_selected()
        shutil.rmtree(target)
        if selected.get("path") and Path(selected["path"]).resolve() == target:
            self.store.set_setting(SELECTED_PROJECT_KEY, {})
        return {"success": True, "slug": clean, "deleted": True}

    def register_tools(self, registry) -> None:
        registry.register_tool(
            name="create_project",
            description="Create a project folder under projects_root by copying the SDD template. HITL in ask mode.",
            parameters={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Folder name under projects_root"},
                    "name": {"type": "string"},
                },
                "required": ["slug"],
            },
            handler=self.create_project,
        )

