"""CARD-677: a "No agent covers X" turn-down files a gap, from the same matcher as the Ask Developer line."""

import pytest

import src.application.kernel.reply_rules as reply_rules
from src.application.orchestration.capability_detector import CapabilityDetector
from src.domain.capabilities.missing_tool import find_missing_tool


@pytest.mark.parametrize(
    "reply, capability",
    [
        ("No agent covers faxing notes.", "faxing notes"),
        ("No agent covers external email functionality in this setup.", "external email functionality"),
        ("Sorry. No other agent here covers sending SMS messages.", "sending SMS messages"),
    ],
)
def test_matcher_finds_no_agent_covers(reply, capability):
    found = find_missing_tool(reply)
    assert found is not None
    assert found.capability == capability


def test_detector_files_a_gap_for_the_live_fax_turn_down():
    det = CapabilityDetector.detect(
        "Fax my meeting notes to 555-0100.",
        "No agent covers faxing notes. You can use Ask Developer to add this.",
    )
    assert det is not None
    assert det.missing_capability == "faxing notes"
    assert "fax" in det.suggested_tool_name


def test_pronoun_object_falls_back_to_the_prompt():
    det = CapabilityDetector.detect("Book me a flight to Denver.", "I can't book flights; no agent covers that.")
    assert det is not None
    assert det.missing_capability == "Book me a flight to Denver."


@pytest.mark.parametrize(
    "reply",
    [
        "Which agent covers DNS?",
        "If no agent covers it, I will tell you.",
        "The Tutor agent covers that: open Tutor in Chat.",
    ],
)
def test_not_a_turn_down(reply):
    assert find_missing_tool(reply) is None


def test_reply_rules_have_no_private_pattern_any_more():
    assert not hasattr(reply_rules, "_NO_AGENT_COVERS")
