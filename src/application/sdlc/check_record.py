"""Green-check record and small git reads for the In Review gate [CARD-562].

run_project_checks records a green run for the project's current HEAD (only when the tree has no uncommitted
changes outside the card folders). set_card_status(In Review) for Developer requires that record for the same HEAD.
The record is a small JSON file under the serve's data folder (or the OS temp folder); nothing inside the project.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

NO_GIT_HEAD = "no-git"


def run_git(root: Path, args: Sequence[str]) -> subprocess.CompletedProcess:
    git = shutil.which("git")
    if not git:
        raise FileNotFoundError("git executable not found")
    return subprocess.run([git, "-C", str(root), *args], capture_output=True, text=True, check=False)


def git_head(root: Path) -> str:
    """Full HEAD sha, or NO_GIT_HEAD when the project is not a git repo (or has no commit)."""
    try:
        proc = run_git(root, ["rev-parse", "HEAD"])
    except FileNotFoundError:
        return NO_GIT_HEAD
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else NO_GIT_HEAD


def git_branch(root: Path) -> str:
    proc = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def git_dirty_paths(root: Path) -> List[str]:
    """Uncommitted paths (tracked changes and untracked files), forward-slash relative to the repo root."""
    proc = run_git(root, ["status", "--porcelain=v1", "-uall"])
    if proc.returncode != 0:
        return []
    paths: List[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        rel = line[3:]
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        paths.append(rel.strip().strip('"').replace("\\", "/"))
    return paths


def _key(root: Path) -> str:
    try:
        resolved = str(Path(root).resolve())
    except OSError:
        resolved = os.path.abspath(str(root))
    return os.path.normcase(resolved)


def default_record_path() -> Path:
    data = str(os.environ.get("AUTOREIV_DATA_DIR") or "").strip()
    base = Path(data).expanduser() if data else Path(tempfile.gettempdir()) / "autoreiv"
    return base / "sdlc" / "green-checks.json"


class GreenCheckRecord:
    """Last green run_project_checks per project: {project: {head, checks, at}}."""

    def __init__(self, path: Optional[Path] = None):
        self._path = Path(path) if path else None
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path or default_record_path()

    def _load(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def record(self, root: Path, head: str, checks: Sequence[str], commands: Optional[Dict[str, str]] = None) -> None:
        with self._lock:
            data = self._load()
            data[_key(root)] = {
                "head": head,
                "checks": list(checks),
                "commands": dict(commands or {}),
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=1), encoding="utf-8")

    def get(self, root: Path) -> Optional[Dict[str, Any]]:
        entry = self._load().get(_key(root))
        return entry if isinstance(entry, dict) else None


_DEFAULT = GreenCheckRecord()


def default_record() -> GreenCheckRecord:
    return _DEFAULT
