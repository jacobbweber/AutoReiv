"""CARD-562: cards are written only by write_card, which assigns the next CARD-N id; file tools refuse card folders."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.kernel import tool_registry as tr
from src.application.skills.card_tools import CARD_DIRS, CardTools
from src.application.skills.project_dev_tools import ProjectDevTools
from src.application.skills.project_file_tools import ProjectFileTools

AUDIT_CARD = """---
id: PROPOSED-1
title: "Guard divide() against divide-by-zero"
status: Ready
priority: P1
---

# PROPOSED-1 Guard divide() against divide-by-zero

## Why
divide(1, 0) returns Infinity.
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "calc"
    (root / ".agents" / "cards").mkdir(parents=True)
    (root / ".agents" / "cards" / "CARD-1-add.md").write_text("---\nid: CARD-1\nstatus: In Review\n---\n# CARD-1 add\n", encoding="utf-8")
    (root / "docs" / "cards").mkdir(parents=True)
    (root / "docs" / "cards" / "CARD-7-legacy.md").write_text("---\nid: CARD-7\nstatus: Done\n---\n# CARD-7 x\n", encoding="utf-8")
    (root / "calc.js").write_text("function add(a, b) { return a + b; }\n", encoding="utf-8")
    return root


@pytest.fixture
def as_developer():
    token = tr._tool_context.set({"agent_id": "developer"})
    yield
    tr._tool_context.reset(token)


@pytest.mark.parametrize("folder", CARD_DIRS)
def test_write_project_file_refuses_card_folders(project: Path, folder: str):
    files = ProjectFileTools(root_resolver=lambda _=None: project)
    res = files.write_project_file(path=f"{folder}/proposed-x.md", content="x")
    assert res["success"] is False and "write_card" in res["error"]
    assert not (project / folder / "proposed-x.md").exists()
    assert files.write_project_file(path="notes/ok.md", content="x")["success"]  # other paths unchanged


def test_patch_project_file_refuses_cards_but_reads_are_fine(project: Path):
    dev = ProjectDevTools(root_resolver=lambda _=None: project)
    res = dev.patch_project_file(path=".agents/cards/CARD-1-add.md", old_text="In Review", new_text="Done")
    assert res["success"] is False and "write_card" in res["error"]
    assert "In Review" in (project / ".agents/cards/CARD-1-add.md").read_text(encoding="utf-8")
    assert dev.patch_project_file(path="calc.js", old_text="a + b", new_text="b + a")["success"]
    read = ProjectFileTools(root_resolver=lambda _=None: project).read_project_file(path=".agents/cards/CARD-1-add.md")
    assert read["success"] and "CARD-1" in read["content"]


def test_developer_new_card_gets_next_id_filename_and_proposed(project: Path, as_developer):
    res = CardTools(default_project_root=str(project)).write_card(AUDIT_CARD, filename="proposed-divide-by-zero-guard.md")
    assert res["success"], res
    assert res["assigned_id"] == "CARD-8" and res["status"] == "Proposed"  # max over all card folders + 1
    path = project / ".agents" / "cards" / "CARD-8-guard-divide-against-divide-by-zero.md"
    text = path.read_text(encoding="utf-8")
    assert "id: CARD-8" in text and "status: Proposed" in text and "# CARD-8 Guard divide()" in text
    assert "PROPOSED-1" not in text
    assert not (project / ".agents" / "cards" / "proposed-divide-by-zero-guard.md").exists()


def test_developer_cannot_overwrite_by_reusing_a_taken_id(project: Path, as_developer):
    res = CardTools(default_project_root=str(project)).write_card(AUDIT_CARD.replace("PROPOSED-1", "CARD-1"))
    assert res["success"] is False and "Keep status" in res["error"]  # treated as an edit of CARD-1, refused


def test_card_without_frontmatter_gets_one_for_developer(project: Path, as_developer):
    res = CardTools(default_project_root=str(project)).write_card("# Missing tests for divide\n\n## Why\nx\n")
    assert res["success"] and res["assigned_id"] == "CARD-8" and res["status"] == "Proposed"


def test_operator_keeps_a_free_explicit_id(project: Path):
    cards = CardTools(default_project_root=str(project))
    res = cards.write_card("---\nid: CARD-600\nstatus: Ready\n---\n# CARD-600 planned\n", filename="CARD-600-planned.md")
    assert res["success"] and res["assigned_id"] == "CARD-600" and res["status"] == "Ready"
    assert (project / ".agents" / "cards" / "CARD-600-planned.md").is_file()
    nxt = cards.write_card("---\nstatus: Discuss\n---\n# Something new\n")
    assert nxt["assigned_id"] == "CARD-601"
