"""
Tests for Autonomous Homelab Domain Orchestration & Self-Learning Pipeline [CARD-206, REQ-HOMELAB-001 - REQ-HOMELAB-006].
"""

import json
from pathlib import Path

from src.application.orchestration.homelab_domain_recipe import (
    generate_domain_topology_hcl,
    get_homelab_domain_workflow_recipe,
)
from src.application.skills.opentofu_tools import extract_hcl_diagnostics

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_opentofu_compiler_diagnostic_parsing():
    """Verify compiler errors are parsed into structured diagnostics [REQ-HOMELAB-004]."""
    sample_tofu_error = """
Error: Unsupported argument

  on main.tf line 42, in resource "hyperv_machine_instance" "dc01":
  42:   switch_name = "DomainSwitch"

An argument named "switch_name" is not expected here. Did you mean "switch_id"?
"""
    diagnostics = extract_hcl_diagnostics(sample_tofu_error)
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag["line"] == 42
    assert diag["file"] == "main.tf"
    assert "Unsupported argument" in diag["summary"]
    assert "switch_name" in diag["detail"]


def test_opentofu_domain_topology_generation_safety_invariants():
    """Verify generated domain HCL enforces isolated internal switch and 3 Gen2 VMs [REQ-HOMELAB-002, REQ-HOMELAB-003]."""
    hcl = generate_domain_topology_hcl(
        domain_name="lab.local",
        subnet="10.10.10.0/24",
        switch_name="DomainSwitch",
    )
    # Safety Invariant: Must use Internal or Private switch, NEVER External
    assert 'resource "hyperv_vmswitch" "domain_switch"' in hcl
    assert 'switch_type = "Internal"' in hcl or 'switch_type = "Private"' in hcl
    assert "External" not in hcl

    # Subnet invariant: 10.10.10.0/24
    assert "10.10.10." in hcl

    # Must contain DC01, DC02, FS01
    assert '"dc01"' in hcl
    assert '"dc02"' in hcl
    assert '"fs01"' in hcl

    # Gen2 VM requirements
    assert "generation = 2" in hcl


def test_opentofu_hyperv_skill_runbook_exists_and_valid():
    """Verify SKILL.md for OpenTofu Hyper-V is present and structured [REQ-HOMELAB-004]."""
    skill_file = REPO_ROOT / "skills" / "opentofu-hyperv" / "SKILL.md"
    assert skill_file.is_file(), f"Expected skill file at {skill_file}"
    content = skill_file.read_text(encoding="utf-8")
    assert "name: opentofu-hyperv" in content
    assert "DomainSwitch" in content
    assert "Internal" in content


def test_homelab_domain_deployment_workflow_recipe_chapters():
    """Verify 4-chapter relay recipe [REQ-HOMELAB-001, REQ-HOMELAB-006]."""
    recipe = get_homelab_domain_workflow_recipe()
    assert recipe["name"] == "homelab-domain-deployment"
    assert recipe["owner_agent_id"] == "homelab"
    chapters = recipe["chapters"]
    assert len(chapters) == 4

    # Chapter 1: Admin
    assert chapters[0]["assigned_agent_id"] == "homelab-admin"
    # Chapter 2: Architect
    assert chapters[1]["assigned_agent_id"] == "homelab-architect"
    # Chapter 3: Engineer
    assert chapters[2]["assigned_agent_id"] == "homelab-engineer"
    # Chapter 4: Admin / Engineer validate & plan
    assert chapters[3]["assigned_agent_id"] in ("homelab-admin", "homelab-engineer")


def test_homelab_engineer_equipped_with_skill():
    """Verify homelab-engineer pack allows opentofu-hyperv skill [REQ-HOMELAB-004]."""
    pack_file = REPO_ROOT / "platform-packs" / "homelab-engineer" / "pack.json"
    assert pack_file.is_file()
    data = json.loads(pack_file.read_text(encoding="utf-8"))
    allowed_skills = data.get("allowed_skill", [])
    assert "opentofu-hyperv" in allowed_skills or any("opentofu" in s for s in allowed_skills)
