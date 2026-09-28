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
BRANCH_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")


# CARD-562: git_commit never writes to the shared branches; card work lives on a card branch.
PROTECTED_COMMIT_BRANCHES = frozenset({"main", "master", "qa"})


class GitTools:
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
            err = status["stderr"] or "git status failed"
            skip = "not a git repository" in err.lower()
            return {
                "success": False,
                "skip_commit": skip,
                "error": (
                    "Not a git repository. Skip git_commit and set_card_status to In Review."
                    if skip
                    else err
                ),
                "project_root": str(root),
            }
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

    def git_create_branch(
        self,
        name: str,
        base: Optional[str] = None,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create and switch to a new branch from base [CARD-562]; never forces.

        Uncommitted changes are carried onto the new branch when it starts at the current HEAD
        (``git switch -c`` keeps the working tree). A dirty tree only refuses when the base is a
        different commit, where switching could lose or mix changes.
        """
        clean = (name or "").strip()
        if not BRANCH_NAME.match(clean) or ".." in clean or clean.endswith((".lock", "/", ".")):
            return {"success": False, "error": f"Invalid branch name '{name}'. Use e.g. card/12-short-slug."}
        try:
            root = self._root(project_root)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        status = self._run(root, ["status", "--porcelain=v1"])
        if status["exit_code"] != 0:
            return {"success": False, "error": status.get("stderr") or "git status failed", "project_root": str(root)}
        tracked = [ln for ln in (status.get("stdout") or "").splitlines() if ln and not ln.startswith("??")]
        current = (self._run(root, ["branch", "--show-current"]).get("stdout") or "").strip()
        exists = self._run(root, ["rev-parse", "--verify", "--quiet", f"refs/heads/{clean}"])["exit_code"] == 0
        if exists:
            if current == clean:
                return {"success": True, "project_root": str(root), "branch": clean, "created": False}
            return {
                "success": False,
                "error": f"Branch '{clean}' already exists. Switching to it is not done by this tool.",
                "project_root": str(root),
            }
        start = (base or "").strip() or self._contract_base(root) or current or "HEAD"
        if not BRANCH_NAME.match(start) and start != "HEAD":
            return {"success": False, "error": f"Invalid base '{start}'."}
        if tracked:
            head_sha = (self._run(root, ["rev-parse", "HEAD"]).get("stdout") or "").strip()
            base_sha = (self._run(root, ["rev-parse", "--verify", "--quiet", f"{start}^{{commit}}"]).get("stdout") or "").strip()
            if not head_sha or head_sha != base_sha:
                return {
                    "success": False,
                    "error": (
                        f"Uncommitted changes and base '{start}' is not the current HEAD; switching could lose them. "
                        "Branch from the current HEAD (omit base) or ask the operator."
                    ),
                    "changes": tracked[:20],
                    "project_root": str(root),
                }
            start = "HEAD"
        made = self._run(root, ["switch", "-c", clean, start])
        if not made["success"]:
            return {"success": False, "error": made.get("stderr") or "git switch failed", "project_root": str(root)}
        out = {"success": True, "project_root": str(root), "branch": clean, "base": start, "created": True}
        if tracked:
            out["carried_changes"] = tracked[:20]
        return out

    def _contract_base(self, root: Path) -> Optional[str]:
        agents = root / "AGENTS.md"
        if not agents.is_file():
            return None
        from src.domain.sdlc.agents_contract import parse_agents_md

        base = parse_agents_md(agents.read_text(encoding="utf-8", errors="replace")).base_branch
        if base and self._run(root, ["rev-parse", "--verify", "--quiet", f"refs/heads/{base}"])["exit_code"] == 0:
            return base
        return None

    def git_commit(
        self,
        subject: Optional[str] = None,
        body: str = "",
        paths: Optional[List[str]] = None,
        project_root: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        subject = (subject or message or "").strip()
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
        head = self._run(root, ["rev-parse", "--abbrev-ref", "HEAD"])
        branch = (head.get("stdout") or "").strip() if head.get("success") else ""
        if branch in PROTECTED_COMMIT_BRANCHES:
            return {
                "success": False,
                "error": f"Refusing to commit on '{branch}'. Create the card branch first (git_create_branch), then commit there.",
                "branch": branch,
            }
        if paths:
            for rel in paths:
                try:
                    jail_join(root, rel)
                except ProjectPathError as exc:
                    return {"success": False, "error": str(exc)}
                added = self._run(root, ["add", "--", rel])
                if not added["success"]:
                    return {"success": False, "error": added.get("stderr") or f"git add failed for {rel}"}
        staged = self._run(root, ["diff", "--cached", "--quiet"])
        if staged.get("success"):  # exit 0 = nothing staged
            return {
                "success": False,
                "error": "Nothing to commit: no staged changes. Pass the changed files in paths.",
                "branch": branch,
            }
        args = ["commit", "-m", subject]
        if (body or "").strip():
            args.extend(["-m", body.strip()])
        result = self._run(root, args)
        if not result["success"]:
            err = result.get("stderr") or "git commit failed"
            skip = "not a git repository" in err.lower()
            return {
                "success": False,
                "skip_commit": skip,
                "error": (
                    "Not a git repository. Skip git_commit and set_card_status to In Review."
                    if skip
                    else err
                ),
                "project_root": str(root),
            }
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
            parameters={"type": "object", "properties": {}},
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
                },
            },
            handler=self.git_diff,
        )
        registry.register_tool(
            name="git_branch",
            description="Show current branch and local branches in project_root.",
            parameters={"type": "object", "properties": {}},
            handler=self.git_branch,
        )
        registry.register_tool(
            name="git_create_branch",
            description=(
                "Create and switch to a new branch in the active project, from base (default: the AGENTS.md "
                "base branch, else the current branch). Refuses uncommitted changes; never forces."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "e.g. card/12-short-slug"},
                    "base": {"type": "string"},
                },
                "required": ["name"],
            },
            handler=self.git_create_branch,
        )
        registry.register_tool(
            name="git_commit",
            description="Commit in project_root with a conventional subject. No --no-verify, amend, force, or push. HITL.",
            parameters={
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "message": {"type": "string", "description": "Conventional commit subject (alias for subject)"},
                    "body": {"type": "string"},
                    "paths": {"type": "array", "items": {"type": "string"}},
                },
            },
            handler=self.git_commit,
        )
