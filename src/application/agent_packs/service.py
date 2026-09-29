"""Install a platform pack folder at boot. Import/export/scaffold removed [CARD-569]; the rest goes in CARD-570."""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Optional, Union

from src.application.agent_packs.schema import (
    FORBIDDEN_PACK_KEYS,
    PACK_SCHEMA_VERSION,
    REQUIRED_PLATFORM_TOOLS,
    AgentPackManifest,
)
from src.domain.agents.guardrails import AgentProfileGuardrail, AgentValidationError
from src.domain.kernel.models import AgentProfile
from src.domain.settings.models import AgentCustomization

_SAFE_ID = re.compile(r"^[a-zA-Z0-9._-]+$")

logger = logging.getLogger(__name__)


class PlatformSkillMountError(RuntimeError):
    """Raised when a required platform skill fails mount-time validation [CARD-330, REQ-SKILL-TIER-002]."""
    pass


def validate_platform_skills(available_tools: Any) -> None:
    """
    Validate that all required platform skills/tools are present at mount time.
    Raises PlatformSkillMountError if any required tool is missing [CARD-330, REQ-SKILL-TIER-002].
    """
    if available_tools is None:
        return
    if isinstance(available_tools, (set, list, tuple)):
        tools_set = set(available_tools)
    elif hasattr(available_tools, "__iter__"):
        tools_set = set(available_tools)
    else:
        return

    missing = [tool for tool in REQUIRED_PLATFORM_TOOLS if tool not in tools_set]
    if missing:
        raise PlatformSkillMountError(
            f"Missing required platform tools at mount time: {missing}. "
            "Platform requires coordination and wiki read tools for all agents."
        )



def _safe_id(value: str) -> str:
    text = (value or "").strip()
    if not text or not _SAFE_ID.match(text):
        raise ValueError(f"Invalid id {value!r}. Use letters, digits, dot, underscore, hyphen.")
    return text


def _strip_forbidden(payload: Any) -> Any:
    """Drop instance facts / secrets from nested dicts before writing a pack."""
    if isinstance(payload, dict):
        return {k: _strip_forbidden(v) for k, v in payload.items() if k not in FORBIDDEN_PACK_KEYS}
    if isinstance(payload, list):
        return [_strip_forbidden(item) for item in payload]
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


class AgentPackService:
    """Write and read one specialist pack. Does not add a kernel primitive."""

    def __init__(
        self,
        data_dir: Union[str, Path],
        agent_registry: Any = None,
        store: Any = None,
        available_tools: Optional[set[str]] = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.agent_registry = agent_registry
        self.store = store if store is not None else getattr(agent_registry, "state_store", None)
        self.available_tools = available_tools
        self.skills_dir = self.data_dir / "skills"
        self.agents_dir = self.data_dir / "agents"
        self.packs_dir = self.data_dir / "packs"

    def pack_dir(self, pack_id: str) -> Path:
        safe = _safe_id(pack_id)
        if self.packs_dir.is_dir():
            for f in self.packs_dir.glob("*/agents/" + safe):
                if f.is_dir():
                    return f
        return self.packs_dir / safe

    def _persist_pack_manifest(self, manifest: AgentPackManifest) -> None:
        dest = self.pack_dir(manifest.id)
        dest.mkdir(parents=True, exist_ok=True)
        payload = manifest.model_dump(mode="json")
        payload["schema_version"] = PACK_SCHEMA_VERSION
        _write_json(dest / "pack.json", payload)

    def import_path(self, source: Union[str, Path]) -> AgentProfile:
        """Install a platform pack folder into the registry (boot only; removed by CARD-570)."""
        src = Path(source)
        if not src.exists():
            raise FileNotFoundError(f"Pack source not found: {src}")
        if not src.is_dir():
            raise ValueError(f"Pack source must be a folder: {src}")
        return self._import_folder(src)

    def _import_folder(self, folder: Path) -> AgentProfile:
        pack_json = folder / "pack.json"
        if not pack_json.is_file():
            raise ValueError("Pack folder is missing pack.json.")
        raw = json.loads(pack_json.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("pack.json must be an object.")
        raw = _strip_forbidden(raw)
        manifest = AgentPackManifest.model_validate(raw)
        manifest.schema_version = PACK_SCHEMA_VERSION

        # Pack skills remain strictly isolated under packs/<agent_id>/skills/ [CARD-203].
        # Never copy agent-specific skills into the platform skills_dir ($DATA_DIR/skills/).
        dest_pack = self.pack_dir(manifest.id)
        if folder.resolve() != dest_pack.resolve():
            dest_pack.mkdir(parents=True, exist_ok=True)
            if (folder / "skills").is_dir():
                shutil.copytree(folder / "skills", dest_pack / "skills", dirs_exist_ok=True)
            if (folder / "tools").is_dir():
                shutil.copytree(folder / "tools", dest_pack / "tools", dirs_exist_ok=True)
            if (folder / "mcp").is_dir():
                shutil.copytree(folder / "mcp", dest_pack / "mcp", dirs_exist_ok=True)
        profile = self._upsert_agent(manifest)
        self._persist_pack_manifest(manifest)
        return profile

    def _upsert_agent(self, manifest: AgentPackManifest) -> AgentProfile:
        if self.agent_registry is None:
            raise ValueError("Agent registry is required to import a pack.")
        existing = self.agent_registry.get_agent(manifest.id)
        storage_enabled = (
            manifest.storage.enabled
            if manifest.storage is not None
            else getattr(manifest, "storage_enabled", False)
        )
        storage_type = (
            manifest.storage.type
            if manifest.storage is not None
            else getattr(manifest, "storage_type", "sqlite") or "sqlite"
        )
        memory_enabled = (
            manifest.memory.enabled
            if manifest.memory is not None
            else getattr(manifest, "memory_enabled", True)
        )
        memory_retention_days = (
            manifest.memory.retention_days
            if manifest.memory is not None
            else getattr(manifest, "memory_retention_days", 30)
        )
        pinned_memory = (
            manifest.memory.pinned_memory
            if manifest.memory is not None
            else getattr(manifest, "pinned_memory", "") or ""
        )
        pack_mcp = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in (manifest.mcp_servers or [])
        ]
        if not pack_mcp and manifest.mcp_server:
            pack_mcp = [manifest.mcp_server.model_dump() if hasattr(manifest.mcp_server, "model_dump") else manifest.mcp_server]

        if existing is not None:
            existing_mcp = [
                s.model_dump() if hasattr(s, "model_dump") else s
                for s in (getattr(existing, "mcp_servers", []) or [])
            ]
            merged_mcp = list(existing_mcp)
            for s in pack_mcp:
                if isinstance(s, dict) and not any(e.get("name") == s.get("name") for e in merged_mcp if isinstance(e, dict)):
                    merged_mcp.append(s)
            data = {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "system_prompt": manifest.system_prompt or existing.system_prompt,
                "provider": getattr(manifest, "provider", "default") or "default",
                "purpose": manifest.purpose,
                "tone": manifest.tone,
                "avatar_icon": manifest.avatar_icon,
                "model": manifest.model,
                "allowed_skill": list(manifest.allowed_skill or existing.allowed_skill or []),
                "show_in_chat": manifest.show_in_chat,
                "visibility": getattr(manifest, "visibility", "public") or "public",
                "fleet": getattr(manifest, "fleet", None),
                "max_turns": existing.max_turns,
                "history_retention_days": existing.history_retention_days,
                "is_builtin": existing.is_builtin,
                "storage_enabled": storage_enabled,
                "storage_type": storage_type,
                "memory_enabled": memory_enabled,
                "memory_retention_days": memory_retention_days,
                "pinned_memory": pinned_memory,
                "mcp_servers": merged_mcp,
            }
        else:
            data = {
                "id": manifest.id,
                "name": manifest.name,
                "description": manifest.description,
                "system_prompt": manifest.system_prompt
                or f"You are AutoReiv's {manifest.name}. Follow the pack runbooks.",
                "provider": getattr(manifest, "provider", "default") or "default",
                "purpose": manifest.purpose,
                "tone": manifest.tone,
                "avatar_icon": manifest.avatar_icon,
                "model": manifest.model,
                "allowed_skill": list(manifest.allowed_skill or []),
                "show_in_chat": manifest.show_in_chat,
                "visibility": getattr(manifest, "visibility", "public") or "public",
                "fleet": getattr(manifest, "fleet", None),
                "is_builtin": False,
                "storage_enabled": storage_enabled,
                "storage_type": storage_type,
                "memory_enabled": memory_enabled,
                "memory_retention_days": memory_retention_days,
                "pinned_memory": pinned_memory,
                "mcp_servers": pack_mcp,
            }

        try:
            profile = AgentProfileGuardrail.validate(data, available_tools=self.available_tools)
        except AgentValidationError as exc:
            raise ValueError(str(exc)) from exc

        if existing is not None and existing.is_builtin:
            if self.store is None:
                raise ValueError("State store is required to update a built-in agent from a pack.")
            self.store.save_agent_override(
                AgentCustomization(
                    agent_id=profile.id,
                    provider=profile.provider,
                    tone=profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone),
                    system_prompt=profile.system_prompt,
                    model=profile.model,
                    purpose=profile.purpose.value if hasattr(profile.purpose, "value") else str(profile.purpose),
                    allowed_skill=profile.allowed_skill,
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
                    mcp_servers=profile.mcp_servers,
                )
            )

        else:
            self.agent_registry.register_custom_agent(profile)
            deleter = getattr(self.store, "delete_agent_override", None)
            if callable(deleter):
                deleter(profile.id)
        loaded = self.agent_registry.get_agent(profile.id)
        return loaded or profile

