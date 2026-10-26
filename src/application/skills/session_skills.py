"""Session-scoped skill activation, progressive skill index, and active tool resolution [CARD-688, ADR-0065]."""

from __future__ import annotations

import json
from typing import Any, Iterable, List, Optional

from src.application.agent_skills.allowed_tools import (
    AUTO_SKILL_WILDCARD,
    AUTO_USER_SKILL_WILDCARD,
    has_auto_skill_wildcard,
    pinned_skills,
    resolve_allowed_tools,
    ticked_skills,
)
from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS

_SESSION_ACTIVATED_SKILLS: dict[str, set[str]] = {}
_DEFAULT_SESSION_KEY = "__default__"


def record_session_skill_activation(session_id: Optional[str], skill_id: str) -> None:
    """Mark ``skill_id`` as activated for ``session_id`` so its tools mount on the next step [CARD-688]."""
    clean_skill = str(skill_id or "").strip()
    if not clean_skill:
        return
    key = str(session_id or "").strip() or _DEFAULT_SESSION_KEY
    _SESSION_ACTIVATED_SKILLS.setdefault(key, set()).add(clean_skill)


def clear_session_skill_activations(session_id: Optional[str] = None) -> None:
    """Clear session skill activations (all sessions when ``session_id`` is None)."""
    if session_id is None:
        _SESSION_ACTIVATED_SKILLS.clear()
        return
    key = str(session_id or "").strip() or _DEFAULT_SESSION_KEY
    _SESSION_ACTIVATED_SKILLS.pop(key, None)


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


def session_activated_skills_from_history(history: Optional[Iterable[Any]] = None) -> set[str]:
    """Extract skill ids opened via ``skill_view``, authored via ``write_skill_file``, or mounted via ``register_mcp_service`` in history [CARD-688, CARD-689, CARD-745]."""
    activated: set[str] = set()
    for msg in history or []:
        for tc in getattr(msg, "tool_calls", None) or []:
            tc_name = getattr(tc, "name", None)
            if tc_name not in ("skill_view", "write_skill_file", "register_mcp_service"):
                continue
            args = getattr(tc, "arguments", None) or getattr(tc, "args", None) or {}
            if isinstance(args, dict):
                if tc_name == "register_mcp_service":
                    srv = str(args.get("name") or "").strip()
                    if srv:
                        from src.infrastructure.mcp.companion_author import mcp_companion_skill_id

                        activated.add(mcp_companion_skill_id(srv))
                else:
                    sid = (
                        args.get("skill_id")
                        or args.get("skill_name")
                        or args.get("id")
                        or args.get("name")
                        or _first_skill(args.get("skills"))
                    )
                    if sid and str(sid).strip():
                        clean_sid = str(sid).strip()
                        activated.add(clean_sid)
                        if clean_sid == "capability-authoring":
                            activated.add("mcp-engineering")
        if getattr(msg, "name", None) in ("skill_view", "write_skill_file", "register_mcp_service"):
            content = getattr(msg, "content", None)
            if isinstance(content, str) and content.strip().startswith("{"):
                try:
                    payload = json.loads(content)
                    if isinstance(payload, dict) and payload.get("success"):
                        sid = payload.get("companion_skill_id") or payload.get("id") or payload.get("skill_id")
                        if sid and str(sid).strip():
                            clean_sid = str(sid).strip()
                            activated.add(clean_sid)
                            if clean_sid == "capability-authoring":
                                activated.add("mcp-engineering")
                except ValueError:
                    pass
    return activated


def get_session_activated_skills(
    session_id: Optional[str] = None,
    history: Optional[Iterable[Any]] = None,
) -> set[str]:
    """All skills activated in ``session_id`` (in-memory tracker + persisted transcript history) [CARD-688]."""
    out = session_activated_skills_from_history(history)
    if session_id is not None:
        key = str(session_id or "").strip() or _DEFAULT_SESSION_KEY
        out |= set(_SESSION_ACTIVATED_SKILLS.get(key, set()))
    else:
        out |= set(_SESSION_ACTIVATED_SKILLS.get(_DEFAULT_SESSION_KEY, set()))
    return out


def _skill_index_entry(catalog: Any, skill_id: str, agent_id: Optional[str]) -> Optional[tuple[str, str]]:
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


def render_skill_index(allowed_skill: Any, catalog: Any = None, agent_id: Any = None, can_open: bool = True) -> str:
    """Name + blurb for ticked runbooks only. Empty allowlist injects nothing.

    Operator-store manifests win. Allowlisted skill runbooks that are not copied
    into ``$DATA_DIR/skills/`` still contribute a name and blurb [CARD-427].
    When ``*`` is in ``allowed_skill``, expands to all non-hidden skills [CARD-688].
    can_open=False (the call is not sent skill_view) leaves out the "open it with skill_view" hint [CARD-675].
    """
    raw_ids = [str(s).strip() for s in (allowed_skill or []) if str(s).strip()]
    if not raw_ids:
        return ""
    by_id: dict[str, Any] = {}
    if catalog is not None:
        try:
            for manifest in catalog.list_manifests():
                by_id[manifest.id] = manifest
        except Exception:
            by_id = {}
    ids: list[str] = []
    for sid in raw_ids:
        if sid == AUTO_SKILL_WILDCARD:
            for mid in by_id:
                if mid not in ids:
                    ids.append(mid)
            for expanded in ticked_skills({"allowed_skill": [AUTO_SKILL_WILDCARD]}):
                if expanded not in ids:
                    ids.append(expanded)
            continue
        if sid == AUTO_USER_SKILL_WILDCARD:
            for expanded in ticked_skills({"allowed_skill": [AUTO_USER_SKILL_WILDCARD]}):
                if expanded not in ids:
                    ids.append(expanded)
            continue
        if sid not in ids:
            ids.append(sid)
    lines: list[str] = []
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
        label = name if name == skill_id else f"{name} (id: {skill_id})"
        if blurb:
            lines.append(f"- {label}: {blurb}")
        else:
            lines.append(f"- {label}")
    if not lines:
        return ""
    if can_open:
        header = (
            "Skills (runbooks) for this agent. Names and short descriptions only. "
            "When a listed runbook matches the task, open it with skill_view to load the full instructions. "
            "Do not open a skill id that is not listed here."
        )
    else:
        header = (
            "Skills (runbooks) for this agent. Names and short descriptions only. "
            "Skill ids are not tools: use only the tools you are sent on this step."
        )
    return "\n".join([header] + lines)


def resolve_turn_active_tools(
    tool_registry: Any,
    agent: Any,
    *,
    matched_capability_ids: Optional[list] = None,
    planning_phase: bool = False,
    session_id: Optional[str] = None,
    history: Optional[Iterable[Any]] = None,
) -> List[Any]:
    """Resolve the active tools sent to the model on the current step [CARD-578, CARD-688].

    Fixed-skill agents get all their ticked tools at once (CARD-578).
    Auto-scoped ('*') agents start with REQUIRED_PLATFORM_TOOLS + skill_view + list_user_skills +
    explicitly pinned skills, and mount additional skills' tools as soon as skill_view(skill_id)
    is called in the session [CARD-688].
    """
    if getattr(agent, "id", None) == "direct":
        return []

    allowed = resolve_allowed_tools(agent)
    ticks = set(ticked_skills(agent))
    ids = matched_capability_ids
    phase_skills = {
        str(cid).strip()[len("skill.") :]
        for cid in ids or []
        if str(cid).strip().startswith("skill.") and str(cid).strip()[len("skill.") :] in ticks
    }

    tools = list(tool_registry.get_tools_for_agent(agent))
    if planning_phase:  # Formulate plans only: handoff and work tools are not mounted [CARD-554]
        from src.application.orchestration.phase_roles import planning_phase_block_reason

        risk_of = getattr(tool_registry, "get_tool_risk", None)
        tools = [
            t
            for t in tools
            if not planning_phase_block_reason(t.name, risk_of(t.name) if callable(risk_of) else None)
        ]

    from src.application.safety.tool_policy_gate import _capability_tool_names

    named = _capability_tool_names(ids) or set()
    if phase_skills and not planning_phase:  # a phase bound to ticked skills mounts only their tools [REQ-CAP-PAGE-004]
        tools = [
            t
            for t in tools
            if phase_skills & set(allowed.skills_for(t.name)) or t.name in REQUIRED_PLATFORM_TOOLS or t.name in named
        ]
    elif has_auto_skill_wildcard(agent) and not named and not planning_phase:
        # CARD-688: '*' auto-scoped agent mounts pinned skills + skills activated via skill_view in this session.
        active_skills = set(pinned_skills(agent)) | get_session_activated_skills(session_id=session_id, history=history)
        tools = [
            t
            for t in tools
            if t.name in REQUIRED_PLATFORM_TOOLS
            or t.name in ("skill_view", "list_user_skills")
            or bool(active_skills & set(allowed.skills_for(t.name)))
        ]

    try:
        from src.application.safety.tool_policy_gate import EDUCATION_FORBIDDEN_WIKI_TOOLS

        subset = None if planning_phase else _capability_tool_names(ids)
        if subset is not None:
            tools = [t for t in tools if t.name in subset or t.name in REQUIRED_PLATFORM_TOOLS]
        else:
            id_list = [str(x) for x in (ids or [])]
            if any(
                s.endswith("socratic-tutoring")
                or s.endswith("education-priming")
                or s.endswith("education-dual-coding")
                for s in id_list
            ):
                tools = [t for t in tools if getattr(t, "name", "") not in EDUCATION_FORBIDDEN_WIKI_TOOLS]
    except Exception:
        pass
    return tools
