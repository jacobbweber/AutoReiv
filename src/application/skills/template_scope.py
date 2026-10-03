"""The calling agent's template scope for wiki tools [CARD-603]."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.application.kernel.tool_registry import get_tool_context
from src.domain.wiki.template_folders import TemplateFolderError, is_hidden, normalize_template_folder

NO_FOLDER_MESSAGE = (
    "No template folder is set for this agent, so it has no templates. "
    "Set one in Agent Studio (Template folder)."
)


@dataclass(frozen=True)
class TemplateScope:
    agent_id: str
    own: Optional[str]
    others: Tuple[str, ...]

    def hides(self, rel_path: str) -> bool:
        return is_hidden(rel_path, self.own, self.others)


def other_agent_template_folders(agent_id: str) -> List[str]:
    """Template folders of every other agent file (shipped or user)."""
    out: List[str] = []
    try:
        from src.infrastructure.content.store import get_store

        for item in get_store().agents.list():
            if item.id.lower() == agent_id.lower():
                continue
            try:
                folder = normalize_template_folder(item.meta.get("template_folder"))
            except TemplateFolderError:
                continue
            if folder and folder not in out:
                out.append(folder)
    except Exception:
        pass
    return out


def caller_template_scope() -> Optional[TemplateScope]:
    """None for platform callers (no agent in the tool context); else the agent's folder and the others'."""
    ctx = get_tool_context()
    agent_id = str(ctx.get("agent_id") or "").strip()
    if not agent_id:
        return None
    try:
        own = normalize_template_folder(ctx.get("template_folder"))
    except TemplateFolderError:
        own = None
    others = tuple(f for f in other_agent_template_folders(agent_id) if f != own)
    return TemplateScope(agent_id=agent_id, own=own, others=others)
