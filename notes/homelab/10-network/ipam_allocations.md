---
doc_type: ipam_table
owner_role: homelab-architect
scope: network
last_verified: "2026-09-09"
status: active
---

# Enterprise Homelab IPAM Static Allocation Sheet

Fixed IP reservations for core physical equipment, virtual machines, and management endpoints.

## Static IP Allocation Registry

| IP Address | Hostname / Entity | Subnet | Role | Notes / MAC Reference |
| :--- | :--- | :--- | :--- | :--- |
| `10.10.10.1` | `p-hl01-gw01` | `MGMT` | Core Firewall / Gateway | OPNSense / pfSense Router |
| `10.10.10.2` | `p-hl01-sw01` | `MGMT` | Core Managed Switch | 24-Port Gigabit L3 Switch |
| `10.10.10.10` | `p-hl01-hvh01` | `MGMT` | Hyper-V Physical Host 01 | Primary Hyper-V Hypervisor Host |
| `10.10.10.11` | `p-hl01-idrac01`| `MGMT` | Out-of-band IPMI/iDRAC | Server Hardware Remote Console |
| `10.10.20.10` | `p-hl01-dc01` | `SERVERS`| Primary Domain Controller | Active Directory Forest Root & DNS |
| `10.10.20.11` | `p-hl01-dc02` | `SERVERS`| Secondary Domain Controller | AD DS Replica & Secondary DNS |
| `10.10.20.20` | `p-hl01-ca01` | `SERVERS`| Certificate Authority (PKI) | Active Directory Certificate Services |
| `10.10.20.30` | `p-hl01-dbs01` | `SERVERS`| Database Server | PostgreSQL 16 Cluster Engine |
| `10.10.40.10` | `p-hl01-rpx01` | `DMZ` | Reverse Proxy Load Balancer | Traefik / NGINX Ingress Proxy |
| `10.10.40.20` | `p-hl01-vpn01` | `DMZ` | Remote Access Gateway | WireGuard / IPsec Gateway |

## Allocation Guidelines for Specialists
- `homelab-engineer`: Before authoring an OpenTofu VM configuration, consult this table and `vlan_matrix.md` to avoid IP address collisions.
- `homelab-admin`: When a new node is provisioned, register its allocated static IP in this sheet.
