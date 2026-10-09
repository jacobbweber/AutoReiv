"""CARD-684: "No tools that change state will be called" says which tools are not used; it is not a missing tool."""

from __future__ import annotations

import pytest

from src.application.orchestration.capability_detector import CapabilityDetector
from src.domain.capabilities.missing_tool import find_missing_tool

PROMPT = "Summarize my gardening notes into a new wiki note using the summary template."

NOT_A_GAP = [
    "**Note:** No tools that change state will be called in this Formulate phase. The plan is ready.",
    "No tools that change state will be called in this Formulate phase.",
    "No write tools will be used in this phase.",
    "No tools will be needed for this step.",
    "No tools which modify notes were called during planning.",
    "No tools have been called yet; this is the plan only.",
    "No state-changing tools are being used here.",
]

STILL_A_GAP = [
    ("I could not send the fax: there is no fax tool.", "fax"),
    ("No tool is available to restart the service.", "restart the service"),
    ("There's no calendar integration available to me.", "calendar"),
    ("There is no tool that can send SMS messages.", "sms"),
]


@pytest.mark.parametrize("reply", NOT_A_GAP)
def test_a_note_about_tools_not_used_is_not_a_gap(reply):
    assert find_missing_tool(reply) is None
    assert CapabilityDetector.detect(PROMPT, reply) is None


@pytest.mark.parametrize("reply,word", STILL_A_GAP)
def test_a_real_missing_tool_is_still_a_gap(reply, word):
    found = CapabilityDetector.detect(PROMPT, reply)
    assert found is not None
    assert word in found.missing_capability.lower()
