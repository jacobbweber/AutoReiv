"""Unit tests for AutoReiv pack alignment and shell tool exclusion [CARD-407, REQ-407-003, REQ-407-004].

Enforces that AutoReiv carries cli_exec only through software-development (ADR-0067 / CARD-729,
approval per call) and that platform-health and diagnostics use application telemetry, never a shell.
"""

from __future__ import annotations

from pathlib import Path

from tests.unit.agent_skills.catalog import SHIPPED_SKILL_TOOLS as DYNAMIC_SKILL_TOOLS
from tests.unit.agent_skills.catalog import pack_dict


def test_autoreiv_pack_gets_cli_exec_only_through_software_development():
    """Amended by ADR-0067 / CARD-729 (Jacob decision 2026-10-18): project commands run through cli_exec, which only
    the software-development skill grants; every other ticked skill stays shell-free."""
    pack_data = pack_dict("autoreiv")  # CARD-570: platform/agents/autoreiv.md + its skills

    for skill in pack_data.get("skills", []):
        skill_tools = skill.get("tools", [])
        if skill.get("id") == "software-development":
            assert "cli_exec" in skill_tools
            continue
        assert "cli_exec" not in skill_tools, (
            f"cli_exec must not be in skill '{skill.get('id')}' for autoreiv"
        )

    # 3. System prompt directs out-of-scope to covering agent/Ask Developer, notes to 00_Inbox/
    system_prompt = pack_data.get("system_prompt", "")
    assert "open in Chat" in system_prompt and "Ask Developer" not in system_prompt  # CARD-615: kernel adds it
    assert "00_Inbox" in system_prompt


def test_dynamic_skill_tools_exclude_cli_exec():
    # Diagnostics and platform-health must never inject cli_exec into packs
    assert "cli_exec" not in DYNAMIC_SKILL_TOOLS.get("platform-health", [])
    assert "cli_exec" not in DYNAMIC_SKILL_TOOLS.get("diagnostics", [])


def test_platform_health_skill_md_excludes_cli_exec():
    repo_root = Path(__file__).resolve().parents[3]
    skill_md_path = (
        repo_root / "platform" / "skills" / "platform-health" / "SKILL.md"
    )
    assert skill_md_path.exists(), f"Missing {skill_md_path}"

    content = skill_md_path.read_text(encoding="utf-8")
    assert "cli_exec" not in content, "platform-health SKILL.md must not reference cli_exec"
    assert "Developer" in content or "developer" in content.lower(), "platform-health SKILL.md advises opening Developer"
    assert "00_Inbox" in content, "platform-health SKILL.md should instruct saving to 00_Inbox/"
