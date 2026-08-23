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
    assert "librarian" in pack_ids
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

    librarian_pack = next((p for p in catalog if p["id"] == "librarian"), None)
    assert librarian_pack is not None
    assert any(t["name"] == "wiki_note_create" for t in librarian_pack["tools"])

    # Unassigned custom tools should fall back to general/custom pack
    custom_pack = next((p for p in catalog if p["id"] == "general-custom"), None)
    assert custom_pack is not None
    assert any(t["name"] == "unassigned_custom_tool" for t in custom_pack["tools"])
