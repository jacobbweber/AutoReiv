"""CARD-563: Architect's card powers are enforced in CardTools; Developer stays Proposed-only."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.kernel import tool_registry as tr
from src.application.skills.card_tools import CardTools


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


def test_architect_files_ready_and_proposed_cards_with_the_next_id(cards):
    tools, root = cards
    token = _as("architect")
    try:
        ready = tools.write_card("---\nstatus: Ready\n---\n# CARD-<n> divide refuses zero\n", title="divide refuses zero")
        plain = tools.write_card("# CARD-<n> no status given\n")
        bad = tools.write_card("---\nstatus: Done\n---\n# CARD-<n> x\n")
    finally:
        tr._tool_context.reset(token)
    assert ready["success"] and ready["assigned_id"] == "CARD-6" and ready["status"] == "Ready"
    assert plain["success"] and plain["status"] == "Proposed"
    text = next((root / ".agents/cards").glob("CARD-6-*.md")).read_text(encoding="utf-8")
    assert "# CARD-6 divide refuses zero" in text and "CARD-<n>" not in text  # placeholder replaced, not kept
    assert next((root / ".agents/cards").glob("CARD-7-*.md")).name == "CARD-7-no-status-given.md"
    assert not bad["success"] and "Proposed or Ready" in bad["error"]


@pytest.mark.parametrize("n,status", [(4, "In Progress"), (5, "In Review")])
def test_architect_does_not_edit_cards_developer_is_working_or_waiting_review(cards, n, status):
    tools, root = cards
    token = _as("architect")
    try:
        res = tools.write_card(_card(n, status) + "\nextra\n", card_id=f"CARD-{n}")
    finally:
        tr._tool_context.reset(token)
    assert not res["success"] and status in res["error"]


@pytest.mark.parametrize(
    "card,target,ok,msg",
    [
        ("CARD-3", "Ready", True, ""),
        ("CARD-2", "Proposed", True, ""),
        ("CARD-1", "Done", False, "review is slice 3"),
        ("CARD-5", "Done", False, "review is slice 3"),
        ("CARD-5", "Returned", False, "review is slice 3"),
        ("CARD-2", "In Progress", False, "use hand_off_card"),
    ],
)
def test_architect_status_moves(cards, card, target, ok, msg):
    tools, _root = cards
    token = _as("architect")
    try:
        res = tools.set_card_status(card, target, return_reason="r")
    finally:
        tr._tool_context.reset(token)
    assert res["success"] is ok, res
    if msg:
        assert msg in res["error"]


def test_developer_still_files_proposed_only(cards):
    tools, _root = cards
    token = _as("developer")
    try:
        res = tools.write_card("---\nstatus: Ready\n---\n# CARD-<n> gap\n")
    finally:
        tr._tool_context.reset(token)
    assert res["success"] and res["status"] == "Proposed"
