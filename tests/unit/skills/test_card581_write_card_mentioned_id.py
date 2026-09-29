"""CARD-581: a new card that mentions another card is a new card, not an edit of the one it mentions."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.kernel import tool_registry as tr
from src.application.skills.card_tools import CardTools, own_card_id


def _card(n: int, status: str) -> str:
    return f"---\nid: CARD-{n}\ntitle: c{n}\nstatus: {status}\n---\n# CARD-{n} c{n}\n"


@pytest.fixture
def cards(tmp_path: Path):
    root = tmp_path / "proj"
    (root / ".agents/cards").mkdir(parents=True)
    for n, st in ((1, "Done"), (2, "Ready"), (3, "Proposed"), (4, "In Progress"), (5, "In Review")):
        (root / f".agents/cards/CARD-{n}-c{n}.md").write_text(_card(n, st), encoding="utf-8")
    return CardTools(root_resolver=lambda _=None: root), root


def _as(agent: str):
    return tr._tool_context.set({"agent_id": agent})


NEW_BODY = (
    '---\ntitle: "multiply() returns the product"\nstatus: {status}\n---\n'
    "# multiply() returns the product\n\n## Scope\n- add multiply(a, b)\n"
    "Out of scope: add() (CARD-5), divide() (CARD-3).\n"
)


def test_architect_new_card_mentioning_an_in_review_card_is_filed_as_new(cards):
    tools, root = cards
    before = (root / ".agents/cards/CARD-5-c5.md").read_text(encoding="utf-8")
    token = _as("architect")
    try:
        res = tools.write_card(NEW_BODY.format(status="Ready"), title="multiply() returns the product")
    finally:
        tr._tool_context.reset(token)
    assert res["success"], res
    assert res["assigned_id"] == "CARD-6" and res["status"] == "Ready"
    assert (root / ".agents/cards/CARD-5-c5.md").read_text(encoding="utf-8") == before


def test_developer_new_card_mentioning_a_proposed_card_does_not_overwrite_it(cards):
    tools, root = cards
    before = (root / ".agents/cards/CARD-3-c3.md").read_text(encoding="utf-8")
    token = _as("developer")
    try:
        res = tools.write_card(NEW_BODY.format(status="Proposed"))
    finally:
        tr._tool_context.reset(token)
    assert res["success"], res
    assert res["assigned_id"] == "CARD-6" and res["status"] == "Proposed"
    assert (root / ".agents/cards/CARD-3-c3.md").read_text(encoding="utf-8") == before


def test_architect_filename_id_wins_over_a_mentioned_id(cards):
    tools, root = cards
    token = _as("architect")
    try:
        res = tools.write_card(NEW_BODY.format(status="Ready"), filename="CARD-6-multiply.md")
    finally:
        tr._tool_context.reset(token)
    assert res["success"] and res["assigned_id"] == "CARD-6"
    assert (root / ".agents/cards/CARD-6-multiply.md").is_file()


def test_edit_by_own_frontmatter_id_still_edits_that_card(cards):
    tools, root = cards
    token = _as("architect")
    try:
        res = tools.write_card(_card(2, "Ready") + "\nSee CARD-5 for context.\n")
    finally:
        tr._tool_context.reset(token)
    assert res["success"] and res["id"] == "CARD-2" and "assigned_id" not in res
    assert "See CARD-5" in (root / ".agents/cards/CARD-2-c2.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "content,expected",
    [
        ("---\nid: CARD-7\n---\n# CARD-7 x\n", "CARD-7"),
        ("---\nid: CARD-<n>\n---\n# CARD-<n> x\nsee CARD-1\n", ""),
        ("# [CARD-563] Title\nrelated CARD-1\n", "CARD-563"),
        ("# Title\nrelated CARD-1\n", ""),
        ("---\ntitle: t\n---\n# t\n## CARD-9 later heading\n", ""),
        ("", ""),
    ],
)
def test_own_card_id_ignores_mentions(content, expected):
    assert own_card_id(content) == expected
