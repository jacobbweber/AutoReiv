"""Unit tests for AutoReiv pack alignment and shell tool exclusion [CARD-407, REQ-407-003, REQ-407-004].

Enforces negative assertions that AutoReiv never carries raw shell tool cli_exec,
that platform-health uses application telemetry, and that shell execution is delegated
to developer via handoff_to_agent.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.application.agent_packs.schema import DYNAMIC_SKILL_TOOLS


def test_autoreiv_pack_excludes_cli_exec():
    repo_root = Path(__file__).resolve().parents[3]
    pack_json_path = repo_root / "platform-packs" / "autoreiv" / "pack.json"
    assert pack_json_path.exists(), f"Missing {pack_json_path}"

    with open(pack_json_path, "r", encoding="utf-8") as f:
        pack_data = json.load(f)

    # 1. pack_tool_names must not contain cli_exec
    pack_tools = pack_data.get("pack_tool_names", [])
    assert "cli_exec" not in pack_tools, "cli_exec must not be in autoreiv pack_tool_names"

    # 2. None of autoreiv's skill definitions may include cli_exec
    for skill in pack_data.get("skills", []):
        skill_tools = skill.get("tools", [])
        assert "cli_exec" not in skill_tools, (
            f"cli_exec must not be in skill '{skill.get('id')}' for autoreiv"
        )

    # 3. System prompt must direct shell requests to developer and notes to 00_Inbox/
    system_prompt = pack_data.get("system_prompt", "")
    assert "developer" in system_prompt
    assert "00_Inbox" in system_prompt


def test_dynamic_skill_tools_exclude_cli_exec():
    # Diagnostics and platform-health must never inject cli_exec into packs
    assert "cli_exec" not in DYNAMIC_SKILL_TOOLS.get("platform-health", [])
    assert "cli_exec" not in DYNAMIC_SKILL_TOOLS.get("diagnostics", [])


def test_platform_health_skill_md_excludes_cli_exec():
    repo_root = Path(__file__).resolve().parents[3]
    skill_md_path = (
        repo_root / "platform-packs" / "autoreiv" / "skills" / "platform-health" / "SKILL.md"
    )
    assert skill_md_path.exists(), f"Missing {skill_md_path}"

    content = skill_md_path.read_text(encoding="utf-8")
    assert "cli_exec" not in content, "platform-health SKILL.md must not reference cli_exec"
    assert "developer" in content, "platform-health SKILL.md should advise handoff to developer"
    assert "00_Inbox" in content, "platform-health SKILL.md should instruct saving to 00_Inbox/"
