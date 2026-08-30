"""
User agentskills.io pack catalog with progressive disclosure [REQ-DATA-009 - REQ-DATA-011].

List is frontmatter only. Body and JSON tool blocks load on demand via
DynamicSkillLoader.load_skill_from_markdown. Python builtins are never replaced.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
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

SNAPSHOTS_DIRNAME = "snapshots"
ARCHIVE_DIRNAME = "_archive"
SKIP_LIST_DIRNAMES = frozenset({SNAPSHOTS_DIRNAME, ARCHIVE_DIRNAME})
SKILL_MD_NAME = "SKILL.md"
PLAYBOOK_NOTES_MD = "PLAYBOOK_NOTES.md"
NOTES_JSONL = "notes.jsonl"
TRACKED_PACK_FILES = (SKILL_MD_NAME, PLAYBOOK_NOTES_MD, NOTES_JSONL)
LAST_USED_NAME = ".last_used"


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
        loaded = self.load_body(pack_id)
        if loaded.get("success"):
            self.record_pack_use(pack_id)
        return loaded

    def resolve_skill_md(self, pack_id: str) -> Path:
        """Jail pack_id to $DATA_DIR/skills/<id>/SKILL.md. Rejects traversal."""
        if self.skills_dir is None:
            raise PackJailError("Skills directory is not configured.")
        if not pack_id or not isinstance(pack_id, str) or not _PACK_ID_RE.match(pack_id):
            raise PackJailError("Invalid pack id.")
        if ".." in pack_id.split("/"):
            raise PackJailError("Path traversal rejected.")
        for part in pack_id.replace("\\", "/").split("/"):
            if part in SKIP_LIST_DIRNAMES:
                raise PackJailError("Invalid pack id.")
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
        self.record_pack_use(pack_id)
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


    def pack_dir(self, pack_id: str) -> Path:
        """Jailed pack directory under $DATA_DIR/skills/<id>/."""
        return self.resolve_skill_md(pack_id).parent

    def _snapshot_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    def snapshot_pack(self, pack_id: str) -> Dict[str, Any]:
        """Copy SKILL.md + notes sidecar to snapshots/<utc-iso>/ [REQ-IMPROVE-004]."""
        try:
            root = self.pack_dir(pack_id)
            snap_id = self._snapshot_id()
            dest = root / SNAPSHOTS_DIRNAME / snap_id
            if dest.exists():
                snap_id = snap_id + "-" + datetime.now(timezone.utc).strftime("%f")
                dest = root / SNAPSHOTS_DIRNAME / snap_id
            dest.mkdir(parents=True, exist_ok=False)
            copied: List[str] = []
            for name in TRACKED_PACK_FILES:
                src = root / name
                if src.is_file():
                    shutil.copy2(src, dest / name)
                    copied.append(name)
            return {
                "success": True,
                "snapshot_id": snap_id,
                "path": str(dest),
                "files": copied,
                "pack_id": pack_id,
            }
        except Exception as exc:
            logger.warning("snapshot_pack failed for %s: %s", pack_id, exc)
            return {"success": False, "error": str(exc), "pack_id": pack_id}

    def list_snapshots(self, pack_id: str) -> List[str]:
        root = self.pack_dir(pack_id) / SNAPSHOTS_DIRNAME
        if not root.is_dir():
            return []
        return sorted(p.name for p in root.iterdir() if p.is_dir())

    def rollback_pack(self, pack_id: str, snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """Restore SKILL.md + notes from a snapshot. Other packs untouched [REQ-IMPROVE-004]."""
        try:
            root = self.pack_dir(pack_id)
            snap_id = (snapshot_id or "").strip() or None
            if snap_id is None:
                ids = self.list_snapshots(pack_id)
                if not ids:
                    return {"success": False, "error": "No snapshots to roll back.", "pack_id": pack_id}
                snap_id = ids[-1]
            dest = (root / SNAPSHOTS_DIRNAME / snap_id).resolve()
            snap_root = (root / SNAPSHOTS_DIRNAME).resolve()
            dest.relative_to(snap_root)
            if not dest.is_dir():
                return {
                    "success": False,
                    "error": f"Snapshot '{snap_id}' not found.",
                    "pack_id": pack_id,
                }
            restored: List[str] = []
            removed: List[str] = []
            for name in TRACKED_PACK_FILES:
                src = dest / name
                live = root / name
                if src.is_file():
                    shutil.copy2(src, live)
                    restored.append(name)
                elif live.exists() and live.is_file():
                    live.unlink()
                    removed.append(name)
            return {
                "success": True,
                "pack_id": pack_id,
                "snapshot_id": snap_id,
                "restored": restored,
                "removed": removed,
            }
        except Exception as exc:
            logger.warning("rollback_pack failed for %s: %s", pack_id, exc)
            return {"success": False, "error": str(exc), "pack_id": pack_id}

    def append_playbook_note(
        self,
        pack_id: str,
        *,
        insight: str,
        evidence: Optional[str] = None,
        session_id: Optional[str] = None,
        turn_span_id: Optional[str] = None,
        source: str = "online-ace",
        snapshot_first: bool = True,
    ) -> Dict[str, Any]:
        """Append-only sidecar notes. Does not modify SKILL.md [REQ-IMPROVE-006]."""
        note = (insight or "").strip()
        if not note:
            return {"success": False, "error": "insight is required.", "pack_id": pack_id}
        snap: Dict[str, Any] = {"success": True, "snapshot_id": None}
        if snapshot_first:
            snap = self.snapshot_pack(pack_id)
            if not snap.get("success"):
                return {
                    "success": False,
                    "error": snap.get("error") or "Snapshot failed; note was not appended.",
                    "pack_id": pack_id,
                    "skill_md_written": False,
                }
        try:
            root = self.pack_dir(pack_id)
            root.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).isoformat()
            record = {
                "ts": ts,
                "pack_id": pack_id,
                "source": source,
                "session_id": session_id,
                "turn_span_id": turn_span_id,
                "insight": note,
                "evidence": evidence,
            }
            jsonl = root / NOTES_JSONL
            with jsonl.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            md = root / PLAYBOOK_NOTES_MD
            with md.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"- [{ts}] {note}\n")
            return {
                "success": True,
                "pack_id": pack_id,
                "snapshot_id": snap.get("snapshot_id"),
                "skill_md_written": False,
                "notes_md": str(md),
                "notes_jsonl": str(jsonl),
            }
        except Exception as exc:
            logger.warning("append_playbook_note failed for %s: %s", pack_id, exc)
            return {
                "success": False,
                "error": str(exc),
                "pack_id": pack_id,
                "skill_md_written": False,
            }


    def record_pack_use(self, pack_id: str) -> None:
        """Touch .last_used so the Hermes curator has a known last-used [REQ-IMPROVE-013]."""
        try:
            root = self.pack_dir(pack_id)
            if not root.is_dir():
                return
            (root / LAST_USED_NAME).write_text(
                datetime.now(timezone.utc).isoformat(),
                encoding="utf-8",
            )
        except (OSError, PackJailError) as exc:
            logger.debug("record_pack_use skipped for %s: %s", pack_id, exc)

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
