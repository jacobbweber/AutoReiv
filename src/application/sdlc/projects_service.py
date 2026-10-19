"""
Projects folder, listing, create/delete jail, and selected project [REQ-SDLC-050..052, CARD-728, ADR-0067].

Projects live in one user-data folder: `DataDirResolver().resolve().projects_path` (AUTOREIV_PROJECTS_DIR, else
<data root>/projects). How to work in a project (conventions, specs, cards) lives in skills, never in a template here.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.application.sdlc.paths import ProjectPathError, jail_join
from src.infrastructure.memory.sqlite_store import SQLiteStateStore

SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")
SELECTED_PROJECT_KEY = "selected_project"
NO_PROJECT_MESSAGE = (
    "No project is selected. Select a project in Projects Studio (or pass project_root) and try again."
)


def _touches_running_checkout(target: Path) -> bool:
    """True when ``target`` is, contains, or sits inside the AutoReiv code this serve runs from [CARD-728].

    The checkout's gitignored ``scratch/`` stays allowed (test and live QA data live there).
    """
    from src.infrastructure.data.resolver import is_checkout_live_tree_path, repo_root

    code = repo_root().resolve()
    return target in code.parents or is_checkout_live_tree_path(target, checkout=code)


def ensure_commit_identity(git_bin: str, repo: Path) -> None:
    """Set a repo-local author only when git has none, so commits work on a bare serve (e.g. Docker)."""
    for key, fallback in (("user.email", "autoreiv@local"), ("user.name", "AutoReiv")):
        have = subprocess.run([git_bin, "-C", str(repo), "config", key], capture_output=True, text=True, check=False)
        if not (have.stdout or "").strip():
            subprocess.run([git_bin, "-C", str(repo), "config", key, fallback], capture_output=True, check=False)


class ProjectsService:
    """Filesystem projects under the user-data projects folder. Not the wiki."""

    def __init__(self, store: Optional[SQLiteStateStore] = None, projects_dir: Optional[Path] = None):
        if store is None:
            store = SQLiteStateStore(db_path=":memory:")
            store.initialize_db()
        self.store = store
        self._projects_dir = Path(projects_dir) if projects_dir is not None else None

    def projects_dir(self) -> Path:
        """The projects folder (created on first use) [CARD-728]."""
        if self._projects_dir is not None:
            root = self._projects_dir
        else:
            from src.infrastructure.data.resolver import DataDirResolver

            root = DataDirResolver().resolve().projects_path
        root = Path(root).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve()

    def _inside_projects_dir(self, target: Path) -> bool:
        root = self.projects_dir()
        return target != root and root in target.parents

    def require_selected_root(self) -> Path:
        """Active project root only — no silent fallback to AutoReiv checkout [CARD-302]."""
        selected = self.get_selected()
        path = (selected or {}).get("path") if isinstance(selected, dict) else None
        if not path:
            raise ProjectPathError("No active project selected")
        root = Path(path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ProjectPathError(f"Active project directory not found: {root}")
        return root

    def selected_root(self, project_root: Optional[str] = None) -> Optional[Path]:
        """The Projects Studio-selected project root; None when no project is selected [CARD-556, CARD-562].

        A passed project_root must be the selected project (else ProjectPathError naming the active project); it is
        never used when nothing is selected. It never falls back to the AutoReiv checkout.
        """
        selected = self.get_selected()
        path = (selected or {}).get("path") if isinstance(selected, dict) else None
        if not path:
            return None  # CARD-562: a passed project_root never stands in for a selection
        active = Path(path).expanduser().resolve()
        if project_root and Path(project_root).expanduser().resolve() != active:
            name = (selected or {}).get("name") or (selected or {}).get("slug") or active.name
            raise ProjectPathError(
                f"project_root '{project_root}' is not the active project '{name}' ({active}). Tools work only in the "
                "project selected in Projects Studio; omit project_root, or ask the operator to select that project."
            )
        return active

    def selected_or_refuse(self, project_root: Optional[str] = None) -> Path:
        """The selected project root; a clear error when none is selected, whatever project_root says [CARD-562]."""
        root = self.selected_root(project_root)
        if root is None:
            raise ProjectPathError(NO_PROJECT_MESSAGE)
        if not root.is_dir():
            raise ProjectPathError(f"Project folder not found: {root}. Select another project in Projects Studio.")
        return root

    def selected_or_scratch(self, project_root: Optional[str] = None) -> Path:
        """Working folder for cli_exec: the project, else the OS-temp scratch folder, never the checkout [CARD-558]."""
        root = self.selected_root(project_root)
        if root is not None:
            return root
        from src.application.sdlc.paths import default_scratch_root

        scratch = default_scratch_root()
        scratch.mkdir(parents=True, exist_ok=True)
        return scratch

    def get_selected(self) -> Dict[str, Any]:
        """The stored selection; one outside the projects folder is ignored (ADR-0067, no old-format reader)."""
        raw = self.store.get_setting(SELECTED_PROJECT_KEY)
        if not isinstance(raw, dict) or not raw.get("path"):
            return {}
        target = Path(str(raw["path"])).expanduser().resolve()
        if not self._inside_projects_dir(target) or _touches_running_checkout(target):
            return {}
        return raw

    def set_selected(self, slug: Optional[str] = None, path: Optional[str] = None) -> Dict[str, Any]:
        if path:
            target = Path(path).expanduser().resolve()
            if _touches_running_checkout(target):
                return {"success": False, "error": "The running AutoReiv code cannot be a project. Clone a copy instead."}
            if not self._inside_projects_dir(target):
                return {"success": False, "error": f"Projects must be inside the projects folder: {self.projects_dir()}"}
            if not target.is_dir():
                return {"success": False, "error": f"Project '{target.name}' not found"}
            payload = {"slug": slug or target.name, "path": str(target)}
        elif slug:
            listed = self.list_projects()
            match = next((p for p in listed.get("projects", []) if p["slug"] == slug), None)
            if not match:
                return {"success": False, "error": f"Project '{slug}' not found"}
            if _touches_running_checkout(Path(match["path"])):
                return {"success": False, "error": "The running AutoReiv code cannot be a project. Clone a copy instead."}
            payload = {"slug": match["slug"], "path": match["path"]}
        else:
            self.store.set_setting(SELECTED_PROJECT_KEY, {})
            return {"success": True, "selected": {}}
        self.store.set_setting(SELECTED_PROJECT_KEY, payload)
        return {"success": True, "selected": payload}

    def list_projects(self) -> Dict[str, Any]:
        root = self.projects_dir()
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

    def browse_folders(self, relative: str = ".") -> Dict[str, Any]:
        """Folder-only navigator under the projects folder [CARD-300]. Never lists files."""
        root = self.projects_dir()
        rel = (relative or ".").strip() or "."
        rel = rel.replace("\\", "/").strip("/")
        if rel in ("", "."):
            cwd_path = root
            cwd_rel = "."
            parent = None
        else:
            try:
                cwd_path = jail_join(root, rel)
            except ProjectPathError as exc:
                return {
                    "success": False,
                    "error": str(exc),
                    "projects_root": str(root),
                    "cwd": ".",
                    "parent": None,
                    "folders": [],
                    "selected": self.get_selected(),
                }
            if not cwd_path.is_dir():
                return {
                    "success": False,
                    "error": f"Not a directory: {rel}",
                    "projects_root": str(root),
                    "cwd": ".",
                    "parent": None,
                    "folders": [],
                    "selected": self.get_selected(),
                }
            cwd_rel = rel
            parts = [p for p in rel.split("/") if p and p != "."]
            parent = "." if len(parts) <= 1 else "/".join(parts[:-1])

        folders: List[Dict[str, Any]] = []
        for child in sorted(cwd_path.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            if child.name.startswith("."):
                continue
            child_rel = child.name if cwd_rel == "." else f"{cwd_rel}/{child.name}"
            folders.append(
                {
                    "name": child.name,
                    "rel": child_rel.replace("\\", "/"),
                    "path": str(child.resolve()),
                }
            )

        return {
            "success": True,
            "projects_root": str(root),
            "cwd": cwd_rel,
            "parent": parent,
            "folders": folders,
            "selected": self.get_selected(),
        }

    def create_project(self, slug: str, name: Optional[str] = None) -> Dict[str, Any]:
        """An empty folder with `git init -b main`. Starter files come from skills, on request [CARD-729]."""
        clean = (slug or "").strip()
        if not SLUG_RE.match(clean):
            return {"success": False, "error": "Invalid slug. Use letters, numbers, dot, underscore, hyphen."}
        try:
            target = jail_join(self.projects_dir(), clean)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        if target.exists():
            return {"success": False, "error": f"Project already exists: {clean}"}
        target.mkdir(parents=True, exist_ok=False)
        git_bin = shutil.which("git")
        git_ready = False
        if git_bin:
            init = subprocess.run([git_bin, "-C", str(target), "init", "-b", "main"], capture_output=True, check=False)
            git_ready = init.returncode == 0
            if git_ready:
                ensure_commit_identity(git_bin, target)
        return {
            "success": True,
            "slug": clean,
            "name": name or clean,
            "path": str(target),
            "git": git_ready,
        }

    def delete_project(self, slug: str, confirm: bool = False) -> Dict[str, Any]:
        if not confirm:
            return {"success": False, "error": "delete requires confirm=true"}
        clean = (slug or "").strip()
        if not SLUG_RE.match(clean):
            return {"success": False, "error": "Invalid slug"}
        try:
            target = jail_join(self.projects_dir(), clean)
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
            description=(
                "Create an empty project folder (git init, branch main) in the projects folder. "
                "Writes no starter files; follow the repo-onboarding skill for those."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Folder name inside the projects folder"},
                    "name": {"type": "string"},
                },
                "required": ["slug"],
            },
            handler=self.create_project,
        )
