"""
Episodic Memory Skill [REQ-MEMORY-003, REQ-EPISODIC-001 - REQ-EPISODIC-003].
Provides tools for saving, searching, and auto-recalling cross-session user/environment facts.
"""

from typing import Any, Dict, List, Optional

from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def render_memory_context(facts: List[Dict[str, Any]]) -> str:
    """
    Renders episodic facts into a markdown context block for agent system prompts [REQ-EPISODIC-002].
    """
    if not facts:
        return ""

    lines = ["[Episodic Memory - Recalled Facts]"]
    for f in facts:
        entity = f.get("entity", "general")
        key = f.get("key", "fact")
        val = f.get("value", "")
        conf = f.get("confidence", 1.0)
        lines.append(f"- {entity}.{key}: {val} (confidence: {conf:.2f})")

    return "\n".join(lines)


class EpisodicMemorySkill:
    """Skill exposing episodic memory fact storage, search, and retrieval tools."""

    def __init__(self, store: SQLiteStateStore):
        self.store = store

    def save_fact(
        self,
        entity: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save or update a cross-session fact."""
        fact = self.store.save_fact(
            entity=entity,
            key=key,
            value=value,
            confidence=confidence,
            source_session_id=source_session_id,
        )
        return {"status": "saved", "fact": fact}

    def get_facts(self, entity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query stored episodic facts."""
        return self.store.get_facts(entity=entity)

    def search_facts(
        self,
        query: str = "",
        entity: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search stored episodic facts matching query or entity [REQ-EPISODIC-001]."""
        return self.store.search_facts(query=query, entity=entity, min_confidence=min_confidence, limit=limit)

    def delete_fact(self, entity: str, key: str) -> Dict[str, Any]:
        """Delete an episodic fact."""
        deleted = self.store.delete_fact(entity=entity, key=key)
        return {"status": "deleted" if deleted else "not_found", "entity": entity, "key": key}

    def auto_recall(
        self,
        prompt: str,
        entity: Optional[str] = None,
        min_confidence: float = 0.6,
        limit: int = 5,
    ) -> str:
        """
        Auto-recalls relevant facts matching the user's prompt and returns a formatted context block [REQ-EPISODIC-002].
        """
        facts = self.store.search_facts(query=prompt, entity=entity, min_confidence=min_confidence, limit=limit)
        return render_memory_context(facts)
