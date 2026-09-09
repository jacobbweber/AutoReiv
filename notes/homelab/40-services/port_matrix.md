---
doc_type: port_matrix
owner_role: homelab-architect
scope: services
last_verified: "2026-09-09"
status: active
---

# Enterprise Homelab Port Allocation Matrix

Port reservation registry across physical hosts, containers, and reverse proxy frontends to eliminate port conflicts.

## Standard Ingress & Host Port Mappings

| Port | Protocol | Service / Application | Host / VM | Internal URL | Security Zone |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **80** | TCP | HTTP (Auto-redirect to 443) | `p-hl01-rpx01` | `http://*.homelab.internal` | DMZ |
| **443** | TCP | HTTPS (TLS Ingress Proxy) | `p-hl01-rpx01` | `https://*.homelab.internal` | DMZ |
| **53** | TCP/UDP | DNS Name Resolution | `p-hl01-dc01`, `dc02` | `dns://10.10.20.10` | SERVERS |
| **88** | TCP/UDP | Kerberos Authentication | `p-hl01-dc01`, `dc02` | `corp.homelab.internal` | SERVERS |
| **389** | TCP/UDP | LDAP Directory Services | `p-hl01-dc01`, `dc02` | `ldap://corp.homelab.internal`| SERVERS |
| **636** | TCP | LDAPS (Secure LDAP over TLS)| `p-hl01-dc01`, `dc02` | `ldaps://corp.homelab.internal`| SERVERS |
| **3389** | TCP | Remote Desktop (RDP) | Host & Admin VMs | Direct RDP | MGMT |
| **5985** | TCP | WinRM HTTP (Disabled) | N/A | None | Blocked |
| **5986** | TCP | WinRM HTTPS (Encrypted) | All Windows Nodes | `https://*:5986/wsman` | MGMT |
| **5432** | TCP | PostgreSQL Database | `p-hl01-dbs01` | `postgresql://10.10.20.30:5432`| SERVERS |
| **9090** | TCP | Prometheus Metrics Collector| `p-hl01-mon01` | `http://10.10.20.40:9090` | SERVERS |
| **3000** | TCP | Grafana Observability Portal| `p-hl01-mon01` | `https://grafana.homelab.internal`| APPS |

## Conflict Prevention Rules
- Specialists authoring new container stacks or web services must reserve ports in this document before binding to `0.0.0.0`.
- All web applications must route through `p-hl01-rpx01` via SNI hostname on port `443` rather than exposing non-standard raw ports.
