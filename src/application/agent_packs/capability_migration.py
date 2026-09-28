"""One-time CARD-539 migration: legacy tool grants become skills or pending proposals (ADR-0061).

Runs once at startup (marker setting). Backs up every agent's old lists first, never grants a tool:
- storage_enabled without the sqlite-storage tick -> tick it (same permission, D3);
- each per-agent MCP server -> a small skill binding mcp_<server>_*, ticked (same permission, D2);
- each allowed_tool_names entry the ticked skills do not cover -> pending proposal: tick the skill that
  binds it, or a new skill with a drafted runbook. Until Jacob accepts, the tool is not allowed.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.application.agent_packs.allowed_tools import (
    NO_TOOL_AGENTS,
    resolve_allowed_tools,
    skill_that_binds,
    ticked_skills,
)
from src.application.agent_packs.tool_attachment import apply_tool_attachment, propose_tool_attachment, tick_skill

logger = logging.getLogger(__name__)

MIGRATION_MARKER = "capability_migration_card539"
BACKUP_NAME = "card-539-allowlists.json"
SESSION = "capability-migration"


def _server_name(srv: Any) -> str:
    return str(getattr(srv, "name", None) or (srv.get("name") if isinstance(srv, dict) else "") or "").strip()


def _dump(value: Any) -> Any:
    return value.model_dump() if hasattr(value, "model_dump") else value


def migrate_legacy_grants(store: Any, agent_registry: Any, *, data_root: Path) -> dict[str, Any]:
    if store.get_setting(MIGRATION_MARKER):
        return {"skipped": True, "proposals": []}
    profiles = [p for p in agent_registry.list_agents() if p is not None]
    backup = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agents": {
            p.id: {
                "allowed_tool_names": list(p.allowed_tool_names or []),
                "pack_tool_names": list(p.pack_tool_names or []),
                "allowed_skill": list(p.allowed_skill or []),
                "storage_enabled": bool(getattr(p, "storage_enabled", False)),
                "mcp_servers": [_dump(s) for s in getattr(p, "mcp_servers", None) or []],
            }
            for p in profiles
        },
    }
    folder = Path(data_root) / "migrations"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / BACKUP_NAME).write_text(json.dumps(backup, indent=2, default=str), encoding="utf-8")

    proposals: list[dict[str, str]] = []
    converted: list[str] = []
    for base in profiles:
        if base.id in NO_TOOL_AGENTS:
            continue
        if getattr(base, "storage_enabled", False) and tick_skill(store, agent_registry, base.id, "sqlite-storage", Path(data_root)):
            converted.append(f"{base.id}: sqlite-storage ticked")
        for srv in getattr(base, "mcp_servers", None) or []:
            name = _server_name(srv)
            if not name:
                continue
            sid = "mcp-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            apply_tool_attachment(
                store, agent_registry, None,
                {"tool": f"mcp_{name}_*", "agent_id": base.id, "skill_id": sid, "new_skill": True,
                 "description": f"Tools of the {name} MCP server"},
                data_root=Path(data_root),
            )
            converted.append(f"{base.id}: {sid} ticked")
        profile = agent_registry.get_agent(base.id) or base
        allowed = resolve_allowed_tools(profile)
        for tool in dict.fromkeys(str(t).strip() for t in profile.allowed_tool_names or []):
            if not tool or tool in allowed:
                continue
            skill = skill_that_binds(tool, profile.id)
            if skill in ticked_skills(profile):
                skill = None  # ticked yet unbound here (operator-edited binding): propose a new skill instead
            approval_id = propose_tool_attachment(
                store, tool=tool, agent_id=profile.id, session_id=SESSION, skill_id=skill,
                description=f"Migrated grant of {tool} (CARD-539)",
            )
            proposals.append({"agent_id": profile.id, "tool": tool, "skill_id": skill or "", "approval_id": approval_id})
    store.set_setting(MIGRATION_MARKER, {"at": backup["created_at"], "proposals": len(proposals), "converted": converted})
    logger.info("CARD-539 migration: %d proposals, %d conversions", len(proposals), len(converted))
    return {"skipped": False, "proposals": proposals, "converted": converted}


CODING_MARKER = "autoreiv_coding_unticked_card544"
CODING_BACKUP_NAME = "card-544-autoreiv-skills.json"


def autoreiv_skills_before_seed(store: Any) -> Optional[list[str]]:
    """Read AutoReiv's stored skill list before the platform seed sync runs (CARD-544).

    An unedited AutoReiv gets the new pack (no coding) during registry bootstrap, before the migration runs, so the
    migration backs up this list instead. Returns None once the migration marker is set or nothing is stored.
    """
    try:
        if store.get_setting(CODING_MARKER):
            return None
        profile = store.get_agent_profile("autoreiv")
    except Exception:
        return None
    if profile is None:
        return None
    return list(getattr(profile, "allowed_skill", None) or [])


def untick_autoreiv_coding(
    store: Any, agent_registry: Any, *, data_root: Path, before_seed: Optional[list[str]] = None
) -> dict[str, Any]:
    """CARD-544 D1 (Jacob): AutoReiv no longer ticks coding; code work routes to Developer.

    Once per install: back up the stored skill list, untick coding through the shared save path, set a
    marker. A later operator re-tick is left alone (the marker stops a second run). When the platform seed sync
    already dropped coding at bootstrap, ``before_seed`` (read before bootstrap) is what gets backed up.
    """
    from src.application.agent_packs.skill_list import remove_skill_from_agent

    if store.get_setting(CODING_MARKER):
        return {"skipped": True, "unticked": False}
    profile = agent_registry.get_agent("autoreiv")
    current = list(getattr(profile, "allowed_skill", None) or []) if profile is not None else []
    by = ""
    if "coding" in current:
        old, by = current, "migration"
    elif before_seed and "coding" in before_seed:
        old, by = list(before_seed), "platform update"
    else:
        old = current
    unticked = bool(by)
    if unticked:
        folder = Path(data_root) / "migrations"
        folder.mkdir(parents=True, exist_ok=True)
        backup = {"created_at": datetime.now(timezone.utc).isoformat(), "agent_id": "autoreiv", "allowed_skill": old, "by": by}
        (folder / CODING_BACKUP_NAME).write_text(json.dumps(backup, indent=2), encoding="utf-8")
    if by == "migration":
        remove_skill_from_agent(store, agent_registry, agent_id="autoreiv", skill_id="coding", data_dir=Path(data_root))
    store.set_setting(CODING_MARKER, {"at": datetime.now(timezone.utc).isoformat(), "unticked": unticked, "by": by})
    logger.info("CARD-544 migration: coding %s on autoreiv", f"unticked ({by})" if unticked else "was not ticked")
    return {"skipped": False, "unticked": unticked, "by": by}


DEV_SKILLS_MARKER = "developer_skills_card562"
DEV_SKILLS_BACKUP_NAME = "card-562-developer-skills.json"
# CARD-562 supersedes CARD-550 D1: Developer works on the active project, not the AutoReiv checkout.
DEV_RETIRED_SKILLS = ("coding", "sdlc-engineering")
DEV_SDLC_SKILLS = (
    "project-orientation",
    "card-intake",
    "card-writing",
    "plan-change",
    "implement-change",
    "write-tests",
    "debug",
    "run-checks",
    "git-workflow",
    "code-review",
    "codebase-audit",
)


def move_developer_to_sdlc_skills(store: Any, agent_registry: Any, *, data_root: Path) -> dict[str, Any]:
    """CARD-562: once per install, swap Developer's coding + sdlc-engineering for the SDLC skill set.

    Goes through the shared save path, backs up the stored list first and sets a marker so a later operator edit
    (for example unticking a skill) survives restarts. Other ticks (tool building, proposals) are left alone.
    """
    from src.application.agent_packs.skill_list import add_skill_to_agent, remove_skill_from_agent

    if store.get_setting(DEV_SKILLS_MARKER):
        return {"skipped": True, "changed": False}
    profile = agent_registry.get_agent("developer")
    if profile is None:
        store.set_setting(DEV_SKILLS_MARKER, {"at": datetime.now(timezone.utc).isoformat(), "changed": False})
        return {"skipped": False, "changed": False, "removed": [], "added": []}
    current = list(getattr(profile, "allowed_skill", None) or [])
    removed = [s for s in DEV_RETIRED_SKILLS if s in current]
    added = [s for s in DEV_SDLC_SKILLS if s not in current]
    if removed or added:
        folder = Path(data_root) / "migrations"
        folder.mkdir(parents=True, exist_ok=True)
        backup = {"created_at": datetime.now(timezone.utc).isoformat(), "agent_id": "developer", "allowed_skill": current}
        (folder / DEV_SKILLS_BACKUP_NAME).write_text(json.dumps(backup, indent=2), encoding="utf-8")
        for sid in removed:
            remove_skill_from_agent(store, agent_registry, agent_id="developer", skill_id=sid, data_dir=Path(data_root))
        for sid in added:
            add_skill_to_agent(store, agent_registry, agent_id="developer", skill_id=sid, data_dir=Path(data_root))
    changed = bool(removed or added)
    store.set_setting(
        DEV_SKILLS_MARKER, {"at": datetime.now(timezone.utc).isoformat(), "changed": changed, "removed": removed}
    )
    logger.info("CARD-562 migration: developer skills removed=%s added=%s", removed, added)
    return {"skipped": False, "changed": changed, "removed": removed, "added": added}
