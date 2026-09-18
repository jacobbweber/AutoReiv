"""
Tool-to-Skill Resolver & Runbook Patch Synthesizer [CARD-354 / REQ-OBS-011].
Maps telemetry tool incidents to user-data SKILL.md runbooks and synthesizes actionable SOP patches.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Set, Tuple, Union

import yaml

from src.domain.observability.models import (
    FrictionIncident,
    FrictionSignatureType,
    RunbookRecommendation,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolSkillResolver:
    """
    Maps (agent_id, tool_name) pairs to user-data SKILL.md runbooks,
    synthesizes targeted anti-pattern SOP bullets, and safely patches runbooks.
    """

    # Built-in platform skills mapping (ADR-0052)
    PLATFORM_SKILL_TOOLS: Dict[str, Set[str]] = {
        "wiki": {
            "wiki_note_read",
            "wiki_note_search",
            "wiki_note_create",
            "wiki_note_update",
            "list_wiki_templates",
            "wiki_template_create",
            "wiki_template_read",
        },
        "diagnostics": {
            "inspect_system_health",
            "get_system_logs",
            "get_recent_errors",
            "get_tool_health_matrix",
            "cli_exec",
        },
        "tasks": {
            "get_or_create_weekly_note",
            "log_daily_work_item",
            "complete_weekly_task",
            "rollover_weekly_tasks",
        },
        "coding": {
            "repo_file_read",
            "repo_file_list",
            "repo_file_write",
            "repo_file_patch",
            "execute_code",
        },
    }

    # Tools known to support pagination/limit/offset arguments
    PAGINATION_AWARE_TOOLS: Set[str] = {
        "wiki_note_search",
        "wiki_note_list",
        "repo_file_list",
        "get_system_logs",
        "get_telemetry_spans",
        "list_sessions",
        "get_messages",
    }

    def __init__(self, data_dir: Union[str, Path]):
        self.data_dir = Path(data_dir).expanduser().resolve()

    def resolve_tool_to_skill(
        self, agent_id: str, tool_name: str
    ) -> Optional[Tuple[str, str]]:
        """
        Returns (skill_id, relative_path) for a tool under user data.
        """
        clean_tool = (tool_name or "").strip()
        clean_agent = (agent_id or "").strip()

        # 1. If agent_id provided, prioritize the agent's own pack skills
        if clean_agent and (self.data_dir / "packs" / clean_agent).is_dir():
            agent_pack_dir = self.data_dir / "packs" / clean_agent
            pack_json = agent_pack_dir / "pack.json"
            if pack_json.is_file():
                try:
                    p_data = json.loads(pack_json.read_text(encoding="utf-8"))
                    for skill in p_data.get("skills", []):
                        if isinstance(skill, dict) and clean_tool in skill.get("tools", []):
                            sk_id = skill.get("id") or ""
                            sk_md = agent_pack_dir / "skills" / sk_id / "SKILL.md"
                            if sk_md.is_file():
                                rel = sk_md.relative_to(self.data_dir).as_posix()
                                return sk_id, rel
                except Exception:
                    pass

            skills_dir = agent_pack_dir / "skills"
            if skills_dir.is_dir():
                for skill_subdir in skills_dir.iterdir():
                    skill_md = skill_subdir / "SKILL.md"
                    if skill_md.is_file():
                        tools = self._parse_skill_tools(skill_md)
                        if clean_tool in tools:
                            rel = skill_md.relative_to(self.data_dir).as_posix()
                            return skill_subdir.name, rel

        # 2. Check built-in platform skills mapping
        for skill_id, tools in self.PLATFORM_SKILL_TOOLS.items():
            if clean_tool in tools:
                rel_path = f"skills/{skill_id}/SKILL.md"
                return skill_id, rel_path

        # 3. Check other user pack skills under packs/*
        packs_dir = self.data_dir / "packs"
        if packs_dir.is_dir():
            for agent_pack_dir in packs_dir.iterdir():
                if not agent_pack_dir.is_dir() or agent_pack_dir.name == clean_agent:
                    continue
                pack_json = agent_pack_dir / "pack.json"
                if pack_json.is_file():
                    try:
                        p_data = json.loads(pack_json.read_text(encoding="utf-8"))
                        for skill in p_data.get("skills", []):
                            if isinstance(skill, dict) and clean_tool in skill.get("tools", []):
                                sk_id = skill.get("id") or ""
                                sk_md = agent_pack_dir / "skills" / sk_id / "SKILL.md"
                                if sk_md.is_file():
                                    rel = sk_md.relative_to(self.data_dir).as_posix()
                                    return sk_id, rel
                    except Exception:
                        pass
                skills_dir = agent_pack_dir / "skills"
                if skills_dir.is_dir():
                    for skill_subdir in skills_dir.iterdir():
                        skill_md = skill_subdir / "SKILL.md"
                        if skill_md.is_file():
                            tools = self._parse_skill_tools(skill_md)
                            if clean_tool in tools:
                                rel = skill_md.relative_to(self.data_dir).as_posix()
                                return skill_subdir.name, rel

        # 3. Check standalone user skills under skills/<skill_id>/
        if (self.data_dir / "skills").is_dir():
            skills_dir = self.data_dir / "skills"
            for skill_subdir in skills_dir.iterdir():
                skill_md = skill_subdir / "SKILL.md"
                if skill_md.is_file():
                    tools = self._parse_skill_tools(skill_md)
                    if clean_tool in tools:
                        rel = skill_md.relative_to(self.data_dir).as_posix()
                        return skill_subdir.name, rel

        return None

    def _parse_skill_tools(self, skill_md_path: Path) -> Set[str]:
        """Parse YAML frontmatter tools list from SKILL.md."""
        try:
            content = skill_md_path.read_text(encoding="utf-8")
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict):
                        raw_tools = fm.get("tools") or []
                        return {str(t).strip() for t in raw_tools}
        except Exception:
            pass
        return set()

    def synthesize_recommendation(
        self, incident: FrictionIncident
    ) -> RunbookRecommendation:
        """
        Synthesizes an actionable RunbookRecommendation from a FrictionIncident.
        """
        resolved = self.resolve_tool_to_skill(incident.agent_id, incident.tool_name)
        skill_id = resolved[0] if resolved else None
        skill_path = resolved[1] if resolved else None

        rec_id = f"rec_{uuid.uuid4().hex[:12]}"
        t_name = incident.tool_name

        if incident.signature == FrictionSignatureType.REDUNDANT_VERIFICATION:
            patch = (
                f"- Do not invoke {t_name} immediately after a successful mutation. "
                f"Rely directly on the ID and status returned by the mutation step."
            )
            summary = f"Prevent redundant verification loop on {t_name}."
            remedy = "runbook_patch"

        elif incident.signature == FrictionSignatureType.PAYLOAD_BLOAT:
            if t_name in self.PAGINATION_AWARE_TOOLS:
                patch = (
                    f"- When calling {t_name}, always specify limit <= 10 or pagination "
                    f"to prevent oversized payloads (> 8 KB)."
                )
                summary = f"Enforce pagination limit on {t_name} to curb payload bloat."
                remedy = "runbook_patch"
            else:
                patch = (
                    f"Escalate {t_name} to Factory Studio: Tool lacks pagination/filter "
                    f"parameters to constrain large payloads ({incident.payload_bytes or 0} bytes)."
                )
                summary = f"Escalate {t_name} to Factory Studio (unbounded payload)."
                remedy = "factory_escalation"

        elif incident.signature == FrictionSignatureType.SEARCH_THRASHING:
            patch = (
                f"- Do not execute consecutive search calls with slight keyword variations ({t_name}). "
                f"Check the directory index or tag authority before querying."
            )
            summary = f"Prevent blind search thrashing on {t_name}."
            remedy = "runbook_patch"

        else:
            patch = f"- Avoid repetitive or stalled execution loops involving {t_name}."
            summary = f"Mitigate operational friction on {t_name}."
            remedy = "runbook_patch"

        return RunbookRecommendation(
            id=rec_id,
            agent_id=incident.agent_id,
            skill_id=skill_id,
            skill_path=skill_path,
            friction_type=incident.signature,
            summary=summary,
            proposed_patch=patch,
            remedy_kind=remedy,
            status="pending",
            created_at=_utc_now(),
        )

    def apply_recommendation(self, recommendation: RunbookRecommendation) -> bool:
        """
        Safely patches the targeted SKILL.md under user data.
        Enforces that target file is strictly jailed within self.data_dir.
        """
        if recommendation.remedy_kind != "runbook_patch":
            return False
        if not recommendation.skill_path:
            return False

        target_file = (self.data_dir / recommendation.skill_path).resolve()

        # Enforce checkout hygiene: target must be inside data_dir
        try:
            target_file.relative_to(self.data_dir)
        except ValueError:
            raise ValueError(f"Target path '{target_file}' is outside user data directory.")

        if not target_file.is_file():
            return False

        content = target_file.read_text(encoding="utf-8")
        bullet = recommendation.proposed_patch.strip()

        # Idempotency check: avoid inserting identical bullet twice
        if bullet in content:
            return True

        pitfall_headers = [
            "## Common Pitfalls & Forbidden Paths",
            "## Common Pitfalls",
            "## Pitfalls",
            "## Forbidden Paths",
        ]
        found_header = None
        for h in pitfall_headers:
            if h in content:
                found_header = h
                break

        if found_header:
            idx = content.find(found_header) + len(found_header)
            lead = content[:idx]
            rest = content[idx:].lstrip("\r\n")
            updated = f"{lead}\n\n{bullet}\n\n{rest}"
        else:
            # Append pitfall section to the end of the markdown
            updated = content.rstrip() + f"\n\n## Common Pitfalls & Forbidden Paths\n\n{bullet}\n"

        target_file.write_text(updated, encoding="utf-8")
        return True
