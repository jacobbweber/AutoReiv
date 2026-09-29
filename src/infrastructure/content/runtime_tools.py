"""Runtime-built tools are files in the data dir (CARD-570, ADR-0062).

Layout under ``<data>/tools/``:

- ``<name>/tool.py``: the tool code (defines ``run(**kwargs)``), run in the subprocess sandbox.
- ``<name>/tool.json``: description, parameters, risk level, HITL flag, tool check result.
- ``.approvals.json``: ``{name: {"enabled": bool, "approved_sha256": str}}``.

A tool is mounted only when it is enabled **and** the sha256 of ``tool.py`` equals the approved
hash. Saving new code for a tool (by an agent or by hand on disk) changes the hash, so the tool is
not mounted again until Jacob re-approves it. ``enable`` / ``disable`` are called only by the
Tools Studio HTTP routes; no agent tool calls them (guard: test_card570_runtime_tools.py).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Optional

APPROVALS_FILE = ".approvals.json"
CODE_FILE = "tool.py"
META_FILE = "tool.json"
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


def code_sha256(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class RuntimeToolFiles:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _dir(self, name: str) -> Path:
        if not _NAME_RE.match(str(name or "")):
            raise ValueError(f"invalid tool name: {name!r}")
        return self.root / name

    def names(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(
            p.name for p in self.root.iterdir() if p.is_dir() and _NAME_RE.match(p.name) and (p / CODE_FILE).is_file()
        )

    def read(self, name: str) -> Optional[dict[str, Any]]:
        try:
            folder = self._dir(name)
        except ValueError:
            return None
        code_path = folder / CODE_FILE
        if not code_path.is_file():
            return None
        try:
            meta = json.loads((folder / META_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        row = dict(meta) if isinstance(meta, dict) else {}
        row["name"] = name
        row["code"] = code_path.read_text(encoding="utf-8")
        row.update(self.approval_state(name, row["code"]))
        return row

    def rows(self) -> list[dict[str, Any]]:
        return [row for row in (self.read(n) for n in self.names()) if row]

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        name = str(record["name"])
        folder = self._dir(name)
        folder.mkdir(parents=True, exist_ok=True)
        meta = {k: v for k, v in record.items() if k not in {"code", "name", "enabled", "approved", "approval"}}
        (folder / CODE_FILE).write_text(str(record["code"]), encoding="utf-8", newline="\n")
        (folder / META_FILE).write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
        return self.read(name) or {}

    def delete(self, name: str) -> bool:
        folder = self._dir(name)
        if not folder.is_dir():
            return False
        shutil.rmtree(folder)
        approvals = self._approvals()
        if approvals.pop(name, None) is not None:
            self._write_approvals(approvals)
        return True

    # Approval: enable flag + approved code hash. Jacob-only (Tools Studio routes).
    def _approvals(self) -> dict[str, dict[str, Any]]:
        try:
            raw = json.loads((self.root / APPROVALS_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)} if isinstance(raw, dict) else {}

    def _write_approvals(self, approvals: dict[str, dict[str, Any]]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / APPROVALS_FILE).write_text(json.dumps(approvals, indent=2, sort_keys=True), encoding="utf-8")

    def approval_state(self, name: str, code: Optional[str] = None) -> dict[str, Any]:
        if code is None:
            path = self.root / name / CODE_FILE
            code = path.read_text(encoding="utf-8") if path.is_file() else ""
        entry = self._approvals().get(name) or {}
        current = code_sha256(code)
        approved_hash = str(entry.get("approved_sha256") or "")
        enabled = bool(entry.get("enabled"))
        if enabled and approved_hash == current:
            state = "enabled"
        elif enabled:
            state = "needs_reapproval"  # code changed since Jacob approved it
        else:
            state = "disabled"
        return {"enabled": enabled, "approval": state, "code_sha256": current, "approved_sha256": approved_hash or None}

    def mountable(self, name: str) -> bool:
        row = self.read(name)
        return bool(row and row.get("approval") == "enabled")

    def enable(self, name: str) -> dict[str, Any]:
        """Approve the current code and enable the tool. Tools Studio route only."""
        row = self.read(name)
        if row is None:
            raise LookupError(name)
        approvals = self._approvals()
        approvals[name] = {"enabled": True, "approved_sha256": row["code_sha256"]}
        self._write_approvals(approvals)
        return self.approval_state(name)

    def disable(self, name: str) -> dict[str, Any]:
        if self.read(name) is None:
            raise LookupError(name)
        approvals = self._approvals()
        approvals[name] = {"enabled": False, "approved_sha256": (approvals.get(name) or {}).get("approved_sha256")}
        self._write_approvals(approvals)
        return self.approval_state(name)
