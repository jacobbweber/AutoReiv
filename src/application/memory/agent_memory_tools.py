"""
Agent Cognitive Memory Tools [CARD-116].

Internal callable tools allowing agents to interact with their dedicated brain:
- recall_agent_memory: Search semantic facts and past milestones.
- memorize_fact: Save an explicit fact with conflict resolution.
"""

from __future__ import annotations

from typing import Any, Dict

from src.application.memory.extractor import CandidateMemoryFact, MemoryExtractorService
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


class AgentMemoryTools:
    """Tool wrapper providing memory recall and memorization tools for an agent."""

    def __init__(self, repository: AgentMemoryRepository) -> None:
        self.repository = repository
        self.extractor_service = MemoryExtractorService(repository=repository)

    def recall_agent_memory(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search the agent's cognitive memory for relevant facts and milestones.

        Args:
            query: The search query terms.
            limit: Maximum number of memories to return (default: 5).
        """
        facts = self.repository.search_facts(query=query, limit=limit)
        summaries = self.repository.list_session_summaries(limit=2)
        return {
            "status": "ok",
            "query": query,
            "facts": facts,
            "recent_milestones": summaries,
        }

    def memorize_fact(
        self,
        entity: str,
        attribute: str,
        value: str,
        category: str = "general",
    ) -> Dict[str, Any]:
        """Save a new atomic fact into the agent's cognitive memory with conflict resolution.

        Args:
            entity: Target entity (e.g. 'user', 'project', 'system').
            attribute: Attribute name (e.g. 'os_platform', 'preferred_language').
            value: The fact value string.
            category: Optional category ('user_pref', 'environment', 'domain', 'constraint', 'general').
        """
        candidate = CandidateMemoryFact(
            action="ADD",
            category=category,
            entity=entity,
            attribute=attribute,
            value=value,
        )
        result = self.extractor_service.apply_candidate_fact(candidate)
        return {
            "status": "ok",
            "action_taken": result.get("action_taken", "ADD"),
            "fact_id": result.get("fact_id"),
            "entity": entity,
            "attribute": attribute,
            "value": value,
        }
