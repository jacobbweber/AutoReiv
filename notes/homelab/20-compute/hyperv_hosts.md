---
doc_type: host_spec
owner_role: homelab-admin
scope: compute
last_verified: "2026-09-09"
status: active
---

# Physical Hyper-V Hypervisor Host Specification

Hardware inventory, NUMA nodes, storage pools, and virtual switches for primary compute hosts.

## Physical Host: `p-hl01-hvh01`

### Hardware Configuration
- **Manufacturer / Model**: Custom Enterprise Rackmount 2U
- **CPU**: Dual AMD EPYC 7302 (32 Cores / 64 Threads total @ 3.0 GHz)
- **Memory**: 128 GB DDR4 ECC Registered (4 x 32 GB Quad-Channel)
- **Host Operating System**: Windows Server 2022 Datacenter (Core / GUI)
- **Management IP**: `10.10.10.10` (VLAN 10 MGMT)
- **iDRAC / IPMI IP**: `10.10.10.11`

### Storage Pools & Volume Layout
| Volume / Drive | Bus / Interface | Usable Capacity | Path on Host | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `C:\` | NVMe PCIe Gen4 | 500 GB | `C:\` | OS, Hyper-V Hypervisor, System Logs |
| `D:\VMs` | NVMe RAID-1 | 2.0 TB | `D:\HyperV\VirtualMachines` | Fast I/O Tier (Active VMs, DBs, Domain Controllers) |
| `E:\Templates` | SATA SSD RAID-5 | 4.0 TB | `E:\HyperV\Templates` | Golden OS ISOs, Autounattend ISOs, Template VHDXs |
| `F:\Backups` | HDD RAID-6 | 12.0 TB | `F:\HyperV\Backups` | Local snapshot exports and weekly Veeam VM backups |

### Configured Virtual Switches
- `vSwitch-External`: Bound to physical 10GbE NIC `NIC1`. VLAN Trunking enabled (VLAN IDs 10, 20, 30, 40, 50, 99).
- `vSwitch-Internal`: Host-only private NAT switch for isolated sandboxes.
