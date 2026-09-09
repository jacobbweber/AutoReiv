---
doc_type: host_spec
owner_role: homelab-admin
scope: compute
last_verified: "2026-09-09"
status: active
---

# Homelab Virtual Machine Catalog

Active inventory of provisioned virtual machines, allocated compute resources, and disk paths.

## Virtual Machine Inventory

| VM Name | OS / Distribution | Tier | Assigned IP | Switch / VLAN | Generation | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `p-hl01-dc01` | Windows Server 2022 | Medium (T4) | `10.10.20.10` | `vSwitch-External` (20) | Gen 2 | Running |
| `p-hl01-dc02` | Windows Server 2022 | Small (T3) | `10.10.20.11` | `vSwitch-External` (20) | Gen 2 | Running |
| `p-hl01-dbs01` | Ubuntu 24.04 LTS | Large (T5) | `10.10.20.30` | `vSwitch-External` (20) | Gen 2 | Running |
| `p-hl01-rpx01` | Alpine Linux 3.20 | Micro (T2) | `10.10.40.10` | `vSwitch-External` (40) | Gen 2 | Running |
| `p-hl01-mon01` | Debian 12 (Bookworm) | Medium (T4) | `10.10.20.40` | `vSwitch-External` (20) | Gen 2 | Running |

## Golden Template Catalog
- `tmpl-win2022-datacenter`: Generation 2 Windows Server 2022 template with VirtIO/Hyper-V integration tools and Sysprep generalization.
- `tmpl-ubuntu2404-server`: Generation 2 UEFI Ubuntu 24.04 LTS cloud-init generalized template.
- `tmpl-debian12-minimal`: Generation 2 minimal Debian 12 base image.
