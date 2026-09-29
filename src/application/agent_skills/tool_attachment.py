"""Attach a tool to a skill of an agent, as a pending proposal Jacob accepts [CARD-539, ADR-0061 rule 8].

Developer (register_native_tool with target_agent_id), Teach and the CARD-539 migration create the
proposal; nothing changes an agent's tools until the proposal is accepted. Accepting edits the skill's
``tools:`` list (user copy of its SKILL.md; a new skill gets a runbook) and ticks the skill on the agent.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Optional

from src.application.agent_skills.allowed_tools import skill_tools

ATTACH_TOOL_PROPOSAL = "attach_tool_to_skill"


def skill_id_for_tool(tool: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(tool).lower()).strip("-") or "new-skill"


def draft_runbook(skill_id: str, tool: str, description: str = "") -> str:
    what = (description or f"Use {tool}").strip().rstrip(".")
    return (
        f"# {skill_id}\n\n{what}.\n\n## Available Tools\n- `{tool}`: {what}.\n\n"
        f"## Workflow Order\n1. Call `{tool}` with the arguments the request gives.\n"
        "2. Report exactly what the tool returned; do not invent values.\n\n"
        "## Done-when\n- The answer quotes the tool result.\n"
    )


def propose_tool_attachment(
    store: Any,
    *,
    tool: str,
    agent_id: str,
    session_id: Optional[str] = None,
    skill_id: Optional[str] = None,
    description: str = "",
    evidence: Optional[Mapping[str, Any]] = None,
) -> str:
    """Create (or return the existing) pending attach proposal. Changes no permission."""
    new_skill = not (skill_id or "").strip()
    sid = (skill_id or "").strip() or skill_id_for_tool(tool)
    for row in store.get_pending_approvals(agent_id=agent_id):
        args = row.get("arguments") or {}
        if row.get("tool_name") == ATTACH_TOOL_PROPOSAL and args.get("tool") == tool and args.get("skill_id") == sid:
            return str(row["id"])
    arguments = {
        "tool": tool,
        "agent_id": agent_id,
        "skill_id": sid,
        "new_skill": new_skill,
        "description": description,
        "runbook": draft_runbook(sid, tool, description) if new_skill else None,
        "evidence": dict(evidence or {}),
    }
    return store.create_approval(
        session_id=session_id or "capability-proposal",
        agent_id=agent_id,
        tool_name=ATTACH_TOOL_PROPOSAL,
        arguments=arguments,
    )


def tick_skill(store: Any, agent_registry: Any, agent_id: str, skill_id: str, data_dir: Optional[Path] = None) -> bool:
    """Tick skill_id on the agent through the shared Studio/Adopt save path, so the tick survives a
    restart's platform promotion (CARD-502). Returns True when it was added."""
    from src.application.agent_skills.skill_list import add_skill_to_agent

    try:
        _profile, already = add_skill_to_agent(store, agent_registry, agent_id=agent_id, skill_id=skill_id, data_dir=data_dir)
    except LookupError as exc:
        raise ValueError(f"Agent '{agent_id}' was not found.") from exc
    return not already


def apply_tool_attachment(
    store: Any, agent_registry: Any, tool_registry: Any, args: Mapping[str, Any], *, data_root: Path
) -> dict[str, Any]:
    """Accept: bind the tool to the skill (new skill gets a runbook) and tick the skill on the agent."""
    from src.application.skills.workshop import catalog_tool_ids, persist_workshop_skill
    from src.infrastructure.content.store import get_store

    tool = str(args.get("tool") or "").strip()
    agent_id = str(args.get("agent_id") or "").strip()
    sid = str(args.get("skill_id") or "").strip()
    if not (tool and agent_id and sid):
        raise ValueError("Proposal is missing tool, agent_id or skill_id.")
    db_path = getattr(store, "db_path", None)
    wildcard = tool.endswith("*")
    if args.get("new_skill"):
        persist_workshop_skill(
            data_root=Path(data_root),
            agent_id=None,
            skill_id=sid,
            skill_content=str(args.get("runbook") or draft_runbook(sid, tool, str(args.get("description") or ""))),
            catalog_ids=catalog_tool_ids(tool_registry),
            name=sid.replace("-", " ").title(),
            description=str(args.get("description") or f"Use {tool}"),
            requires_tools=[] if wildcard else [tool],
            db_path=db_path,
        )
        if wildcard:
            get_store().set_skill_tools(sid, [tool])
    else:
        current = skill_tools([sid], agent_id).get(sid, [])
        if tool not in current:
            get_store().set_skill_tools(sid, current + [tool])  # user copy of the SKILL.md [CARD-570]
    tick_skill(store, agent_registry, agent_id, sid, Path(data_root))
    return {"tool": tool, "agent_id": agent_id, "skill_id": sid, "new_skill": bool(args.get("new_skill")), "ticked": True}
