"""Active-project developer tools: checks, search, patch, project info [CARD-562].

All of them work only in the project selected in Projects Studio (or an explicit project_root).
run_project_checks runs only the commands listed under `## Checks` in the project's AGENTS.md.
"""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.sdlc.paths import ProjectPathError, inside_checkout, jail_join, protected_write_error
from src.domain.sdlc.agents_contract import CONTRACT_SECTIONS, parse_agents_md

SKIP_DIRS = frozenset(
    {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
     "dist", "build", ".tox", ".idea", ".next", "coverage"}
)
MAX_SEARCH_FILE_BYTES = 1_000_000
OUTPUT_TAIL_CHARS = 4000
DEFAULT_CHECK_TIMEOUT_S = 900
MAX_CHECK_TIMEOUT_S = 14400  # CARD-592: 4 h cap (was 1 h)


class ProjectDevTools:
    def __init__(
        self,
        root_resolver: Callable[[Optional[str]], Path],
        card_tools: Any = None,
        selected_info: Optional[Callable[[], Dict[str, Any]]] = None,
        check_record: Any = None,
    ):
        from src.application.sdlc.check_record import default_record

        self._root_resolver = root_resolver
        self._cards = card_tools
        self._selected_info = selected_info
        self._check_record = check_record or default_record()

    def _root(self, project_root: Optional[str] = None) -> Path:
        return Path(self._root_resolver(project_root)).resolve()

    def _contract(self, root: Path):
        agents = root / "AGENTS.md"
        text = agents.read_text(encoding="utf-8", errors="replace") if agents.is_file() else ""
        return agents.is_file(), parse_agents_md(text)

    # --- run_project_checks -------------------------------------------------
    def run_project_checks(
        self,
        check: str = "fast",
        timeout_seconds: int = DEFAULT_CHECK_TIMEOUT_S,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            root = self._root(project_root)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        present, contract = self._contract(root)
        if not present:
            return {"success": False, "error": "This project has no AGENTS.md. Add a '## Checks' section first."}
        if not contract.checks:
            return {
                "success": False,
                "error": "AGENTS.md has no commands under '## Checks' (lines like '- fast: pytest -q').",
            }
        wanted = (check or "fast").strip().lower()
        names = list(contract.checks) if wanted == "all" else [wanted]
        unknown = [n for n in names if n not in contract.checks]
        if unknown:
            return {
                "success": False,
                "error": f"No check named '{unknown[0]}' in AGENTS.md. Available: {', '.join(contract.checks)}, all.",
            }
        blocked = protected_write_error(root)
        if blocked:
            return {"success": False, "error": blocked}
        timeout = max(10, min(int(timeout_seconds or DEFAULT_CHECK_TIMEOUT_S), MAX_CHECK_TIMEOUT_S))
        results: List[Dict[str, Any]] = []
        for name in names:
            cmd = contract.checks[name]
            try:
                proc = subprocess.run(
                    cmd, shell=True, cwd=str(root), capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=timeout, check=False,
                )
                out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
                results.append({
                    "check": name, "command": cmd, "exit_code": proc.returncode,
                    "passed": proc.returncode == 0, "output_tail": out[-OUTPUT_TAIL_CHARS:],
                })
            except subprocess.TimeoutExpired:
                results.append({"check": name, "command": cmd, "exit_code": None, "passed": False,
                                "output_tail": f"Timed out after {timeout}s."})
        passed = all(r["passed"] for r in results)
        out: Dict[str, Any] = {"success": True, "project_root": str(root), "passed": passed, "results": results}
        if passed:
            out.update(self._record_green(root, names))
        return out

    def _record_green(self, root: Path, names: List[str]) -> Dict[str, Any]:
        """CARD-562: remember a green run for HEAD, only when the code it ran on is committed."""
        from src.application.sdlc.check_record import NO_GIT_HEAD, git_dirty_paths, git_head
        from src.application.skills.card_tools import CARD_DIRS

        head = git_head(root)
        dirty = [] if head == NO_GIT_HEAD else [
            p for p in git_dirty_paths(root) if not any(p.startswith(d + "/") for d in CARD_DIRS)
        ]
        if dirty:
            return {
                "green_recorded": False,
                "note": "Green, but not recorded for In Review: uncommitted changes outside the card folder ("
                + ", ".join(dirty[:5])
                + "). Commit them with git_commit, then run run_project_checks again.",
            }
        _, contract = self._contract(root)
        self._check_record.record(root, head, names, {n: contract.checks.get(n, "") for n in names})
        return {"green_recorded": True, "head": head[:12]}

    # --- search_project -----------------------------------------------------
    def search_project(
        self,
        pattern: str,
        path: str = ".",
        glob: Optional[str] = None,
        regex: bool = False,
        ignore_case: bool = True,
        max_results: int = 50,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not (pattern or "").strip():
            return {"success": False, "error": "pattern is required"}
        try:
            root = self._root(project_root)
            base = jail_join(root, path or ".")
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        flags = re.IGNORECASE if ignore_case else 0
        try:
            rx = re.compile(pattern if regex else re.escape(pattern), flags)
        except re.error as exc:
            return {"success": False, "error": f"Bad regex: {exc}"}
        limit = max(1, min(int(max_results or 50), 200))
        matches: List[Dict[str, Any]] = []
        files_scanned = 0
        truncated = False
        walker = [(str(base.parent), [], [base.name])] if base.is_file() else os.walk(base)
        for dirpath, dirnames, filenames in walker:
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for fname in sorted(filenames):
                fpath = Path(dirpath) / fname
                rel = str(fpath.relative_to(root)).replace("\\", "/")
                if glob and not (fnmatch.fnmatch(fname, glob) or fnmatch.fnmatch(rel, glob)):
                    continue
                try:
                    if fpath.stat().st_size > MAX_SEARCH_FILE_BYTES:
                        continue
                    raw = fpath.read_bytes()
                except OSError:
                    continue
                if b"\x00" in raw[:4096]:
                    continue
                files_scanned += 1
                for no, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), 1):
                    if rx.search(line):
                        matches.append({"path": rel, "line": no, "text": line.strip()[:300]})
                        if len(matches) >= limit:
                            truncated = True
                            break
                if truncated:
                    break
            if truncated:
                break
        return {
            "success": True, "project_root": str(root), "matches": matches,
            "files_scanned": files_scanned, "truncated": truncated,
        }

    # --- patch_project_file ------------------------------------------------
    def patch_project_file(
        self,
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
        project_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not path or old_text is None or old_text == "":
            return {"success": False, "error": "path and old_text are required"}
        try:
            root = self._root(project_root)
            target = jail_join(root, path)
        except ProjectPathError as exc:
            return {"success": False, "error": str(exc)}
        checkout = inside_checkout(target)
        if checkout is not None:
            return {"success": False, "error": f"Refusing to change the AutoReiv checkout ({checkout})."}
        blocked = protected_write_error(target)
        if blocked:
            return {"success": False, "error": blocked}
        from src.application.skills.card_tools import cards_folder_refusal

        cards_refused = cards_folder_refusal(root, target)
        if cards_refused:
            return {"success": False, "error": cards_refused}
        if not target.is_file():
            return {"success": False, "error": f"File not found: {path}"}
        raw = target.read_bytes().decode("utf-8", errors="replace")
        crlf = "\r\n" in raw
        text = raw.replace("\r\n", "\n")
        old = old_text.replace("\r\n", "\n")
        new = (new_text or "").replace("\r\n", "\n")
        count = text.count(old)
        if count == 0:
            return {"success": False, "error": "old_text not found. Read the file again and copy the exact text."}
        if count > 1 and not replace_all:
            return {"success": False, "error": f"old_text matches {count} places. Add context or set replace_all."}
        updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
        if crlf:
            updated = updated.replace("\n", "\r\n")
        target.write_bytes(updated.encode("utf-8"))
        return {
            "success": True, "project_root": str(root),
            "path": str(target.relative_to(root)).replace("\\", "/"),
            "replacements": count if replace_all else 1,
        }

    # --- active_project_info -----------------------------------------------
    def active_project_info(self, project_root: Optional[str] = None) -> Dict[str, Any]:
        try:
            root = self._root(project_root)
        except ProjectPathError as exc:
            return {"success": False, "selected": False, "error": str(exc)}
        present, contract = self._contract(root)
        git: Dict[str, Any] = {"is_repo": (root / ".git").exists()}
        if git["is_repo"]:
            def _git(*args: str) -> str:
                try:
                    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
                    return (p.stdout or "").strip()
                except OSError:
                    return ""
            git["branch"] = _git("branch", "--show-current")
            git["dirty"] = bool(_git("status", "--porcelain=v1", "--untracked-files=no"))
        cards: Dict[str, Any] = {}
        if self._cards is not None:
            try:
                listed = self._cards.list_cards(project_root=str(root))
                counts: Dict[str, int] = {}
                for c in listed.get("cards") or []:
                    counts[c.get("status") or "?"] = counts.get(c.get("status") or "?", 0) + 1
                cards = {"folder": str(self._cards._cards_dir(root).relative_to(root)).replace("\\", "/"),
                         "counts": counts}
            except Exception as exc:  # a broken card must not hide the project info
                cards = {"error": str(exc)}
        name = root.name
        if self._selected_info is not None and not project_root:
            name = (self._selected_info() or {}).get("slug") or name
        return {
            "success": True,
            "selected": True,
            "name": name,
            "project_root": str(root),
            "git": git,
            "agents_md": {
                "present": present,
                "sections": contract.sections,
                "missing_sections": contract.missing_sections if present else list(CONTRACT_SECTIONS),
                "checks": contract.checks,
                "base_branch": contract.base_branch,
            },
            "cards": cards,
        }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        root_prop: dict = {}  # CARD-562: project_root is not model-facing; the selected project is used
        registry.register_tool(
            name="run_project_checks",
            description=(
                "Run the active project's tests and linters (pytest, npm test, ruff...): only the commands listed "
                "under '## Checks' in its AGENTS.md (check=fast|full|lint|<name>|all). Returns pass/fail and the "
                "output tail per check. Use it to verify a fix or change."
            ),
            parameters={
                "type": "object",
                "properties": {"check": {"type": "string", "default": "fast"},
                               "timeout_seconds": {"type": "integer", "default": DEFAULT_CHECK_TIMEOUT_S}, **root_prop},
            },
            handler=self.run_project_checks,
        )
        registry.register_tool(
            name="search_project",
            description=(
                "Search text in the active project's files (skips .git, node_modules, .venv). Literal by default; "
                "regex=true for a regex. Optional path and glob (e.g. *.py). Returns path, line and text."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"}, "path": {"type": "string", "default": "."},
                    "glob": {"type": "string"}, "regex": {"type": "boolean", "default": False},
                    "ignore_case": {"type": "boolean", "default": True},
                    "max_results": {"type": "integer", "default": 50}, **root_prop,
                },
                "required": ["pattern"],
            },
            handler=self.search_project,
        )
        registry.register_tool(
            name="patch_project_file",
            description=(
                "Fix or change code: replace exact text in one source file of the active project (src, tests, "
                "docs). old_text must match exactly once unless replace_all=true. Prefer this over rewriting a "
                "whole file. HITL in ask mode."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"},
                    "replace_all": {"type": "boolean", "default": False}, **root_prop,
                },
                "required": ["path", "old_text", "new_text"],
            },
            handler=self.patch_project_file,
        )
        registry.register_tool(
            name="active_project_info",
            description=(
                "Which project is active: path, git branch and dirty state, AGENTS.md sections (and which of the "
                "contract sections are missing), its check commands and base branch, and card counts by status."
            ),
            parameters={"type": "object", "properties": {**root_prop}},
            handler=self.active_project_info,
        )
