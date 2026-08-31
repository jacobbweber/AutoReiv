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
    """JSON files next to existing user agent data. Reload reads from disk."""

    def __init__(self, agents_path: Path) -> None:
        self._root = Path(agents_path)

    def _dir(self, owner_agent_id: str) -> Path:
        return self._root / safe_id(owner_agent_id) / "workflows"

    def _path(self, owner_agent_id: str, workflow_id: str) -> Path:
        return self._dir(owner_agent_id) / f"{safe_id(workflow_id)}.json"

    def list_for_agent(self, owner_agent_id: str) -> List[Workflow]:
        folder = self._dir(owner_agent_id)
        if not folder.is_dir():
            return []
        items: List[Workflow] = []
        for path in sorted(folder.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                items.append(Workflow.model_validate(data))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
        items.sort(key=lambda w: (w.name.lower(), w.id))
        return items

    def get(self, owner_agent_id: str, workflow_id: str) -> Optional[Workflow]:
        path = self._path(owner_agent_id, workflow_id)
        if not path.is_file():
            return None
        try:
            return Workflow.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValueError):
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
        path = self._path(owner_agent_id, workflow_id)
        if not path.is_file():
            return False
        path.unlink()
        return True


def new_workflow_id() -> str:
    return _new_workflow_id()
