"""The one function that decides which tools an agent may use [CARD-539, ADR-0061].

allowed = REQUIRED_PLATFORM_TOOLS + tools of the agent's ticked skills.
A skill's tools come only from the ``tools:`` list of its winning SKILL.md (user copy in the data
dir, else platform/skills in the repo) [CARD-570]. An unknown tool id grants nothing.
Legacy tool lists, profile flags and agent ids grant nothing. Every consumer calls this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from src.application.agent_skills.schema import REQUIRED_PLATFORM_TOOLS

NO_TOOL_AGENTS = frozenset({"direct"})
# CARD-563: platform tools an agent must not get. Architect starts Developer only through hand_off_card.
WITHHELD_PLATFORM_TOOLS: dict[str, frozenset[str]] = {"architect": frozenset({"handoff_to_agent", "lookup_agents"})}
# Checkers the platform itself runs after a turn (reflexion / phase verification). Never offered to a model.
PLATFORM_VERIFIER_TOOLS = frozenset({"verify_telemetry_consistency", "assert_json_schema", "validate_metric_bounds"})
PLATFORM = "platform"

@dataclass(frozen=True)
class AllowedTools:
    """Allowed tool names in display order, with the ticked skills that grant each one."""

    ordered: tuple[str, ...] = ()
    provenance: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    patterns: tuple[str, ...] = ()  # wildcard bindings such as mcp_files_*

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self.ordered)

    def __contains__(self, tool: object) -> bool:
        name = str(tool or "")
        return name in self.provenance or any(name.startswith(p[:-1]) for p in self.patterns)

    def __iter__(self):
        return iter(self.ordered)

    def __len__(self) -> int:
        return len(self.ordered)

    def skills_for(self, tool: str) -> tuple[str, ...]:
        if tool in self.provenance:
            return self.provenance[tool]
        return tuple(s for p in self.patterns if tool.startswith(p[:-1]) for s in self.provenance[p])

    def filter(self, tools: Iterable[str]) -> list[str]:
        return [t for t in tools if t in self]


def _field(agent: Any, *names: str) -> Any:
    for name in names:
        value = agent.get(name) if isinstance(agent, Mapping) else getattr(agent, name, None)
        if value:
            return value
    return None


def ticked_skills(agent: Any) -> list[str]:
    seen: list[str] = []
    for sid in _field(agent, "allowed_skill", "skills") or []:
        clean = str(sid).strip()
        if clean and clean not in seen:
            seen.append(clean)
    return seen


def _store():
    from src.infrastructure.content.store import get_store

    return get_store()


def _granted(tool: str) -> bool:
    """Unknown tool ids grant nothing once the tool registry is known [CARD-570]."""
    from src.infrastructure.content.store import is_known_tool

    return is_known_tool(tool)


def skill_tools(skill_ids: Iterable[str], agent_id: Optional[str] = None) -> dict[str, list[str]]:
    """Tools of each skill: the ``tools:`` list of its winning SKILL.md (one source)."""
    ids = [str(s).strip() for s in skill_ids if str(s).strip()]
    raw = _store().skill_tools(ids)
    return {sid: [t for t in raw.get(sid) or [] if _granted(t)] for sid in ids}


def resolve_allowed_tools(agent: Any) -> AllowedTools:
    """REQUIRED_PLATFORM_TOOLS + ticked-skill tools. The only permission decider (ADR-0061)."""
    if agent is None or str(_field(agent, "id") or "") in NO_TOOL_AGENTS:
        return AllowedTools()
    withheld = WITHHELD_PLATFORM_TOOLS.get(str(_field(agent, "id") or ""), frozenset())
    provenance: dict[str, tuple[str, ...]] = {t: (PLATFORM,) for t in REQUIRED_PLATFORM_TOOLS if t not in withheld}
    ticks = ticked_skills(agent)
    for sid, tools in skill_tools(ticks, str(_field(agent, "id") or "")).items():
        for tool in tools:
            if tool in withheld:
                continue
            if provenance.get(tool) != (PLATFORM,):
                provenance[tool] = provenance.get(tool, ()) + (sid,)
    if ticks:
        from src.application.skills.user_catalog import LIST_USER_SKILLS, SKILL_VIEW

        for tool in (SKILL_VIEW, LIST_USER_SKILLS):
            provenance.setdefault(tool, (PLATFORM,))
    ordered = tuple(t for t in provenance if not t.endswith("*"))
    patterns = tuple(t for t in provenance if t.endswith("*"))
    return AllowedTools(ordered=ordered, provenance=provenance, patterns=patterns)


def skill_that_binds(tool: str, agent_id: Optional[str] = None) -> Optional[str]:
    """First skill that lists the tool: the agent's ticked skills, then every other skill."""
    store = _store()
    agent = None
    if agent_id:
        loaded = store.agents.load(agent_id)
        agent = loaded.skills if loaded else None
    ordered = list(agent or []) + [s.id for s in store.skills.list()]
    for sid in dict.fromkeys(ordered):
        loaded = store.skills.load(sid)
        if loaded and tool in loaded.tools:
            return sid
    return None


def skills_version(agent: Any) -> str:
    """Short hash of the ticked skills; Studio sends it back so a stale Save gets 409 (D10)."""
    import hashlib

    return hashlib.sha1(json.dumps(sorted(ticked_skills(agent))).encode("utf-8")).hexdigest()[:12]


def platform_seed_tools(skill_ids: Iterable[str]) -> list[str]:
    """Tools of the given skills from their SKILL.md. For display only, never permission."""
    tools = skill_tools(skill_ids)
    return list(dict.fromkeys(t for sid in tools for t in tools[sid]))


def allowed_capability_ids(agent: Any) -> set[str]:
    """Catalog ids the agent may be matched to: its allowed tools and ticked skills."""
    allowed = resolve_allowed_tools(agent)
    return {f"tool.{t}" for t in allowed.ordered} | {f"skill.{s}" for s in ticked_skills(agent)}


def _skill_meta(sid: str, agent_id: Optional[str] = None, owner: Optional[dict] = None) -> dict[str, Any]:
    loaded = _store().skills.load(sid)
    return dict(loaded.meta) if loaded else {}


def skill_entries(agent_id: Optional[str]) -> dict[str, dict[str, Any]]:
    """Kept name for callers: {skill id: frontmatter} for the agent's ticked skills."""
    store = _store()
    loaded = store.agents.load(agent_id) if agent_id else None
    out: dict[str, dict[str, Any]] = {}
    for sid in loaded.skills if loaded else []:
        skill = store.skills.load(sid)
        if skill:
            out[sid] = {"id": sid, **skill.meta}
    return out


def skill_label(sid: str, agent_id: Optional[str] = None, owner: Optional[dict] = None) -> str:
    meta = _skill_meta(sid, agent_id, owner)
    return str(meta.get("name") or sid.replace("-", " ").replace("_", " ").title())


def _labels(agent: Any) -> list[str]:
    agent_id = str(_field(agent, "id") or "")
    return [skill_label(s, agent_id) for s in ticked_skills(agent)]


def _blurbed_labels(agent: Any, limit: int = 90) -> list[str]:
    """"Name (first sentence of the description)" per ticked skill (D5: ticked skill blurbs)."""
    agent_id = str(_field(agent, "id") or "")
    out = []
    for sid in ticked_skills(agent):
        meta = _skill_meta(sid, agent_id)
        label = str(meta.get("name") or sid.replace("-", " ").replace("_", " ").title())
        blurb = " ".join(str(meta.get("description") or "").split()).split(". ")[0].rstrip(".")
        blurb = blurb if len(blurb) <= limit else blurb[: limit - 3].rstrip() + "..."
        out.append(f"{label} ({blurb})" if blurb else label)
    return out


def domain_line(agent: Any) -> str:
    """Generated domain boundary for the system prompt: ticked skills, then hand off or Ask Developer."""
    name = str(_field(agent, "name", "id") or "This agent")
    labels = _blurbed_labels(agent)
    covers = "; ".join(labels) if labels else "general conversation only"
    if "handoff_to_agent" in WITHHELD_PLATFORM_TOOLS.get(str(_field(agent, "id") or ""), frozenset()):
        return f"{name} covers: {covers}. For anything else, say so plainly; do not try to reach other agents."
    return (
        f"{name} covers: {covers}. For anything else, find the right agent with lookup_agents and "
        'hand off with handoff_to_agent; if no agent covers it, say so plainly and end your reply with "You can use Ask Developer to add this."'
    )


def routing_summary(agent: Any, limit: int = 160) -> str:
    """Short routing text for directory cards, built from ticked skill names (never tool ids)."""
    text = "; ".join(_labels(agent)) or str(_field(agent, "description", "name", "id") or "")
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."
