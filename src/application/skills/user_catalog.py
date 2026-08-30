"""
User agentskills.io pack catalog with progressive disclosure [REQ-DATA-009 - REQ-DATA-011].

List is frontmatter only. Body and JSON tool blocks load on demand via
DynamicSkillLoader.load_skill_from_markdown. Python builtins are never replaced.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.dynamic_loader import DynamicSkillLoader
from src.domain.skills.user_pack import UserSkillManifest

logger = logging.getLogger(__name__)

LIST_USER_SKILL_PACKS = "list_user_skill_packs"
SKILL_VIEW = "skill_view"

_PACK_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$"
)


class PackJailError(ValueError):
    """Pack id is not a jailed path under $DATA_DIR/skills."""


def render_skill_md(name: str, description: str, instructions: str) -> str:
    """Serialize agentskills.io SKILL.md (frontmatter + playbook body)."""
    dumped = yaml.safe_dump(
        {"name": name, "description": description},
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    body = (instructions or "").replace("\r\n", "\n").strip()
    if body:
        return f"---\n{dumped}\n---\n\n{body}\n"
    return f"---\n{dumped}\n---\n"


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

    def resolve_skill_md(self, pack_id: str) -> Path:
        """Jail pack_id to $DATA_DIR/skills/<id>/SKILL.md. Rejects traversal."""
        if self.skills_dir is None:
            raise PackJailError("Skills directory is not configured.")
        if not pack_id or not isinstance(pack_id, str) or not _PACK_ID_RE.match(pack_id):
            raise PackJailError("Invalid pack id.")
        if ".." in pack_id.split("/"):
            raise PackJailError("Path traversal rejected.")
        root = self.skills_dir.expanduser().resolve()
        candidate = self.skills_dir / pack_id / "SKILL.md"
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            raise PackJailError(str(exc)) from exc
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise PackJailError("Path traversal rejected.") from exc
        try:
            if os.path.commonpath([str(root), str(resolved)]) != str(root):
                raise PackJailError("Path traversal rejected.")
        except ValueError as exc:
            raise PackJailError("Path traversal rejected.") from exc
        return resolved

    def read_pack(self, pack_id: str) -> Dict[str, Any]:
        """Read SKILL.md for Skills Studio. Parses tools; does not mount them."""
        path = self.resolve_skill_md(pack_id)
        if not path.is_file():
            return {"success": False, "error": f"Pack '{pack_id}' not found.", "not_found": True}
        parsed = DynamicSkillLoader.load_skill_from_markdown(str(path))
        if not parsed:
            return {"success": False, "error": f"Failed to load SKILL.md for pack '{pack_id}'."}
        tools_meta = []
        for tool in parsed.get("tools") or []:
            tools_meta.append({"name": tool.name, "description": tool.description})
        return {
            "success": True,
            "manifest": {
                "id": pack_id,
                "name": parsed.get("name", pack_id),
                "description": parsed.get("description", ""),
                "path": str(path),
                "origin": "user",
            },
            "instructions": parsed.get("instructions", ""),
            "tools": tools_meta,
        }

    def save_pack(
        self,
        pack_id: str,
        name: str,
        description: str,
        instructions: str,
    ) -> Dict[str, Any]:
        """Write SKILL.md inside the skills tree. Creates the pack folder if needed."""
        path = self.resolve_skill_md(pack_id)
        clean_name = (name or "").strip()
        clean_description = (description or "").strip()
        if not clean_name or not clean_description:
            return {"success": False, "error": "name and description are required."}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            render_skill_md(clean_name, clean_description, instructions or ""),
            encoding="utf-8",
        )
        self.list_manifests()
        return self.read_pack(pack_id)

    def create_pack(
        self,
        pack_id: str,
        name: Optional[str] = None,
        description: str = "User skill pack.",
    ) -> Dict[str, Any]:
        """Create an empty playbook pack (folder + SKILL.md)."""
        path = self.resolve_skill_md(pack_id)
        if path.is_file():
            return {"success": False, "error": f"Pack '{pack_id}' already exists.", "conflict": True}
        display = (name or pack_id).strip() or pack_id
        desc = (description or "User skill pack.").strip() or "User skill pack."
        return self.save_pack(pack_id, display, desc, "")

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
