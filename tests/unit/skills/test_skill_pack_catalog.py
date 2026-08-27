"""
Unit tests for Hierarchical Skill Pack Catalog & Manifests [REQ-SKIL-001].
"""

from src.application.skills.manifest import BUILTIN_SKILL_PACKS, get_hierarchical_skills_catalog
from src.domain.gateway.models import ToolDefinition


def test_builtin_skill_packs_defined():
    """Verify built-in skill pack manifests are defined with valid metadata."""
    assert len(BUILTIN_SKILL_PACKS) >= 5

    pack_ids = {p.id for p in BUILTIN_SKILL_PACKS}
    assert "sysadmin" in pack_ids
    assert "wiki" in pack_ids
    assert "tasks" in pack_ids
    assert "diagnostics" in pack_ids
    assert "verification" in pack_ids
    assert "planning" in pack_ids
    assert "agent-builder" in pack_ids


def test_get_hierarchical_skills_catalog():
    """Verify tools are correctly clustered into hierarchical skill packs."""
    mock_tools = [
        ToolDefinition(name="cli_exec", description="Execute command"),
        ToolDefinition(name="system_info", description="Get system specs"),
        ToolDefinition(name="wiki_note_create", description="Create note"),
        ToolDefinition(name="assert_json_schema", description="Assert schema"),
        ToolDefinition(name="unassigned_custom_tool", description="Custom tool"),
    ]

    catalog = get_hierarchical_skills_catalog(mock_tools)

    assert len(catalog) >= 3

    sysadmin_pack = next((p for p in catalog if p["id"] == "sysadmin"), None)
    assert sysadmin_pack is not None
    assert sysadmin_pack["name"] == "Linux Sysadmin Pack"
    assert any(t["name"] == "cli_exec" for t in sysadmin_pack["tools"])
    assert any(t["name"] == "system_info" for t in sysadmin_pack["tools"])

    wiki_pack = next((p for p in catalog if p["id"] == "wiki"), None)
    assert wiki_pack is not None
    assert any(t["name"] == "wiki_note_create" for t in wiki_pack["tools"])

    # Unassigned custom tools should fall back to general/custom pack
    custom_pack = next((p for p in catalog if p["id"] == "general-custom"), None)
    assert custom_pack is not None
    assert any(t["name"] == "unassigned_custom_tool" for t in custom_pack["tools"])


def test_get_hierarchical_skills_catalog_clusters_mcp_servers():
    """Verify MCP tools are automatically clustered into dedicated MCP skill packs [REQ-MCP-010]."""
    mock_tools = [
        ToolDefinition(name="cli_exec", description="Execute command"),
        ToolDefinition(name="mcp_github-tools_create_issue", description="Create GitHub issue"),
        ToolDefinition(name="mcp_github-tools_get_repo", description="Get GitHub repository"),
        ToolDefinition(name="mcp_sqlite_query", description="Run SQL query"),
    ]

    catalog = get_hierarchical_skills_catalog(mock_tools)

    github_pack = next((p for p in catalog if p["id"] == "mcp_github-tools"), None)
    assert github_pack is not None
    assert github_pack["name"] == "MCP: github-tools"
    assert github_pack["icon"] == "plug"
    assert len(github_pack["tools"]) == 2
    assert any(t["name"] == "mcp_github-tools_create_issue" for t in github_pack["tools"])
    assert any(t["name"] == "mcp_github-tools_get_repo" for t in github_pack["tools"])

    sqlite_pack = next((p for p in catalog if p["id"] == "mcp_sqlite"), None)
    assert sqlite_pack is not None
    assert sqlite_pack["name"] == "MCP: sqlite"
    assert len(sqlite_pack["tools"]) == 1
    assert sqlite_pack["tools"][0]["name"] == "mcp_sqlite_query"

