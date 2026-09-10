---
name: opentofu-hyperv
description: Declarative Infrastructure as Code runbook for Windows Domain homelab provisioning on Hyper-V using OpenTofu.
---

# OpenTofu Hyper-V Skill Runbook

Declarative, reproducible virtual machine and network provisioning on Hyper-V hosts using OpenTofu configuration templates.

## Overview
This runbook governs the authoring, compiler-guided syntax validation, dry-run planning, and state lifecycle management of Hyper-V infrastructure resources. All domain resources must adhere to strict network isolation invariants to safeguard host physical networking.

## Architectural Rules & Invariants
- **Isolated Virtual Switch**: Always attach lab virtual machines to a dedicated `Internal` or `Private` switch (e.g. `DomainSwitch`). **NEVER bind virtual machines directly to host physical adapters or external bridge interfaces.**
- **Gen2 Virtual Machines**: All Windows Domain Controllers (`DC01`, `DC02`) and member servers (`FS01`) must be provisioned as `generation = 2` with static RAM allocations and synthetic SCSI controllers.
- **Compiler-Guided Feedback**: Whenever `tofu validate` or `tofu plan` emits HCL syntax errors, parse compiler diagnostics (`extract_hcl_diagnostics`) and iteratively correct configuration arguments prior to execution.

## Tool Invocation Sequence
1. **Host Capacity Inspection**:
   ```python
   manage_opentofu_hyperv(action="inspect_host")
   ```
   Confirm sufficient host RAM and CPU core availability.

2. **Configuration Authoring**:
   Author HCL templates targeting `infra/homelab` with `hyperv_vmswitch` (`DomainSwitch`, `switch_type = "Internal"`) and `hyperv_machine_instance` resources for `dc01`, `dc02`, and `fs01`.

3. **Compiler Syntax Validation**:
   ```python
   manage_opentofu_hyperv(action="validate", config_path="infra/homelab")
   ```
   If errors occur, extract diagnostics and refine HCL parameters.

4. **Execution Plan Generation (Dry-Run)**:
   ```python
   manage_opentofu_hyperv(action="plan", config_path="infra/homelab", dry_run=True)
   ```
   Inspect projected additions and verify zero unexpected resource destruction.

5. **Human Approval Gate**:
   Present the validated plan summary to the human operator for explicit confirmation before executing `apply`.

## Common Diagnostics & Corrections
- **Unsupported argument `switch_name` in older provider schemas**:
  Ensure network adaptors use nested block:
  ```hcl
  network_adaptors {
    name        = "Ethernet"
    switch_name = hyperv_vmswitch.domain_switch.name
  }
  ```
- **Generation Mismatch**:
  Always set `generation = 2` for modern UEFI and Secure Boot support.

## Done-When
- OpenTofu configuration passes `tofu validate` with zero compiler errors.
- Dry-run plan confirms creation of `DomainSwitch` (Internal) and 3 Gen2 VMs (`DC01`, `DC02`, `FS01`).
- Plan is reviewed and approved for apply by the human operator.
