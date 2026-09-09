---
doc_type: template
owner_role: homelab-architect
scope: network
last_verified: "2026-09-09"
status: template
---

# Template: IPAM Static Allocation Sheet

Use this template when recording static IP address reservations.

## Static IP Allocation Registry

| IP Address | Hostname / Entity | Subnet | Role | MAC Address | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[IP]` | `[Hostname]` | `[Subnet Name]` | `[Role]` | `[MAC]` | `[Notes]` |

## Allocation Checklist
- [ ] Confirmed IP falls within the static reservation block of the subnet.
- [ ] Added DNS forward (A) record in authoritative zone.
- [ ] Added DNS reverse (PTR) record in matching in-addr.arpa zone.
