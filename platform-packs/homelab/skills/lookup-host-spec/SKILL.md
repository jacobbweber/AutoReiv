---
name: lookup-host-spec
description: Inspect physical Hyper-V host capacity, CPU, RAM, virtual switch mappings, and storage pools from notes/homelab/20-compute/.
---

# Lookup Host Spec

Retrieve and verify physical hypervisor resource allocations, hardware capacity, storage volumes, and virtual switch topology prior to VM provisioning.

## Overview
This runbook provides the operational procedure for querying compute documentation under `notes/homelab/20-compute/`. Ensuring adequate physical CPU cores, unallocated RAM, and disk LUN capacity prevents resource starvation and deployment failures.

## Tools
- `lookup_homelab_docs`: Primary query tool for retrieving compute specifications, host catalogs, and switch topologies.
- `manage_opentofu_hyperv`: Optional live inspection tool with `action="inspect_host"` to corroborate documented capacity against live system telemetry.

## Order
1. **Query Host Documentation**: Call `lookup_homelab_docs(category="20-compute", query="hosts")` to retrieve physical hardware parameters and storage LUN paths.
2. **Review VM Catalog**: Call `lookup_homelab_docs(category="20-compute", query="vm_catalog")` to sum current resource commitments across active virtual machines.
3. **Check Resource Headroom**: Compare committed vCPU and RAM against host maximums, adhering to the sizing tiers in `notes/homelab/00-governance/sizing_tiers.md`.
4. **Identify Virtual Switch**: Verify the exact virtual switch name (e.g., `External-VLAN-Trunk`) to bind the virtual network adapter to.
5. **Verify Storage Path**: Identify the correct physical disk path or storage pool (e.g., `C:\Hyper-V\Virtual Hard Disks`) for VHDX placement.

## Pitfalls
- **Overcommitting RAM**: Hyper-V does not dynamically balance memory beyond physical limits without dynamic memory configuration; ensure minimum startup RAM is available.
- **Wrong Switch Name**: Specifying a nonexistent switch name halts OpenTofu apply during NIC creation.
- **Path Typos**: Hardcoding incorrect storage paths results in hypervisor disk creation errors.

## Done-when
- Physical host hardware constraints and target virtual switch name identified from `notes/homelab/20-compute/hyperv_hosts.md`.
- Sizing tier (Small, Medium, Large) selected according to `notes/homelab/00-governance/sizing_tiers.md`.
- Available storage path confirmed for virtual disk allocation.
