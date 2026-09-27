"""CARD-378 Specialist agent resolution unit tests [REQ-ORCH-044].

Ensures execution phases resolve to active platform agents; code work goes to
Developer unless the default agent ticks coding (CARD-544 D1).
"""

from src.application.orchestration.job_phase_orchestrator import (
    resolve_specialist_agent_for_capabilities,
)


def test_coding_tools_resolve_to_developer_when_autoreiv_does_not_tick_coding():
    """[REQ-ORCH-044, CARD-544 D1]: AutoReiv no longer ticks coding, so code execute phases go to Developer."""
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
    assert resolved == "developer"


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
