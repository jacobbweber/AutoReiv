"""Agent pack tools for AutoReiv: inspect, export, import, and scaffold one specialist pack.

``inspect_agent_pack`` moved here from the retired Factory dispatch tools [CARD-497 D6, ADR-0060].
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.application.agent_packs.service import AgentPackService
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.infrastructure.agents.registry import BuiltinAgentRegistry

logger = logging.getLogger(__name__)


class AgentPackTools:
    """Atomic callables that write the same pack schema as Agent Studio import/export."""

    def __init__(
        self,
        agent_registry: BuiltinAgentRegistry,
        tool_registry: Optional[ScopedToolRegistry] = None,
        store: Any = None,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.agent_registry = agent_registry
        self.tool_registry = tool_registry or getattr(agent_registry, "master_tool_registry", None)
        self.store = store if store is not None else getattr(agent_registry, "state_store", None)
        self.data_dir = Path(data_dir) if data_dir is not None else None

    def _resolved_data_dir(self) -> Path:
        if self.data_dir is not None:
            return Path(self.data_dir)
        from src.infrastructure.data.resolver import DataDirResolver

        return DataDirResolver().resolve().root

    def _inspect_data_dir(self) -> Path:
        try:
            return self._resolved_data_dir()
        except Exception:
            return Path.cwd() / "scratch"

    def _available_tools(self) -> Optional[set[str]]:
        if self.tool_registry is None:
            return None
        return {t.name for t in self.tool_registry.list_tools()}

    def _service(self) -> AgentPackService:
        return AgentPackService(
            data_dir=self._resolved_data_dir(),
            agent_registry=self.agent_registry,
            store=self.store,
            available_tools=self._available_tools(),
        )

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="inspect_agent_pack",
            description=(
                "Inspect an agent's current identity, tools, skills, and pack storage without modifying it. "
                "Use this to understand what the target agent already does before designing new capabilities."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Agent id (slug) to inspect (e.g. autoreiv, developer, tutor, direct).",
                    },
                },
                "required": ["agent_id"],
            },
            handler=self.inspect_agent_pack,
        )

        registry.register_tool(
            name="export_agent_pack",
            description=(
                "Export one agent as an Agent Pack folder and zip only. "
                "Includes identity, SKILL.md runbooks, pack-owned tool ids, Show in Chat. "
                "Folder/zip only. Does not copy transcripts, secrets, or instance facts."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent id to export."},
                },
                "required": ["agent_id"],
            },
            handler=self.export_agent_pack,
        )
        registry.register_tool(
            name="import_agent_pack",
            description=(
                "Import an Agent Pack from a folder or zip path only. "
                "Creates or updates the specialist from that pack. Not a recommendation draft. "
                "Not for New Agent / create-a-new-agent (use scaffold_agent_pack)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Filesystem path to a pack folder or .zip.",
                    },
                },
                "required": ["path"],
            },
            handler=self.import_agent_pack,
        )
        registry.register_tool(
            name="scaffold_agent_pack",
            description=(
                "Write or import a nested Agent Pack when the human wants a new specialist. "
                "Use this for New Agent, 'create a new agent', and pack authoring. "
                "Tools in the spec must be existing catalog ids. Do not invent Python. "
                "This is the write path for a new pack. Do not use propose_agent_specification "
                "or save_agent_specification to birth a pack."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "spec": {
                        "type": "object",
                        "description": (
                            "Pack spec: id, name, description, system_prompt, tone, purpose, "
                            "avatar_icon, model, show_in_chat, skills (id, tools, optional "
                            "name/description/body), optional pack_tool_names/allowed_skill "
                            "compat fields."
                        ),
                    },
                },
                "required": ["spec"],
            },
            handler=self.scaffold_agent_pack,
        )

    async def inspect_agent_pack(self, agent_id: str, **kwargs: Any) -> Dict[str, Any]:
        """Inspect target agent capabilities, tool names, and skill runbooks [REQ-FACT-062]."""
        clean_id = str(agent_id or "").strip()
        if not clean_id:
            return {"success": False, "error": "agent_id is required."}

        profile = None
        if self.agent_registry is not None and hasattr(self.agent_registry, "get_profile"):
            profile = self.agent_registry.get_profile(clean_id)
        if profile is None and self.agent_registry is not None and hasattr(self.agent_registry, "get_agent"):
            profile = self.agent_registry.get_agent(clean_id)

        if profile is None:
            # Fallback: inspect user data packs directory directly
            packs_dir = self._inspect_data_dir() / "packs" / clean_id
            manifest_file = packs_dir / "pack.json"
            if manifest_file.is_file():
                try:
                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    tools: list[str] = []
                    skills: list[str] = []
                    for s in data.get("skills", []):
                        if isinstance(s, dict):
                            skills.append(s.get("id", ""))
                            tools.extend(s.get("tools", []))
                        elif isinstance(s, str):
                            skills.append(s)
                    return {
                        "success": True,
                        "agent_id": clean_id,
                        "name": data.get("name", clean_id),
                        "description": data.get("description", ""),
                        "avatar_icon": data.get("avatar_icon", "bot"),
                        "tools": sorted(set(filter(None, tools))),
                        "skills": sorted(set(filter(None, skills))),
                        "pack_path": str(packs_dir),
                    }
                except Exception as exc:
                    logger.warning("Failed reading pack.json for %s: %s", clean_id, exc)

            return {"success": False, "error": f"Agent '{clean_id}' not found in registry or pack store."}

        # Extract tools and skills from profile
        tools_list: list[str] = []
        if getattr(profile, "pack_tool_names", None):
            tools_list.extend(profile.pack_tool_names)
        if getattr(profile, "skills", None):
            for s in profile.skills:
                if hasattr(s, "tools") and s.tools:
                    tools_list.extend(s.tools)
                elif isinstance(s, dict) and "tools" in s:
                    tools_list.extend(s["tools"])
        if not tools_list and getattr(profile, "allowed_tool_names", None):
            tools_list.extend(profile.allowed_tool_names)

        skills_list: list[str] = []
        if getattr(profile, "skills", None):
            for s in profile.skills:
                sid = getattr(s, "id", None) or (s.get("id") if isinstance(s, dict) else str(s))
                if sid:
                    skills_list.append(sid)
        if getattr(profile, "allowed_skill", None):
            skills_list.extend(profile.allowed_skill)

        pack_path = self._inspect_data_dir() / "packs" / clean_id

        return {
            "success": True,
            "agent_id": clean_id,
            "name": getattr(profile, "name", clean_id),
            "description": getattr(profile, "description", ""),
            "avatar_icon": getattr(profile, "avatar_icon", "bot"),
            "tools": sorted(set(filter(None, tools_list))),
            "skills": sorted(set(filter(None, skills_list))),
            "pack_path": str(pack_path) if pack_path.exists() else None,
        }

    async def export_agent_pack(self, agent_id: str, **kwargs) -> Dict[str, Any]:
        try:
            service = self._service()
            folder = service.export_folder(agent_id)
            zip_path = service.export_zip(agent_id)
            return {
                "success": True,
                "agent_id": agent_id,
                "folder": str(folder),
                "zip": str(zip_path),
            }
        except (KeyError, ValueError, FileNotFoundError) as exc:
            return {"success": False, "error": str(exc)}

    async def import_agent_pack(self, path: str, **kwargs) -> Dict[str, Any]:
        try:
            profile = self._service().import_path(path)
            return {
                "success": True,
                "agent_id": profile.id,
                "name": profile.name,
                "show_in_chat": profile.show_in_chat,
                "pack_tool_names": list(profile.pack_tool_names or []),
                "allowed_skill": list(profile.allowed_skill or []),
            }
        except (KeyError, ValueError, FileNotFoundError, OSError) as exc:
            return {"success": False, "error": str(exc)}

    async def scaffold_agent_pack(self, spec: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        payload = spec if isinstance(spec, dict) else kwargs.get("spec")
        if not isinstance(payload, dict):
            return {"success": False, "error": "spec object is required."}
        try:
            service = self._service()
            folder = service.scaffold_pack(payload)
            profile = service.import_path(folder)
            return {
                "success": True,
                "agent_id": profile.id,
                "name": profile.name,
                "folder": str(folder),
                "show_in_chat": profile.show_in_chat,
                "pack_tool_names": list(profile.pack_tool_names or []),
                "allowed_skill": list(profile.allowed_skill or []),
            }
        except (KeyError, ValueError, FileNotFoundError, OSError) as exc:
            return {"success": False, "error": str(exc)}
