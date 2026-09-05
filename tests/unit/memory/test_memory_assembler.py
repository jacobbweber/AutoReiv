"""
Unit tests for CARD-116: Dynamic Context Window Token Budgeting,
Three-Shelf Prompt Injection, and Agent Memory Tools.
"""

from src.application.memory.agent_memory_tools import AgentMemoryTools
from src.application.memory.assembler import MemoryContextAssembler, get_budget_tier
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def test_get_budget_tier():
    tier_small = get_budget_tier(4096)
    assert tier_small["tier_name"] == "tight"
    assert tier_small["max_facts"] == 3
    assert tier_small["max_summaries"] == 0

    tier_8k = get_budget_tier(8192)
    assert tier_8k["tier_name"] == "tight"

    tier_16k = get_budget_tier(16384)
    assert tier_16k["tier_name"] == "standard"
    assert tier_16k["max_facts"] == 6
    assert tier_16k["max_summaries"] == 1

    tier_128k = get_budget_tier(131072)
    assert tier_128k["tier_name"] == "broad"
    assert tier_128k["max_facts"] == 15
    assert tier_128k["max_summaries"] == 3


def test_memory_context_assembler_formatting(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    # Populate shelves
    repo.add_pinned_memory("Always verify PowerShell commands before execution.")
    repo.record_session_summary("s-10", "Built per-agent memory SQLite repo.", turn_count=4)
    repo.add_semantic_fact("user", "os_platform", "Windows 11", category="environment")
    repo.add_semantic_fact("user", "preferred_shell", "pwsh", category="user_pref")

    assembler = MemoryContextAssembler(repository=repo)

    # Broad model (e.g. 64k)
    block_broad = assembler.assemble(
        context_limit=65536,
        user_query="PowerShell",
        pinned_override="Host: Windows 11 Pro",
    )
    assert "[Agent Brain - Pinned Directives]" in block_broad
    assert "Host: Windows 11 Pro" in block_broad
    assert "Always verify PowerShell commands" in block_broad
    assert "[Agent Brain - Episodic Milestones]" in block_broad
    assert "Built per-agent memory SQLite repo." in block_broad
    assert "[Agent Brain - Recalled Relevant Facts]" in block_broad
    assert "Windows 11" in block_broad

    # Tight model (e.g. 4k)
    block_tight = assembler.assemble(
        context_limit=4096,
        user_query="PowerShell",
    )
    assert "[Agent Brain - Pinned Directives]" in block_tight
    # Episodic summaries must be omitted in tight mode to conserve tokens
    assert "[Agent Brain - Episodic Milestones]" not in block_tight
    assert "[Agent Brain - Recalled Relevant Facts]" in block_tight


def test_agent_memory_tools(tmp_path):
    db_file = tmp_path / "test_memory.db"
    repo = AgentMemoryRepository(db_path=db_file)
    repo.initialize_schema()

    tools = AgentMemoryTools(repository=repo)

    # 1. Memorize fact
    res = tools.memorize_fact(
        entity="user",
        attribute="favorite_editor",
        value="VS Code",
        category="user_pref",
    )
    assert res["status"] == "ok"
    assert res["action_taken"] == "ADD"

    # 2. Recall memory
    search_res = tools.recall_agent_memory(query="VS Code")
    assert search_res["status"] == "ok"
    assert len(search_res["facts"]) >= 1
    assert search_res["facts"][0]["value"] == "VS Code"
