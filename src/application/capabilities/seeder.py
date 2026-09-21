"""
Built-in Platform Capability Seeder [CARD-407, REQ-407-001].

Seeds trusted platform tools, agent profiles, and platform skills into
the durable CapabilityIndexRepository (capability_index in SQLite) on startup.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    RiskLevel,
    TrustTier,
)

logger = logging.getLogger(__name__)


def seed_builtin_capabilities(
    repo: Any,
    tool_registry: Any,
    agent_registry: Any,
    user_skill_catalog: Optional[Any] = None,
) -> int:
    """
    Seed built-in tools, agents, and platform skills into capability_index with TrustTier.TRUSTED.
    """
    if repo is None:
        return 0

    seeded_count = 0
    profiles = []
    if agent_registry is not None:
        if hasattr(agent_registry, "list_agents"):
            profiles = list(agent_registry.list_agents() or [])
        elif hasattr(agent_registry, "list_profiles"):
            profiles = list(agent_registry.list_profiles() or [])

    # 1. Seed Tools from tool_registry
    if tool_registry is not None and hasattr(tool_registry, "list_tools"):
        for defn in tool_registry.list_tools():
            tool_name = defn.name
            # Determine which agents explicitly allow this tool in their skills or pack_tool_names
            roles = []
            for p in profiles:
                allowed_tools = set(getattr(p, "allowed_tool_names", None) or getattr(p, "pack_tool_names", None) or [])
                for s in (getattr(p, "skills", None) or []):
                    allowed_tools.update(getattr(s, "tools", []) or [])
                if tool_name in allowed_tools:
                    roles.append(p.id)

            keywords = {tool_name.lower()}
            keywords.update(w.lower() for w in tool_name.replace("_", " ").split() if len(w) > 2)
            if defn.description:
                keywords.update(w.lower() for w in re.findall(r"[a-zA-Z0-9]+", defn.description) if len(w) > 3)

            entry = CapabilityIndexEntry(
                id=f"tool.{tool_name}",
                kind=CapabilityKind.TOOL,
                name=tool_name,
                summary=defn.description or f"Tool {tool_name}",
                keywords=sorted(keywords),
                roles=roles,
                trust_tier=TrustTier.TRUSTED,
                risk_level=RiskLevel.LOW,
                requires_hitl=False,
                source="builtin",
            )
            repo.upsert_entry(entry)
            seeded_count += 1

    # 2. Seed Agents from agent_registry
    for p in profiles:
        keywords = {p.id.lower(), p.name.lower()}
        keywords.update(w.lower() for w in p.name.split() if len(w) > 2)
        if p.description:
            keywords.update(w.lower() for w in re.findall(r"[a-zA-Z0-9]+", p.description) if len(w) > 3)

        entry = CapabilityIndexEntry(
            id=f"agent.{p.id}",
            kind=CapabilityKind.AGENT,
            name=p.name,
            summary=p.description or f"Agent {p.name}",
            keywords=sorted(keywords),
            roles=[p.id],
            trust_tier=TrustTier.TRUSTED,
            risk_level=RiskLevel.LOW,
            requires_hitl=False,
            source="builtin",
        )
        repo.upsert_entry(entry)
        seeded_count += 1

    # 3. Seed Skills from user_skill_catalog
    if user_skill_catalog is not None and hasattr(user_skill_catalog, "list_skill_metadata"):
        for meta in user_skill_catalog.list_skill_metadata():
            sid = meta["id"]
            cid = sid if sid.startswith("skill.") else f"skill.{sid}"
            keywords = {meta["title"].lower(), meta.get("pack_id", "").lower(), "skill", "runbook"}
            if meta.get("description"):
                keywords.update(w.lower() for w in re.findall(r"[a-zA-Z0-9]+", meta["description"]) if len(w) > 3)
            entry = CapabilityIndexEntry(
                id=cid,
                kind=CapabilityKind.SKILL,
                name=meta["title"],
                summary=meta.get("description") or "",
                keywords=sorted(keywords),
                roles=[meta.get("pack_id", "")] if meta.get("pack_id") else [],
                trust_tier=TrustTier.TRUSTED,
                risk_level=RiskLevel.MEDIUM,
                requires_hitl=False,
                source=meta.get("origin", "platform"),
                metadata={"pack_id": meta.get("pack_id", ""), "origin": meta.get("origin", "user")},
            )
            repo.upsert_entry(entry)
            seeded_count += 1

    # 4. Seed Skills defined on profiles
    for p in profiles:
        for skill in (getattr(p, "skills", None) or []):
            sid = getattr(skill, "id", None)
            if not sid:
                continue
            cid = sid if sid.startswith("skill.") else f"skill.{sid}"
            keywords = {sid.lower(), getattr(skill, "name", "").lower(), p.id.lower(), "skill"}
            if getattr(skill, "description", None):
                keywords.update(w.lower() for w in re.findall(r"[a-zA-Z0-9]+", skill.description) if len(w) > 3)
            entry = CapabilityIndexEntry(
                id=cid,
                kind=CapabilityKind.SKILL,
                name=getattr(skill, "name", sid),
                summary=getattr(skill, "description", "") or "",
                keywords=sorted(keywords),
                roles=[p.id],
                trust_tier=TrustTier.TRUSTED,
                risk_level=RiskLevel.MEDIUM,
                requires_hitl=False,
                source="builtin",
                metadata={"pack_id": p.id, "tools": getattr(skill, "tools", [])},
            )
            repo.upsert_entry(entry)
            seeded_count += 1

    logger.info("Capability index seeded with %d trusted entries.", seeded_count)
    return seeded_count
