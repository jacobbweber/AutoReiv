"""CARD-563: the Architect pack is a planner: no code-writing, check, commit, shell or generic handoff tool."""

from __future__ import annotations

from src.application.agent_packs.allowed_tools import domain_line, resolve_allowed_tools
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall
from tests.unit.agent_packs.catalog import platform_pack_profile

PLANNING = {
    "active_project_info", "read_project_file", "search_project", "list_project_dir", "read_steering",
    "list_cards", "read_card", "write_card", "set_card_status", "hand_off_card", "review_card", "finish_review",
}
FORBIDDEN = {
    "write_project_file", "patch_project_file", "run_project_checks", "git_commit", "git_create_branch",
    "cli_exec", "execute_code", "handoff_to_agent", "lookup_agents",
}




def test_architect_tools_are_the_planning_set():
    allowed = set(resolve_allowed_tools(platform_pack_profile("architect")).ordered)
    assert PLANNING <= allowed
    assert not (FORBIDDEN & allowed), FORBIDDEN & allowed
    assert "handoff_to_agent" not in domain_line(platform_pack_profile("architect"))


def test_developer_does_not_get_hand_off_card():
    assert "hand_off_card" not in set(resolve_allowed_tools(platform_pack_profile("developer")).ordered)


class _Store:
    def get_setting(self, key):
        return None


def test_review_verdict_needs_no_click():
    """CARD-564 D1: review_card and finish_review run without approval (hand_off_card asks unless autorun, CARD-566)."""
    gate = ToolPolicyGate(_Store())
    arch = platform_pack_profile("architect")
    for name in ("review_card", "finish_review"):
        call = ToolCall(id="1", name=name, arguments={"card_id": "CARD-2"})
        assert gate.evaluate(call, arch).verdict == ToolPolicyVerdict.ALLOW, name
    assert "review_card" not in set(resolve_allowed_tools(platform_pack_profile("developer")).ordered)
