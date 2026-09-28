"""CARD-566: hand_off_card follows the approval mode like every other tool (reverses CARD-563 D1)."""

from __future__ import annotations

from src.application.safety import tool_policy_gate
from src.application.safety.tool_policy_gate import ToolPolicyGate, ToolPolicyVerdict
from src.domain.gateway.models import ToolCall
from tests.unit.agent_packs.catalog import platform_pack_profile


class _Store:
    def __init__(self, settings=None):
        self._settings = settings or {}

    def get_setting(self, key):
        return self._settings.get(key)


class _Hitl:
    def __init__(self):
        self.parked = []

    def park_tool_call(self, **kw):
        self.parked.append(kw["tool_call"].name)
        return f"ap-{len(self.parked)}"


def _apply(mode, store=None):
    gate = ToolPolicyGate(store or _Store())
    arch = platform_pack_profile("architect")
    call = ToolCall(id="1", name="hand_off_card", arguments={"card_id": "CARD-2"})
    decision = gate.evaluate(call, arch)
    hitl = _Hitl()
    res = gate.apply_to_tool_result(decision, call, session_id="s", agent=arch, hitl_engine=hitl, approval_mode=mode, log=False)
    return decision, res, hitl


def test_autorun_does_not_park_the_hand_off():
    decision, res, hitl = _apply("run")
    assert decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM  # still a high-risk tool, logged as such
    assert res is None and hitl.parked == []


def test_ask_mode_parks_the_hand_off_once():
    decision, res, hitl = _apply("ask")
    assert decision.verdict == ToolPolicyVerdict.REQUIRE_CONFIRM
    assert res is not None and res.error == "approval_required:ap-1"
    assert hitl.parked == ["hand_off_card"]


def test_no_tool_is_exempt_from_autorun_any_more():
    assert not hasattr(tool_policy_gate, "ALWAYS_CONFIRM_TOOLS")
