"""
Unit tests for list_card_status skill script.
Verifies YAML frontmatter, Markdown blockquote parsing, granular search,
token-efficient default filtering, and single-card inspection.
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / ".agents" / "skills" / "card-status" / "scripts" / "list_card_status.py"


def test_list_card_status_parses_yaml_and_blockquotes(tmp_path: Path):
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()

    # Card 1: YAML frontmatter format
    card1 = cards_dir / "CARD-901-yaml-feature.md"
    card1.write_text(
        """---
id: CARD-901
title: "YAML Feature"
status: Ready
created: 2026-09-19
adr: ADR-0010
labels:
  - type:feature
  - area:skills
---

# [CARD-901] YAML Feature

## 1. Why / Intent (Beat 1)
This is a test intent for the YAML feature.
""",
        encoding="utf-8",
    )

    # Card 2: Markdown blockquote format (Done)
    card2 = cards_dir / "CARD-902-blockquote-bug.md"
    card2.write_text(
        """# [CARD-902] Blockquote Bug

> **Status**: Done
> **Created**: 2026-09-18
> **Completed**: 2026-09-19
> **Labels**: `type:bug`, `area:wiki`
> **ADR Reference**: ADR-0020

## 1. Why / Intent
Fixing a blockquote bug.
""",
        encoding="utf-8",
    )

    # Card 3: Parked card
    card3 = cards_dir / "CARD-903-parked-idea.md"
    card3.write_text(
        """# [CARD-903] Parked Idea

> **Status**: Parked (holding)
> **Labels**: `type:idea`

## 1. Why / Intent
Parked for later.
""",
        encoding="utf-8",
    )

    # 1. Default run should ONLY return open card (CARD-901)
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(res.stdout)
    assert len(data) == 1
    assert data[0]["id"] == "CARD-901"
    assert data[0]["status"] == "Ready"
    assert "area:skills" in data[0]["labels"]
    assert "test intent for the YAML feature" in data[0]["intent"]

    # 2. --all should return all 3 cards
    res_all = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--all", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data_all = json.loads(res_all.stdout)
    assert len(data_all) == 3

    # 3. --done should return CARD-902
    res_done = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--done", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data_done = json.loads(res_done.stdout)
    assert len(data_done) == 1
    assert data_done[0]["id"] == "CARD-902"

    # 4. --parked should return CARD-903
    res_parked = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--parked", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data_parked = json.loads(res_parked.stdout)
    assert len(data_parked) == 1
    assert data_parked[0]["id"] == "CARD-903"

    # 5. --search across content
    res_search = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--search", "ADR-0020", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data_search = json.loads(res_search.stdout)
    assert len(data_search) == 1
    assert data_search[0]["id"] == "CARD-902"

    # 6. --label filtering
    res_label = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--label", "area:wiki", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data_label = json.loads(res_label.stdout)
    assert len(data_label) == 1
    assert data_label[0]["id"] == "CARD-902"

    # 7. --card inspector view
    res_card = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--card", "901"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "[CARD-901] YAML Feature" in res_card.stdout
    assert "Status:       Ready (open)" in res_card.stdout
    assert "Intent / Why (Beat 1):" in res_card.stdout
    assert "test intent for the YAML feature" in res_card.stdout

    # 8. --recent 2 returns 903 and 902
    res_recent = subprocess.run(
        [sys.executable, str(SCRIPT), "--cards-dir", str(cards_dir), "--recent", "2", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data_recent = json.loads(res_recent.stdout)
    assert len(data_recent) == 2
    assert data_recent[0]["id"] == "CARD-903"
    assert data_recent[1]["id"] == "CARD-902"
