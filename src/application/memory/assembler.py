"""
Dynamic Context Window Token Budgeting & Three-Shelf Memory Injection [CARD-116].

Dynamically adapts memory injection budget to the active model's context capacity:
- Tight (<= 8k): ~350 tokens (Shelf 1 Pinned + Top 3 Facts; Shelf 2 omitted)
- Standard (8k - 32k): ~800 tokens (Shelf 1 Pinned + 1 recent summary + Top 6 Facts)
- Broad (> 32k): ~2000 tokens (Shelf 1 Pinned + 3 session summaries + Top 15 Facts)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

logger = logging.getLogger(__name__)


def get_budget_tier(context_limit: int) -> Dict[str, Any]:
    """Return memory token budget and shelf limits according to model context limit."""
    if context_limit <= 8192:
        return {
            "tier_name": "tight",
            "max_tokens": 350,
            "max_pinned_tokens": 150,
            "max_summaries": 0,
            "max_facts": 3,
        }
    elif context_limit <= 32768:
        return {
            "tier_name": "standard",
            "max_tokens": 800,
            "max_pinned_tokens": 250,
            "max_summaries": 1,
            "max_facts": 6,
        }
    else:
        return {
            "tier_name": "broad",
            "max_tokens": 2000,
            "max_pinned_tokens": 400,
            "max_summaries": 3,
            "max_facts": 15,
        }


class MemoryContextAssembler:
    """Assembles Shelf 1 (Pinned), Shelf 2 (Episodic), and Shelf 3 (Semantic) into a prompt block."""

    def __init__(self, repository: AgentMemoryRepository) -> None:
        self.repository = repository

    def assemble(
        self,
        context_limit: int = 16384,
        user_query: Optional[str] = None,
        pinned_override: Optional[str] = None,
    ) -> str:
        """Assemble the three memory shelves formatted for system prompt injection."""
        tier = get_budget_tier(context_limit)
        sections: List[str] = []

        # --- Shelf 1: Pinned Directives ---
        pinned_items: List[str] = []
        if pinned_override and pinned_override.strip():
            pinned_items.append(pinned_override.strip())

        try:
            stored_pins = self.repository.list_pinned_memories()
            for pin in stored_pins:
                content = pin.get("content", "").strip()
                if content and content not in pinned_items:
                    pinned_items.append(content)
        except Exception as exc:
            logger.debug("Failed listing pinned memories: %s", exc)

        if pinned_items:
            lines = ["[Agent Brain - Pinned Directives]"]
            for item in pinned_items:
                lines.append(f"- {item}")
            sections.append("\n".join(lines))

        # --- Shelf 2: Episodic Summaries ---
        if tier["max_summaries"] > 0:
            try:
                summaries = self.repository.list_session_summaries(limit=tier["max_summaries"])
                if summaries:
                    lines = ["[Agent Brain - Episodic Milestones]"]
                    for s in summaries:
                        date_str = (s.get("created_at") or "")[:10]
                        sid = s.get("session_id", "session")
                        summary_txt = s.get("summary", "").strip()
                        lines.append(f"- {date_str} ({sid}): {summary_txt}")
                    sections.append("\n".join(lines))
            except Exception as exc:
                logger.debug("Failed listing episodic summaries: %s", exc)

        # --- Shelf 3: Semantic Facts with FTS5 BM25 & Decay ---
        max_facts = tier["max_facts"]
        if max_facts > 0:
            facts: List[Dict[str, Any]] = []
            try:
                if user_query and user_query.strip():
                    facts = self.repository.search_facts(query=user_query, limit=max_facts)
                if not facts:
                    facts = self.repository.list_semantic_facts(active_only=True, limit=max_facts)

                if facts:
                    lines = ["[Agent Brain - Recalled Relevant Facts]"]
                    for f in facts:
                        entity = f.get("entity", "fact")
                        attr = f.get("attribute", "info")
                        val = f.get("value", "")
                        lines.append(f"- {entity}.{attr}: {val}")
                    sections.append("\n".join(lines))
            except Exception as exc:
                logger.debug("Failed recalling semantic facts: %s", exc)

        if not sections:
            return ""

        return "\n\n".join(sections)
