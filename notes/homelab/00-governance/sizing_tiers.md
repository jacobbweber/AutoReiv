---
doc_type: governance_spec
owner_role: homelab-architect
scope: governance
last_verified: "2026-09-09"
status: active
---

# Homelab Compute & VM Sizing Tiers

Standard resource quotas and hardware allocation profiles across all virtual machines and containers.

## Standard Virtual Machine Tiers

| Tier Name | vCPU Cores | RAM (GB) | OS Disk (VHDX) | Data Disk | Typical Workload Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Nano (T1)** | 1 vCPU | 1 GB | 30 GB | Optional | DNS forwarder, NTP server, lightweight edge proxy |
| **Micro (T2)** | 2 vCPU | 2 GB | 40 GB | Optional | DHCP, jumpbox, monitoring node, telemetry collector |
| **Small (T3)** | 2 vCPU | 4 GB | 60 GB | 100 GB | Secondary Domain Controller, reverse proxy (NGINX/Traefik) |
| **Medium (T4)** | 4 vCPU | 8 GB | 80 GB | 250 GB | Primary Domain Controller, GitLab runner, internal API gateway |
| **Large (T5)** | 6 vCPU | 16 GB | 100 GB | 500 GB | Docker container host, database engine (PostgreSQL/MSSQL) |
| **X-Large (T6)** | 8 vCPU | 32 GB | 120 GB | 1000 GB | Big data, centralized ELK/Grafana Loki log pipeline |

## Memory Overcommit & Dynamic Memory Invariants
1. **Domain Controllers (`DC01`, `DC02`)**: Static RAM only. Dynamic memory is strictly prohibited to prevent Kerberos ticket sync drift.
2. **Database Servers**: Static RAM configured to maximum database buffer pool sizing.
3. **Application & Worker Nodes**: Dynamic RAM allowed with minimum buffer `1024 MB` and maximum buffer set to tier upper bound.
