"""
Unit tests for ToolSynthesizer [REQ-FACT-009, REQ-FACT-016, REQ-FACT-017].
"""

import pytest

from src.application.orchestration.tool_synthesizer import ToolSynthesizer


def test_is_powershell_or_system_domain():
    assert ToolSynthesizer.is_powershell_or_system_domain("hyperv") is True
    assert ToolSynthesizer.is_powershell_or_system_domain("sysadmin", "Manage windows services") is True
    assert ToolSynthesizer.is_powershell_or_system_domain("vm-builder", "create virtual machines") is True
    assert ToolSynthesizer.is_powershell_or_system_domain("bot", "seed intent", ["New-VM cmdlet"]) is True
    assert ToolSynthesizer.is_powershell_or_system_domain("writer", "Write marketing copy") is False


def test_synthesize_powershell_tool_files():
    files_map = ToolSynthesizer.synthesize_tool(
        agent_id="hyperv",
        seed_intent="Provision and configure virtual machines with RAM, vCPU, and VHDX disks on Hyper-V",
        objectives=["Create VM with RAM and vCPU", "Attach VHDX virtual hard disk"],
    )

    assert "tools/manage_hyperv.py" in files_map
    assert "tools/manage_hyperv.ps1" in files_map
    assert "skills/hyperv/SKILL.md" in files_map

    py_code = files_map["tools/manage_hyperv.py"]
    ps1_code = files_map["tools/manage_hyperv.ps1"]

    # Verify real PowerShell cmdlets exist and are fully qualified with Hyper-V\ [REQ-FACT-029]
    assert "powershell.exe" in py_code
    assert "Import-Module Hyper-V" in py_code
    assert "Hyper-V\\\\New-VM" in py_code
    assert "Hyper-V\\\\Get-VM" in py_code
    assert "Hyper-V\\\\Start-VM" in py_code
    assert "Hyper-V\\\\Stop-VM" in py_code
    assert "Hyper-V\\\\Checkpoint-VM" in py_code

    # Verify PowerShell script contains real cmdlets and error handling with module qualification [REQ-FACT-029, REQ-FACT-030]
    assert "param(" in ps1_code
    assert "Import-Module Hyper-V" in ps1_code
    assert "Hyper-V\\New-VM" in ps1_code
    assert "Hyper-V\\New-VHD" in ps1_code
    assert "ConvertTo-Json" in ps1_code

    # Verify no disallowed path traversal patterns ("C:\)
    assert '"C:\\' not in py_code


def test_synthesize_generic_tool_files():
    files_map = ToolSynthesizer.synthesize_tool(
        agent_id="data-analyst",
        seed_intent="Analyze customer churn CSV records",
    )

    assert "tools/manage_data_analyst.py" in files_map
    assert "skills/data_analyst/SKILL.md" in files_map
    assert "tools/manage_data_analyst.ps1" not in files_map

    py_code = files_map["tools/manage_data_analyst.py"]
    assert "manage_data_analyst" in py_code


def test_generate_verification_test():
    test_code = ToolSynthesizer.generate_verification_test("manage_hyperv")
    assert "from tool import manage_hyperv" in test_code
    assert "inspect.signature" in test_code
    assert "assert callable(manage_hyperv)" in test_code


@pytest.mark.asyncio
async def test_synthesized_powershell_tool_passes_4_stage_battery():
    from src.application.orchestration.verification_battery import VerificationBatteryService

    files_map = ToolSynthesizer.synthesize_tool(
        agent_id="hyperv",
        seed_intent="Manage Hyper-V VMs",
    )
    tool_code = files_map["tools/manage_hyperv.py"]
    skill_content = files_map["skills/hyperv/SKILL.md"]
    test_code = ToolSynthesizer.generate_verification_test("manage_hyperv")

    battery = VerificationBatteryService()
    eval_pkt = await battery.run_battery(
        tool_code=tool_code,
        test_code=test_code,
        skill_content=skill_content,
        repeats=3,
    )

    assert eval_pkt.passed is True
    assert eval_pkt.stage_1_functional is True
    assert eval_pkt.stage_2_safety is True
    assert eval_pkt.stage_3_idempotency is True
    assert eval_pkt.stage_4_critic is True


def test_synthesized_skill_has_agentskills_yaml_frontmatter():
    import yaml

    files_map = ToolSynthesizer.synthesize_tool(
        agent_id="hyperv",
        seed_intent="Manage Hyper-V virtual machines and disks",
        objectives=["Create VM", "Manage VHDX"],
    )
    skill_content = files_map["skills/hyperv/SKILL.md"]

    assert skill_content.startswith("---\n")
    parts = skill_content.split("---", 2)
    assert len(parts) >= 3
    frontmatter = yaml.safe_load(parts[1])
    assert isinstance(frontmatter, dict)
    assert "name" in frontmatter and len(frontmatter["name"]) > 2
    assert "description" in frontmatter and len(frontmatter["description"]) > 5


def test_evaluate_skill_runbook():
    files_map = ToolSynthesizer.synthesize_tool(
        agent_id="hyperv",
        seed_intent="Manage Hyper-V VMs",
    )
    tool_code = files_map["tools/manage_hyperv.py"]
    skill_content = files_map["skills/hyperv/SKILL.md"]

    report = ToolSynthesizer.evaluate_skill_runbook(skill_content=skill_content, tool_code=tool_code)
    assert report["passed"] is True
    assert report["frontmatter_valid"] is True
    assert report["language_feasibility"] is True
    assert report["action_parity"] is True

    # Failure mode on bad / missing frontmatter
    bad_skill = "# No frontmatter\n## Purpose\nJust markdown."
    bad_report = ToolSynthesizer.evaluate_skill_runbook(skill_content=bad_skill, tool_code=tool_code)
    assert bad_report["passed"] is False
    assert bad_report["frontmatter_valid"] is False


