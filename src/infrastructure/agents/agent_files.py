"""AgentProfile <-> agent file (CARD-570).

The agent file holds what the agent *is* (name, description, tone, purpose, avatar,
show_in_chat, max_turns, skills, prompt and the operator fields Studio edits). Per-agent
model/provider/endpoint stay separate settings (``agent_model_settings``), so "Use shipped
version" keeps them.
"""

from __future__ import annotations

from typing import Any, Optional

from src.domain.kernel.models import AgentOrigin, AgentProfile
from src.infrastructure.content.store import ContentFile

MODEL_SETTINGS_KEY = "agent_model_settings"
MODEL_FIELDS = ("model", "provider", "api_base_url", "api_key", "context_window")
# Header fields written first, in this order; body = system prompt.
HEADER_FIELDS = ("name", "description", "tone", "purpose", "avatar", "show_in_chat", "max_turns", "skills")
# Operator fields a Studio save may also write (full copy, no merging).
EXTRA_FIELDS = (
    "visibility",
    "fleet",
    "history_retention_days",
    "always_auto_run",  # CARD-573 Agent Preferences
    "storage_enabled",
    "storage_type",
    "memory_enabled",
    "memory_retention_days",
    "pinned_memory",
    "allowed_credentials",
    "mcp_servers",
    "template_folder",  # CARD-603
)
_DEFAULTS = {name: f.default for name, f in AgentProfile.model_fields.items() if f.default is not None}


def _plain(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, list):
        return [_plain(v.model_dump() if hasattr(v, "model_dump") else v) for v in value]
    return value


def profile_from_file(item: ContentFile, model_settings: Optional[dict[str, Any]] = None) -> AgentProfile:
    meta = dict(item.meta)
    data: dict[str, Any] = {
        "id": item.id,
        "name": str(meta.get("name") or item.id),
        "description": str(meta.get("description") or ""),
        "system_prompt": item.body.strip(),
        "allowed_skill": item.skills,
        "avatar_icon": str(meta.get("avatar") or "bot"),
        "origin": AgentOrigin.FILE,  # all file agents are normal chat agents; shipped/edited is in file status
        "is_builtin": False,  # is_builtin/"system" hide an agent in the UI
        "user_modified": item.edited,
        "seed_content_hash": item.shipped_hash,
    }
    for key in ("tone", "purpose", "show_in_chat", "max_turns", *EXTRA_FIELDS):
        if meta.get(key) is not None:
            data[key] = meta[key]
    for key, value in (model_settings or {}).items():
        if key in MODEL_FIELDS and value not in (None, ""):
            data[key] = value
    return AgentProfile.model_validate(data)


def meta_from_profile(profile: AgentProfile) -> tuple[dict[str, Any], str]:
    meta: dict[str, Any] = {
        "name": profile.name,
        "description": profile.description or "",
        "tone": _plain(profile.tone),
    }
    if profile.purpose:
        meta["purpose"] = _plain(profile.purpose)
    meta["avatar"] = profile.avatar_icon or "bot"
    meta["show_in_chat"] = bool(profile.show_in_chat)
    meta["max_turns"] = profile.max_turns
    meta["skills"] = list(profile.allowed_skill or [])
    for key in EXTRA_FIELDS:
        value = _plain(getattr(profile, key, None))
        if value in (None, "", []) or value == _DEFAULTS.get(key):
            continue
        meta[key] = value
    return meta, profile.system_prompt or ""


def model_settings_from_profile(profile: AgentProfile) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in MODEL_FIELDS:
        value = getattr(profile, key, None)
        if value in (None, "") or (key in ("model", "provider") and value == "default"):
            continue
        out[key] = value
    return out
