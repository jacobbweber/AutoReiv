"""
Episodic Fact Memory Repository Mixin [REQ-MEMORY-003, REQ-EPISODIC-001].
"""

import uuid
from typing import Any, Dict, List, Optional


class FactRepositoryMixin:
    """Methods for storing, retrieving, and tokenized searching of episodic facts."""

    def save_fact(
        self,
        entity: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert an episodic fact record into SQLite."""
        conn = self._get_connection()
        fact_id = str(uuid.uuid4())
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO episodic_facts (id, entity, key, value, confidence, source_session_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(entity, key) DO UPDATE SET
                    value = excluded.value,
                    confidence = excluded.confidence,
                    source_session_id = excluded.source_session_id,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (fact_id, entity, key, value, confidence, source_session_id),
            )
            conn.commit()
            return {
                "id": fact_id,
                "entity": entity,
                "key": key,
                "value": value,
                "confidence": confidence,
                "source_session_id": source_session_id,
            }
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_facts(self, entity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve episodic facts filtered optionally by entity."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if entity:
                cur.execute(
                    "SELECT id, entity, key, value, confidence, source_session_id, updated_at FROM episodic_facts WHERE entity = ? ORDER BY key ASC;",
                    (entity,),
                )
            else:
                cur.execute(
                    "SELECT id, entity, key, value, confidence, source_session_id, updated_at FROM episodic_facts ORDER BY entity ASC, key ASC;"
                )
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "entity": r["entity"],
                    "key": r["key"],
                    "value": r["value"],
                    "confidence": r["confidence"],
                    "source_session_id": r["source_session_id"],
                    "updated_at": str(r["updated_at"]),
                }
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def search_facts(
        self,
        query: str = "",
        entity: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search episodic facts using tokenized substring matching and confidence filtering [REQ-EPISODIC-001].
        """
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cleaned_query = (query or "").strip().lower()
            tokens = [t for t in cleaned_query.split() if len(t) >= 2]

            conditions = ["confidence >= ?"]
            params: List[Any] = [min_confidence]

            if entity:
                conditions.append("LOWER(entity) = ?")
                params.append(entity.strip().lower())

            if tokens:
                token_clauses = []
                for token in tokens:
                    token_clauses.append("(LOWER(entity) LIKE ? OR LOWER(key) LIKE ? OR LOWER(value) LIKE ?)")
                    wildcard = f"%{token}%"
                    params.extend([wildcard, wildcard, wildcard])
                conditions.append(f"({' OR '.join(token_clauses)})")

            where_sql = " WHERE " + " AND ".join(conditions)
            sql = f"""
                SELECT id, entity, key, value, confidence, source_session_id, updated_at
                FROM episodic_facts
                {where_sql}
                ORDER BY confidence DESC, updated_at DESC
                LIMIT ?;
            """
            params.append(limit)

            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [
                {
                    "id": r["id"],
                    "entity": r["entity"],
                    "key": r["key"],
                    "value": r["value"],
                    "confidence": r["confidence"],
                    "source_session_id": r["source_session_id"],
                    "updated_at": str(r["updated_at"]),
                }
                for r in rows
            ]
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_fact(self, entity: str, key: str) -> bool:
        """Delete an episodic fact record by entity and key."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM episodic_facts WHERE entity = ? AND key = ?;", (entity, key))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()
