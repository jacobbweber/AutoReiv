"""
CARD-597: Memory: don't save short-lived state, drop newest-15 fallback,
date facts, and drop content-free milestones.
"""

from datetime import datetime, timedelta, timezone

from src.application.memory.assembler import MemoryContextAssembler
from src.application.memory.extractor import (
    CandidateMemoryFact,
    MemoryExtractorService,
    is_short_lived_fact,
    parse_extraction_response,
)
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def test_is_short_lived_fact_patterns():
    # Short-lived state examples from CARD-546 and CARD-597
    assert is_short_lived_fact("user", "flashcard_review_due_today", "false") is True
    assert is_short_lived_fact("system", "srs_due_items_queued", "0") is True
    assert is_short_lived_fact("system", "queue_count", "0") is True
    assert is_short_lived_fact("user", "review_due", "none") is True
    assert is_short_lived_fact("assistant", "turn_status", "in_progress") is True
    assert is_short_lived_fact("user", "items_due_today", "5") is True
    assert is_short_lived_fact("session", "current_status", "waiting for reply") is True

    # Enduring facts must NOT be considered short-lived
    assert is_short_lived_fact("user", "preferred_language", "Python") is False
    assert is_short_lived_fact("user", "os_platform", "Windows 11") is False
    assert is_short_lived_fact("project", "database_engine", "SQLite") is False
    assert is_short_lived_fact("user", "math_mastery_level", "advanced") is False


def test_extractor_drops_short_lived_state_facts(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()
    service = MemoryExtractorService(repository=repo)

    # 1. Parsing raw response with short-lived candidate should filter it out
    raw_response = """[
        {"action": "ADD", "category": "general", "entity": "user", "attribute": "flashcard_review_due_today", "value": "false"},
        {"action": "ADD", "category": "user_pref", "entity": "user", "attribute": "favorite_editor", "value": "Neovim"}
    ]"""
    candidates = parse_extraction_response(raw_response)
    # Only the durable preference should survive parsing
    assert len(candidates) == 1
    assert candidates[0].attribute == "favorite_editor"

    # 2. Applying candidate fact directly checks short-lived guard
    c_transient = CandidateMemoryFact(
        action="ADD",
        category="general",
        entity="system",
        attribute="srs_due_items_queued",
        value="0",
    )
    res = service.apply_candidate_fact(c_transient)
    assert res["action_taken"] == "SKIPPED_SHORT_LIVED"
    assert res["fact_id"] is None

    # Verify nothing was added to the database
    all_facts = repo.list_semantic_facts()
    assert len(all_facts) == 0


def test_assembler_no_newest_15_fallback_when_no_match(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Add facts about Python and Linux
    repo.add_semantic_fact("user", "preferred_language", "Python")
    repo.add_semantic_fact("user", "os_platform", "Ubuntu Linux")

    assembler = MemoryContextAssembler(repository=repo)

    # When query matches nothing (e.g. quantum biology), no facts block should be assembled
    block = assembler.assemble(
        context_limit=65536,
        user_query="How does photosynthesis work in deep ocean vents?",
    )
    assert "Saved notes" not in block
    assert "Recalled Relevant Facts" not in block
    assert "Python" not in block
    assert "Ubuntu Linux" not in block


def test_assembler_renders_seen_dates_and_out_of_date_header(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Add fact with explicit observed_at
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    repo.add_semantic_fact(
        entity="user",
        attribute="editor",
        value="VS Code",
        observed_at=f"{today_str}T10:00:00Z",
    )

    assembler = MemoryContextAssembler(repository=repo)
    block = assembler.assemble(context_limit=65536, user_query="editor")

    # Header check
    assert "[Saved notes (may be out of date; check with tools before relying on them)]" in block
    # Date rendering check: (seen YYYY-MM-DD)
    assert f"- user.editor: VS Code (seen {today_str})" in block


def test_assembler_drops_content_free_milestones(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Add one boilerplate content-free milestone and one meaningful milestone
    repo.record_session_summary("s-1", "Turn completed with 5 durable facts compiled.", turn_count=1)
    repo.record_session_summary("s-2", "Implemented SQLite full-text search indexing.", turn_count=3)

    assembler = MemoryContextAssembler(repository=repo)
    block = assembler.assemble(context_limit=65536, user_query="irrelevant query")

    assert "[Agent Brain - Episodic Milestones]" in block
    assert "Implemented SQLite full-text search indexing." in block
    assert "Turn completed with" not in block


def test_deactivate_short_lived_facts_migration(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Directly insert short-lived fact and durable fact
    repo.add_semantic_fact("user", "flashcard_review_due_today", "false")
    repo.add_semantic_fact("system", "srs_due_items_queued", "0")
    repo.add_semantic_fact("user", "preferred_shell", "pwsh")

    deactivated_count = repo.deactivate_short_lived_facts()
    assert deactivated_count == 2

    # f1 and f2 must now be inactive
    active_facts = repo.list_semantic_facts(active_only=True)
    active_attrs = [f["attribute"] for f in active_facts]
    assert "preferred_shell" in active_attrs
    assert "flashcard_review_due_today" not in active_attrs
    assert "srs_due_items_queued" not in active_attrs


def test_expired_facts_not_returned_by_search(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    past_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    future_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Expired fact
    repo.add_semantic_fact(
        entity="session",
        attribute="temp_auth_token",
        value="token_expired_123",
        expires_at=past_date,
    )
    # Valid unexpired fact
    repo.add_semantic_fact(
        entity="session",
        attribute="active_cluster",
        value="cluster_alpha_node",
        expires_at=future_date,
    )

    search_expired = repo.search_facts("token_expired_123")
    assert len(search_expired) == 0

    search_valid = repo.search_facts("cluster_alpha_node")
    assert len(search_valid) == 1
    assert search_valid[0]["value"] == "cluster_alpha_node"
