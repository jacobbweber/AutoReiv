"""
Dedicated SQLite Cognitive Memory Brain Repository [CARD-116].

Per-agent physical database (<agent_slug>_memory.db) maintaining:
- Shelf 1: Pinned Directives (pinned_memories)
- Shelf 2: Episodic Summaries (session_summaries)
- Shelf 3: Semantic Facts with FTS5 BM25 search & exponential decay (semantic_facts)
- Audit & consolidation event log (memory_events)
"""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

from src.infrastructure.data.resolver import resolve_agent_memory_path


def calculate_effective_memory_score(
    base_confidence: float,
    days_elapsed: float,
    half_life_days: float = 30.0,
    access_count: int = 1,
    alpha: float = 0.15,
) -> float:
    """Calculate effective memory score with half-life decay and access reinforcement.

    Formula: S_eff = S_base * e^(-lambda * delta_t) + alpha * ln(1 + N_access)
    where lambda = ln(2) / half_life_days.
    """
    if half_life_days <= 0:
        half_life_days = 30.0
    decay_rate = math.log(2) / half_life_days
    decay_factor = math.exp(-decay_rate * max(0.0, days_elapsed))
    reinforcement = alpha * math.log(1 + max(1, access_count))
    return (base_confidence * decay_factor) + reinforcement


class AgentMemoryRepository:
    """Repository managing an individual agent's dedicated cognitive memory database."""

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        agent_id: Optional[str] = None,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        if db_path is not None:
            self.db_path = Path(db_path)
        elif agent_id is not None:
            self.db_path = resolve_agent_memory_path(agent_id, data_dir=data_dir)
        else:
            raise ValueError("Either db_path or agent_id must be provided to AgentMemoryRepository.")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            conn.execute("PRAGMA foreign_keys = ON;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Create all tables, FTS5 virtual tables, triggers, and indices."""
        with self.get_connection() as conn:
            conn.executescript(
                """
                -- Shelf 1: Pinned Directives & Non-Decaying Anchor Facts
                CREATE TABLE IF NOT EXISTS pinned_memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );

                -- Shelf 2: Episodic Memory (Rolling Session & Job Summaries)
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_decisions TEXT,
                    turn_count INTEGER NOT NULL DEFAULT 1,
                    outcome_status TEXT NOT NULL DEFAULT 'completed',
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );
                CREATE INDEX IF NOT EXISTS idx_session_summaries_created ON session_summaries(created_at DESC);

                -- Shelf 3: Semantic Facts (Atomic Extracted Facts with Decay Dynamics)
                CREATE TABLE IF NOT EXISTS semantic_facts (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL DEFAULT 'general',
                    entity TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    access_count INTEGER NOT NULL DEFAULT 1,
                    decay_half_life_days REAL NOT NULL DEFAULT 30.0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                    last_accessed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );
                CREATE INDEX IF NOT EXISTS idx_semantic_facts_entity_attr ON semantic_facts(entity, attribute);
                CREATE INDEX IF NOT EXISTS idx_semantic_facts_active ON semantic_facts(is_active);

                -- Full-Text Search Virtual Table (FTS5 BM25 Indexing)
                CREATE VIRTUAL TABLE IF NOT EXISTS semantic_facts_fts USING fts5(
                    id UNINDEXED,
                    category,
                    entity,
                    attribute,
                    value,
                    tokenize = 'porter unicode61'
                );

                -- Triggers for automatic FTS synchronization
                CREATE TRIGGER IF NOT EXISTS trg_semantic_facts_ai AFTER INSERT ON semantic_facts BEGIN
                    INSERT INTO semantic_facts_fts(id, category, entity, attribute, value)
                    VALUES (new.id, new.category, new.entity, new.attribute, new.value);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_semantic_facts_au AFTER UPDATE ON semantic_facts BEGIN
                    UPDATE semantic_facts_fts SET
                        category = new.category,
                        entity = new.entity,
                        attribute = new.attribute,
                        value = new.value
                    WHERE id = old.id;
                END;

                CREATE TRIGGER IF NOT EXISTS trg_semantic_facts_ad AFTER DELETE ON semantic_facts BEGIN
                    DELETE FROM semantic_facts_fts WHERE id = old.id;
                END;

                -- Audit & Maintenance Log
                CREATE TABLE IF NOT EXISTS memory_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    fact_id TEXT,
                    details TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                );
                """
            )


    # --- Shelf 1: Pinned Memories ---

    def add_pinned_memory(self, content: str, memory_id: Optional[str] = None) -> str:
        mid = memory_id or f"pin_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO pinned_memories (id, content, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    updated_at = excluded.updated_at
                """,
                (mid, content.strip(), now, now),
            )
        return mid

    def list_pinned_memories(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT id, content, created_at, updated_at FROM pinned_memories ORDER BY created_at ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def update_pinned_memory(self, memory_id: str, content: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                "UPDATE pinned_memories SET content = ?, updated_at = ? WHERE id = ?",
                (content.strip(), now, memory_id),
            )
            return cur.rowcount > 0

    def delete_pinned_memory(self, memory_id: str) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM pinned_memories WHERE id = ?", (memory_id,))
            return cur.rowcount > 0

    # --- Shelf 2: Episodic Session Summaries ---

    def record_session_summary(
        self,
        session_id: str,
        summary: str,
        key_decisions: Optional[List[str]] = None,
        turn_count: int = 1,
        outcome_status: str = "completed",
        summary_id: Optional[str] = None,
    ) -> str:
        sid = summary_id or f"sum_{uuid.uuid4().hex[:12]}"
        decisions_json = json.dumps(key_decisions or [])
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO session_summaries (id, session_id, summary, key_decisions, turn_count, outcome_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (sid, session_id, summary.strip(), decisions_json, turn_count, outcome_status, now),
            )
        return sid

    def list_session_summaries(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, session_id, summary, key_decisions, turn_count, outcome_status, created_at
                FROM session_summaries
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            summaries = []
            for row in rows:
                item = dict(row)
                try:
                    item["key_decisions"] = json.loads(item["key_decisions"] or "[]")
                except (json.JSONDecodeError, TypeError):
                    item["key_decisions"] = []
                summaries.append(item)
            return summaries

    # --- Shelf 3: Semantic Facts with FTS5 & Decay ---

    def add_semantic_fact(
        self,
        entity: str,
        attribute: str,
        value: str,
        category: str = "general",
        confidence: float = 1.0,
        decay_half_life_days: float = 30.0,
        fact_id: Optional[str] = None,
    ) -> str:
        fid = fact_id or f"fact_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO semantic_facts (
                    id, category, entity, attribute, value, confidence, access_count,
                    decay_half_life_days, is_active, created_at, updated_at, last_accessed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, 1, ?, ?, ?)
                """,
                (
                    fid,
                    category.strip(),
                    entity.strip(),
                    attribute.strip(),
                    value.strip(),
                    confidence,
                    decay_half_life_days,
                    now,
                    now,
                    now,
                ),
            )
            # Log event
            conn.execute(
                "INSERT INTO memory_events (id, event_type, fact_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    f"evt_{uuid.uuid4().hex[:12]}",
                    "ADD",
                    fid,
                    json.dumps({"entity": entity, "attribute": attribute, "value": value}),
                    now,
                ),
            )
        return fid

    def get_semantic_fact(self, fact_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM semantic_facts WHERE id = ?",
                (fact_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_semantic_facts(self, active_only: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM semantic_facts"
            params: List[Any] = []
            if active_only:
                query += " WHERE is_active = 1"
            query += " ORDER BY last_accessed_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    def update_semantic_fact(
        self,
        fact_id: str,
        value: Optional[str] = None,
        confidence: Optional[float] = None,
        category: Optional[str] = None,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        updates = ["updated_at = ?"]
        params: List[Any] = [now]
        if value is not None:
            updates.append("value = ?")
            params.append(value.strip())
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        if category is not None:
            updates.append("category = ?")
            params.append(category.strip())
        params.append(fact_id)

        with self.get_connection() as conn:
            cur = conn.execute(
                f"UPDATE semantic_facts SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            if cur.rowcount > 0:
                conn.execute(
                    "INSERT INTO memory_events (id, event_type, fact_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        f"evt_{uuid.uuid4().hex[:12]}",
                        "UPDATE",
                        fact_id,
                        json.dumps({"value": value, "confidence": confidence}),
                        now,
                    ),
                )
                return True
            return False

    def touch_fact(self, fact_id: str) -> bool:
        """Increment access count and touch last_accessed_at timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                UPDATE semantic_facts
                SET access_count = access_count + 1,
                    last_accessed_at = ?
                WHERE id = ?
                """,
                (now, fact_id),
            )
            return cur.rowcount > 0

    def delete_semantic_fact(self, fact_id: str, permanent: bool = True) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            if permanent:
                cur = conn.execute("DELETE FROM semantic_facts WHERE id = ?", (fact_id,))
            else:
                cur = conn.execute(
                    "UPDATE semantic_facts SET is_active = 0, updated_at = ? WHERE id = ?",
                    (now, fact_id),
                )
            if cur.rowcount > 0:
                conn.execute(
                    "INSERT INTO memory_events (id, event_type, fact_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (f"evt_{uuid.uuid4().hex[:12]}", "DELETE", fact_id, json.dumps({"permanent": permanent}), now),
                )
                return True
            return False

    def search_facts(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search active semantic facts via FTS5 BM25 relevance scored with decay physics."""
        cleaned_query = "".join(c if c.isalnum() or c in " _-" else " " for c in query).strip()
        if not cleaned_query:
            return []

        # Split words for prefix matching (e.g. 'PowerShell*' matches 'powershell')
        terms = [f'"{term}"*' for term in cleaned_query.split() if term]
        if not terms:
            return []
        fts_expr = " OR ".join(terms)

        with self.get_connection() as conn:
            sql = """
                SELECT
                    sf.id, sf.category, sf.entity, sf.attribute, sf.value,
                    sf.confidence, sf.access_count, sf.decay_half_life_days,
                    sf.created_at, sf.updated_at, sf.last_accessed_at,
                    bm25(semantic_facts_fts) AS bm25_rank
                FROM semantic_facts sf
                JOIN semantic_facts_fts fts ON sf.id = fts.id
                WHERE sf.is_active = 1
                  AND semantic_facts_fts MATCH ?
                ORDER BY bm25_rank ASC
                LIMIT 50
            """
            rows = conn.execute(sql, (fts_expr,)).fetchall()

            now = datetime.now(timezone.utc)
            results = []
            for row in rows:
                item = dict(row)
                # Parse last_accessed_at for decay calculation
                try:
                    last_acc_dt = datetime.fromisoformat(item["last_accessed_at"].replace("Z", "+00:00"))
                    if last_acc_dt.tzinfo is None:
                        last_acc_dt = last_acc_dt.replace(tzinfo=timezone.utc)
                    days_elapsed = max(0.0, (now - last_acc_dt).total_seconds() / 86400.0)
                except Exception:
                    days_elapsed = 0.0

                decay_score = calculate_effective_memory_score(
                    base_confidence=item["confidence"],
                    days_elapsed=days_elapsed,
                    half_life_days=item["decay_half_life_days"],
                    access_count=item["access_count"],
                )
                # BM25 in SQLite is negative (lower = better match)
                # Combined score: -bm25 * (1.0 + 0.2 * decay_score)
                bm25_val = abs(item.get("bm25_rank") or 1.0)
                final_score = bm25_val * (1.0 + 0.2 * decay_score)

                item["decay_score"] = decay_score
                item["final_score"] = final_score

                if final_score >= min_score:
                    results.append(item)

            # Sort by highest combined relevance score
            results.sort(key=lambda x: x["final_score"], reverse=True)
            return results[:limit]

    def purge_all(self) -> None:
        """Purge all cognitive memories (Shelf 1, Shelf 2, Shelf 3, and events)."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM pinned_memories;")
            conn.execute("DELETE FROM session_summaries;")
            conn.execute("DELETE FROM semantic_facts;")
            conn.execute("DELETE FROM semantic_facts_fts;")
            conn.execute("DELETE FROM memory_events;")
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO memory_events (id, event_type, fact_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (f"evt_{uuid.uuid4().hex[:12]}", "PURGE", None, json.dumps({"action": "purge_all"}), now),
            )

    def evict_expired_facts(self, retention_days: int) -> int:
        """Evict active facts whose last access exceeds the retention days limit."""
        if retention_days <= 0:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                DELETE FROM semantic_facts
                WHERE last_accessed_at < ?
                """,
                (cutoff,),
            )
            count = cur.rowcount
            if count > 0:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO memory_events (id, event_type, fact_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (
                        f"evt_{uuid.uuid4().hex[:12]}",
                        "EXPIRE",
                        None,
                        json.dumps({"retention_days": retention_days, "evicted_count": count}),
                        now,
                    ),
                )
            return count
