"""
User agentskills.io skill catalog with progressive disclosure [REQ-DATA-009 - REQ-DATA-011].

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

from src.application.kernel.tool_registry import ScopedToolRegistry
from src.application.skills.dynamic_loader import DynamicSkillLoader
from src.domain.skills.user_skill import UserSkillManifest

logger = logging.getLogger(__name__)

LIST_USER_SKILLS = "list_user_skills"
SKILL_VIEW = "skill_view"

_SKILL_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$"
)

SNAPSHOTS_DIRNAME = "snapshots"
ARCHIVE_DIRNAME = "_archive"
SKIP_LIST_DIRNAMES = frozenset({SNAPSHOTS_DIRNAME, ARCHIVE_DIRNAME})
SKILL_MD_NAME = "SKILL.md"
PLAYBOOK_NOTES_MD = "PLAYBOOK_NOTES.md"
NOTES_JSONL = "notes.jsonl"
TRACKED_SKILL_FILES = (SKILL_MD_NAME, PLAYBOOK_NOTES_MD, NOTES_JSONL)
LAST_USED_NAME = ".last_used"


def _first_skill(skills: Any) -> str:
    """First id from a list, or from a list sent as a JSON/Python string ("['a', 'b']")."""
    if isinstance(skills, str):
        text = skills.strip()
        if text.startswith("["):
            try:
                import ast

                skills = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return text.strip("[]'\" ")
        else:
            return text
    if isinstance(skills, (list, tuple)) and skills:
        return str(skills[0]).strip()
    return ""


def render_skill_index(allowed_skill, catalog=None, agent_id=None) -> str:
    """Name + blurb for ticked runbooks only. Empty allowlist injects nothing.

    Operator-store manifests win. Allowlisted skill runbooks that are not copied
    into ``$DATA_DIR/skills/`` still contribute a name and blurb [CARD-427].
    """
    ids = [str(s).strip() for s in (allowed_skill or []) if str(s).strip()]
    if not ids:
        return ""
    by_id = {}
    if catalog is not None:
        try:
            for manifest in catalog.list_manifests():
                by_id[manifest.id] = manifest
        except Exception:
            by_id = {}
    lines = []
    for skill_id in ids:
        manifest = by_id.get(skill_id)
        name = ""
        blurb = ""
        if manifest is not None:
            name = (manifest.name or skill_id).strip()
            blurb = (manifest.description or "").strip()
        else:
            entry = _skill_index_entry(catalog, skill_id, agent_id)
            if entry is None:
                continue
            name, blurb = entry
        # CARD-523: show the id next to the name so skill_view gets the id.
        label = name if name == skill_id else f"{name} (id: {skill_id})"
        if blurb:
            lines.append(f"- {label}: {blurb}")
        else:
            lines.append(f"- {label}")
    if not lines:
        return ""
    header = (
        "Skills (runbooks) for this agent. Names and short descriptions only. "
        "When a listed runbook matches the task, open it with skill_view to load the full instructions. "
        "Do not open a skill id that is not listed here."
    )
    return chr(10).join([header] + lines)


def _skill_index_entry(catalog, skill_id: str, agent_id: Optional[str]) -> Optional[tuple]:
    """Name and description for one skill runbook. Body stays out of the index."""
    if catalog is None:
        return None
    reader = getattr(catalog, "skill_index_entry", None)
    if not callable(reader):
        return None
    try:
        found = reader(skill_id, agent_id=agent_id)
    except Exception:
        return None
    if not found:
        return None
    name = str(found[0] or skill_id).strip() or skill_id
    blurb = str(found[1] or "").strip()
    return name, blurb


class SkillJailError(ValueError):
    """Skill id is not a jailed path under $DATA_DIR/skills."""


class UserSkillCatalog:
    """Catalog of user skills under $DATA_DIR/skills. Repo .agents/skills are not scanned."""

    def __init__(
        self,
        skills_dir: Optional[Union[str, Path]] = None,
        tool_registry: Optional[ScopedToolRegistry] = None,
    ) -> None:
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self.tool_registry = tool_registry
        self.agent_lookup = None
        self._manifests: List[UserSkillManifest] = []

    def list_manifests(self) -> List[UserSkillManifest]:
        """Return name + description + path. Does not parse SKILL.md bodies.

        Data-dir skills win; shipped ``platform/skills`` fill in the rest (minus hidden ones) [CARD-570].
        """
        found: List[UserSkillManifest] = []
        if self.skills_dir is not None and self.skills_dir.is_dir():
            found = DynamicSkillLoader.list_skill_manifests(str(self.skills_dir))
        seen = {m.id for m in found}
        try:
            from src.infrastructure.content.store import REPO_PLATFORM, get_store

            hidden = get_store().skills.hidden()
            for manifest in DynamicSkillLoader.list_skill_manifests(str(REPO_PLATFORM / "skills")):
                if manifest.id not in seen and manifest.id not in hidden:
                    found.append(manifest)
                    seen.add(manifest.id)
        except Exception:
            pass
        self._manifests = found
        return list(self._manifests)

    def mount_at_bootstrap(self) -> List[UserSkillManifest]:
        """Scan frontmatter and register progressive-disclosure tools. No body parse."""
        manifests = self.list_manifests()
        if self.tool_registry is not None:
            self.register_tools(self.tool_registry)
        return manifests

    def _manifest_by_id(self, skill_id: str) -> Optional[UserSkillManifest]:
        if not self._manifests:
            self.list_manifests()
        for manifest in self._manifests:
            if manifest.id == skill_id:
                return manifest
        # CARD-228: skills may appear after bootstrap — refresh once on miss.
        self.list_manifests()
        for manifest in self._manifests:
            if manifest.id == skill_id:
                return manifest
        return None

    def list_skill_metadata(self) -> List[Dict[str, Any]]:
        """Progressive catalog index: id/title only — never SKILL.md bodies [CARD-228]."""
        rows: List[Dict[str, Any]] = []
        for manifest in self.list_manifests():
            rows.append(
                {
                    "id": f"skill.{manifest.id}",
                    "title": manifest.name,
                    "skill_id": manifest.id,
                    "description": manifest.description,
                    "path": manifest.path,
                    "origin": manifest.origin,
                    "metadata_only": True,
                    "body_loaded": False,
                }
            )
        return rows

    def index_metadata_into_capability_catalog(
        self,
        capability_repo: Any,
        *,
        risk_level: str = "medium",
        requires_hitl: bool = False,
    ) -> int:
        """Upsert USER skill manifests as capability index rows without bodies [CARD-228]."""
        from src.domain.capabilities.models import (
            CapabilityIndexEntry,
            CapabilityKind,
            RiskLevel,
        )

        count = 0
        for meta in self.list_skill_metadata():
            entry = CapabilityIndexEntry.self_authored(
                id=meta["id"],
                kind=CapabilityKind.SKILL,
                name=meta["title"],
                summary=meta.get("description") or "",
                keywords=[meta["title"], meta["skill_id"], "skill", "runbook"],
                risk_level=RiskLevel(risk_level),
                requires_hitl=requires_hitl,
                metadata={"skill_id": meta["skill_id"], "origin": meta.get("origin", "user")},
            )
            capability_repo.upsert_entry(entry)
            count += 1
        return count

    def load_body(self, skill_id: str) -> Dict[str, Any]:
        """Load SKILL.md body and JSON tool labels on demand [REQ-DATA-010].

        Stub JSON tools stay in the runbook payload. They are not registered as callables.
        """
        manifest = self._manifest_by_id(skill_id)
        source_path: Optional[str] = None
        result_id = skill_id
        fallback_name = skill_id
        fallback_desc = ""
        if manifest is not None:
            source_path = manifest.path
            result_id = manifest.id
            fallback_name = manifest.name
            fallback_desc = manifest.description
        else:
            # Same live file Skill Studio opens. Do not copy it into $DATA_DIR/skills/.
            live = self.resolve_chat_skill_md(skill_id)
            if live is None or not live.is_file():
                return {
                    "success": False,
                    "error": f"Unknown skill '{skill_id}'.",
                }
            source_path = str(live)
        loaded = DynamicSkillLoader.load_skill_from_markdown(source_path)
        if not loaded:
            return {"success": False, "error": f"Failed to load SKILL.md for skill '{skill_id}'."}

        # CARD-121: JSON `tools` in SKILL.md are labels in the runbook, not model callables.
        skipped = self._mount_skill_tools(loaded)
        tools_meta = []
        for tool in loaded.get("tools") or []:
            tools_meta.append({"name": tool.name, "description": tool.description})
        return {
            "success": True,
            "id": result_id,
            "name": loaded.get("name", fallback_name),
            "description": loaded.get("description", fallback_desc),
            "path": loaded.get("path", source_path),
            "instructions": loaded.get("instructions", ""),
            "tools": tools_meta,
            "skipped_tools": skipped,
        }

    def _mount_skill_tools(self, _loaded: Dict[str, Any]) -> List[str]:
        """SKILL.md JSON stubs are labels, not registry callables (CARD-121)."""
        return []

    def _playbook_tool_handler(self, tool_name: str, skill_name: str):
        def handler(**kwargs: Any) -> Dict[str, Any]:
            return {
                "success": False,
                "error": (
                    f"Tool '{tool_name}' is declared by user skill '{skill_name}' as an "
                    "agentskills.io schema, not an executable Python builtin."
                ),
            }

        return handler

    def _allowed_skill_ids_for_current_agent(self) -> Optional[set]:
        """Allowlist when a tool-call agent is in context; None if no agent context."""
        from src.application.kernel.tool_registry import get_tool_context

        ctx = get_tool_context()
        if not ctx.get("agent_id"):
            return None
        if "allowed_skill" in ctx:
            return {str(s).strip() for s in (ctx.get("allowed_skill") or []) if str(s).strip()}
        lookup = getattr(self, "agent_lookup", None)
        if not callable(lookup):
            return set()
        agent = lookup(ctx.get("agent_id"))
        if agent is None:
            return set()
        return {str(s).strip() for s in (getattr(agent, "allowed_skill", None) or []) if str(s).strip()}

    def list_user_skills(self) -> Dict[str, Any]:
        """Tool handler: catalog list is name + description only. Agent calls see ticked ids only.

        Allowlisted skill runbooks that are not copied into ``$DATA_DIR/skills/`` are
        included with name and description only. The runbook body stays out [CARD-428].
        """
        skill_rows = []
        for manifest in self.list_manifests():
            skill_rows.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "description": manifest.description,
                    "path": manifest.path,
                    "origin": manifest.origin,
                }
            )
        allowed = self._allowed_skill_ids_for_current_agent()
        if allowed is not None:
            skill_rows = [p for p in skill_rows if p["id"] in allowed]
            known = {p["id"] for p in skill_rows}
            agent_id = self._chat_agent_id()
            for skill_id in sorted(allowed):
                if skill_id in known:
                    continue
                found = self.skill_index_entry(skill_id, agent_id=agent_id)
                if not found:
                    continue
                name, description = found
                skill_rows.append(
                    {
                        "id": skill_id,
                        "name": name,
                        "description": description,
                    }
                )
        return {"skills": skill_rows}

    def skill_view(
        self,
        skill_id: str = "",
        skill_name: Optional[str] = None,
        id: Optional[str] = None,  # noqa: A002 - models send it
        name: Optional[str] = None,
        skills: Any = None,
    ) -> Dict[str, Any]:
        """Tool handler: load SKILL.md body for one allowed runbook.
        CARD-523: skill_name / id / name / skills (first item, list or list-as-string) are aliases of skill_id."""
        skill_id = skill_id or skill_name or id or name or _first_skill(skills)
        if not skill_id:
            return {"success": False, "error": "skill_view needs skill_id (one id from the skill list)."}
        allowed = self._allowed_skill_ids_for_current_agent()
        if allowed is not None and skill_id not in allowed:
            # CARD-564: models often pass the skill's display name ("Review Developer's Work"); map it to its id.
            agent_id = self._chat_agent_id()
            by_name = {
                str((self.skill_index_entry(sid, agent_id=agent_id) or ("",))[0]).strip().lower(): sid
                for sid in allowed
            }
            match = by_name.get(str(skill_id or "").strip().lower())
            if not match:
                return {
                    "success": False,
                    "error": f"Skill '{skill_id}' is not allowed for this agent. Use one of these ids: "
                    + ", ".join(sorted(allowed)) + ".",
                }
            skill_id = match
        loaded = self.load_body(skill_id)
        if loaded.get("success"):
            self.record_skill_use(skill_id)
        return loaded

    def resolve_skill_md(self, skill_id: str) -> Path:
        """Jail skill_id to $DATA_DIR/skills/<id>/SKILL.md. Rejects traversal."""
        if self.skills_dir is None:
            raise SkillJailError("Skills directory is not configured.")
        if not skill_id or not isinstance(skill_id, str) or not _SKILL_ID_RE.match(skill_id):
            raise SkillJailError("Invalid skill id.")
        if ".." in skill_id.split("/"):
            raise SkillJailError("Path traversal rejected.")
        for part in skill_id.replace("\\", "/").split("/"):
            if part in SKIP_LIST_DIRNAMES:
                raise SkillJailError("Invalid skill id.")
        root = self.skills_dir.expanduser().resolve()
        candidate = self.skills_dir / skill_id / "SKILL.md"
        try:
            resolved = candidate.resolve()
        except OSError as exc:
            raise SkillJailError(str(exc)) from exc
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise SkillJailError("Path traversal rejected.") from exc
        try:
            if os.path.commonpath([str(root), str(resolved)]) != str(root):
                raise SkillJailError("Path traversal rejected.")
        except ValueError as exc:
            raise SkillJailError("Path traversal rejected.") from exc
        return resolved

    def resolve_skill_scoped_skill_md(self, skill_id: str) -> Optional[Path]:
        """Winning SKILL.md for an id: data ``skills/`` copy, else repo ``platform/skills`` [CARD-570]."""
        from src.infrastructure.content.store import get_store

        clean_id = skill_id.strip().replace("\\", "/").split("/")[-1]
        loaded = get_store().skills.load(clean_id)
        return loaded.path if loaded else None

    def resolve_chat_skill_md(self, skill_id: str, agent_id: Optional[str] = None) -> Optional[Path]:
        """Live SKILL.md for chat: operator store, this agent's skill, then any skill or seed.

        Read-only. A skill runbook is not copied into ``$DATA_DIR/skills/`` [CARD-427].
        """
        if self.skills_dir is None:
            return None
        chosen = (agent_id or self._chat_agent_id() or "").strip() or None
        from src.application.skills.workshop import locate_skill_markdown

        found = locate_skill_markdown(self.skills_dir.parent, skill_id, agent_id=chosen)
        if found is not None and found.is_file():
            return found
        return None

    def skill_index_entry(self, skill_id: str, agent_id: Optional[str] = None) -> Optional[tuple]:
        """Frontmatter name and description for a skill runbook. Omits the body."""
        path = self.resolve_chat_skill_md(skill_id, agent_id=agent_id)
        if path is None:
            return None
        parsed = DynamicSkillLoader.load_skill_from_markdown(str(path))
        if not parsed:
            return None
        name = str(parsed.get("name") or skill_id).strip() or skill_id
        description = str(parsed.get("description") or "").strip()
        return name, description

    def _chat_agent_id(self) -> Optional[str]:
        try:
            from src.application.kernel.tool_registry import get_tool_context

            agent_id = (get_tool_context() or {}).get("agent_id")
        except Exception:
            return None
        text = str(agent_id or "").strip()
        return text or None

    def read_skill(self, skill_id: str) -> Dict[str, Any]:
        """Read SKILL.md for Agent Studio. Parses tools; does not mount them."""
        try:
            path = self.resolve_skill_md(skill_id)
        except SkillJailError:
            path = None
        if not path or not path.is_file():
            skill_scoped = self.resolve_skill_scoped_skill_md(skill_id)
            if skill_scoped and skill_scoped.is_file():
                path = skill_scoped
            else:
                return {"success": False, "error": f"Skill '{skill_id}' not found.", "not_found": True}
        parsed = DynamicSkillLoader.load_skill_from_markdown(str(path))
        if not parsed:
            return {"success": False, "error": f"Failed to load SKILL.md for skill '{skill_id}'."}
        tools_meta = []
        for tool in parsed.get("tools") or []:
            tools_meta.append({"name": tool.name, "description": tool.description})
        frontmatter_view: Dict[str, Any] = {}
        markdown = ""
        try:
            from src.application.skills.runbook_frontmatter import frontmatter_view as _frontmatter_view

            markdown = path.read_text(encoding="utf-8")
            frontmatter_view = _frontmatter_view(markdown)
        except Exception:
            frontmatter_view = {}
            markdown = ""
        return {
            "success": True,
            "manifest": {
                "id": skill_id,
                "name": parsed.get("name", skill_id),
                "description": parsed.get("description", ""),
                "path": str(path),
                "origin": "platform" if path.parent.parent.parent.name == "platform" else "user",
            },
            "instructions": parsed.get("instructions", ""),
            "tools": tools_meta,
            "frontmatter": frontmatter_view,
            "markdown": markdown,
        }

    def save_skill(
        self,
        skill_id: str,
        name: str,
        description: str,
        instructions: str,
    ) -> Dict[str, Any]:
        """Write the data copy ``skills_dir/<id>/SKILL.md``; never the shipped ``platform/skills`` file [CARD-611].

        Name, description and body are replaced; other frontmatter (``tools:``, tier, ...) is kept from the
        copy that is live now, so saving a shipped skill does not drop the tools it grants.
        """
        clean_name = (name or "").strip()
        clean_description = (description or "").strip()
        if not clean_name or not clean_description:
            return {"success": False, "error": "name and description are required."}
        from src.infrastructure.content.store import InvalidIdError, get_store, join_frontmatter, split_frontmatter

        path = self.resolve_skill_md(skill_id)
        live = path if path.is_file() else self.resolve_skill_scoped_skill_md(skill_id)
        meta: Dict[str, Any] = {}
        if live and live.is_file():
            meta, _ = split_frontmatter(live.read_text(encoding="utf-8"))
        meta = {"name": clean_name, "description": clean_description,
                **{k: v for k, v in meta.items() if k not in ("name", "description", "based_on", "id")}}
        body = (instructions or "").replace("\r\n", "\n").strip()
        skills = get_store().skills
        try:
            # Same file as the store's user copy: let the store write it (records based_on for a shipped id).
            if skills.user_dir is None or skills.user_path(skill_id).resolve() != path:
                raise InvalidIdError(skill_id)
            skills.save(skill_id, meta, body)
        except InvalidIdError:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(join_frontmatter(meta, body), encoding="utf-8", newline="\n")
        self.list_manifests()
        self.record_skill_use(skill_id)
        return self.read_skill(skill_id)

    def create_skill(
        self,
        skill_id: str,
        name: Optional[str] = None,
        description: str = "User skill.",
    ) -> Dict[str, Any]:
        """Create an empty playbook skill (folder + SKILL.md)."""
        path = self.resolve_skill_md(skill_id)
        if path.is_file():
            return {"success": False, "error": f"Skill '{skill_id}' already exists.", "conflict": True}
        display = (name or skill_id).strip() or skill_id
        desc = (description or "User skill.").strip() or "User skill."
        return self.save_skill(skill_id, display, desc, "")


    def skill_dir(self, skill_id: str) -> Path:
        """Jailed skill directory under $DATA_DIR/skills/<id>/."""
        return self.resolve_skill_md(skill_id).parent

    def _snapshot_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    def snapshot_skill(self, skill_id: str) -> Dict[str, Any]:
        """Copy SKILL.md + notes sidecar to snapshots/<utc-iso>/ [REQ-IMPROVE-004]."""
        try:
            root = self.skill_dir(skill_id)
            snap_id = self._snapshot_id()
            dest = root / SNAPSHOTS_DIRNAME / snap_id
            if dest.exists():
                snap_id = snap_id + "-" + datetime.now(timezone.utc).strftime("%f")
                dest = root / SNAPSHOTS_DIRNAME / snap_id
            dest.mkdir(parents=True, exist_ok=False)
            copied: List[str] = []
            for name in TRACKED_SKILL_FILES:
                src = root / name
                if src.is_file():
                    shutil.copy2(src, dest / name)
                    copied.append(name)
            return {
                "success": True,
                "snapshot_id": snap_id,
                "path": str(dest),
                "files": copied,
                "skill_id": skill_id,
            }
        except Exception as exc:
            logger.warning("snapshot_skill failed for %s: %s", skill_id, exc)
            return {"success": False, "error": str(exc), "skill_id": skill_id}

    def list_snapshots(self, skill_id: str) -> List[str]:
        root = self.skill_dir(skill_id) / SNAPSHOTS_DIRNAME
        if not root.is_dir():
            return []
        return sorted(p.name for p in root.iterdir() if p.is_dir())

    def rollback_skill(self, skill_id: str, snapshot_id: Optional[str] = None) -> Dict[str, Any]:
        """Restore SKILL.md + notes from a snapshot. Other skills untouched [REQ-IMPROVE-004]."""
        try:
            root = self.skill_dir(skill_id)
            snap_id = (snapshot_id or "").strip() or None
            if snap_id is None:
                ids = self.list_snapshots(skill_id)
                if not ids:
                    return {"success": False, "error": "No snapshots to roll back.", "skill_id": skill_id}
                snap_id = ids[-1]
            dest = (root / SNAPSHOTS_DIRNAME / snap_id).resolve()
            snap_root = (root / SNAPSHOTS_DIRNAME).resolve()
            dest.relative_to(snap_root)
            if not dest.is_dir():
                return {
                    "success": False,
                    "error": f"Snapshot '{snap_id}' not found.",
                    "skill_id": skill_id,
                }
            restored: List[str] = []
            removed: List[str] = []
            for name in TRACKED_SKILL_FILES:
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
                "skill_id": skill_id,
                "snapshot_id": snap_id,
                "restored": restored,
                "removed": removed,
            }
        except Exception as exc:
            logger.warning("rollback_skill failed for %s: %s", skill_id, exc)
            return {"success": False, "error": str(exc), "skill_id": skill_id}

    def append_playbook_note(
        self,
        skill_id: str,
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
            return {"success": False, "error": "insight is required.", "skill_id": skill_id}
        snap: Dict[str, Any] = {"success": True, "snapshot_id": None}
        if snapshot_first:
            snap = self.snapshot_skill(skill_id)
            if not snap.get("success"):
                return {
                    "success": False,
                    "error": snap.get("error") or "Snapshot failed; note was not appended.",
                    "skill_id": skill_id,
                    "skill_md_written": False,
                }
        try:
            root = self.skill_dir(skill_id)
            root.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).isoformat()
            record = {
                "ts": ts,
                "skill_id": skill_id,
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
                "skill_id": skill_id,
                "snapshot_id": snap.get("snapshot_id"),
                "skill_md_written": False,
                "notes_md": str(md),
                "notes_jsonl": str(jsonl),
            }
        except Exception as exc:
            logger.warning("append_playbook_note failed for %s: %s", skill_id, exc)
            return {
                "success": False,
                "error": str(exc),
                "skill_id": skill_id,
                "skill_md_written": False,
            }


    def record_skill_use(self, skill_id: str) -> None:
        """Touch .last_used so the skill curator has a known last-used [REQ-IMPROVE-013]."""
        try:
            root = self.skill_dir(skill_id)
            if not root.is_dir():
                return
            (root / LAST_USED_NAME).write_text(
                datetime.now(timezone.utc).isoformat(),
                encoding="utf-8",
            )
        except (OSError, SkillJailError) as exc:
            logger.debug("record_skill_use skipped for %s: %s", skill_id, exc)

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register progressive-disclosure tools. Does not dump SKILL.md into the system prompt."""
        registry.register_tool(
            name=LIST_USER_SKILLS,
            description=(
                "Optional catalog of this agent's allowed SKILL.md runbooks (name and description only). "
                "Includes allowlisted skill runbooks that stay under platform/skills/ and are not copied "
                "into $DATA_DIR/skills. The same index is already in the system prompt. Prefer the prompt list; "
                "do not treat this as a way to discover unticked runbooks."
            ),
            parameters={"type": "object", "properties": {}},
            handler=self.list_user_skills,
        )
        registry.register_tool(
            name=SKILL_VIEW,
            description=(
                "Load the full SKILL.md body for one allowed runbook. "
                "Use when a listed skill matches the task. Does not replace Python builtin tools."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": (
                            "Allowlisted skill id. Opens the operator skill store copy when one exists, "
                            "otherwise the agent runbook. Does not copy a skill file into $DATA_DIR/skills."
                        ),
                    },
                },
                "required": ["skill_id"],
            },
            handler=self.skill_view,
        )
