---
doc_type: template
owner_role: homelab-architect
scope: network
last_verified: "2026-09-09"
status: template
---

# Template: VLAN & Subnet Matrix Specification

Use this template when defining new network segments, VLAN tags, or subnets in `notes/homelab/10-network/`.

## 1. Network Zone Overview
- **Zone Name**: `[e.g., IOT, DMZ, STORAGE]`
- **VLAN ID**: `[e.g., 60]`
- **Subnet CIDR**: `[e.g., 10.10.60.0/24]`
- **Default Gateway**: `[e.g., 10.10.60.1]`
- **Security Zone**: `[e.g., Restricted / Isolated]`

## 2. IP Allocation Sub-Ranges
- **Reserved Infrastructure**: `[e.g., 10.10.60.1 - 10.10.60.20]`
- **DHCP Dynamic Pool**: `[e.g., 10.10.60.50 - 10.10.60.200]`
- **Static Workloads**: `[e.g., 10.10.60.201 - 10.10.60.254]`

## 3. Firewall & Routing Invariants
- Allowed outbound destinations: `[...]`
- Prohibited intra-zone communication: `[...]`
