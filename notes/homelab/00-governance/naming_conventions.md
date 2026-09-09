---
doc_type: governance_spec
owner_role: homelab-architect
scope: governance
last_verified: "2026-09-09"
status: active
---

# Enterprise Homelab Naming Conventions

Deterministic hostname, subnet, and resource naming standards to maintain enterprise order across all IT assets.

## Hostname Naming Schema

All nodes follow the structured syntax:
`[env]-[site]-[role][index].[domain]`

### Components:
- **`env`**: Environment tier
  - `p` = Production / Core homelab
  - `s` = Staging / Pre-flight
  - `d` = Development / Sandbox
  - `l` = Lab / Ephemeral
- **`site`**: Location or cluster ID
  - `hl01` = Primary Homelab Rack 1
  - `dmz` = Demilitarized zone / edge
- **`role`**: 3-letter workload descriptor
  - `hvh` = Hyper-V Host
  - `dc` = Active Directory Domain Controller
  - `rpx` = Reverse Proxy
  - `app` = Application Server
  - `dbs` = Database Server
  - `mon` = Monitoring / Observability
  - `ans` = Automation / Ansible control node
- **`index`**: 2-digit sequential integer (`01`, `02`, `03`)

### Examples:
- `p-hl01-hvh01` = Production Homelab Primary Hyper-V Host 01
- `p-hl01-dc01` = Production Primary Domain Controller 01
- `p-hl01-rpx01` = Production Edge Reverse Proxy 01
- `d-hl01-app01` = Development Application Worker 01

## Virtual Switch Naming Standard
- `vSwitch-Management`: Untagged physical management traffic.
- `vSwitch-Trunk`: 802.1Q tagged VLAN trunking for guest VMs.
- `vSwitch-Private`: Host-only isolated virtual switch for sandbox experiments.
