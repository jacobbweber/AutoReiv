"""Phase roles for job phases [CARD-554].

The Formulate phase plans: it must not do the work itself or hand off to another agent. The agent assigned to a
later phase (for example Developer on Execute) does the work with its own tools.
"""

from __future__ import annotations

from typing import Any, Collection, Optional, Sequence

PLANNING_PHASE_PREFIXES: tuple[str, ...] = ("formulate",)
DELEGATION_TOOLS: frozenset[str] = frozenset({"handoff_to_agent"})
_HIGH_RISK_LEVELS = frozenset({"high", "critical"})


def is_planning_phase(phase: Any) -> bool:
    name = str(getattr(phase, "name", "") or "").strip().lower()
    return bool(name) and name.startswith(PLANNING_PHASE_PREFIXES)


def planning_phase_block_reason(tool_name: str, tool_risk: Optional[str] = None) -> Optional[str]:
    """Why ``tool_name`` may not run in a planning phase, else None (handoff and work tools are blocked)."""
    from src.application.kernel.hitl_engine import DEFAULT_HIGH_RISK_TOOLS

    name = str(tool_name or "").strip()
    if name in DELEGATION_TOOLS:
        return f"Tool '{name}' is not used while planning: plan only; the next phase's agent does the work"
    if name in DEFAULT_HIGH_RISK_TOOLS or str(tool_risk or "").strip().lower() in _HIGH_RISK_LEVELS:
        return f"Tool '{name}' changes something and is not used while planning: plan only; the work runs in a later phase"
    return None


def format_planning_phase_block(phases: Sequence[Any], current: Any) -> str:
    """Formulate assignment: plan only, and name the agent that runs each later phase."""
    later = [p for p in phases if int(getattr(p, "index", 0) or 0) > int(getattr(current, "index", 0) or 0)]
    runs = "; ".join(
        f"{getattr(p, 'name', 'Phase')} runs on {getattr(p, 'assigned_agent_id', '') or 'the same agent'}" for p in later
    )
    lines = [
        "PLANNING PHASE [CARD-554]:",
        "- Write the plan only. Do not do the work, do not call tools that change anything, and do not hand off to "
        "another agent.",
    ]
    if runs:
        lines.append(f"- {runs}. That agent does the work with its own tools; plan for it.")
    return "\n".join(lines)


def format_planning_repo_note(suggested_paths: Sequence[str] = ()) -> str:
    """Formulate gets this instead of the repo MUST-read constraint; the Execute phase reads the checkout."""
    paths = ", ".join(f"`{p}`" for p in suggested_paths) if suggested_paths else "the files the task names"
    return (
        "REPO / CODE NOTE [CARD-262, CARD-554]: the Execute phase must read "
        f"{paths} with `repo_file_read` before claiming anything about them. Do not claim file contents in the plan."
    )


def format_planning_tools_block(
    offered: Sequence[str],
    matched_ids: Sequence[str] = (),
    granted: Collection[str] = (),
    skills: Collection[str] = (),
) -> str:
    """Formulate assignment: the exact tools this call is sent, and which matched names are not callable [CARD-665].

    ``offered`` is the kernel's set for the call (AgentKernel.offered_tool_names): the agent's granted tools
    narrowed by the job's match and plan-only rules. Matched skills and tools outside it are named as what they are.
    """
    callable_now = sorted({str(n) for n in offered or () if str(n).strip()})
    granted_set = {str(n) for n in granted or ()}
    lines = [
        "TOOLS YOU CAN CALL IN THIS PHASE: " + (", ".join(callable_now) + "." if callable_now else "none: write the plan in text."),
        "- Call only these. Skill ids, capability ids and tool names in the skill text or the matched list are not "
        "tools you can call here unless they are in this list.",
    ]
    not_callable: list[str] = []
    for raw in matched_ids or ():
        cid = str(raw or "").strip()
        if cid.startswith("skill."):
            not_callable.append(f"{cid[len('skill.'):]} (a skill, not a tool)")
        elif cid.startswith("tool.") and cid[len("tool.") :] not in callable_now:
            name = cid[len("tool.") :]
            if name not in granted_set:
                why = "not granted to you"
            elif planning_phase_block_reason(name):
                why = "granted to you, not used while planning"
            else:
                why = "granted to you, not offered in this step"
            not_callable.append(f"{name} ({why})")
    if not_callable:
        lines.append("- Not callable in this phase: " + "; ".join(not_callable) + ".")
    matched_skills = {str(c).strip()[len("skill.") :] for c in matched_ids or () if str(c).strip().startswith("skill.")}
    own_skills = [str(s).strip() for s in skills or () if str(s).strip() and str(s).strip() not in matched_skills]
    if own_skills:
        lines.append("- Your skills are runbooks, not tools: " + ", ".join(own_skills) + ".")
    lines.append(
        "- If the plan needs a tool or skill that is not in the list, say so in the plan (and which later phase or "
        "agent needs it). Do not call it."
    )
    return "\n".join(lines)


def planning_tools_block_for(
    kernel: Any, agent: Any, job_id: Optional[str], phase_id: Optional[str], matched_ids: Sequence[str] = ()
) -> str:
    """The CARD-665 tools block for a Formulate phase, from the same offered set the kernel sends on the call."""
    from src.application.agent_skills.allowed_tools import resolve_allowed_tools, ticked_skills

    offered = kernel.offered_tool_names(agent, job_id=job_id, phase_id=phase_id)
    return format_planning_tools_block(
        offered, matched_ids, granted=resolve_allowed_tools(agent).names, skills=ticked_skills(agent)
    )
