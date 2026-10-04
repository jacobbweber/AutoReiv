"""Attach a tool to a skill of an agent, as a pending proposal Jacob accepts [CARD-539, ADR-0061 rule 8].

Toolsmith (register_native_tool with target_agent_id), Teach and the CARD-539 migration create the
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


def make_skill_write_guard(state_store: Any):
    """Skill-write guard for the content store [CARD-570, ADR-0061].

    A write made inside an agent's tool call (Skill Studio assistant, workshop, adopt, distillation
    or any future path) cannot add tools to a skill: each added tool becomes a pending
    attach-tool-to-skill proposal and the file is saved without it. Jacob's own Studio saves (HTTP,
    no tool call in flight) save directly: he is the approver, so a proposal would only ask him to
    approve himself. The proposal accept path runs from Jacob's approval decision, also outside a
    tool call, so accepting writes the tool.
    """

    def guard(skill_id: str, added: list[str]) -> bool:
        from src.application.kernel.tool_registry import get_tool_context

        ctx = get_tool_context()
        agent_id = str(ctx.get("agent_id") or "").strip()
        if not agent_id:
            return False
        for tool in added:
            propose_tool_attachment(
                state_store,
                tool=tool,
                agent_id=agent_id,
                session_id=str(ctx.get("session_id") or "") or None,
                skill_id=skill_id,
                description=f"{agent_id} asked to add {tool} to skill {skill_id}.",
            )
        return True

    return guard


def tick_skill(store: Any, agent_registry: Any, agent_id: str, skill_id: str, data_dir: Optional[Path] = None) -> bool:
    """Tick skill_id on the agent through the shared Studio/Adopt save path, so the tick survives a
    restart's platform promotion (CARD-502). Returns True when it was added."""
    from src.application.agent_skills.skill_list import add_skill_to_agent

    try:
        _profile, already = add_skill_to_agent(store, agent_registry, agent_id=agent_id, skill_id=skill_id, data_dir=data_dir)
    except LookupError as exc:
        raise ValueError(f"Agent '{agent_id}' was not found.") from exc
    return not already


def runtime_tool_not_enabled(tool: str) -> Optional[str]:
    """CARD-571 Gap 1: a runtime-built tool must be enabled (approved code) before any agent gets it.

    Returns the refusal sentence, or None for built-in tools and enabled runtime tools.
    """
    from src.application.tools.native_packaging import NativeToolError, runtime_tool_files

    try:
        files = runtime_tool_files()
    except NativeToolError:  # no data dir configured: no runtime tools exist
        return None
    name = str(tool or "").strip()
    if not name or files.read(name) is None:
        return None
    if files.mountable(name):
        return None
    return (
        f"{name} is a runtime-built tool that is not enabled (or its code changed since approval). "
        "Enable it in Tools Studio > Runtime-built tools; enabling also accepts this proposal."
    )


def runtime_tool_safety(tool: str) -> Optional[dict[str, bool]]:
    """Skill frontmatter safety copied from a runtime tool's declared risk [CARD-545]; None for built-ins."""
    from src.application.tools.native_packaging import NativeToolError, runtime_tool_files

    try:
        row = runtime_tool_files().read(str(tool or "").strip())
    except (NativeToolError, ValueError):
        return None
    if not row:
        return None
    return {"read_only": str(row.get("risk") or "") == "read_only", "requires_hitl": bool(row.get("requires_hitl"))}


def pending_attach_proposals(store: Any, tool: str) -> list[dict[str, Any]]:
    """Pending attach proposals for one tool (all agents), for Tools Studio and the one-step enable."""
    out: list[dict[str, Any]] = []
    getter = getattr(store, "get_pending_approvals", None)
    if not callable(getter):
        return out
    for row in getter() or []:
        args = row.get("arguments") or {}
        if row.get("tool_name") == ATTACH_TOOL_PROPOSAL and args.get("tool") == tool:
            out.append({"approval_id": str(row.get("id")), "agent_id": args.get("agent_id"), "skill_id": args.get("skill_id")})
    return out


def accept_attach_proposals(
    store: Any, agent_registry: Any, tool_registry: Any, tool: str, *, data_root: Path
) -> list[dict[str, Any]]:
    """CARD-571 D5: Jacob enabling a runtime tool also accepts its pending attach proposals (one step).

    Called only from the Tools Studio enable route, after the tool is enabled.
    """
    accepted: list[dict[str, Any]] = []
    for item in pending_attach_proposals(store, tool):
        record = store.get_approval(item["approval_id"]) or {}
        result = apply_tool_attachment(store, agent_registry, tool_registry, record.get("arguments") or {}, data_root=data_root)
        store.resolve_approval(
            approval_id=item["approval_id"], decision="approved", reason="Accepted by enabling the tool in Tools Studio."
        )
        accepted.append(result | {"approval_id": item["approval_id"]})
    return accepted


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
    refusal = runtime_tool_not_enabled(tool)
    if refusal:
        raise ValueError(refusal)
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
            safety=None if wildcard else runtime_tool_safety(tool),  # CARD-545: the tool's risk
            tools=[] if wildcard else [tool],
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
