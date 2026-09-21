"""
Agent Cognitive Memory Tools [CARD-116, CARD-405].

Internal callable tools allowing agents to interact with their dedicated brain (<agent_slug>_memory.db):
- recall_agent_memory: Search semantic facts and past milestones.
- memorize_fact: Save an explicit fact with conflict resolution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry, get_tool_context
from src.application.memory.extractor import CandidateMemoryFact, MemoryExtractorService
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


class AgentMemoryTools:
    """Tool wrapper providing memory recall and memorization tools for agents."""

    def __init__(
        self,
        repository: Optional[AgentMemoryRepository] = None,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.repository = repository
        self.data_dir = Path(data_dir) if data_dir is not None else None

    def _resolve_repo(self, agent_id: Optional[str] = None) -> AgentMemoryRepository:
        if self.repository is not None:
            return self.repository
        target_id = (agent_id or "").strip()
        if not target_id:
            ctx = get_tool_context()
            target_id = str(ctx.get("agent_id") or "").strip()
        if not target_id:
            target_id = "developer"
        repo = AgentMemoryRepository(agent_id=target_id, data_dir=self.data_dir)
        repo.initialize_schema()
        return repo

    def recall_agent_memory(
        self,
        query: str,
        limit: int = 5,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search the agent's cognitive memory for relevant facts and milestones.

        Args:
            query: The search query terms.
            limit: Maximum number of memories to return (default: 5).
            agent_id: Optional explicit agent ID (defaults to current caller agent).
        """
        repo = self._resolve_repo(agent_id)
        facts = repo.search_facts(query=query, limit=limit)
        if not facts and any(w in query.lower() for w in ("all", "stored", "everything", "*", "any", "brain", "facts", "memories", "list")):
            facts = repo.list_semantic_facts(limit=limit)
        summaries = repo.list_session_summaries(limit=2)
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
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a new atomic fact into the agent's cognitive memory with conflict resolution.

        Args:
            entity: Target entity (e.g. 'user', 'project', 'system').
            attribute: Attribute name (e.g. 'os_platform', 'preferred_language').
            value: The fact value string.
            category: Optional category ('user_pref', 'environment', 'domain', 'constraint', 'general').
            agent_id: Optional explicit agent ID (defaults to current caller agent).
        """
        repo = self._resolve_repo(agent_id)
        extractor = MemoryExtractorService(repository=repo)
        candidate = CandidateMemoryFact(
            action="ADD",
            category=category,
            entity=entity,
            attribute=attribute,
            value=value,
        )
        result = extractor.apply_candidate_fact(candidate)
        return {
            "status": "ok",
            "action_taken": result.get("action_taken", "ADD"),
            "fact_id": result.get("fact_id"),
            "entity": entity,
            "attribute": attribute,
            "value": value,
        }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        """Register memory tools with the platform ScopedToolRegistry."""
        registry.register_tool(
            name="recall_agent_memory",
            description=(
                "Search the agent's dedicated cognitive memory brain (<agent_slug>_memory.db) "
                "for relevant facts, user preferences, environment constraints, and past milestones."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query terms to find relevant memories.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return (default: 5).",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Optional explicit agent ID (defaults to caller agent).",
                    },
                },
                "required": ["query"],
            },
            handler=self.recall_agent_memory,
        )

        registry.register_tool(
            name="memorize_fact",
            description=(
                "Save a new atomic fact into the agent's dedicated cognitive memory brain (<agent_slug>_memory.db) "
                "with automatic conflict resolution (ADD, UPDATE, BUMP). Use this to persist user preferences, "
                "project architecture, tooling choices, or environment constraints."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Target entity (e.g. 'user', 'project', 'system').",
                    },
                    "attribute": {
                        "type": "string",
                        "description": "Normalized attribute name (e.g. 'preferred_runner', 'database_engine').",
                    },
                    "value": {
                        "type": "string",
                        "description": "The fact value string.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category ('user_pref', 'environment', 'domain', 'constraint', 'general').",
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Optional explicit agent ID (defaults to caller agent).",
                    },
                },
                "required": ["entity", "attribute", "value"],
            },
            handler=self.memorize_fact,
        )
