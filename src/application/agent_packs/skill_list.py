"""One save path for an agent's skill list [CARD-502 / REQ-502-001].

Agent Studio Save (``PUT /api/agents/{id}``) and Teach > Adopt both call
``persist_agent_profile`` so a skill switched on either way is stored the same way:
the operator override row, the content-lock rule (CARD-449), the operator
disabled / added skill records that restart promotion reads, and the live
``packs/<id>/pack.json`` projection.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.domain.settings.models import AgentCustomization

logger = logging.getLogger(__name__)


def _enum_text(value: Any) -> Any:
    return value.value if hasattr(value, "value") else str(value)


def customization_from_profile(profile: Any, agent_id: str) -> AgentCustomization:
    """Operator override row for a full agent profile."""
    return AgentCustomization(
        agent_id=agent_id,
        name=profile.name,
        provider=profile.provider,
        api_base_url=profile.api_base_url,
        api_key=profile.api_key,
        context_window=profile.context_window,
        tone=_enum_text(profile.tone),
        system_prompt=profile.system_prompt,
        model=profile.model,
        purpose=_enum_text(profile.purpose),
        allowed_tool_names=profile.allowed_tool_names,
        allowed_skill=profile.allowed_skill,
        pack_tool_names=profile.pack_tool_names,
        show_in_chat=profile.show_in_chat,
        max_turns=profile.max_turns,
        history_retention_days=profile.history_retention_days,
        storage_enabled=profile.storage_enabled,
        storage_type=profile.storage_type,
        memory_enabled=profile.memory_enabled,
        memory_retention_days=profile.memory_retention_days,
        pinned_memory=profile.pinned_memory,
        allow_autonomous_training=profile.allow_autonomous_training,
        max_training_retries=profile.max_training_retries,
        allow_wiki_access=profile.allow_wiki_access,
        allowed_credentials=profile.allowed_credentials,
        mcp_servers=profile.mcp_servers,
    )


def studio_can_show_skill(skill_id: str, data_root: Optional[Path], agent_id: Optional[str] = None) -> bool:
    """Agent Studio shows a pill for this skill: a platform skill, or any skill with a SKILL.md [CARD-509]."""
    from src.application.agent_packs.schema import PLATFORM_SKILL_IDS
    from src.infrastructure.skills.platform_pack_promotion import find_skill_md

    return skill_id in PLATFORM_SKILL_IDS or find_skill_md(data_root, skill_id, agent_id) is not None


def studio_extra_skill_pills(profile: Any, shown_ids: set[str], data_root: Optional[Path]) -> list[dict[str, Any]]:
    """Pills for allowed or shipped skills that no other list shows (for example AutoReiv ``coding``) [CARD-509 / D3].

    ``shown_ids`` are the ids the catalog and the pack manifest already show. Skills without a
    SKILL.md get no pill. Tools stay empty: the pill only switches the skill on or off.
    """
    from src.application.skills.runbook_frontmatter import frontmatter_view
    from src.infrastructure.skills.platform_pack_promotion import find_skill_md, platform_seed_skills

    agent_id = str(getattr(profile, "id", "") or "")
    extras: list[dict[str, Any]] = []
    for sid in list(getattr(profile, "allowed_skill", None) or []) + platform_seed_skills(agent_id):
        if sid in shown_ids or any(e["id"] == sid for e in extras):
            continue
        path = find_skill_md(data_root, sid, agent_id)
        if path is None:
            continue
        try:
            view = frontmatter_view(path.read_text(encoding="utf-8"))
        except OSError:
            view = {}
        extras.append(
            {
                "id": sid,
                "name": str(view.get("name") or "").strip() or sid,
                "description": str(view.get("description") or "").strip(),
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
    """Store an edited agent profile.

    ``skills_only`` is the Adopt path: only the skill list changed, so the content
    lock is never newly set and the prompt/tool checks are skipped.
    ``data_dir`` lets the disabled-skill record skip skills Studio cannot show (CARD-509).
    """
    from src.application.agent_packs.schema import is_platform_pack
    from src.infrastructure.skills.platform_pack_promotion import (
        record_operator_added_skills,
        record_operator_disabled_skills,
        should_set_content_lock,
    )

    live_skills = list(profile.allowed_skill or [])
    lock = not skills_only
    if is_platform_pack(agent_id):
        stock = list(getattr(existing, "allowed_skill", None) or [])
        if not skills_only:
            # CARD-449: lock only when pack-owned content actually changed
            lock = should_set_content_lock(
                existing=existing,
                new_prompt=profile.system_prompt,
                new_skills=live_skills,
                new_tools=list(profile.allowed_tool_names or []),
                store=store,
                pack_id=agent_id,
            )
            showable = {s for s in stock if studio_can_show_skill(s, data_dir, agent_id)}
            record_operator_disabled_skills(
                store, agent_id, live_skills=live_skills, stock_skills=stock, showable=showable
            )
        # CARD-502: skills the operator switched on beyond the platform seed survive restart
        record_operator_added_skills(store, agent_id, live_skills=live_skills)
    user_modified = True if lock else bool(getattr(existing, "user_modified", False))

    if not existing.is_builtin:
        registry.register_custom_agent(profile)
    if store is None or not hasattr(store, "save_agent_override"):
        return
    customization = customization_from_profile(profile, agent_id)
    customization.user_modified = user_modified
    store.save_agent_override(customization)
    if hasattr(store, "mark_agent_user_modified"):
        store.mark_agent_user_modified(agent_id, modified=user_modified)


def sync_pack_json_skills(
    data_dir: Optional[Path],
    agent_id: str,
    allowed_skill: list[str],
    skill_entry: Optional[dict[str, Any]] = None,
) -> None:
    """Keep ``packs/<id>/pack.json`` allowed_skill (and the skill entry) in step."""
    if data_dir is None:
        return
    pack_json = Path(data_dir) / "packs" / agent_id / "pack.json"
    data: dict[str, Any] = {}
    if pack_json.is_file():
        try:
            data = json.loads(pack_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Unreadable pack.json for %s; rewriting skill fields only", agent_id)
            data = {}
    data["allowed_skill"] = list(allowed_skill)
    if skill_entry is not None:
        skills = [s for s in (data.get("skills") or []) if not (isinstance(s, dict) and s.get("id") == skill_entry["id"])]
        skills.append(skill_entry)
        data["skills"] = skills
    pack_json.parent.mkdir(parents=True, exist_ok=True)
    pack_json.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_skill_to_agent(
    store: Any,
    registry: Any,
    *,
    agent_id: str,
    skill_id: str,
    data_dir: Optional[Path] = None,
    skill_entry: Optional[dict[str, Any]] = None,
) -> tuple[Any, bool]:
    """Switch one skill on for an agent through the shared save path.

    Returns ``(fresh_profile, already_on)``. Raises ``LookupError`` for an unknown agent.
    """
    existing = registry.get_agent(agent_id)
    if existing is None:
        raise LookupError(agent_id)
    current = list(getattr(existing, "allowed_skill", None) or [])
    already = skill_id in current
    new_skills = current if already else current + [skill_id]
    profile = existing.model_copy(update={"allowed_skill": new_skills})
    persist_agent_profile(store, registry, existing, profile, agent_id=agent_id, skills_only=True)
    sync_pack_json_skills(data_dir, agent_id, new_skills, skill_entry)
    return registry.get_agent(agent_id), already
