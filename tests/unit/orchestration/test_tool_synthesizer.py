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


def test_synthesize_windows_services_tool_not_hyperv():
    """CARD-171: services/sysadmin briefs must not emit Hyper-V Get-VM costume."""
    files_map = ToolSynthesizer.synthesize_tool(
        agent_id="win-services-atf",
        seed_intent="List Windows services status for operators",
        objectives=[
            "List all Windows services with Status, StartType, and DisplayName",
            "Filter services by name pattern",
        ],
    )
    assert "tools/manage_win_services_atf.py" in files_map
    assert "tools/manage_win_services_atf.ps1" in files_map
    py_code = files_map["tools/manage_win_services_atf.py"]
    ps1_code = files_map["tools/manage_win_services_atf.ps1"]
    skill = files_map["skills/win_services_atf/SKILL.md"]
    assert "Get-Service" in py_code or "Get-Service" in ps1_code
    assert "Hyper-V\\Get-VM" not in py_code.replace("\\\\", "\\")
    assert "Hyper-V\\Get-VM" not in ps1_code
    assert "Import-Module Hyper-V" not in py_code
    assert "virtual machine" not in skill.lower()
    assert "Purpose" in skill
    assert "Starter Objectives" in skill or "Objectives" in skill
    assert "Status" in skill or "service" in skill.lower()


def test_is_hyperv_domain_vs_services():
    assert ToolSynthesizer.is_hyperv_domain("hyperv-lab", "unattend ISO Hyper-V template", ["Mount OS ISO"]) is True
    assert (
        ToolSynthesizer.is_hyperv_domain("win-services-atf", "List Windows services status", ["List services"]) is False
    )


def test_objectives_with_apostrophe_do_not_break_python():
    files_map = ToolSynthesizer.synthesize_tool(
        agent_id="svc-quote",
        seed_intent="List Windows services",
        objectives=["Report a service's StartType"],
    )
    py_code = files_map["tools/manage_svc_quote.py"]
    # Must be valid Python
    compile(py_code, "<tool>", "exec")


def test_hyperv_tool_focus_recognizes_create_action():
    focus = ToolSynthesizer._hyperv_tool_focus(
        tool_name="manage_hyperv_vm",
        seed_intent="manage hyperv virtual machines",
        objectives=["status", "list", "get", "create", "start", "stop", "checkpoint"],
    )
    assert focus == "vm"


def test_synthesize_tool_with_grounded_project_manifest():
    manifest = {
        "target_directory": "D:\\Projects\\Exprimentation\\Homelab",
        "discovered_binaries": ["powershell.exe", "tofu.exe", "ansible-playbook"],
        "files_tree": [
            {"relative_path": "tofu/blueprints/enterprise-windows-domain/main.tf", "format": "opentofu"},
            {"relative_path": "ansible/playbooks/01_gateway_network.yml", "format": "ansible"},
            {"relative_path": "automation/infra/powershell/Test-LabHealth.ps1", "format": "powershell"},
        ],
    }
    files = ToolSynthesizer.synthesize_tool(
        agent_id="homelab-admin",
        seed_intent="Manage homelab infrastructure using OpenTofu and Ansible",
        objectives=["Deploy domain", "Configure network", "Verify lab health"],
        manifest=manifest,
    )
    assert "tools/manage_homelab_admin.py" in files
    assert "skills/homelab_admin/SKILL.md" in files
    py_code = files["tools/manage_homelab_admin.py"]
    skill_md = files["skills/homelab_admin/SKILL.md"]

    assert "tofu" in py_code.lower()
    assert "ansible" in py_code.lower()
    assert "D:\\\\Projects\\\\Exprimentation\\\\Homelab" in py_code or "Homelab" in py_code
    assert "## Overview" in skill_md or "## Purpose" in skill_md
    assert "tofu" in skill_md.lower()
    assert "ansible" in skill_md.lower()

    # Execute verification test harness code against the generated tool
    test_code = ToolSynthesizer.generate_verification_test("manage_homelab_admin")
    scope = {}
    exec(compile(py_code, "manage_homelab_admin.py", "exec"), scope)
    test_scope = {"manage_homelab_admin": scope["manage_homelab_admin"]}
    exec(compile(test_code.replace("from tool import manage_homelab_admin", ""), "<test>", "exec"), test_scope)


def test_synthesize_tool_with_hyperv_driver_and_existing_tool_augmentation():
    manifest = {
        "target_directory": "D:\\Projects\\Exprimentation\\Homelab",
        "discovered_binaries": ["powershell.exe", "tofu.exe"],
        "files_tree": [
            {"relative_path": "orchestration/LabManager.ps1", "format": "powershell"},
            {"relative_path": "orchestration/providers/HyperVDriver.psm1", "format": "powershell"},
            {"relative_path": "orchestration/New-UnattendIso.ps1", "format": "powershell"},
        ],
    }
    existing_tool_code = """
VALID_ACTIONS = {"status", "tofu_plan", "ansible_playbook", "checkpoint_lab"}
"""
    files = ToolSynthesizer.synthesize_tool(
        agent_id="homelab-admin",
        seed_intent="Manage Hyper-V VM lifecycle, switch configuration, and build unattend ISOs",
        objectives=["List lab VMs", "Start lab VMs", "Stop lab VMs", "Build unattend ISO"],
        manifest=manifest,
        existing_tool_code=existing_tool_code,
    )
    py_code = files["tools/manage_homelab_admin.py"]
    skill_md = files["skills/homelab_admin/SKILL.md"]
    assert "name: homelab_admin" in skill_md
    assert "Build unattend ISO" in skill_md or "Start lab VMs" in skill_md

    # Check preserved existing actions
    assert "tofu_plan" in py_code
    assert "ansible_playbook" in py_code
    assert "checkpoint_lab" in py_code

    # Check new synthesized Hyper-V driver and ISO actions
    assert "list_vms" in py_code or "vms" in py_code
    assert "start_vms" in py_code
    assert "stop_vms" in py_code
    assert "build_iso" in py_code

    # Verify execution via test harness
    scope = {}
    exec(compile(py_code, "manage_homelab_admin.py", "exec"), scope)
    fn = scope["manage_homelab_admin"]
    res_dry = fn(action="start_vms", dry_run=True)
    assert res_dry["success"] is True
    assert res_dry["action"] == "start_vms"

    res_iso = fn(action="build_iso", dry_run=True)
    assert res_iso["success"] is True
