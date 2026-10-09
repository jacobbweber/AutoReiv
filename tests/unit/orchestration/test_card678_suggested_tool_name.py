"""CARD-678: a gap's suggested tool name comes from the capability, not the prompt's first words."""

import pytest

from src.application.orchestration.capability_detector import CapabilityDetector

FILLER = {"do", "not", "call", "any", "tools", "please", "just", "my"}


@pytest.mark.parametrize(
    "prompt, reply, word",
    [
        ("Do not call any tools. Fax my notes to 555-0100.", "There is no fax tool available to me.", "fax"),
        ("Do not call any tools. Email my notes to Bob.", "I do not have a direct email-sending tool.", "email"),
        ("Please just text Bob that I am late.", "I do not have an SMS tool.", "sms"),
    ],
)
def test_suggested_name_is_built_from_the_capability(prompt, reply, word):
    det = CapabilityDetector.detect(prompt, reply)
    assert det is not None
    assert word in det.suggested_tool_name
    assert not (set(det.suggested_tool_name.split("_")) & FILLER), det.suggested_tool_name


def test_short_capability_is_used_and_prompt_only_when_none():
    assert "fax" in CapabilityDetector._suggest_tool_name("fax", "Do not call any tools")
    assert CapabilityDetector._suggest_tool_name("", "restart the printer") == "manage_restart_printer"
