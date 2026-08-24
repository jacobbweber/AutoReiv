"""
Episodic Memory Skill [REQ-MEMORY-003].
Provides tools for saving and retrieving cross-session user/environment facts.
"""

from typing import Any, Dict, List, Optional

from src.infrastructure.memory.sqlite_store import SQLiteStateStore


class EpisodicMemorySkill:
    """Skill exposing episodic memory fact storage and retrieval tools."""

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

    def delete_fact(self, entity: str, key: str) -> Dict[str, Any]:
        """Delete an episodic fact."""
        deleted = self.store.delete_fact(entity=entity, key=key)
        return {"status": "deleted" if deleted else "not_found", "entity": entity, "key": key}
