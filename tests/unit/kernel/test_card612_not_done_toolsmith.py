"""CARD-612: no false "Not done" lines on Toolsmith.

- The Ask Developer brief lists only the fields Jacob filled in and carries a marker line; a brief is one work order,
  so the skipped-parts checker does not run on it (live QA: the example question copied from a capability gap and the
  notes read as separate asks).
- The checker sees short tool arguments first, so register_native_tool(target_agent_id=...) is visible.
- A "Not done" tool line is dropped when register_native_tool ran and succeeded; a result that reports a failure
  still counts as failed.
- Toolsmith's domain line never tells it to end with "You can use Ask Developer to add this."
"""

from __future__ import annotations

from src.application.agent_skills.allowed_tools import domain_line
from src.application.kernel.reply_rules import (
    BRIEF_NOTES_MARKER,
    describe_tool_run,
    drop_false_not_done,
    needs_parts_check,
)
from src.application.tools.developer_mediation import build_packet, format_developer_prompt
from tests.unit.agent_skills.catalog import platform_pack_profile

REPLY = "I registered tide_times and proposed it for Tutor. Enable it in Tools Studio, then accept the proposal."


def _brief(**draft) -> str:
    return format_developer_prompt(build_packet("create", {"behavior": "Look up tide times for a harbour", **draft}))


def test_brief_lists_only_filled_fields():
    text = _brief(target_agent_id="tutor")
    for empty in ("Language hint", "Runtime hint", "Path or context", "Packaging preference", "none", "unspecified"):
        assert empty not in text.split(BRIEF_NOTES_MARKER)[0]
    assert "What it should do: Look up tide times for a harbour" in text
    assert 'Register with target_agent_id "tutor"' in text
    filled = _brief(language_hint="python", packaging_preference="native")
    assert "Language hint: python" in filled
    assert "Packaging preference (note only, not a completed package): native" in filled


def test_a_brief_is_never_parts_checked():
    text = _brief(target_agent_id="tutor")
    assert BRIEF_NOTES_MARKER in text
    assert not needs_parts_check(text, REPLY)  # the brief's notes used to make it look like a 6-part request
    # live QA run 3: a capability gap copies the user's question into the brief; it is an example, not an ask
    gap = format_developer_prompt(build_packet("create", {
        "tool_name": "days_between",
        "behavior": "How many days from March 3 to June 9?\n\nMissing capability: Compute the number of days between "
                    "two calendar dates\n\nRequested from a capability gap for tutor.",
        "target_agent_id": "tutor",
    }))
    assert not needs_parts_check(gap, REPLY)


def test_real_multi_part_message_is_still_checked():
    msg = "Remember my bike is blue, then look up the weather, and also list my notes"
    assert needs_parts_check(msg, "Saved and here is the weather.")


def test_target_agent_is_visible_behind_long_code():
    args = {"name": "tide_times", "code": "x = 1\n" * 200, "description": "Tide times", "parameters": "{}" * 40,
            "sample_arguments": "{}", "target_agent_id": "tutor"}
    line = describe_tool_run("register_native_tool", args, False)
    assert "target_agent_id=tutor" in line and line.endswith(" ok")
    assert describe_tool_run("register_native_tool", {}, False, {"success": False, "error": "x"}).endswith(" failed")


def test_tool_lines_dropped_only_when_register_succeeded():
    not_done = "Not done: register the tool with target agent tutor.\nNot done: send the summary email."
    ok = [describe_tool_run("register_native_tool", {"name": "tide_times", "target_agent_id": "tutor"}, False)]
    assert drop_false_not_done(not_done, ok) == "Not done: send the summary email."
    failed = [describe_tool_run("register_native_tool", {"name": "tide_times"}, True)]
    assert drop_false_not_done(not_done, failed) == not_done


def test_toolsmith_domain_line_has_no_ask_developer_ending():
    assert "Ask Developer" not in domain_line(platform_pack_profile("toolsmith"))
    line = domain_line(platform_pack_profile("autoreiv"))
    assert 'end your reply with "You can use Ask Developer to add this."' in line
    assert "Only a reply that turns the request down ends with that line." in line
