---
doc_type: governance_spec
owner_role: homelab-architect
scope: network
last_verified: "2026-09-09"
status: active
---

# Enterprise Homelab DNS Zones & Name Resolution

Authoritative domain namespace layout, forward/reverse lookup zones, and DNS forwarders.

## Primary Forward Zones

| Zone Name | Type | Primary Server | Secondary Server | Dynamic Updates |
| :--- | :--- | :--- | :--- | :--- |
| `corp.homelab.internal` | Active Directory Integrated | `10.10.20.10` (`p-hl01-dc01`) | `10.10.20.11` (`p-hl01-dc02`) | Secure only (802.1X / AD joined) |
| `lab.homelab.internal` | Primary Forward Zone | `10.10.20.10` | `10.10.20.11` | Non-secure and secure |
| `dmz.homelab.internal` | Split-Horizon DNS | `10.10.40.10` | N/A | None (Static A/CNAME records) |

## Reverse Lookup Zones (PTR)
- `10.10.10.in-addr.arpa`: Subnet `10.10.10.0/24` (Management)
- `20.10.10.in-addr.arpa`: Subnet `10.10.20.0/24` (Core Servers)
- `30.10.10.in-addr.arpa`: Subnet `10.10.30.0/24` (Applications)

## Upstream Forwarders
- Primary Forwarder: `1.1.1.1` (Cloudflare DNS over TLS)
- Fallback Forwarder: `9.9.9.9` (Quad9 Secure DNS)
