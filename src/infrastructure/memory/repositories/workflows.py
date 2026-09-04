"""
File-backed workflow recipes [CARD-123].
Stored under $DATA_DIR/agents/<owner_agent_id>/workflows/<id>.json
Reload-safe user data, not git. Lives on the agent who starts the recipe.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import List, Optional

from src.domain.orchestration.workflow import Workflow

_SAFE_ID = re.compile(r"^[a-zA-Z0-9._-]+$")


def _new_workflow_id() -> str:
    return f"wf_{uuid.uuid4().hex[:12]}"


def safe_id(value: str) -> str:
    text = (value or "").strip()
    if not text or not _SAFE_ID.match(text):
        raise ValueError(f"Invalid id {value!r}. Use letters, digits, dot, underscore, hyphen.")
    return text


class WorkflowStore:
    """JSON files next to agent pack data [CARD-123, CARD-148]. Reload reads from disk."""

    def __init__(self, packs_path: Path, legacy_agents_path: Optional[Path] = None) -> None:
        self._root = Path(packs_path)
        self._legacy_root = Path(legacy_agents_path) if legacy_agents_path is not None else None

    def _dir(self, owner_agent_id: str) -> Path:
        return self._root / safe_id(owner_agent_id) / "workflows"

    def _legacy_dir(self, owner_agent_id: str) -> Optional[Path]:
        if self._legacy_root is not None:
            return self._legacy_root / safe_id(owner_agent_id) / "workflows"
        return None

    def _path(self, owner_agent_id: str, workflow_id: str) -> Path:
        return self._dir(owner_agent_id) / f"{safe_id(workflow_id)}.json"

    def _legacy_path(self, owner_agent_id: str, workflow_id: str) -> Optional[Path]:
        ld = self._legacy_dir(owner_agent_id)
        if ld is not None:
            return ld / f"{safe_id(workflow_id)}.json"
        return None

    def list_for_agent(self, owner_agent_id: str) -> List[Workflow]:
        by_id: dict[str, Workflow] = {}
        # 1. Read legacy first
        legacy_folder = self._legacy_dir(owner_agent_id)
        if legacy_folder and legacy_folder.is_dir():
            for path in sorted(legacy_folder.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    wf = Workflow.model_validate(data)
                    by_id[wf.id] = wf
                except (OSError, json.JSONDecodeError, ValueError):
                    continue
        # 2. Read pack folder (overrides legacy)
        folder = self._dir(owner_agent_id)
        if folder.is_dir():
            for path in sorted(folder.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    wf = Workflow.model_validate(data)
                    by_id[wf.id] = wf
                except (OSError, json.JSONDecodeError, ValueError):
                    continue
        items = list(by_id.values())
        items.sort(key=lambda w: (w.name.lower(), w.id))
        return items

    def get(self, owner_agent_id: str, workflow_id: str) -> Optional[Workflow]:
        path = self._path(owner_agent_id, workflow_id)
        if path.is_file():
            try:
                return Workflow.model_validate(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ValueError):
                return None
        legacy = self._legacy_path(owner_agent_id, workflow_id)
        if legacy and legacy.is_file():
            try:
                return Workflow.model_validate(json.loads(legacy.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError, ValueError):
                return None
        return None

    def save(self, workflow: Workflow) -> Workflow:
        if not workflow.id:
            workflow.id = _new_workflow_id()
        folder = self._dir(workflow.owner_agent_id)
        folder.mkdir(parents=True, exist_ok=True)
        path = self._path(workflow.owner_agent_id, workflow.id)
        payload = workflow.model_dump(mode="json")
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
        return workflow

    def delete(self, owner_agent_id: str, workflow_id: str) -> bool:
        deleted = False
        path = self._path(owner_agent_id, workflow_id)
        if path.is_file():
            path.unlink()
            deleted = True
        legacy = self._legacy_path(owner_agent_id, workflow_id)
        if legacy and legacy.is_file():
            legacy.unlink()
            deleted = True
        return deleted


def new_workflow_id() -> str:
    return _new_workflow_id()
