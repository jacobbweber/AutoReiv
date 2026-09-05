"""
Unit tests for CARD-116: Autonomous Memory Consolidation & Maintenance Routine.
"""

from datetime import datetime, timedelta, timezone

from src.application.memory.consolidation import MemoryConsolidationRoutine
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def test_consolidation_merges_duplicate_facts(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Create two facts with same entity/attribute directly in DB
    with repo.get_connection() as conn:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO semantic_facts (id, category, entity, attribute, value, access_count, is_active, created_at, updated_at, last_accessed_at)
            VALUES ('fact_1', 'environment', 'user', 'os_platform', 'Windows 11', 2, 1, ?, ?, ?)
            """,
            (now, now, now),
        )
        conn.execute(
            """
            INSERT INTO semantic_facts (id, category, entity, attribute, value, access_count, is_active, created_at, updated_at, last_accessed_at)
            VALUES ('fact_2', 'environment', 'user', 'os_platform', 'Windows 11 Pro', 3, 1, ?, ?, ?)
            """,
            (now, now, now),
        )

    assert len(repo.list_semantic_facts(active_only=True)) == 2

    routine = MemoryConsolidationRoutine(repository=repo)
    result = routine.consolidate(retention_days=30)

    assert result["merged_count"] == 1
    remaining_facts = repo.list_semantic_facts(active_only=True)
    assert len(remaining_facts) == 1
    # Combined access count: 2 + 3 = 5
    assert remaining_facts[0]["access_count"] == 5


def test_consolidation_evicts_expired_facts(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    old_date = (datetime.now(timezone.utc) - timedelta(days=45)).isoformat()
    fresh_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    with repo.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO semantic_facts (id, category, entity, attribute, value, access_count, is_active, created_at, updated_at, last_accessed_at)
            VALUES ('old_fact', 'general', 'temp', 'old_key', 'val', 1, 1, ?, ?, ?)
            """,
            (old_date, old_date, old_date),
        )
        conn.execute(
            """
            INSERT INTO semantic_facts (id, category, entity, attribute, value, access_count, is_active, created_at, updated_at, last_accessed_at)
            VALUES ('fresh_fact', 'general', 'temp', 'fresh_key', 'val', 1, 1, ?, ?, ?)
            """,
            (fresh_date, fresh_date, fresh_date),
        )

    routine = MemoryConsolidationRoutine(repository=repo)
    result = routine.consolidate(retention_days=30)

    assert result["evicted_count"] == 1
    remaining = repo.list_semantic_facts(active_only=True)
    assert len(remaining) == 1
    assert remaining[0]["id"] == "fresh_fact"


def test_consolidation_audit_event_logged(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    routine = MemoryConsolidationRoutine(repository=repo)
    routine.consolidate(retention_days=30)

    with repo.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_events WHERE event_type = 'CONSOLIDATE'"
        ).fetchall()
        assert len(rows) >= 1
