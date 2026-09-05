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

    # Verify real PowerShell cmdlets exist
    assert "powershell.exe" in py_code
    assert "New-VM" in py_code
    assert "Get-VM" in py_code
    assert "Start-VM" in py_code
    assert "Stop-VM" in py_code
    assert "Checkpoint-VM" in py_code

    # Verify PowerShell script contains real cmdlets and error handling
    assert "param(" in ps1_code
    assert "New-VM" in ps1_code
    assert "New-VHD" in ps1_code
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
    test_code = ToolSynthesizer.generate_verification_test("manage_hyperv")

    battery = VerificationBatteryService()
    eval_pkt = await battery.run_battery(
        tool_code=tool_code,
        test_code=test_code,
        repeats=3,
    )

    assert eval_pkt.passed is True
    assert eval_pkt.stage_1_functional is True
    assert eval_pkt.stage_2_safety is True
    assert eval_pkt.stage_3_idempotency is True
    assert eval_pkt.stage_4_critic is True

