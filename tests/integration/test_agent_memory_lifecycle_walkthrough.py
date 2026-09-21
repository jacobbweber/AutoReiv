"""
End-to-end integration lifecycle test suite and stress audit for Agent Cognitive Memory [CARD-405].

Validates:
- [REQ-405-001] Strict Per-Agent Isolation (Developer vs Tutor memory boundary)
- [REQ-405-002] Multi-Tier Memory Context Assembly (Tight, Standard, Broad budgets)
- [REQ-405-003] Atomic Conflict Resolution (ADD, UPDATE, BUMP, DELETE)
- [REQ-405-004] FTS5 BM25 Relevance with Decay Physics
- [REQ-405-005] Small-Talk Trivial Turn Bypass (Negative Assertion)
- SQLite WAL durability and server restart / re-open persistence
- Agent Memory REST APIs (GET, search query, DELETE fact, DELETE / POST purge)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.memory.agent_memory_tools import AgentMemoryTools
from src.application.memory.assembler import MemoryContextAssembler, get_budget_tier
from src.application.memory.extractor import (
    CandidateMemoryFact,
    MemoryExtractorService,
    should_skip_extraction,
)
from src.domain.kernel.models import AgentProfile
from src.infrastructure.memory.repositories.agent_memory import (
    AgentMemoryRepository,
    calculate_effective_memory_score,
)
from src.web.app import create_app

# ============================================================================
# 1. [REQ-405-001] Strict Per-Agent Isolation
# ============================================================================


def test_strict_per_agent_isolation(tmp_path):
    """[REQ-405-001] Two agents store data in completely separate DBs with zero bleed."""
    data_dir = tmp_path / "user_data"

    # Instantiate Developer and Tutor repositories
    repo_dev = AgentMemoryRepository(agent_id="developer", data_dir=data_dir)
    repo_tutor = AgentMemoryRepository(agent_id="tutor", data_dir=data_dir)

    repo_dev.initialize_schema()
    repo_tutor.initialize_schema()

    # Verify physical file isolation
    assert repo_dev.db_path != repo_tutor.db_path
    assert "developer" in str(repo_dev.db_path)
    assert "tutor" in str(repo_tutor.db_path)

    # Developer stores backend preferences
    dev_fact_id = repo_dev.add_semantic_fact(
        entity="developer_env",
        attribute="language",
        value="Python 3.12",
        category="environment",
    )
    repo_dev.add_pinned_memory("Always write typed code.")
    repo_dev.record_session_summary("s-dev-1", "Built REST endpoints.")

    # Tutor stores pedagogical styles
    tutor_fact_id = repo_tutor.add_semantic_fact(
        entity="learner",
        attribute="style",
        value="Socratic questioning",
        category="user_pref",
    )
    repo_tutor.add_pinned_memory("Never give direct answers immediately.")
    repo_tutor.record_session_summary("s-tut-1", "Reviewed calculus concepts.")

    # Assert Developer cannot see Tutor facts
    dev_facts = repo_dev.list_semantic_facts()
    assert len(dev_facts) == 1
    assert dev_facts[0]["id"] == dev_fact_id
    assert dev_facts[0]["value"] == "Python 3.12"
    assert repo_dev.get_semantic_fact(tutor_fact_id) is None
    assert len(repo_dev.search_facts("Socratic")) == 0

    # Assert Tutor cannot see Developer facts
    tutor_facts = repo_tutor.list_semantic_facts()
    assert len(tutor_facts) == 1
    assert tutor_facts[0]["id"] == tutor_fact_id
    assert tutor_facts[0]["value"] == "Socratic questioning"
    assert repo_tutor.get_semantic_fact(dev_fact_id) is None
    assert len(repo_tutor.search_facts("Python")) == 0

    # Purging Developer memory does not touch Tutor
    repo_dev.purge_all()
    assert len(repo_dev.list_semantic_facts()) == 0
    assert len(repo_dev.list_pinned_memories()) == 0
    assert len(repo_dev.list_session_summaries()) == 0

    # Tutor remains completely intact
    assert len(repo_tutor.list_semantic_facts()) == 1
    assert len(repo_tutor.list_pinned_memories()) == 1
    assert len(repo_tutor.list_session_summaries()) == 1


# ============================================================================
# 2. [REQ-405-002] Multi-Tier Memory Context Assembly
# ============================================================================


def test_multi_tier_memory_context_assembly(tmp_path):
    """[REQ-405-002] Multi-tier prompt assembly respects budget caps for tight, standard, broad."""
    repo = AgentMemoryRepository(agent_id="test-bot", data_dir=tmp_path)
    repo.initialize_schema()

    # Seed Shelf 1: Pinned
    repo.add_pinned_memory("Rule: Be deterministic.")
    repo.add_pinned_memory("Rule: No shadow levers.")

    # Seed Shelf 2: Episodic Summaries
    for i in range(5):
        repo.record_session_summary(
            session_id=f"sess-{i}",
            summary=f"Completed milestone step {i} with verified tests.",
        )

    # Seed Shelf 3: Semantic Facts
    for i in range(20):
        repo.add_semantic_fact(
            entity="system",
            attribute=f"config_param_{i}",
            value=f"value_{i}_active",
            category="environment",
        )

    assembler = MemoryContextAssembler(repository=repo)

    # 1. Tight tier (<= 8k tokens): max 3 facts, 0 summaries
    tight_tier = get_budget_tier(8192)
    assert tight_tier["tier_name"] == "tight"
    assert tight_tier["max_summaries"] == 0
    assert tight_tier["max_facts"] == 3

    block_tight = assembler.assemble(context_limit=4096, user_query="config")
    assert "[Agent Brain - Pinned Directives]" in block_tight
    assert "Rule: Be deterministic." in block_tight
    assert "[Agent Brain - Episodic Milestones]" not in block_tight  # Omitted on tight tier
    assert "[Agent Brain - Recalled Relevant Facts]" in block_tight
    # Exactly 3 facts included
    tight_fact_lines = [line for line in block_tight.splitlines() if line.startswith("- system.config_param_")]
    assert len(tight_fact_lines) == 3

    # 2. Standard tier (8k - 32k tokens): max 6 facts, 1 summary
    std_tier = get_budget_tier(16384)
    assert std_tier["tier_name"] == "standard"
    assert std_tier["max_summaries"] == 1
    assert std_tier["max_facts"] == 6

    block_std = assembler.assemble(context_limit=16384, user_query="config")
    assert "[Agent Brain - Pinned Directives]" in block_std
    assert "[Agent Brain - Episodic Milestones]" in block_std
    std_summary_lines = [line for line in block_std.splitlines() if "(sess-" in line]
    assert len(std_summary_lines) == 1
    std_fact_lines = [line for line in block_std.splitlines() if line.startswith("- system.config_param_")]
    assert len(std_fact_lines) == 6

    # 3. Broad tier (> 32k tokens): max 15 facts, 3 summaries
    broad_tier = get_budget_tier(65536)
    assert broad_tier["tier_name"] == "broad"
    assert broad_tier["max_summaries"] == 3
    assert broad_tier["max_facts"] == 15

    block_broad = assembler.assemble(context_limit=65536, user_query="config")
    assert "[Agent Brain - Pinned Directives]" in block_broad
    assert "[Agent Brain - Episodic Milestones]" in block_broad
    broad_summary_lines = [line for line in block_broad.splitlines() if "(sess-" in line]
    assert len(broad_summary_lines) == 3
    broad_fact_lines = [line for line in block_broad.splitlines() if line.startswith("- system.config_param_")]
    assert len(broad_fact_lines) == 15


# ============================================================================
# 3. [REQ-405-003] Atomic Conflict Resolution
# ============================================================================


def test_atomic_conflict_resolution(tmp_path):
    """[REQ-405-003] Atomic conflict resolution: ADD, duplicate BUMP, update UPDATE, and DELETE."""
    repo = AgentMemoryRepository(agent_id="conflict-bot", data_dir=tmp_path)
    repo.initialize_schema()
    extractor = MemoryExtractorService(repository=repo)

    # 1. Fresh ADD
    cand1 = CandidateMemoryFact(
        action="ADD",
        entity="user",
        attribute="favorite_shell",
        value="pwsh",
        category="user_pref",
    )
    res1 = extractor.apply_candidate_fact(cand1)
    assert res1["action_taken"] == "ADD"
    fact1_id = res1["fact_id"]
    fact1 = repo.get_semantic_fact(fact1_id)
    assert fact1["value"] == "pwsh"
    assert fact1["access_count"] == 1

    # 2. Identical ADD -> promoted to BUMP (no duplicate created!)
    cand_dup = CandidateMemoryFact(
        action="ADD",
        entity="user",
        attribute="favorite_shell",
        value="pwsh",
        category="user_pref",
    )
    res_dup = extractor.apply_candidate_fact(cand_dup)
    assert res_dup["action_taken"] == "BUMP"
    assert res_dup["fact_id"] == fact1_id

    # Verify access_count was incremented to 2, and total facts is still 1
    all_facts = repo.list_semantic_facts()
    assert len(all_facts) == 1
    assert all_facts[0]["access_count"] == 2

    # 3. Conflicting ADD with new value -> promoted to UPDATE in place
    cand_new_val = CandidateMemoryFact(
        action="ADD",
        entity="user",
        attribute="favorite_shell",
        value="zsh",
        category="user_pref",
    )
    res_upd = extractor.apply_candidate_fact(cand_new_val)
    assert res_upd["action_taken"] == "UPDATE"
    assert res_upd["fact_id"] == fact1_id

    # Verify value changed in place, total facts still 1
    all_facts_after = repo.list_semantic_facts()
    assert len(all_facts_after) == 1
    assert all_facts_after[0]["value"] == "zsh"

    # 4. Explicit UPDATE action
    cand_explicit_upd = CandidateMemoryFact(
        action="UPDATE",
        entity="user",
        attribute="favorite_shell",
        value="bash",
        category="user_pref",
        confidence=0.9,
    )
    res_exp_upd = extractor.apply_candidate_fact(cand_explicit_upd)
    assert res_exp_upd["action_taken"] == "UPDATE"
    updated_fact = repo.get_semantic_fact(fact1_id)
    assert updated_fact["value"] == "bash"
    assert updated_fact["confidence"] == 0.9

    # 5. Explicit BUMP action
    cand_bump = CandidateMemoryFact(
        action="BUMP",
        entity="user",
        attribute="favorite_shell",
    )
    res_bump = extractor.apply_candidate_fact(cand_bump)
    assert res_bump["action_taken"] == "BUMP"
    bumped_fact = repo.get_semantic_fact(fact1_id)
    assert bumped_fact["access_count"] == 3

    # 6. Explicit DELETE action
    cand_del = CandidateMemoryFact(
        action="DELETE",
        entity="user",
        attribute="favorite_shell",
    )
    res_del = extractor.apply_candidate_fact(cand_del)
    assert res_del["action_taken"] == "DELETE"

    # Fact is soft deleted: is_active = 0, excluded from active list and searches
    assert len(repo.list_semantic_facts(active_only=True)) == 0
    assert len(repo.search_facts("bash")) == 0


# ============================================================================
# 4. [REQ-405-004] FTS5 BM25 Relevance with Decay Physics
# ============================================================================


def test_fts5_bm25_relevance_and_decay_physics(tmp_path):
    """[REQ-405-004] FTS5 search combines text relevance with exponential decay and access count."""
    repo = AgentMemoryRepository(agent_id="decay-bot", data_dir=tmp_path)
    repo.initialize_schema()

    # Fact A: touched frequently (high access count)
    id_a = repo.add_semantic_fact(
        entity="project",
        attribute="testing_framework",
        value="pytest with async plugins",
        category="domain",
        confidence=1.0,
        decay_half_life_days=30.0,
    )
    for _ in range(10):
        repo.touch_fact(id_a)

    # Fact B: stale fact from 90 days ago, accessed only once
    id_b = repo.add_semantic_fact(
        entity="project",
        attribute="legacy_framework",
        value="pytest old runner",
        category="domain",
        confidence=1.0,
        decay_half_life_days=30.0,
    )

    # Manually backdate Fact B's last_accessed_at to 90 days ago (3 half-lives: decay factor ~0.125)
    stale_ts = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    with repo.get_connection() as conn:
        conn.execute("UPDATE semantic_facts SET last_accessed_at = ? WHERE id = ?", (stale_ts, id_b))

    # Verify formula directly:
    score_a = calculate_effective_memory_score(
        base_confidence=1.0,
        days_elapsed=0.0,
        half_life_days=30.0,
        access_count=11,
    )
    score_b = calculate_effective_memory_score(
        base_confidence=1.0,
        days_elapsed=90.0,
        half_life_days=30.0,
        access_count=1,
    )
    # score_a: 1.0*1.0 + 0.15*ln(12) ≈ 1.0 + 0.3727 = 1.3727
    # score_b: 1.0*(2^-3) + 0.15*ln(2) ≈ 0.125 + 0.1039 = 0.2289
    assert score_a > score_b

    # Search for "pytest": both match FTS5, but Fact A must rank first due to decay physics
    results = repo.search_facts("pytest", limit=10)
    assert len(results) == 2
    assert results[0]["id"] == id_a
    assert results[1]["id"] == id_b
    assert results[0]["final_score"] > results[1]["final_score"]


# ============================================================================
# 5. [REQ-405-005] Small-Talk Trivial Turn Bypass (Negative Assertion)
# ============================================================================


@pytest.mark.asyncio
async def test_trivial_turn_bypass_negative_assertion(tmp_path):
    """[REQ-405-005] Small talk / trivial utterances strictly bypass extraction without LLM calls."""
    trivial_utterances = [
        "ok",
        "okay",
        "k",
        "thanks",
        "thank you",
        "thank you!",
        "thanks.",
        "hi",
        "hello there",
        "yes",
        "no",
        "yep",
        "good morning",
        "cool",
        "awesome",
        "perfect",
        "understood",
        "done",
    ]

    for utterance in trivial_utterances:
        assert should_skip_extraction(utterance) is True, f"Expected '{utterance}' to be skipped"

    substantive_utterances = [
        "I want to deploy to production tomorrow.",
        "My database port is 5432.",
        "Please use PowerShell for all automation scripts.",
        "Let's switch from React to Vue.",
    ]
    for utterance in substantive_utterances:
        assert should_skip_extraction(utterance) is False, f"Expected '{utterance}' NOT to be skipped"

    # Verify process_turn makes ZERO LLM calls when given trivial text
    mock_llm = AsyncMock()
    repo = AgentMemoryRepository(agent_id="bypass-bot", data_dir=tmp_path)
    repo.initialize_schema()
    service = MemoryExtractorService(repository=repo, llm_service=mock_llm)

    res = await service.process_turn(user_text="thanks", assistant_text="You're welcome!")
    assert res == []
    mock_llm.generate.assert_not_called()

    # Verify LLM is called when substantive text is passed
    mock_llm.generate.return_value = '[]'
    res_sub = await service.process_turn(
        user_text="I prefer PostgreSQL over MySQL for high-load systems.",
        assistant_text="Noted.",
    )
    assert res_sub == []
    mock_llm.generate.assert_called_once()


# ============================================================================
# 6. SQLite WAL Durability & Server Restart Survival
# ============================================================================


def test_sqlite_wal_durability_and_restart_survival(tmp_path):
    """Verify that all 3 shelves and FTS5 indexes survive complete repository re-instantiation."""
    db_file = tmp_path / "persistent_agent_memory.db"

    # 1. Instance 1 writes data
    repo1 = AgentMemoryRepository(db_path=db_file)
    repo1.initialize_schema()
    pin_id = repo1.add_pinned_memory("Permanent Ground Rule: Keep schemas normalized.")
    sum_id = repo1.record_session_summary("sess-persist", "Migrated database cleanly.")
    fact_id = repo1.add_semantic_fact(
        entity="cluster",
        attribute="node_count",
        value="12 workers",
        category="environment",
    )

    # Simulate reboot: completely discard repo1, create repo2 on the same db path
    del repo1

    repo2 = AgentMemoryRepository(db_path=db_file)
    repo2.initialize_schema()  # Idempotent re-initialization

    # Verify Shelf 1 survived
    pins = repo2.list_pinned_memories()
    assert len(pins) == 1
    assert pins[0]["id"] == pin_id
    assert "Permanent Ground Rule" in pins[0]["content"]

    # Verify Shelf 2 survived
    sums = repo2.list_session_summaries()
    assert len(sums) == 1
    assert sums[0]["id"] == sum_id
    assert sums[0]["session_id"] == "sess-persist"

    # Verify Shelf 3 and FTS5 survived
    facts = repo2.list_semantic_facts()
    assert len(facts) == 1
    assert facts[0]["id"] == fact_id
    assert facts[0]["value"] == "12 workers"

    search_res = repo2.search_facts("cluster")
    assert len(search_res) == 1
    assert search_res[0]["id"] == fact_id


# ============================================================================
# 7. Agent Memory REST APIs & Brain Drawer Contract
# ============================================================================


@pytest.mark.asyncio
async def test_agent_memory_rest_api_contract(tmp_path, monkeypatch):
    """Verify REST API outputs matching frontend Forge Brain Drawer expectations."""
    monkeypatch.setenv("AUTOREIV_DATA_DIR", str(tmp_path))
    app = create_app()

    # Register an agent
    registry = app.state.registry
    agent_id = "brain-demo-agent"
    profile = AgentProfile(
        id=agent_id,
        name="Brain Demo Agent",
        description="Demo agent for brain tests",
        system_prompt="Test agent",
        memory_enabled=True,
        memory_retention_days=60,
        pinned_memory="Always use strict types.",
    )
    registry.register_custom_agent(profile)

    # Seed memories via repository
    repo = AgentMemoryRepository(agent_id=agent_id, data_dir=tmp_path)
    repo.initialize_schema()
    fact_id = repo.add_semantic_fact(
        entity="user",
        attribute="editor",
        value="Neovim",
        category="user_pref",
        confidence=0.95,
    )
    repo.record_session_summary("sess-demo-99", "Configured plugins and keymaps.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/agents/{id}/memory
        get_res = await client.get(f"/api/agents/{agent_id}/memory")
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["status"] == "ok"
        assert data["agent_id"] == agent_id
        assert data["memory_enabled"] is True
        assert data["retention_days"] == 60

        # Contract assertion: dual keys present for both frontend and backend standards
        assert "facts" in data and "semantic_facts" in data
        assert "summaries" in data and "session_summaries" in data

        # Contract assertion: enriched display strings present
        fact = data["facts"][0]
        assert fact["id"] == fact_id
        assert fact["fact_text"] == "user.editor: Neovim"
        assert fact["category"] == "user_pref"
        assert fact["confidence"] == 0.95

        summary = data["summaries"][0]
        assert summary["summary_text"] == "Configured plugins and keymaps."

        # 2. Search query filter
        search_res = await client.get(f"/api/agents/{agent_id}/memory?query=Neovim")
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data["facts"]) == 1
        assert search_data["facts"][0]["id"] == fact_id

        # 3. DELETE /api/agents/{id}/memory/facts/{fact_id} (Forget fact)
        del_fact_res = await client.delete(f"/api/agents/{agent_id}/memory/facts/{fact_id}")
        assert del_fact_res.status_code == 200
        assert del_fact_res.json()["status"] == "ok"

        # Fact is gone
        after_del = await client.get(f"/api/agents/{agent_id}/memory")
        assert len(after_del.json()["facts"]) == 0

        # 4. POST /api/agents/{id}/memory/purge (Purge episodic memory)
        purge_res = await client.post(f"/api/agents/{agent_id}/memory/purge")
        assert purge_res.status_code == 200
        assert purge_res.json()["status"] == "ok"
        assert purge_res.json()["purged"] is True

        # Summaries gone
        after_purge = await client.get(f"/api/agents/{agent_id}/memory")
        assert len(after_purge.json()["summaries"]) == 0


# ============================================================================
# 8. AgentMemoryTools Callable Integration
# ============================================================================


def test_agent_memory_tools_callable(tmp_path):
    """Verify internal agent tools (recall_agent_memory, memorize_fact) work accurately."""
    repo = AgentMemoryRepository(agent_id="tools-bot", data_dir=tmp_path)
    repo.initialize_schema()

    tools = AgentMemoryTools(repository=repo)

    # 1. Memorize fact
    mem_res = tools.memorize_fact(
        entity="project",
        attribute="target_os",
        value="Windows Server 2025",
        category="environment",
    )
    assert mem_res["status"] == "ok"
    assert mem_res["action_taken"] == "ADD"
    assert mem_res["fact_id"] is not None

    # 2. Recall memory
    recall_res = tools.recall_agent_memory(query="Windows Server")
    assert recall_res["status"] == "ok"
    assert len(recall_res["facts"]) == 1
    assert recall_res["facts"][0]["attribute"] == "target_os"
    assert recall_res["facts"][0]["value"] == "Windows Server 2025"
