"""
Unit tests for Homelab Fleet Packs, OpenTofu tool, and skills [CARD-198, REQ-FLEET-004, REQ-FLEET-005, REQ-FLEET-006].
"""

import json
from pathlib import Path

import pytest

from src.application.skills.opentofu_tools import OpenTofuHyperVTools
from src.domain.agents.profiles import (
    HOMELAB_ADMIN_PROFILE,
    HOMELAB_ARCHITECT_PROFILE,
    HOMELAB_COORDINATOR_PROFILE,
    HOMELAB_ENGINEER_PROFILE,
    HOMELAB_JANITOR_PROFILE,
    get_homelab_profile,
)

GOLD_STANDARD_SECTIONS = [
    "[IDENTITY & ROLE]",
    "[DOMAIN BOUNDARIES & REFUSALS]",
    "[EXECUTION PROTOCOL]",
    "[SAFETY & APPROVALS]",
    "[TOOL USAGE RULES]",
    "[OUTPUT FORMAT]",
]

MATT_POCOCK_SECTIONS = [
    "## Overview",
    "## Tools",
    "## Order",
    "## Pitfalls",
    "## Done-when",
]


def test_homelab_fleet_profiles_defined_and_valid():
    """Verify the 5 homelab fleet profiles have correct visibility, fleet, and 6-section system prompts."""
    profiles = [
        HOMELAB_COORDINATOR_PROFILE,
        HOMELAB_ARCHITECT_PROFILE,
        HOMELAB_ENGINEER_PROFILE,
        HOMELAB_ADMIN_PROFILE,
        HOMELAB_JANITOR_PROFILE,
    ]

    for p in profiles:
        assert p.fleet == "homelab"
        assert p.id.startswith("homelab")
        # System prompt must contain all 6 gold-standard sections
        for sec in GOLD_STANDARD_SECTIONS:
            assert sec in p.system_prompt, f"Missing {sec} in {p.id} prompt"

    # Only lead coordinator is public and visible in chat
    assert HOMELAB_COORDINATOR_PROFILE.visibility == "public"
    assert HOMELAB_COORDINATOR_PROFILE.show_in_chat is True

    # All 4 specialists are internal and hidden from chat
    for spec in [
        HOMELAB_ARCHITECT_PROFILE,
        HOMELAB_ENGINEER_PROFILE,
        HOMELAB_ADMIN_PROFILE,
        HOMELAB_JANITOR_PROFILE,
    ]:
        assert spec.visibility == "internal"
        assert spec.show_in_chat is False

    # Profiles map retrieval
    assert get_homelab_profile("homelab") is HOMELAB_COORDINATOR_PROFILE
    assert get_homelab_profile("homelab-architect") is HOMELAB_ARCHITECT_PROFILE
    assert get_homelab_profile("homelab-engineer") is HOMELAB_ENGINEER_PROFILE
    assert get_homelab_profile("homelab-admin") is HOMELAB_ADMIN_PROFILE
    assert get_homelab_profile("homelab-janitor") is HOMELAB_JANITOR_PROFILE


def test_homelab_platform_pack_files_exist():
    """Verify platform-packs contains all 5 homelab packs as 1:1 packs with valid pack.json [CARD-199, CARD-201]."""
    repo_root = Path(__file__).resolve().parents[3]
    platform_packs_dir = repo_root / "platform-packs"

    expected_packs = {
        "homelab": {"visibility": "public", "show_in_chat": True},
        "homelab-architect": {"visibility": "internal", "show_in_chat": False},
        "homelab-engineer": {"visibility": "internal", "show_in_chat": False},
        "homelab-admin": {"visibility": "internal", "show_in_chat": False},
        "homelab-janitor": {"visibility": "internal", "show_in_chat": False},
    }

    for pack_id, expected_meta in expected_packs.items():
        pack_json_path = platform_packs_dir / pack_id / "pack.json"
        assert pack_json_path.is_file(), f"Missing pack.json for {pack_id}"
        with open(pack_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("id") == pack_id
        assert data.get("fleet") == "homelab"
        assert data.get("visibility") == expected_meta["visibility"]
        assert data.get("show_in_chat") == expected_meta["show_in_chat"]

        prompt = data.get("system_prompt", "")
        for sec in GOLD_STANDARD_SECTIONS:
            assert sec in prompt, f"Missing {sec} in {pack_id}/pack.json"


def test_homelab_skills_matt_pocock_structure():
    """Verify homelab pack skills adhere to Matt Pocock 5 sections and YAML frontmatter [CARD-199, CARD-201]."""
    repo_root = Path(__file__).resolve().parents[3]
    skill_path = (
        repo_root
        / "platform-packs"
        / "homelab-engineer"
        / "skills"
        / "manage-opentofu-hyperv"
        / "SKILL.md"
    )
    assert skill_path.is_file(), f"Missing SKILL.md at {skill_path}"
    content = skill_path.read_text(encoding="utf-8")

    assert content.startswith("---")
    assert "name: manage-opentofu-hyperv" in content

    for heading in MATT_POCOCK_SECTIONS:
        assert heading in content, f"Missing heading {heading} in manage-opentofu-hyperv/SKILL.md"


@pytest.mark.asyncio
async def test_manage_opentofu_hyperv_dry_run_and_actions():
    """Verify manage_opentofu_hyperv tool behavior with safe dry-run mode."""
    tools = OpenTofuHyperVTools()

    # Plan action with dry_run
    res_plan = await tools.manage_opentofu_hyperv(
        action="plan",
        config_path="infra/homelab",
        variables={"vm_name": "test-vm-01", "vlan": 10},
        dry_run=True,
    )
    assert res_plan["status"] == "ok"
    assert res_plan["action"] == "plan"
    assert res_plan["dry_run"] is True
    assert "plan" in res_plan

    # Apply with dry_run=True should simulate and NOT execute destructive apply
    res_apply_dry = await tools.manage_opentofu_hyperv(
        action="apply",
        config_path="infra/homelab",
        dry_run=True,
    )
    assert res_apply_dry["status"] == "ok"
    assert res_apply_dry["dry_run"] is True
    assert "dry-run" in res_apply_dry["message"].lower() or "dry_run" in res_apply_dry["message"].lower()

    # Host inspection action
    res_host = await tools.manage_opentofu_hyperv(
        action="inspect_host",
    )
    assert res_host["status"] == "ok"
    assert "host_info" in res_host

    # Invalid action check
    res_invalid = await tools.manage_opentofu_hyperv(
        action="unsupported_action",
    )
    assert res_invalid["status"] == "error"
