---
name: lookup-network-spec
description: Inspect enterprise homelab network topology, VLAN IDs, subnets, and IPAM allocations from notes/homelab/10-network/.
---

# Lookup Network Spec

Consult and verify enterprise network topology, VLAN boundaries, and IP address management allocations before configuring infrastructure or virtual machines.

## Overview
This runbook provides the operational procedure for querying network blueprints in `notes/homelab/10-network/`. Always inspect allocated subnets, reserved gateway addresses, and DNS zones prior to authoring or deploying network-dependent configurations.

## Tools
- `lookup_homelab_docs`: Primary query tool for retrieving categorized network notes and IPAM allocation tables.

## Order
1. **Identify Required Network Scope**: Determine whether the target workload requires access to Management (VLAN 10), Servers (VLAN 20), DMZ (VLAN 30), or Storage (VLAN 40).
2. **Query VLAN Matrix**: Call `lookup_homelab_docs(category="10-network", query="vlan")` to inspect the canonical VLAN matrix and gateway definitions.
3. **Query IPAM Allocations**: Call `lookup_homelab_docs(category="10-network", query="ipam")` to identify reserved static IP blocks and available address ranges.
4. **Extract Target IP & DNS**: Select the next available static IP within the chosen subnet, ensuring it falls outside the DHCP dynamic lease pool. Verify forward/reverse DNS records in `dns_zones.md`.
5. **Pass Parameters to Engineer/Admin**: Include the verified VLAN ID, CIDR subnet, gateway, and chosen static IP in the execution brief.

## Pitfalls
- **IP Collision**: Never assign an IP address without checking `ipam_allocations.md` for existing static reservations.
- **Gateway Overwrite**: Do not allocate `.1` or `.254` if designated as gateway or router interfaces.
- **VLAN Mismatch**: Ensure the target Hyper-V virtual switch trunk is configured to pass the selected VLAN ID tag.

## Done-when
- Verified VLAN ID and CIDR subnet retrieved from `notes/homelab/10-network/vlan_matrix.md`.
- Unique unallocated static IP confirmed from `notes/homelab/10-network/ipam_allocations.md`.
- Network configuration parameters validated against governance naming standards.
