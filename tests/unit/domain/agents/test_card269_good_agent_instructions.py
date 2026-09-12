"""CARD-269: good-agent Instructions template + pack backfill."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.agents.good_agent_instructions import (
    REQUIRED_INSTRUCTION_SECTIONS,
    assert_good_agent_sections,
    render_good_agent_instructions,
)

ROOT = Path(__file__).resolve().parents[4]


def test_required_sections_are_stable():
    assert "[IDENTITY & ROLE]" in REQUIRED_INSTRUCTION_SECTIONS
    assert "[PROVENANCE & HONESTY]" in REQUIRED_INSTRUCTION_SECTIONS
    assert len(REQUIRED_INSTRUCTION_SECTIONS) >= 7


def test_render_includes_all_sections():
    prompt = render_good_agent_instructions(
        name="Assistant",
        role="day-to-day assistant",
        domain_focus="daily tasks",
        mission_bullets=["Help organize the day."],
    )
    assert assert_good_agent_sections(prompt) == []
    assert "Assistant" in prompt
    assert "HITL" in prompt


@pytest.mark.parametrize(
    "pack_path",
    [
        ROOT / "platform-packs" / "assistant" / "pack.json",
        ROOT / "platform-packs" / "autoreiv" / "pack.json",
        ROOT / "packs" / "finance" / "pack.json",
    ],
)
def test_backfilled_packs_match_template(pack_path: Path):
    assert pack_path.is_file(), pack_path
    data = json.loads(pack_path.read_text(encoding="utf-8"))
    missing = assert_good_agent_sections(data.get("system_prompt") or "")
    assert missing == [], f"{pack_path.name} missing {missing}"


def test_forge_scaffold_includes_provenance():
    forge = (ROOT / "src" / "web" / "static" / "modules" / "studios" / "forge.js").read_text(
        encoding="utf-8"
    )
    assert "[PROVENANCE & HONESTY]" in forge
    assert "buildQuickScaffoldPayload" in forge
