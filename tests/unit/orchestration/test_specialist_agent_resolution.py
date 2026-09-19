"""CARD-378 Specialist agent resolution unit tests [REQ-ORCH-044].

Ensures coding tools and execution phases resolve cleanly to active platform
agents ('autoreiv') and never return retired / vestigial agents like 'developer'.
"""

from src.application.orchestration.job_phase_orchestrator import (
    resolve_specialist_agent_for_capabilities,
)


def test_coding_tools_resolve_to_autoreiv_not_developer():
    """[REQ-ORCH-044]: Coding tools must resolve to autoreiv, never developer."""
    coding_capabilities = [
        "tool.repo_file_read",
        "tool.repo_file_write",
        "tool.write_project_file",
        "tool.repo_file_list",
    ]
    resolved = resolve_specialist_agent_for_capabilities(
        matched_ids=coding_capabilities,
        default_agent_id="autoreiv",
    )
    assert resolved == "autoreiv"
    assert resolved != "developer"


def test_blender_and_mcp_tools_resolve_to_active_agent():
    """[REQ-ORCH-044]: External MCP tools resolve to default agent when no specialist matches."""
    mcp_capabilities = [
        "tool.mcp_blender_execute_blender_code",
        "tool.mcp_blender_get_blendfile_summary",
    ]
    resolved = resolve_specialist_agent_for_capabilities(
        matched_ids=mcp_capabilities,
        default_agent_id="autoreiv",
    )
    assert resolved == "autoreiv"
    assert resolved != "developer"


def test_custom_agent_id_respected_when_explicit():
    """[REQ-ORCH-044]: Explicit agent.<name> capability continues to resolve to that custom agent."""
    matched = [
        "agent.3d_designer",
        "tool.repo_file_read",
    ]
    resolved = resolve_specialist_agent_for_capabilities(
        matched_ids=matched,
        default_agent_id="autoreiv",
    )
    assert resolved == "3d_designer"
