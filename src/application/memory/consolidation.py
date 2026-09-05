"""
Autonomous Cognitive Memory Consolidation & Maintenance Routine [CARD-116].

Performs periodic background maintenance:
1. Evicts active facts that have decayed past the agent's retention limit.
2. Identifies duplicate (entity, attribute) facts and merges them into the freshest
   record while summing access counts to reinforce frequently referenced facts.
3. Records a structured CONSOLIDATE audit event in memory_events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository

logger = logging.getLogger(__name__)


class MemoryConsolidationRoutine:
    """Routine executing background memory maintenance and deduplication."""

    def __init__(self, repository: AgentMemoryRepository) -> None:
        self.repository = repository

    def consolidate(self, retention_days: int = 30) -> Dict[str, Any]:
        """Execute synchronous consolidation pass. Returns summary of evicted and merged counts."""
        evicted_count = self.repository.evict_expired_facts(retention_days)
        merged_count = 0

        with self.repository.get_connection() as conn:
            # 1. Identify groups with duplicates by (entity, attribute)
            duplicate_groups = conn.execute(
                """
                SELECT entity, attribute, COUNT(*) as cnt
                FROM semantic_facts
                WHERE is_active = 1
                GROUP BY entity, attribute
                HAVING cnt > 1
                """
            ).fetchall()

            for group in duplicate_groups:
                entity = group["entity"]
                attribute = group["attribute"]

                # Fetch all active facts for this (entity, attribute) ordered by recency
                facts = conn.execute(
                    """
                    SELECT id, access_count, last_accessed_at, value, confidence, category
                    FROM semantic_facts
                    WHERE entity = ? AND attribute = ? AND is_active = 1
                    ORDER BY last_accessed_at DESC, access_count DESC
                    """,
                    (entity, attribute),
                ).fetchall()

                if len(facts) <= 1:
                    continue

                keeper = facts[0]
                duplicates = facts[1:]

                total_access = int(keeper["access_count"]) + sum(int(d["access_count"]) for d in duplicates)

                # Update keeper with combined access count
                conn.execute(
                    "UPDATE semantic_facts SET access_count = ? WHERE id = ?",
                    (total_access, keeper["id"]),
                )

                # Delete duplicate records
                dup_ids = [d["id"] for d in duplicates]
                placeholders = ", ".join("?" for _ in dup_ids)
                conn.execute(
                    f"DELETE FROM semantic_facts WHERE id IN ({placeholders})",
                    dup_ids,
                )
                merged_count += len(duplicates)

            # 2. Record consolidation event in audit log
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO memory_events (id, event_type, fact_id, details, created_at)
                VALUES (?, 'CONSOLIDATE', NULL, ?, ?)
                """,
                (
                    f"evt_{uuid.uuid4().hex[:12]}",
                    json.dumps(
                        {
                            "evicted_count": evicted_count,
                            "merged_count": merged_count,
                            "retention_days": retention_days,
                        }
                    ),
                    now,
                ),
            )

        logger.info(
            "Memory consolidation completed for %s: evicted=%d, merged=%d",
            self.repository.db_path.name,
            evicted_count,
            merged_count,
        )
        return {
            "status": "ok",
            "evicted_count": evicted_count,
            "merged_count": merged_count,
            "retention_days": retention_days,
        }

    async def run_background(self, retention_days: int = 30) -> Dict[str, Any]:
        """Execute consolidation non-blockingly in a separate worker thread."""
        return await asyncio.to_thread(self.consolidate, retention_days=retention_days)
