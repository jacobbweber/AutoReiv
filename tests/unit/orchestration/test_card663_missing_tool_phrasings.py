"""CARD-663: one shared matcher decides "the reply admits a missing tool" for both the gap detector and the
Ask Developer line, so the detector files a gap for every wording the line already reacts to.
"""

from __future__ import annotations

import pytest

from src.application.kernel import reply_rules
from src.application.kernel.reply_rules import ASK_DEVELOPER_LINE, ask_developer_ending
from src.application.orchestration.capability_detector import CapabilityDetector
from src.domain.capabilities.missing_tool import admits_missing_tool, find_missing_tool

PROMPT = "summarize the gardening notes and email them to me"

# (reply, a word the extracted capability must contain)
MISSED = [
    ("Summary: water deeply.\n\n**Email status:** I do not have a direct email-sending tool in my skill set.", "email"),
    ("I can't access a tool that sends SMS messages, so I stopped there.", "sms"),
    ("I could not send the fax: there is no fax tool.", "fax"),
    ("There's no calendar integration available to me.", "calendar"),
    ("This agent does not have a Slack posting tool.", "slack"),
    ("I lack a tool for scheduling meetings.", "scheduling meetings"),
    ("No tool is available to restart the service.", "restart the service"),
    ("I'm unable to use any tool that can query DNS records.", "query dns records"),
    ("The PDF export tool isn't available to me in this session.", "pdf export"),
]

STILL_CAUGHT = [
    ("I don't have the tools to query Active Directory users.", "active directory"),
    ("I cannot directly create virtual machines.", "create virtual machines"),
    ("I'm unable to reboot servers without a tool.", "reboot servers"),
]

NOT_GAPS = [
    "Here is the summary of the gardening notes.",
    "I did not use any tools for this answer; it comes from the note you pasted.",
    "You don't have a backup tool configured yet; consider adding one.",
    "If you don't have the tool installed, run the installer first.",
    "Do you have a tool for this?",
    "There is no problem with the tool; it ran fine.",
    "I don't have any notes about that topic yet.",
    "The wiki has no gardening notes, so there is nothing to summarize.",
    "I can't book flights; no agent covers that.",
]


@pytest.mark.parametrize("reply,word", MISSED + STILL_CAUGHT)
def test_detector_files_a_gap_for_each_admission(reply, word):
    gap = CapabilityDetector.detect(PROMPT, reply)
    assert gap is not None, reply
    assert word in gap.missing_capability.lower(), gap.missing_capability
    assert gap.context_summary == reply.strip()


@pytest.mark.parametrize("reply", NOT_GAPS)
def test_detector_stays_quiet_when_no_tool_is_missing(reply):
    assert CapabilityDetector.detect(PROMPT, reply) is None
    assert not admits_missing_tool(reply)


@pytest.mark.parametrize("reply,_word", MISSED + STILL_CAUGHT)
def test_ask_developer_line_and_detector_agree(reply, _word):
    assert admits_missing_tool(reply)
    gap = CapabilityDetector.detect(PROMPT, reply)
    out = ask_developer_ending(reply, [], gap.missing_capability if gap else None, ())
    assert out.endswith(ASK_DEVELOPER_LINE), out


def test_reply_rules_has_no_private_lacks_tool_pattern():
    assert not hasattr(reply_rules, "_LACKS_TOOL")


def test_a_gap_about_the_agents_own_tool_is_not_filed():
    own = {"wiki_note_create"}
    for reply in (
        "I cannot create the note: I do not have the tool wiki_note_create available.",
        "**I do not have the `wiki_note_create` tool available** in this execution context.",
    ):
        assert find_missing_tool(reply) is not None
        assert CapabilityDetector.detect(PROMPT, reply, own_tools=own) is None
        assert CapabilityDetector.detect(PROMPT, reply) is not None


def test_greetings_and_empty_input_still_return_none():
    assert CapabilityDetector.detect("hi", "I do not have an email tool.") is None
    assert CapabilityDetector.detect(PROMPT, "") is None
