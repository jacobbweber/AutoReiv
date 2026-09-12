"""CARD-262 repo/code fail-closed grounding [REQ-REPO-003]."""

from __future__ import annotations

import json

from src.application.orchestration.repo_code_grounding import (
    ACTION_HONEST_FAIL,
    ACTION_REQUIRE_READ,
    ACTION_SKIP,
    assess_repo_code_grounding,
    collect_provenanced_repo_paths_from_tool_result,
    extract_claimed_repo_paths,
    format_repo_grounding_constraint_block,
    format_repo_honest_fail_message,
    format_ungrounded_repo_claim_honesty,
    is_repo_code_ask,
    is_repo_source_dependent_ask,
    should_honest_fail_after_turn,
    ungrounded_claimed_repo_paths,
)

POS_ASK = (
    "Using repo_file_read, what does AGENTS.md say about cards? "
    "Done-when: answer cites only content returned by repo_file_read of AGENTS.md. "
    "Keep under 120 words."
)
NEG_ASK = (
    "Using repo_file_read, what does TotallyFakeCheckoutFile-ZZZ.md say about the three beats? "
    "Done-when: if read fails, honest fail / park - do not invent. Keep under 80 words."
)


def test_classifiers():
    assert is_repo_code_ask(POS_ASK) is True
    assert is_repo_source_dependent_ask(POS_ASK) is True
    assert is_repo_code_ask(NEG_ASK) is True
    assert is_repo_code_ask("what is the weather") is False


def test_assess_require_read():
    d = assess_repo_code_grounding(POS_ASK)
    assert d.action == ACTION_REQUIRE_READ
    assert "AGENTS.md" in d.suggested_paths
    block = format_repo_grounding_constraint_block(d)
    assert "repo_file_read" in block
    assert "CARD-262" in block


def test_assess_skip_non_repo():
    d = assess_repo_code_grounding("hello there")
    assert d.action == ACTION_SKIP


def test_honest_fail_when_no_provenance():
    d = assess_repo_code_grounding(NEG_ASK, provenanced_paths=[], read_failed=True)
    assert d.action == ACTION_HONEST_FAIL
    msg = format_repo_honest_fail_message(d, job_id="job_test", error="File not found")
    assert "Not done" in msg
    assert "will not invent" in msg


def test_provenance_from_tool_result():
    ok = collect_provenanced_repo_paths_from_tool_result(
        "repo_file_read",
        json.dumps({"success": True, "path": "AGENTS.md", "content": "Cards stay Ready"}),
    )
    assert ok == ["AGENTS.md"]
    bad = collect_provenanced_repo_paths_from_tool_result(
        "repo_file_read",
        {"success": False, "path": "TotallyFakeCheckoutFile-ZZZ.md", "error": "File not found"},
    )
    assert bad == []
    listed = collect_provenanced_repo_paths_from_tool_result(
        "repo_file_list",
        {"success": True, "path": ".", "entries": [{"name": "AGENTS.md", "path": "AGENTS.md", "type": "file"}]},
    )
    assert listed == []  # list does not content-ground
    assert should_honest_fail_after_turn(NEG_ASK, []) is True
    assert should_honest_fail_after_turn(NEG_ASK, ["AGENTS.md"]) is True  # wrong file
    assert should_honest_fail_after_turn(POS_ASK, ["AGENTS.md"]) is False


def test_claim_guard():
    claimed = extract_claimed_repo_paths("See AGENTS.md and src/web/app.py for details.")
    assert "AGENTS.md" in claimed
    assert "src/web/app.py" in claimed
    bad = ungrounded_claimed_repo_paths(
        "AGENTS.md says cards stay Ready forever invent.",
        provenanced=[],
    )
    assert "AGENTS.md" in bad
    honesty = format_ungrounded_repo_claim_honesty(bad, [], job_id="job_x")
    assert "ungrounded checkout" in honesty
    ok = ungrounded_claimed_repo_paths(
        "AGENTS.md says cards stay Ready until build.",
        provenanced=["AGENTS.md"],
    )
    assert ok == []


def test_should_honest_fail_after_turn():
    assert should_honest_fail_after_turn(POS_ASK, []) is True
    assert should_honest_fail_after_turn(POS_ASK, ["AGENTS.md"]) is False
    assert should_honest_fail_after_turn("weather?", []) is False
