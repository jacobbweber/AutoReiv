---
doc_type: template
owner_role: homelab-admin
scope: compute
last_verified: "2026-09-09"
status: template
---

# Template: Physical Hypervisor Host Specification

Use this template when commissioning or documenting a physical compute/virtualization host.

## Physical Host: `[Hostname]`

### 1. Hardware Specifications
- **Hardware Model**: `[Model]`
- **Processor (CPU)**: `[Socket count, Model, Cores, Frequency]`
- **RAM**: `[Total Capacity, Speed, Channel configuration]`
- **Operating System**: `[OS & Version / Build]`
- **Host Management IP**: `[IP]`
- **Out-of-Band Management (IPMI/iDRAC/iLO)**: `[IP]`

### 2. Storage Topology
| Volume Name | Media Type | Total Size | Host Mount Path | Allocation Target |
| :--- | :--- | :--- | :--- | :--- |
| `[Volume]` | `[NVMe/SSD/HDD]` | `[Size]` | `[Path]` | `[Purpose]` |

### 3. Virtual Switches
| Switch Name | Switch Type | Physical Uplink | VLAN Trunking Enabled |
| :--- | :--- | :--- | :--- |
| `[Name]` | `[External/Internal/Private]` | `[NIC Name]` | `[Yes/No]` |
