"""Agent pack tools for AutoReiv: export, import, and scaffold one specialist pack."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.application.agent_packs.service import AgentPackService
from src.application.kernel.tool_registry import ScopedToolRegistry
from src.infrastructure.agents.registry import BuiltinAgentRegistry


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
            name="export_agent_pack",
            description=(
                "Export one agent as an Agent Pack folder and zip only. "
                "Includes identity, SKILL.md runbooks, pack-owned tool ids, Show in Chat, "
                "and workflows. Folder/zip only. Does not copy transcripts, secrets, or instance facts."
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
                            "compat fields, and workflows."
                        ),
                    },
                },
                "required": ["spec"],
            },
            handler=self.scaffold_agent_pack,
        )

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
