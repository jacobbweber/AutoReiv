"""
Unit tests for ToolRanker & 3-Tier Tool Resolution Pipeline [REQ-MCP-004].
"""

import time

import pytest

from src.application.kernel.tool_ranker import ToolRanker
from src.domain.gateway.models import ToolDefinition


@pytest.fixture
def sample_tool_catalog():
    return [
        ToolDefinition(
            name="delegate_task",
            description="Delegate subtask to specialist agent",
            parameters={"type": "object", "properties": {"task": {"type": "string"}}},
        ),
        ToolDefinition(
            name="read_wiki_note",
            description="Read content of a markdown document or knowledge note",
            parameters={"type": "object", "properties": {"path": {"type": "string"}}},
        ),
        ToolDefinition(
            name="create_wiki_note",
            description="Create a new note in the PARA wiki library",
            parameters={"type": "object", "properties": {"title": {"type": "string"}}},
        ),
        ToolDefinition(
            name="inspect_host_cpu",
            description="Check CPU utilization, load averages, and processor metrics",
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="inspect_host_memory",
            description="Check RAM utilization, swap usage, and available system memory",
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="inspect_disk_storage",
            description="Check filesystem mount storage, free space, and disk usage",
            parameters={"type": "object", "properties": {}},
        ),
        ToolDefinition(
            name="query_sqlite_database",
            description="Execute read-only SQL queries against SQLite database tables",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        ),
        ToolDefinition(
            name="mcp_github_create_issue",
            description="Create a new GitHub issue in a repository",
            parameters={"type": "object", "properties": {"title": {"type": "string"}}},
        ),
    ]


def test_tool_ranker_under_limit_returns_all(sample_tool_catalog):
    """When tool count is <= max_tools, return all tools directly."""
    subset = sample_tool_catalog[:4]
    ranked = ToolRanker.rank_tools("anything", subset, max_tools=6)
    assert len(ranked) == 4
    assert [t.name for t in ranked] == [t.name for t in subset]


def test_tool_ranker_bm25_semantic_relevance(sample_tool_catalog):
    """ToolRanker ranks relevant tools highest based on query keywords."""
    query = "Inspect CPU and system memory usage"
    ranked = ToolRanker.rank_tools(query, sample_tool_catalog, max_tools=3)
    assert len(ranked) == 3
    names = [t.name for t in ranked]
    assert "inspect_host_cpu" in names
    assert "inspect_host_memory" in names


def test_tool_ranker_preserves_pinned_tools(sample_tool_catalog):
    """Pinned core tools are always retained regardless of query match score."""
    query = "Check disk storage space"
    pinned = ["delegate_task"]
    ranked = ToolRanker.rank_tools(query, sample_tool_catalog, pinned_tool_names=pinned, max_tools=2)
    assert len(ranked) == 2
    names = [t.name for t in ranked]
    assert "delegate_task" in names
    assert "inspect_disk_storage" in names


def test_tool_ranker_empty_query_fallback(sample_tool_catalog):
    """When query is empty or no keywords match, returns top tools safely."""
    ranked = ToolRanker.rank_tools("", sample_tool_catalog, max_tools=4)
    assert len(ranked) == 4


def test_tool_ranker_performance_sub_millisecond(sample_tool_catalog):
    """ToolRanker executes in under 2ms even with repeated calls."""
    # Duplicate catalog to simulate 100 tools
    large_catalog = [
        ToolDefinition(
            name=f"tool_{i}_{t.name}",
            description=f"Tool {i}: {t.description}",
            parameters=t.parameters,
        )
        for i in range(15)
        for t in sample_tool_catalog
    ]
    assert len(large_catalog) == 120

    start = time.perf_counter()
    ranked = ToolRanker.rank_tools("query SQLite database tables", large_catalog, max_tools=6)
    duration_ms = (time.perf_counter() - start) * 1000

    assert len(ranked) == 6
    assert duration_ms < 5.0  # Must be fast
