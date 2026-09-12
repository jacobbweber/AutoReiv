"""CARD-269: Shared good-agent Instructions template (standing system contract).

Mirrors Forge `buildQuickScaffoldPayload` sections and adds provenance/HITL
honesty so Assistant / AutoReiv / Finance match new-agent create quality.
"""
from __future__ import annotations

from typing import Iterable, Sequence

# Deterministic section headers — tests and live smoke assert these exact markers.
REQUIRED_INSTRUCTION_SECTIONS: tuple[str, ...] = (
    "[IDENTITY & ROLE]",
    "[DOMAIN BOUNDARIES & REFUSALS]",
    "[EXECUTION PROTOCOL]",
    "[SAFETY & APPROVALS]",
    "[TOOL USAGE RULES]",
    "[PROVENANCE & HONESTY]",
    "[OUTPUT FORMAT]",
)


def render_good_agent_instructions(
    *,
    name: str,
    role: str,
    domain_focus: str,
    mission_bullets: Sequence[str] | None = None,
    tool_notes: Sequence[str] | None = None,
    safety_notes: Sequence[str] | None = None,
    extra_sections: Sequence[tuple[str, Sequence[str]]] | None = None,
) -> str:
    """Build a standing Instructions contract with the required section headers.

    Domain-specific mission/tool/safety lines are folded into the standard
    sections so we do not invent a second prompt dialect.
    """
    clean_name = (name or "").strip() or "Agent"
    clean_role = (role or "").strip() or clean_name
    clean_domain = (domain_focus or "").strip() or clean_role
    mission = [b.strip() for b in (mission_bullets or ()) if str(b).strip()]
    tools = [b.strip() for b in (tool_notes or ()) if str(b).strip()]
    safety = [b.strip() for b in (safety_notes or ()) if str(b).strip()]

    identity_lines = [
        f"You are {clean_name}, a specialized AI agent focused on: {clean_role}.",
    ]
    identity_lines.extend(mission)

    domain_lines = [
        f"Focus strictly on {clean_domain}. Refuse requests outside your authorized domain or refer them to other specialists.",
    ]

    execution_lines = [
        "1. Inspect and read the current environment or state before making changes.",
        "2. Formulate an explicit plan before executing commands or actions.",
        "3. Validate all inputs and parameters defensively.",
        "4. Verify completion and report clear outcomes with evidence.",
    ]

    safety_lines = [
        "Always require confirmation before executing destructive, mutating, or production operations. Use dry-runs where available.",
        "HITL gates (REQUIRE_CONFIRM / Approve / Reject) are authoritative — never treat a toast or UI hint as approval.",
    ]
    safety_lines.extend(safety)

    tool_lines = [
        "Invoke tools atomically and check return status codes. Handle failures gracefully with actionable diagnostic messages.",
        "Only claim tool results you actually received this turn. Listed tools are capabilities, not proof of execution.",
    ]
    tool_lines.extend(tools)

    provenance_lines = [
        "Separate operator-visible facts (tool returns, job_id, wiki/repo reads) from inference.",
        "When citing wiki or checkout files, name the source path or note id; do not invent contents.",
        "On kill/resume and handoffs, keep the same job_id and report continuity honestly.",
    ]

    output_lines = [
        "Provide concise, structured markdown with clear checklists, diagnostic tables, or code snippets.",
    ]

    blocks: list[str] = [
        "[IDENTITY & ROLE]",
        *identity_lines,
        "",
        "[DOMAIN BOUNDARIES & REFUSALS]",
        *domain_lines,
        "",
        "[EXECUTION PROTOCOL]",
        *execution_lines,
        "",
        "[SAFETY & APPROVALS]",
        *safety_lines,
        "",
        "[TOOL USAGE RULES]",
        *tool_lines,
        "",
        "[PROVENANCE & HONESTY]",
        *provenance_lines,
        "",
        "[OUTPUT FORMAT]",
        *output_lines,
    ]

    for header, lines in extra_sections or ():
        h = str(header).strip()
        if not h:
            continue
        if not h.startswith("["):
            h = f"[{h}]"
        blocks.append("")
        blocks.append(h)
        blocks.extend(str(x).strip() for x in lines if str(x).strip())

    return "\n".join(blocks).strip() + "\n"


def assert_good_agent_sections(prompt: str) -> list[str]:
    """Return missing REQUIRED_INSTRUCTION_SECTIONS headers (empty = ok)."""
    text = prompt or ""
    return [s for s in REQUIRED_INSTRUCTION_SECTIONS if s not in text]


def prompts_match_template(prompts: Iterable[str]) -> bool:
    return all(not assert_good_agent_sections(p) for p in prompts)
