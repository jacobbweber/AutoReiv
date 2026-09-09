---
doc_type: vlan_matrix
owner_role: homelab-architect
scope: network
last_verified: "2026-09-09"
status: active
---

# Enterprise Homelab VLAN & Subnet Matrix

Canonical allocation table of network segments, 802.1Q tags, gateway addresses, and DHCP policies.

## Subnet Allocation Table

| VLAN ID | Name | Subnet (CIDR) | Gateway | DHCP Scope | Purpose & Security Zone |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **10** | `MGMT` | `10.10.10.0/24` | `10.10.10.1` | Disabled (Static only) | Hyper-V hosts, IPMI/iDRAC, managed switches, PDU |
| **20** | `SERVERS` | `10.10.20.0/24` | `10.10.20.1` | `10.10.20.100 - .200` | Core infrastructure VMs (AD DS, DNS, CA, DB) |
| **30** | `APPS` | `10.10.30.0/24` | `10.10.30.1` | `10.10.30.50 - .250` | Application workloads, Docker containers, web services |
| **40** | `DMZ` | `10.10.40.0/24` | `10.10.40.1` | Disabled (Static only) | External-facing reverse proxies and bastion hosts |
| **50** | `STORAGE` | `10.10.50.0/24` | `10.10.50.1` | Disabled (Static only) | iSCSI, SMB3 multichannel, and NFS storage networks |
| **99** | `SANDBOX` | `10.10.99.0/24` | `10.10.99.1` | `10.10.99.50 - .250` | Isolated ephemeral test VMs and testing environments |

## Inter-VLAN Routing Invariants
- `VLAN 40 (DMZ)` cannot initiate connections into `VLAN 10 (MGMT)` or `VLAN 20 (SERVERS)` except on specific service ports (e.g., LDAP 636, Kerberos 88).
- `VLAN 99 (SANDBOX)` is air-gapped with no route to `VLAN 10` or `VLAN 20`.
- All management protocols (SSH 22, WinRM 5985/5986, RDP 3389) are strictly restricted to `VLAN 10`.
