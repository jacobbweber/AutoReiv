"""
Integration and unit tests for CARD-116: SQLite AgentMemoryRepository,
FTS5 full-text search triggers, and memory half-life decay physics.
"""

from src.infrastructure.memory.repositories.agent_memory import (
    AgentMemoryRepository,
    calculate_effective_memory_score,
)


def test_decay_formula_calculation():
    # 1. Immediate access (delta_t = 0 days), base=1.0, count=1
    score_fresh = calculate_effective_memory_score(
        base_confidence=1.0,
        days_elapsed=0.0,
        half_life_days=30.0,
        access_count=1,
    )
    # S_base * 1.0 + 0.15 * ln(1 + 1) = 1.0 + 0.15 * 0.693147 = ~1.104
    assert round(score_fresh, 3) == 1.104

    # 2. Decayed after 1 half-life (30 days), access_count=1
    score_decayed = calculate_effective_memory_score(
        base_confidence=1.0,
        days_elapsed=30.0,
        half_life_days=30.0,
        access_count=1,
    )
    # S_base * 0.5 + 0.15 * ln(2) = 0.5 + 0.10397 = ~0.604
    assert round(score_decayed, 3) == 0.604

    # 3. High access reinforcement (access_count=20), delta_t=10 days
    score_reinforced = calculate_effective_memory_score(
        base_confidence=1.0,
        days_elapsed=10.0,
        half_life_days=30.0,
        access_count=20,
    )
    assert score_reinforced > score_decayed


def test_repo_initializes_tables_and_fts(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    with repo.get_connection() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type in ('table', 'view')"
            ).fetchall()
        ]
        assert "pinned_memories" in tables
        assert "session_summaries" in tables
        assert "semantic_facts" in tables
        assert "semantic_facts_fts" in tables
        assert "memory_events" in tables


def test_pinned_memories_crud(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Add pinned memory
    p_id = repo.add_pinned_memory("Always format dates as YYYY-MM-DD.")
    assert p_id is not None

    pinned = repo.list_pinned_memories()
    assert len(pinned) == 1
    assert pinned[0]["content"] == "Always format dates as YYYY-MM-DD."

    # Update pinned memory
    repo.update_pinned_memory(p_id, "Always format dates as ISO 8601.")
    pinned = repo.list_pinned_memories()
    assert len(pinned) == 1
    assert pinned[0]["content"] == "Always format dates as ISO 8601."

    # Delete pinned memory
    repo.delete_pinned_memory(p_id)
    assert len(repo.list_pinned_memories()) == 0


def test_session_summaries_crud(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    repo.record_session_summary(
        session_id="session-101",
        summary="Configured SQLite FTS5 search for memory.",
        key_decisions=["Use pure SQLite instead of external vector database"],
        turn_count=5,
        outcome_status="completed",
    )

    summaries = repo.list_session_summaries(limit=10)
    assert len(summaries) == 1
    assert summaries[0]["session_id"] == "session-101"
    assert "Configured SQLite FTS5" in summaries[0]["summary"]
    assert any("Use pure SQLite" in d for d in summaries[0]["key_decisions"])


def test_semantic_facts_and_fts_search(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Add facts
    fact1_id = repo.add_semantic_fact(
        entity="user",
        attribute="os_platform",
        value="Windows 11 Pro with PowerShell",
        category="environment",
    )
    repo.add_semantic_fact(
        entity="user",
        attribute="preferred_language",
        value="Python 3.12 and TypeScript",
        category="user_pref",
    )

    # Search facts using FTS5 BM25 matching
    matches = repo.search_facts("PowerShell")
    assert len(matches) >= 1
    assert matches[0]["id"] == fact1_id
    assert "Windows 11 Pro with PowerShell" in matches[0]["value"]

    # Touch fact (increment access count)
    repo.touch_fact(fact1_id)
    fact1 = repo.get_semantic_fact(fact1_id)
    assert fact1 is not None
    assert fact1["access_count"] == 2

    # Update fact (triggers should sync FTS)
    repo.update_semantic_fact(
        fact_id=fact1_id,
        value="Windows 11 Enterprise with PowerShell 7",
    )
    matches = repo.search_facts("Enterprise")
    assert len(matches) >= 1
    assert matches[0]["id"] == fact1_id

    # Delete fact
    repo.delete_semantic_fact(fact1_id)
    matches_after_delete = repo.search_facts("Enterprise")
    assert len(matches_after_delete) == 0


def test_purge_all_memories(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    repo.add_pinned_memory("Rule 1")
    repo.record_session_summary("s-1", "Summary 1")
    repo.add_semantic_fact("user", "key", "val")

    assert len(repo.list_pinned_memories()) == 1
    assert len(repo.list_session_summaries()) == 1
    assert len(repo.search_facts("val")) == 1

    repo.purge_all()

    assert len(repo.list_pinned_memories()) == 0
    assert len(repo.list_session_summaries()) == 0
    assert len(repo.search_facts("val")) == 0
