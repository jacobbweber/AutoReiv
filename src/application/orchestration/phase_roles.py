"""Phase roles for job phases [CARD-554].

The Formulate phase plans: it must not do the work itself or hand off to another agent. The agent assigned to a
later phase (for example Developer on Execute) does the work with its own tools.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

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
