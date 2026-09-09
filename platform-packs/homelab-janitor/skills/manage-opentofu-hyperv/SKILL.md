---
name: manage-opentofu-hyperv
description: Declarative VM lifecycle and infrastructure provisioning on Hyper-V using OpenTofu configuration files.
---

# Manage OpenTofu Hyper-V

Declarative, reproducible virtual machine and infrastructure lifecycle management on Hyper-V hosts using OpenTofu configurations and state files.

## Overview
This runbook governs the authoring, validation, planning, and safe execution of OpenTofu configurations targeting Hyper-V infrastructure. All infrastructure modifications must follow declarative IaC workflows rather than ad-hoc manual hypervisor adjustments.

## Tools
- `manage_opentofu_hyperv`: Execute OpenTofu actions (`init`, `validate`, `plan`, `apply`, `destroy`, `inspect_host`, `get_vm_status`).
- `cli_exec`: Execute guarded CLI operations and infrastructure diagnostics.

## Order
1. **Gather Parameters**: Consult `notes/homelab/10-network/` and `notes/homelab/20-compute/` to establish VM name, sizing tier, VLAN ID, and static IP.
2. **Inspect Host State**: Call `manage_opentofu_hyperv(action="inspect_host")` to confirm hypervisor availability and virtual switch bindings.
3. **Validate Configuration**: Call `manage_opentofu_hyperv(action="validate", config_path="infra/homelab")` to ensure syntax integrity.
4. **Generate Execution Plan (Dry-Run)**: Call `manage_opentofu_hyperv(action="plan", config_path="infra/homelab", variables={...}, dry_run=True)` to inspect projected changes.
5. **Request Human Confirmation**: If destructive changes or resource additions are planned, present the plan summary to the human for approval.
6. **Apply Plan**: Upon approval, execute `manage_opentofu_hyperv(action="apply", config_path="infra/homelab", dry_run=False)`.
7. **Verify Provisioning**: Query VM status with `manage_opentofu_hyperv(action="get_vm_status", vm_name="...")` to verify power state and network connectivity.

## Pitfalls
- **Skipping Dry-Run**: Never run `apply` without executing and reviewing `plan` in dry-run mode first.
- **State File Desync**: Avoid out-of-band manual changes in Hyper-V Manager to prevent state drift.
- **Missing Provider Plugins**: Ensure `action="init"` has been completed before attempting validation or planning.

## Done-when
- OpenTofu configuration validated and plan reviewed with zero unexpected destructions.
- Virtual machine successfully provisioned in the desired power state.
- Operational details (IP address, MAC address, switch port) verified and logged in the homelab inventory.
