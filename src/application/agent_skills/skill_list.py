"""One save path for an agent's skill list [CARD-502, CARD-570].

Agent Studio Save (``PUT /api/agents/{id}``) and Teach > Adopt both call
``persist_agent_profile``: the full agent file is written as a user copy in data ``agents/``
(it wins by id). Model/provider stay separate settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def studio_can_show_skill(skill_id: str, data_root: Optional[Path] = None, agent_id: Optional[str] = None) -> bool:
    """Agent Studio shows a pill for any skill that has a SKILL.md (shipped or user)."""
    from src.infrastructure.content.store import get_store

    return get_store().skills.load(skill_id) is not None


def studio_extra_skill_pills(profile: Any, shown_ids: set[str], data_root: Optional[Path] = None) -> list[dict[str, Any]]:
    """Pills for ticked skills no other list shows. Tools stay empty: the pill only switches the skill."""
    from src.infrastructure.content.store import get_store

    store = get_store()
    extras: list[dict[str, Any]] = []
    for sid in list(getattr(profile, "allowed_skill", None) or []):
        if sid in shown_ids or any(e["id"] == sid for e in extras):
            continue
        loaded = store.skills.load(sid)
        if loaded is None:
            continue
        extras.append(
            {
                "id": sid,
                "name": str(loaded.meta.get("name") or sid),
                "description": str(loaded.meta.get("description") or ""),
                "tools": [],
            }
        )
    return extras


def persist_agent_profile(
    store: Any,
    registry: Any,
    existing: Any,
    profile: Any,
    *,
    agent_id: str,
    skills_only: bool = False,
    data_dir: Optional[Path] = None,
) -> None:
    """Write the full agent file (user copy). ``skills_only`` is the Adopt path (same write)."""
    registry.save_agent(profile)


def add_skill_to_agent(
    store: Any,
    registry: Any,
    *,
    agent_id: str,
    skill_id: str,
    data_dir: Optional[Path] = None,
    skill_entry: Optional[dict[str, Any]] = None,
) -> tuple[Any, bool]:
    """Switch one skill on. Returns ``(fresh_profile, already_on)``. Raises ``LookupError``."""
    existing = registry.get_agent(agent_id)
    if existing is None:
        raise LookupError(agent_id)
    current = list(getattr(existing, "allowed_skill", None) or [])
    already = skill_id in current
    if not already:
        profile = existing.model_copy(update={"allowed_skill": current + [skill_id]})
        persist_agent_profile(store, registry, existing, profile, agent_id=agent_id, skills_only=True)
    return registry.get_agent(agent_id), already


def remove_skill_from_agent(
    store: Any,
    registry: Any,
    *,
    agent_id: str,
    skill_id: str,
    data_dir: Optional[Path] = None,
) -> tuple[Any, bool]:
    """Switch one skill off. Returns ``(fresh_profile, was_on)``."""
    existing = registry.get_agent(agent_id)
    if existing is None:
        raise LookupError(agent_id)
    current = list(getattr(existing, "allowed_skill", None) or [])
    if skill_id not in current:
        return existing, False
    profile = existing.model_copy(update={"allowed_skill": [s for s in current if s != skill_id]})
    persist_agent_profile(store, registry, existing, profile, agent_id=agent_id, skills_only=True)
    return registry.get_agent(agent_id), True
