"""The one function that decides which tools an agent may use [CARD-539, ADR-0061].

allowed = REQUIRED_PLATFORM_TOOLS + tools bound to the agent's ticked skills.
A skill's tools come from its SQLite binding row when one exists (D1), otherwise from the
agent pack.json seed (user data, then repo platform-packs) and the platform skill tables.
Legacy tool lists, profile flags and agent ids grant nothing. Every consumer calls this.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from src.application.agent_packs.schema import (
    DYNAMIC_SKILL_TOOLS,
    PLATFORM_SKILL_METADATA,
    PLATFORM_SKILL_TOOLS,
    REQUIRED_PLATFORM_TOOLS,
)

REPO_PACKS = Path(__file__).resolve().parents[3] / "platform-packs"
NO_TOOL_AGENTS = frozenset({"direct"})
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


def _data_root() -> Optional[Path]:
    try:
        from src.infrastructure.data.resolver import DataDirResolver

        return DataDirResolver().resolve().root
    except Exception:
        return None


def pack_skill_entries(agent_id: Optional[str]) -> dict[str, dict[str, Any]]:
    """skills[] of the agent's pack.json: user data first, repo seed for anything missing."""
    entries: dict[str, dict[str, Any]] = {}
    clean = (agent_id or "").strip()
    if not clean:
        return entries
    root = _data_root()
    for base in [root / "packs" if root else None, REPO_PACKS]:
        path = base / clean / "pack.json" if base else None
        if not path or not path.is_file():
            continue
        try:
            skills = json.loads(path.read_text(encoding="utf-8")).get("skills") or []
        except (OSError, ValueError):
            continue
        for entry in skills:
            if isinstance(entry, dict) and entry.get("id") and str(entry["id"]) not in entries:
                entries[str(entry["id"])] = entry
    return entries


def skill_tools(skill_ids: Iterable[str], agent_id: Optional[str] = None) -> dict[str, list[str]]:
    """Tools bound to each skill. A SQLite binding row wins over every seed (D1)."""
    ids = [str(s).strip() for s in skill_ids if str(s).strip()]
    try:
        from src.infrastructure.memory.repositories.skill_bindings import sqlite_tools_for_skills

        bound = sqlite_tools_for_skills(ids)
    except Exception:
        bound = {}
    pack = pack_skill_entries(agent_id) if any(s not in bound for s in ids) else {}
    out: dict[str, list[str]] = {}
    for sid in ids:
        if sid in bound:
            tools = list(bound[sid])
        else:
            tools = [str(t) for t in (pack.get(sid) or {}).get("tools") or []]
            tools += list(PLATFORM_SKILL_TOOLS.get(sid, ())) + list(DYNAMIC_SKILL_TOOLS.get(sid, ()))
        out[sid] = list(dict.fromkeys(t for t in tools if t))
    return out


def resolve_allowed_tools(agent: Any) -> AllowedTools:
    """REQUIRED_PLATFORM_TOOLS + ticked-skill tools. The only permission decider (ADR-0061)."""
    if agent is None or str(_field(agent, "id") or "") in NO_TOOL_AGENTS:
        return AllowedTools()
    provenance: dict[str, tuple[str, ...]] = {t: (PLATFORM,) for t in REQUIRED_PLATFORM_TOOLS}
    ticks = ticked_skills(agent)
    for sid, tools in skill_tools(ticks, str(_field(agent, "id") or "")).items():
        for tool in tools:
            if provenance.get(tool) != (PLATFORM,):
                provenance[tool] = provenance.get(tool, ()) + (sid,)
    if ticks:
        from src.application.skills.user_catalog import LIST_USER_SKILL_PACKS, SKILL_VIEW

        for tool in (SKILL_VIEW, LIST_USER_SKILL_PACKS):
            provenance.setdefault(tool, (PLATFORM,))
    ordered = tuple(t for t in provenance if not t.endswith("*"))
    patterns = tuple(t for t in provenance if t.endswith("*"))
    return AllowedTools(ordered=ordered, provenance=provenance, patterns=patterns)


def ticked_skills_for_domains(agent: Any, domains: Iterable[str]) -> list[str]:
    """Map intent domains (wiki, coding, an MCP server name...) onto the agent's ticked skills only.

    A ticked skill matches a domain when it is that domain, or binds a tool the domain's seed binds,
    or binds that MCP server's tools. Nothing outside the ticks is ever returned (REQ-539-003).
    """
    wanted = [str(d).strip().lower() for d in domains if str(d).strip()]
    if not wanted:
        return []
    ticks = ticked_skills(agent)
    bound = skill_tools(ticks, str(_field(agent, "id") or ""))
    out: list[str] = []
    for sid in ticks:
        tools = set(bound.get(sid) or [])
        for dom in wanted:
            seed = set(PLATFORM_SKILL_TOOLS.get(dom, ())) | set(DYNAMIC_SKILL_TOOLS.get(dom, ()))
            mcp = f"mcp_{dom.replace('-', '_')}_"
            if sid.lower() == dom or tools & seed or any(t.startswith(mcp) for t in tools):
                out.append(sid)
                break
    return out


def skill_that_binds(tool: str, agent_id: Optional[str] = None) -> Optional[str]:
    """First known skill that binds the tool: the agent's pack skills, then the platform seeds."""
    for sid, entry in pack_skill_entries(agent_id).items():
        if tool in (entry.get("tools") or []):
            return sid
    for table in (PLATFORM_SKILL_TOOLS, DYNAMIC_SKILL_TOOLS):
        for sid, tools in table.items():
            if tool in tools:
                return sid
    return None


def skills_version(agent: Any) -> str:
    """Short hash of the ticked skills; Studio sends it back so a stale Save gets 409 (D10)."""
    import hashlib

    return hashlib.sha1(json.dumps(sorted(ticked_skills(agent))).encode("utf-8")).hexdigest()[:12]


def platform_seed_tools(skill_ids: Iterable[str]) -> list[str]:
    """Tools of platform skills from the seed table only. For derived display/compat columns, never permission."""
    return list(dict.fromkeys(t for sid in skill_ids for t in PLATFORM_SKILL_TOOLS.get(str(sid).strip(), ())))


def allowed_capability_ids(agent: Any) -> set[str]:
    """Catalog ids the agent may be matched to: its allowed tools and ticked skills."""
    allowed = resolve_allowed_tools(agent)
    return {f"tool.{t}" for t in allowed.ordered} | {f"skill.{s}" for s in ticked_skills(agent)}


def _operator_skill_meta(sid: str) -> dict[str, Any]:
    """name/description from an operator skill's SKILL.md frontmatter ({data}/skills/<id>/SKILL.md)."""
    root = _data_root()
    path = root / "skills" / sid / "SKILL.md" if root else None
    try:
        text = path.read_text(encoding="utf-8") if path and path.is_file() else ""
        if not text.startswith("---"):
            return {}
        import yaml

        meta = yaml.safe_load(text.split("---", 2)[1]) or {}
        return meta if isinstance(meta, dict) else {}
    except Exception:  # unreadable or malformed frontmatter: no blurb
        return {}


def _skill_meta(sid: str, agent_id: Optional[str] = None, pack: Optional[dict] = None) -> dict[str, Any]:
    return (
        PLATFORM_SKILL_METADATA.get(sid)
        or (pack if pack is not None else pack_skill_entries(agent_id)).get(sid)
        or _operator_skill_meta(sid)
    )


def skill_label(sid: str, agent_id: Optional[str] = None, pack: Optional[dict] = None) -> str:
    meta = _skill_meta(sid, agent_id, pack)
    return str(meta.get("name") or sid.replace("-", " ").replace("_", " ").title())


def _labels(agent: Any) -> list[str]:
    agent_id = str(_field(agent, "id") or "")
    pack = pack_skill_entries(agent_id)
    return [skill_label(s, agent_id, pack) for s in ticked_skills(agent)]


def _blurbed_labels(agent: Any, limit: int = 90) -> list[str]:
    """"Name (first sentence of the description)" per ticked skill (D5: ticked skill blurbs)."""
    agent_id = str(_field(agent, "id") or "")
    pack = pack_skill_entries(agent_id)
    out = []
    for sid in ticked_skills(agent):
        meta = _skill_meta(sid, agent_id, pack)
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
    return (
        f"{name} covers: {covers}. For anything else, find the right agent with lookup_agents and "
        'hand off with handoff_to_agent; if no agent covers it, say so plainly and end your reply with "You can use Ask Developer to add this."'
    )


def routing_summary(agent: Any, limit: int = 160) -> str:
    """Short routing text for directory cards, built from ticked skill names (never tool ids)."""
    text = "; ".join(_labels(agent)) or str(_field(agent, "description", "name", "id") or "")
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."
