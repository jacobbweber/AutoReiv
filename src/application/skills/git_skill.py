"""
Jailed git tools with conventional commit gate [REQ-SDLC-060, REQ-SDLC-061].
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError, jail_join, resolve_project_root

CONVENTIONAL = re.compile(
    r"^(feat|fix|docs|chore|test|refactor)(\([A-Za-z0-9._/-]+\))?: .+\S",
)
FORBIDDEN_TOKENS = ("--no-verify", "--amend", "--force", "git config", "-c user.", "--config")


class GitSkill:
    """Read git status/diff/branch and commit inside project_root only."""

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

    def _git_bin(self) -> str:
        found = shutil.which("git")
        if not found:
            raise FileNotFoundError("git executable not found")
        return found

    def _run(self, root: Path, args: List[str]) -> Dict[str, Any]:
        for token in FORBIDDEN_TOKENS:
            joined = " ".join(args)
            if token in joined:
                return {"success": False, "error": f"Refused git flag: {token}"}
        cmd = [self._git_bin(), "-C", str(root), *args]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    def git_status(self, project_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            root = self._root(project_root)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        branch = self._run(root, ["branch", "--show-current"])
        status = self._run(root, ["status", "--porcelain=v1"])
        if status["exit_code"] != 0:
            return {"success": False, "error": status["stderr"] or "git status failed", "project_root": str(root)}
        return {
            "success": True,
            "project_root": str(root),
            "branch": (branch.get("stdout") or "").strip(),
            "porcelain": status.get("stdout") or "",
        }

    def git_diff(
        self,
        path: Optional[str] = None,
        staged: bool = False,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            root = self._root(project_root)
            args = ["diff"]
            if staged:
                args.append("--cached")
            if path:
                target = jail_join(root, path)
                args.extend(["--", str(target)])
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        result = self._run(root, args)
        result["project_root"] = str(root)
        return result if result["success"] else {"success": False, "error": result.get("stderr") or "git diff failed"}

    def git_branch(self, project_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            root = self._root(project_root)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        current = self._run(root, ["branch", "--show-current"])
        listed = self._run(root, ["branch", "--list"])
        if listed["exit_code"] != 0:
            return {"success": False, "error": listed.get("stderr") or "git branch failed"}
        return {
            "success": True,
            "project_root": str(root),
            "current": (current.get("stdout") or "").strip(),
            "branches": listed.get("stdout") or "",
        }

    def git_commit(
        self,
        subject: str,
        body: str = "",
        paths: Optional[List[str]] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        subject = (subject or "").strip()
        if any(tok in subject or tok in (body or "") for tok in FORBIDDEN_TOKENS):
            return {"success": False, "error": "Commit text refuses git config, --no-verify, force, and amend."}
        if not CONVENTIONAL.match(subject):
            return {
                "success": False,
                "error": "Subject must be conventional: feat|fix|docs|chore|test|refactor(scope): description",
            }
        try:
            root = self._root(project_root)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        if paths:
            for rel in paths:
                try:
                    jail_join(root, rel)
                except ProjectPathError as exc:
                    return {"success": False, "error": str(exc)}
                added = self._run(root, ["add", "--", rel])
                if not added["success"]:
                    return {"success": False, "error": added.get("stderr") or f"git add failed for {rel}"}
        args = ["commit", "-m", subject]
        if (body or "").strip():
            args.extend(["-m", body.strip()])
        result = self._run(root, args)
        if not result["success"]:
            return {"success": False, "error": result.get("stderr") or "git commit failed", "project_root": str(root)}
        return {
            "success": True,
            "project_root": str(root),
            "subject": subject,
            "stdout": result.get("stdout") or "",
        }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="git_status",
            description="git status --porcelain in project_root.",
            parameters={"type": "object", "properties": {"project_root": {"type": "string"}}},
            handler=self.git_status,
        )
        registry.register_tool(
            name="git_diff",
            description="git diff in project_root. Optional jailed path. staged=true for cached.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "staged": {"type": "boolean", "default": False},
                    "project_root": {"type": "string"},
                },
            },
            handler=self.git_diff,
        )
        registry.register_tool(
            name="git_branch",
            description="Show current branch and local branches in project_root.",
            parameters={"type": "object", "properties": {"project_root": {"type": "string"}}},
            handler=self.git_branch,
        )
        registry.register_tool(
            name="git_commit",
            description="Commit in project_root with a conventional subject. No --no-verify, amend, force, or push. HITL.",
            parameters={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "project_root": {"type": "string"},
                },
                "required": ["subject"],
            },
            handler=self.git_commit,
        )
