"""
YAML CARD-001 Ready path [REQ-SDLC-072].
"""

from pathlib import Path

from src.application.skills.card_tools import CardTools

YAML_CARD_001 = """---
id: CARD-001
title: Educational single-script ReAct loop in PowerShell
status: Discuss
owner: Jacob
review_rounds: 0
max_review_rounds: 3
spec: react-loop-powershell
tags: [powershell, react, ollama, education]
---

# CARD-001 - Educational single-script ReAct loop in PowerShell

## Goal
Body stays.
"""


def test_write_read_yaml_roundtrip(tmp_path: Path):
    (tmp_path / ".github" / "cards").mkdir(parents=True)
    skill = CardTools(default_project_root=str(tmp_path))
    written = skill.write_card(content=YAML_CARD_001, filename="CARD-001-react-loop-powershell.md")
    assert written["success"] is True
    assert written["status"] == "Discuss"
    assert written["spec_reference"] == "react-loop-powershell"
    read = skill.read_card(card_id="CARD-001")
    assert read["success"] is True
    assert read["spec_reference"] == "react-loop-powershell"
    assert read["status"] == "Discuss"
    assert read["content"].lstrip().startswith("---")


def test_yaml_card_ready_when_spec_dir_exists(tmp_path: Path):
    cards = tmp_path / ".github" / "cards"
    spec = tmp_path / "docs" / "specs" / "react-loop-powershell"
    cards.mkdir(parents=True)
    spec.mkdir(parents=True)
    (spec / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    (spec / "design.md").write_text("# Design\n", encoding="utf-8")
    (spec / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    skill = CardTools(default_project_root=str(tmp_path))
    skill.write_card(content=YAML_CARD_001, filename="CARD-001-react-loop-powershell.md")
    ready = skill.set_card_status(card_id="CARD-001", status="Ready")
    assert ready["success"] is True
    assert ready["status"] == "Ready"
    path = cards / "CARD-001-react-loop-powershell.md"
    text = path.read_text(encoding="utf-8")
    assert text.lstrip().startswith("---")
    assert "status: Ready" in text
    assert "> **Status**" not in text
    assert "## Goal" in text
    assert "Body stays." in text


def test_yaml_ready_denied_without_spec_dir(tmp_path: Path):
    (tmp_path / ".github" / "cards").mkdir(parents=True)
    skill = CardTools(default_project_root=str(tmp_path))
    skill.write_card(content=YAML_CARD_001, filename="CARD-001-react-loop-powershell.md")
    deny = skill.set_card_status(card_id="CARD-001", status="Ready")
    assert deny["success"] is False
    assert "spec" in deny["error"].lower()
