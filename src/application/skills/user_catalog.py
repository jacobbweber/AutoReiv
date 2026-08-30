"""
User agentskills.io pack catalog with progressive disclosure [REQ-DATA-009 - REQ-DATA-011].

List is frontmatter only. Body and JSON tool blocks load on demand via
DynamicSkillLoader.load_skill_from_markdown. Python builtins are never replaced.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.dynamic_loader import DynamicSkillLoader
from src.domain.skills.user_pack import UserSkillManifest

logger = logging.getLogger(__name__)

LIST_USER_SKILL_PACKS = "list_user_skill_packs"
SKILL_VIEW = "skill_view"


class UserSkillCatalog:
    """Catalog of USER packs under $DATA_DIR/skills. Repo .agents/skills are not scanned."""

    def __init__(
        self,
        skills_dir: Optional[Union[str, Path]] = None,
        tool_registry: Optional[ScopedToolRegistry] = None,
    ) -> None:
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self.tool_registry = tool_registry
        self._manifests: List[UserSkillManifest] = []

    def list_manifests(self) -> List[UserSkillManifest]:
        """Return name + description + path. Does not parse SKILL.md bodies."""
        if self.skills_dir is None or not self.skills_dir.is_dir():
            self._manifests = []
            return []
        self._manifests = DynamicSkillLoader.list_skill_manifests(str(self.skills_dir))
        return list(self._manifests)

    def mount_at_bootstrap(self) -> List[UserSkillManifest]:
        """Scan frontmatter and register progressive-disclosure tools. No body parse."""
        manifests = self.list_manifests()
        if self.tool_registry is not None:
            self.register_tools(self.tool_registry)
        return manifests

    def _manifest_by_id(self, pack_id: str) -> Optional[UserSkillManifest]:
        if not self._manifests:
            self.list_manifests()
        for manifest in self._manifests:
            if manifest.id == pack_id:
                return manifest
        return None

    def load_body(self, pack_id: str) -> Dict[str, Any]:
        """Load SKILL.md body and JSON tool blocks on demand [REQ-DATA-010]."""
        manifest = self._manifest_by_id(pack_id)
        if manifest is None:
            return {
                "success": False,
                "error": f"Unknown user pack '{pack_id}'. Call {LIST_USER_SKILL_PACKS} for the catalog.",
            }
        loaded = DynamicSkillLoader.load_skill_from_markdown(manifest.path)
        if not loaded:
            return {"success": False, "error": f"Failed to load SKILL.md for pack '{pack_id}'."}

        skipped = self._mount_pack_tools(loaded)
        tools_meta = []
        for tool in loaded.get("tools") or []:
            tools_meta.append({"name": tool.name, "description": tool.description})
        return {
            "success": True,
            "id": manifest.id,
            "name": loaded.get("name", manifest.name),
            "description": loaded.get("description", manifest.description),
            "path": loaded.get("path", manifest.path),
            "instructions": loaded.get("instructions", ""),
            "tools": tools_meta,
            "skipped_tools": skipped,
        }

    def _mount_pack_tools(self, loaded: Dict[str, Any]) -> List[str]:
        """Mount JSON-declared tools. Existing (builtin) names win; do not exec JSON as Python."""
        skipped: List[str] = []
        if self.tool_registry is None:
            return skipped
        pack_name = str(loaded.get("name") or "user-pack")
        for tool in loaded.get("tools") or []:
            if tool.name in self.tool_registry._tools:
                logger.warning(
                    "User pack tool '%s' collides with existing tool; builtin wins, skipping (pack=%s)",
                    tool.name,
                    pack_name,
                )
                skipped.append(tool.name)
                continue
            self.tool_registry.register_tool(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters if isinstance(tool.parameters, dict) else {},
                handler=self._playbook_tool_handler(tool.name, pack_name),
            )
        return skipped

    def _playbook_tool_handler(self, tool_name: str, pack_name: str):
        def handler(**kwargs: Any) -> Dict[str, Any]:
            return {
                "success": False,
                "error": (
                    f"Tool '{tool_name}' is declared by user pack '{pack_name}' as an "
                    "agentskills.io schema, not an executable Python builtin."
                ),
            }

        return handler

    def list_user_skill_packs(self) -> Dict[str, Any]:
        """Tool handler: catalog list is name + description only."""
        packs = []
        for manifest in self.list_manifests():
            packs.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "description": manifest.description,
                    "path": manifest.path,
                    "origin": manifest.origin,
                }
            )
        return {"packs": packs}

    def skill_view(self, pack_id: str) -> Dict[str, Any]:
        """Tool handler: activate a pack and load its body + declared tools."""
        return self.load_body(pack_id)

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register progressive-disclosure tools. Does not dump SKILL.md into the system prompt."""
        catalog_bits = [f"{m.name}: {m.description}" for m in self._manifests]
        catalog_summary = "; ".join(catalog_bits) if catalog_bits else "(none mounted)"
        registry.register_tool(
            name=LIST_USER_SKILL_PACKS,
            description=(
                "List user agentskills.io packs from the data dir (name and description only). "
                f"Catalog: {catalog_summary}"
            ),
            parameters={"type": "object", "properties": {}},
            handler=self.list_user_skill_packs,
        )
        registry.register_tool(
            name=SKILL_VIEW,
            description=(
                "Load the full SKILL.md body and declared JSON tools for one user pack. "
                f"Use {LIST_USER_SKILL_PACKS} first. Does not replace Python builtin skills."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pack_id": {
                        "type": "string",
                        "description": "User pack id (directory slug under $DATA_DIR/skills).",
                    },
                },
                "required": ["pack_id"],
            },
            handler=self.skill_view,
        )
