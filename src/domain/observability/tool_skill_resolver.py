"""
Tool-to-Skill Resolver & Runbook Patch Synthesizer [CARD-354 / REQ-OBS-011].
Maps telemetry tool incidents to user-data SKILL.md runbooks and synthesizes actionable SOP patches.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple, Union

import yaml

from src.domain.observability.models import (
    CODE_CHANGE,
    TOOL_ESCALATION,
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

    # Tools known to support pagination/limit/offset arguments
    PAGINATION_AWARE_TOOLS: Set[str] = {
        "wiki_note_search",
        "wiki_note_list",
        "repo_file_list",
        "get_system_logs",
        "get_telemetry_spans",
        "list_sessions",
        "get_messages",
        # CARD-527: built-in tools that take a limit and stay under 8 KB by default.
        "get_recent_errors",
        "list_available_skills_and_tools",
    }

    def __init__(self, data_dir: Union[str, Path], platform_dir: Optional[Union[str, Path]] = None):
        self.data_dir = Path(data_dir).expanduser().resolve()
        repo = Path(__file__).resolve().parents[3]
        self.platform_dir = Path(platform_dir) if platform_dir else repo / "platform" / "skills"

    def resolve_tool_to_skill(
        self, agent_id: str, tool_name: str, agent_skill_ids: Optional[Iterable[str]] = None
    ) -> Optional[Tuple[str, str]]:
        """(skill_id, relative_path) of the first skill whose SKILL.md ``tools:`` lists the tool.

        The agent's own ticked skills come first [CARD-527]; then any skill. User copies in the data
        dir win over shipped ``platform/skills`` [CARD-570].
        """
        clean_tool = (tool_name or "").strip()
        if not clean_tool:
            return None
        user_dir = self.data_dir / "skills"
        for sid in agent_skill_ids or []:
            sid = str(sid).strip()
            if not sid or "/" in sid or "\\" in sid or sid.startswith("."):
                continue
            for base in (user_dir, self.platform_dir):
                skill_md = base / sid / "SKILL.md"
                if skill_md.is_file():
                    if clean_tool in self._parse_skill_tools(skill_md):
                        return sid, f"skills/{sid}/SKILL.md"
                    break  # the user copy wins; do not read the shipped one
        seen: Set[str] = set()
        for base in (user_dir, self.platform_dir):
            if not base.is_dir():
                continue
            for skill_md in sorted(base.glob("*/SKILL.md")):
                sid = skill_md.parent.name
                if sid in seen:
                    continue
                seen.add(sid)
                if clean_tool in self._parse_skill_tools(skill_md):
                    return sid, f"skills/{sid}/SKILL.md"
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
        self,
        incident: FrictionIncident,
        *,
        builtin_tools: Optional[Set[str]] = None,
        agent_skill_ids: Optional[Iterable[str]] = None,
    ) -> RunbookRecommendation:
        """
        Synthesizes an actionable RunbookRecommendation from a FrictionIncident.

        ``builtin_tools``: tools that are Python in this repo. Such a tool never gets an Ask Developer
        remedy (Developer only builds runtime tools); it gets a runbook patch or "needs a code change"
        [CARD-527]. None means unknown: the CARD-520 behaviour.
        """
        resolved = self.resolve_tool_to_skill(incident.agent_id, incident.tool_name, agent_skill_ids)
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
            elif builtin_tools is not None and t_name in builtin_tools:
                # CARD-527: Python in this repo; neither Developer nor a runbook can change it.
                patch = (
                    f"Built-in tool: {t_name} needs a code change in AutoReiv (pagination, a limit or a "
                    f"filter). It returned {incident.payload_bytes or 0} bytes (limit 8 KB). Developer "
                    f"cannot change built-in tools, so card it for the AutoReiv repo, then dismiss this."
                )
                summary = f"Built-in tool {t_name} needs a code change in AutoReiv (unbounded payload)."
                remedy = CODE_CHANGE
            else:
                # CARD-520 D9: the tool needs changing; Ask Developer is the action.
                patch = (
                    f"Ask Developer to add pagination or a filter to {t_name}: "
                    f"it returned {incident.payload_bytes or 0} bytes (limit 8 KB)."
                )
                summary = f"{t_name} needs pagination or a filter (unbounded payload)."
                remedy = TOOL_ESCALATION

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
            tool_name=t_name,
            payload_bytes=incident.payload_bytes,
            session_id=incident.session_id,
        )

    def apply_recommendation(self, recommendation: RunbookRecommendation) -> bool:
        """Bool wrapper kept for the auditor's auto-apply."""
        return self.apply_with_reason(recommendation)[0]

    def apply_with_reason(self, recommendation: RunbookRecommendation) -> Tuple[bool, str]:
        """
        Safely patches the targeted SKILL.md under user data and says why when it cannot [CARD-520 D8].
        Reasons: applied, already_present, tool_escalation, code_change, no_skill, missing_file, not_a_patch.
        Enforces that target file is strictly jailed within self.data_dir.
        """
        if recommendation.remedy_kind == TOOL_ESCALATION:
            return False, "tool_escalation"
        if recommendation.remedy_kind == CODE_CHANGE:
            return False, "code_change"
        if recommendation.remedy_kind != "runbook_patch":
            return False, "not_a_patch"
        if not recommendation.skill_path:
            return False, "no_skill"

        target_file = (self.data_dir / recommendation.skill_path).resolve()

        # Enforce checkout hygiene: target must be inside data_dir
        try:
            target_file.relative_to(self.data_dir)
        except ValueError:
            raise ValueError(f"Target path '{target_file}' is outside user data directory.")

        if not target_file.is_file():
            return False, "missing_file"

        content = target_file.read_text(encoding="utf-8")
        bullet = recommendation.proposed_patch.strip()

        # Idempotency check: avoid inserting identical bullet twice
        if bullet in content:
            return True, "already_present"

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
        return True, "applied"
