"""
Sync SDLC cards to GitHub issues via gh [REQ-SDLC-040..042].
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import resolve_project_root
from src.application.skills.card_tools import CardTools
from src.domain.sdlc.github_labels import github_label_map
from src.domain.sdlc.models import parse_card_frontmatter, serialize_card_frontmatter


class GitHubIssueTools:
    """Create or update a GitHub issue from a card. Uses gh. No tokens. No MCP."""

    def __init__(
        self,
        default_project_root: Optional[str] = None,
        root_resolver: Optional[Callable[[Optional[str]], Path]] = None,
        runner: Optional[Callable[[List[str], Path], Dict[str, Any]]] = None,
        card_tools: Optional[CardTools] = None,
    ):
        self._default_root = Path(default_project_root).resolve() if default_project_root else None
        self._root_resolver = root_resolver
        self._runner = runner
        self._cards = card_tools or CardTools(
            default_project_root=default_project_root,
            root_resolver=root_resolver,
        )

    def _root(self, project_root: Optional[str] = None) -> Path:
        if self._root_resolver is not None:
            return Path(self._root_resolver(project_root)).resolve()
        return resolve_project_root(project_root, default_root=self._default_root)

    def _run_gh(self, args: List[str], cwd: Path) -> Dict[str, Any]:
        if self._runner is not None:
            return self._runner(args, cwd)
        gh = shutil.which("gh")
        if not gh:
            return {
                "success": False,
                "error": "gh is not available. Install GitHub CLI and authenticate. Do not invent tokens.",
            }
        proc = subprocess.run([gh, *args], cwd=str(cwd), capture_output=True, text=True, check=False)
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }

    def sync_card_issue(
        self,
        card_id: str,
        project_root: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        card = self._cards.read_card(card_id=card_id, project_root=project_root)
        if not card.get("success"):
            return card
        labels = github_label_map(card.get("status") or "Discuss", parse_card_frontmatter(card["content"]).fields.get("Labels", ""))
        title = f"{card.get('id')} {card.get('title')}".strip()
        body = card.get("content") or ""
        payload = {
            "success": True,
            "dry_run": bool(dry_run),
            "title": title,
            "labels": labels,
            "github_issue": card.get("github_issue") or "",
        }
        if dry_run:
            payload["body_chars"] = len(body)
            return payload
        root = self._root(project_root)
        existing = (card.get("github_issue") or "").strip()
        if existing:
            args = ["issue", "edit", existing, "--title", title, "--body", body]
            for lab in labels:
                args.extend(["--add-label", lab])
            result = self._run_gh(args, root)
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error") or result.get("stderr") or "gh issue edit failed",
                }
            issue = existing
        else:
            args = ["issue", "create", "--title", title, "--body", body]
            for lab in labels:
                args.extend(["--label", lab])
            args.extend(["--json", "number,url"])
            result = self._run_gh(args, root)
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error") or result.get("stderr") or "gh issue create failed",
                }
            issue = (result.get("stdout") or "").strip()
            try:
                parsed = json.loads(result.get("stdout") or "{}")
                issue = str(parsed.get("number") or parsed.get("url") or issue)
            except json.JSONDecodeError:
                pass
            path = Path(card["path"])
            fm = parse_card_frontmatter(path.read_text(encoding="utf-8"))
            fm.fields["github_issue"] = issue
            path.write_text(serialize_card_frontmatter(fm), encoding="utf-8")
        payload["github_issue"] = issue
        return payload

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="sync_card_issue",
            description="Create or update a GitHub issue from a card using gh. HITL. Fails clearly if gh is missing.",
            parameters={
                "type": "object",
                "properties": {
                    "card_id": {"type": "string"},
                    "project_root": {"type": "string"},
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["card_id"],
            },
            handler=self.sync_card_issue,
        )
