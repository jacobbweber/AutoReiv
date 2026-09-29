"""
Just-In-Time (JIT) Agent Directory Indexing Service [REQ-ORCH-001].
Discovers and ranks agent capabilities dynamically on demand without prompt bloat.
"""

import re
from typing import Any, Dict, List, Optional

from src.application.agent_skills.allowed_tools import routing_summary
from src.domain.orchestration.models import CompactAgentCard
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class AgentDirectoryService:
    """
    Indexes active built-in agent profiles and custom SQLite agents,
    providing fast keyword & capability discovery returning token-efficient CompactAgentCards.
    """

    def __init__(
        self,
        agent_registry: Optional[BuiltinAgentRegistry] = None,
        state_store: Optional[SQLiteStateStore] = None,
    ):
        self.state_store = state_store or SQLiteStateStore()
        self.agent_registry = agent_registry or BuiltinAgentRegistry(state_store=self.state_store)

    def search_agents(self, query: str, limit: int = 3) -> List[CompactAgentCard]:
        """
        Search available agents matching a capability query.
        Returns up to `limit` compact agent cards sorted by relevance.
        """
        query_terms = [t.lower().strip() for t in re.findall(r"\w+", query) if len(t) >= 2]
        all_agents = self._get_all_agent_profiles()

        if not query_terms:
            return [self._to_compact_card(a) for a in all_agents[:limit]]

        scored_agents = []
        for profile in all_agents:
            score = self._compute_relevance_score(profile, query_terms)
            if score > 0:
                scored_agents.append((score, profile))

        # Sort by relevance score descending
        scored_agents.sort(key=lambda x: x[0], reverse=True)

        return [self._to_compact_card(profile) for _, profile in scored_agents[:limit]]

    def get_agent_card(self, agent_id: str) -> Optional[CompactAgentCard]:
        """Fetch a single compact agent card by ID."""
        for profile in self._get_all_agent_profiles():
            if profile.get("id") == agent_id:
                return self._to_compact_card(profile)
        return None

    def _get_all_agent_profiles(self) -> List[Dict[str, Any]]:
        """Aggregate profiles via BuiltinAgentRegistry."""
        profiles = []
        for profile in self.agent_registry.list_agents():
            profiles.append(
                {
                    "id": profile.id,
                    "name": profile.name,
                    "system_prompt": profile.system_prompt,
                    "tone": profile.tone.value if hasattr(profile.tone, "value") else str(profile.tone),
                    # CARD-539 D5: route by ticked skills, never tool lists.
                    "skills": list(getattr(profile, "allowed_skill", None) or []),
                    "routing": routing_summary(profile),
                }
            )
        return profiles

    def _compute_relevance_score(self, profile: Dict[str, Any], query_terms: List[str]) -> float:
        """Compute matching score for an agent profile against query terms."""
        score = 0.0
        aid = profile.get("id", "").lower()
        name = profile.get("name", "").lower()
        prompt = profile.get("system_prompt", "").lower()
        tools = f"{' '.join(profile.get('skills', []))} {profile.get('routing', '')}".lower()
        tone = profile.get("tone", "").lower()

        searchable_corpus = f"{aid} {name} {prompt} {tools} {tone}"

        # Common domain synset mappings
        synonyms = {
            "sql": ["database", "postgres", "db", "query", "table", "migration"],
            "db": ["database", "sql", "postgres", "sqlite", "table"],
            "shell": ["sysadmin", "bash", "command", "system", "terminal", "os"],
            "bash": ["sysadmin", "shell", "command", "system", "exec"],
            "docs": ["librarian", "specs", "specifications", "notes", "wiki", "adr"],
            "specs": ["librarian", "docs", "requirements", "design", "tasks"],
            "verify": ["verification", "assert", "test", "audit", "check", "review"],
            "review": ["qa", "tester", "spec", "returned"],
            "qa": ["review", "tester"],
            "tester": ["review", "qa"],
            "plan": ["planning", "milestone", "goal", "decompose", "dag", "conductor", "scrum"],
            "conductor": ["product", "plan", "scrum", "cards", "spec"],
            "product": ["conductor", "plan", "scrum", "spec"],
            "scrum": ["conductor", "product", "plan", "cards"],
            "code": ["coding", "python", "script", "sandbox"],
            "python": ["coding", "code", "script", "sandbox"],
        }

        for term in query_terms:
            # Direct matches
            if term in aid or term in name:
                score += 5.0
            if term in tools:
                score += 3.0
            if term in prompt:
                score += 2.0

            # Synonym expansions
            for syn_key, syn_words in synonyms.items():
                if term == syn_key or term in syn_words:
                    for w in syn_words:
                        if w in searchable_corpus:
                            score += 1.5

        return score

    def _to_compact_card(self, profile: Dict[str, Any]) -> CompactAgentCard:
        """Compact router card from ticked skills (CARD-539 D5): routing summary + skill ids."""
        summary = (profile.get("routing") or "").strip() or f"{profile.get('name', 'Agent')} (no skills ticked)"
        return CompactAgentCard(
            id=profile.get("id", "agent"),
            name=profile.get("name", profile.get("id", "Agent").title()),
            tone=profile.get("tone", "analytical"),
            summary=summary,
            skills=list(profile.get("skills") or [])[:4],
        )
