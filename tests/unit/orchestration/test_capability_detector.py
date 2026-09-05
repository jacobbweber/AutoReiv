"""
Unit tests for CapabilityDetector turn-time analysis & capability extraction [REQ-FACT-027, REQ-FACT-028].
"""

import pytest
from src.application.orchestration.capability_detector import CapabilityDetector


def test_extract_capabilities_from_powershell_response():
    resp = """
I don't have command execution tools (cli_exec, system_info, etc.) available in this session — only a document reader. I can't run PowerShell or interact with your Hyper-V host directly.

To create "billy" yourself, run this in an elevated PowerShell on the Hyper-V host:

# Create the VM (4 GB RAM, 2 vCPU)
New-VM -Name "billy" -MemoryStartupBytes 4GB -Generation 2
Set-VM -Name "billy" -ProcessorCount 2

# Create + attach a 64 GB VHDX
New-VHD -Path "C:\\HyperV\\VMs\\billy\\billy.vhdx" -SizeBytes 64GB | Out-Null
Add-VMHardDiskDrive -VMName "billy" -Path "C:\\HyperV\\VMs\\billy\\billy.vhdx"

# Attach to your external switch (adjust name)
Add-VMSwitch -Name "billy" -SwitchName "Default Switch" -VMName "billy"
"""
    # Even if user prompt was a generic retry "can you try again":
    extracted = CapabilityDetector.extract_capabilities_from_turn(
        user_prompt="can you try again",
        assistant_response=resp,
        agent_id="hyperv",
        agent_name="Hyper-V Specialist",
    )

    assert "Hyper-V" in extracted["identified_capability"] or "Virtual Machine" in extracted["identified_capability"]
    assert "New-VM" in extracted["turn_text"] or "Virtual Machine" in extracted["turn_text"]
    assert extracted["suggested_tool_name"].startswith(("hyperv_", "vm_"))
    assert len(extracted["objectives"]) >= 2


def test_extract_capabilities_from_cli_commands():
    resp = """
I cannot execute Docker commands directly on this host. Run these commands:
docker run -d -p 8080:80 --name webserver nginx:latest
docker compose up -d
"""
    extracted = CapabilityDetector.extract_capabilities_from_turn(
        user_prompt="start an nginx container",
        assistant_response=resp,
        agent_id="docker-admin",
        agent_name="Docker Admin",
    )

    assert "Docker" in extracted["identified_capability"]
    assert "docker" in extracted["suggested_tool_name"]


def test_extract_capabilities_standard_missing_tool():
    resp = "I don't have the tools to query Active Directory users or reset domain passwords."
    extracted = CapabilityDetector.extract_capabilities_from_turn(
        user_prompt="reset password for user jsmith",
        assistant_response=resp,
        agent_id="sysadmin",
        agent_name="System Admin",
    )

    assert "Active Directory" in extracted["identified_capability"] or "password" in extracted["identified_capability"].lower()
    assert extracted["suggested_tool_name"] is not None
