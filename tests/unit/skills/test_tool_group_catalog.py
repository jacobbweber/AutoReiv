"""
Unit tests for hierarchical tool-group catalog [REQ-SKIL-001].
"""

from src.application.skills.manifest import BUILTIN_TOOL_GROUPS, TOOL_GROUP_TIERS, get_hierarchical_tool_groups
from src.domain.gateway.models import ToolDefinition


def test_builtin_tool_groups_defined():
    """Verify built-in tool-group manifests are defined with valid metadata and tiers [REQ-TAX-001, REQ-TAX-002]."""
    assert len(BUILTIN_TOOL_GROUPS) == 9
    assert len(TOOL_GROUP_TIERS) == 3

    tier_ids = {t.id for t in TOOL_GROUP_TIERS}
    assert tier_ids == {"productivity", "system", "cognition"}

    pack_map = {p.id: p for p in BUILTIN_TOOL_GROUPS}
    assert pack_map["wiki"].tier == "productivity"
    assert pack_map["wiki"].name == "Wiki & Knowledge Vault"
    assert "yaml_frontmatter_parse" not in pack_map["wiki"].tool_names

    assert pack_map["weekly-notes"].tier == "productivity"
    assert pack_map["weekly-notes"].name == "Weekly Notes & To-Dos"
    assert pack_map["worker"].tier == "productivity"

    assert pack_map["sysadmin"].tier == "system"
    assert pack_map["diagnostics"].tier == "system"
    assert pack_map["diagnostics"].is_core is True
    assert pack_map["diagnostics"].name == "AutoReiv Core Platform SRE & Diagnostics"

    assert pack_map["planning"].tier == "cognition"
    assert pack_map["orchestration"].tier == "cognition"
    assert pack_map["verification"].tier == "cognition"
    assert pack_map["verification"].name == "Agent Logic Verification (Critic)"
    assert pack_map["agent-builder"].tier == "cognition"


def test_get_hierarchical_tool_groups():
    """Verify tools are correctly clustered into hierarchical tool groups with tier metadata."""
    mock_tools = [
        ToolDefinition(name="cli_exec", description="Execute command"),
        ToolDefinition(name="system_info", description="Get system specs"),
        ToolDefinition(name="wiki_note_create", description="Create note"),
        ToolDefinition(name="assert_json_schema", description="Assert schema"),
        ToolDefinition(name="unassigned_custom_tool", description="Custom tool"),
    ]

    catalog = get_hierarchical_tool_groups(mock_tools)

    assert len(catalog) >= 3

    sysadmin_pack = next((p for p in catalog if p["id"] == "sysadmin"), None)
    assert sysadmin_pack is not None
    assert sysadmin_pack["name"] == "Host Terminal & Linux Sysadmin"
    assert sysadmin_pack["tier"] == "system"
    assert any(t["name"] == "cli_exec" for t in sysadmin_pack["tools"])
    assert any(t["name"] == "system_info" for t in sysadmin_pack["tools"])

    wiki_pack = next((p for p in catalog if p["id"] == "wiki"), None)
    assert wiki_pack is not None
    assert wiki_pack["tier"] == "productivity"
    assert any(t["name"] == "wiki_note_create" for t in wiki_pack["tools"])

    # Unassigned custom tools should fall back to general/custom pack
    custom_pack = next((p for p in catalog if p["id"] == "general-custom"), None)
    assert custom_pack is not None
    assert any(t["name"] == "unassigned_custom_tool" for t in custom_pack["tools"])


def test_get_hierarchical_tool_groups_clusters_mcp_servers():
    """Verify MCP tools are automatically clustered into dedicated MCP tool groups [REQ-MCP-010]."""
    mock_tools = [
        ToolDefinition(name="cli_exec", description="Execute command"),
        ToolDefinition(name="mcp_github-tools_create_issue", description="Create GitHub issue"),
        ToolDefinition(name="mcp_github-tools_get_repo", description="Get GitHub repository"),
        ToolDefinition(name="mcp_sqlite_query", description="Run SQL query"),
    ]

    catalog = get_hierarchical_tool_groups(mock_tools)

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
