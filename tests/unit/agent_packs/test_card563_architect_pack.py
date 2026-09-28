"""CARD-563: the Architect pack is a planner: no code-writing, check, commit, shell or generic handoff tool."""

from __future__ import annotations

from src.application.agent_packs.allowed_tools import domain_line, resolve_allowed_tools
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall
from src.infrastructure.skills.platform_packs import ALL_PLATFORM_PACK_IDS
from tests.unit.agent_packs.catalog import load_platform_manifest, platform_pack_profile

PLANNING = {
    "active_project_info", "read_project_file", "search_project", "list_project_dir", "read_steering",
    "list_cards", "read_card", "write_card", "set_card_status", "hand_off_card",
}
FORBIDDEN = {
    "write_project_file", "patch_project_file", "run_project_checks", "git_commit", "git_create_branch",
    "cli_exec", "execute_code", "handoff_to_agent", "lookup_agents",
}


def test_architect_is_seeded_shown_and_on_the_default_model():
    m = load_platform_manifest("architect")
    assert "architect" in ALL_PLATFORM_PACK_IDS
    assert m.model == "default" and m.provider == "default" and m.show_in_chat
    assert list(m.allowed_skill) == ["project-orientation", "brainstorm", "card-writing", "hand-off"]


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


def test_hand_off_card_asks_every_time_even_in_run_mode():
    gate = ToolPolicyGate(_Store())
    call = ToolCall(id="1", name="hand_off_card", arguments={"card_id": "CARD-2"})
    decision = gate.evaluate(call, platform_pack_profile("architect"))
    assert decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM

    class _Hitl:
        def park_tool_call(self, **kw):
            return "ap-1"

    res = gate.apply_to_tool_result(
        decision, call, session_id="s", agent=platform_pack_profile("architect"), hitl_engine=_Hitl(),
        approval_mode="run", log=False,
    )
    assert res is not None and res.error == "approval_required:ap-1"
