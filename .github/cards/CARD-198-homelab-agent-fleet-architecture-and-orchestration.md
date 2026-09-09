# [CARD-198] Homelab Agent Fleet Architecture and Orchestration

> **Status**: Done
> **Created**: 2026-09-09
> **Spec Reference**: `docs/specs/homelab-fleet-orchestration/requirements.md`
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Three Beats

### Beat 1: What you mean
Your homelab is a major target for AutoReiv. The homelab will host and operate complete enterprise-grade IT systems, servers, applications, networks, identity domains, and services—functioning like a full-blown IT company. Managing Hyper-V hosts, virtual machines, networking subnets, Terraform infrastructure-as-code, Ansible configuration playbooks, guest OS provisioning, Windows Active Directory domains, and cleanup is far too large for a single agent.

To scale reliably without confusion or bloated prompts, you want:
1. **A Specialized Homelab Fleet** organized by lifecycle responsibility:
   - **`homelab` (Lead Coordinator)**: The single visible front-of-house agent in Chat Studio. You converse with this agent. It coordinates requests, consults homelab blueprints, delegates tasks to internal specialists, and presents unified summaries back to you.
   - **`homelab-architect`**: Focuses purely on system design and blueprints. Plans network topology, IP ranges, VM resource sizing, and domain layouts. Writes and maintains these plans as cataloged Wiki documents.
   - **`homelab-engineer`**: Focuses on implementation. Takes the architect's blueprints and writes the Infrastructure as Code (Terraform `.tf` files, Ansible playbooks `.yml`, setup scripts).
   - **`homelab-admin`**: Focuses on operational execution and health. Provisions VMs on the Hyper-V host, executes playbooks, promotes domain controllers, and monitors service statuses.
   - **`homelab-janitor`**: Focuses on environment hygiene. Cleans orphan disks/checkpoints, rotates logs, prunes decommissioned resources, and flags configuration drift.

2. **An Enterprise IT Documentation Framework & Template Library (Under `notes/homelab/`)**:
   - To keep documentation permanently consistent, accurate, and structured over time across all IT domains, establish a formal documentation framework inside the existing Wiki notes directory (`notes/homelab/`).
   - **Critical Boundary**: Zero changes or impact to the existing Wiki engine, routers, or database. Homelab documentation purely uses the existing Wiki note system, living strictly under `notes/homelab/`.
   - Just like an enterprise IT organization, documentation must be categorized into standard directories:
     - `notes/homelab/10-network`: VLAN sheets, IPAM subnet allocation tables, DNS zones, firewall/gateway rules.
     - `notes/homelab/20-compute`: Physical Hyper-V host specifications, virtual switches, storage volumes, VM templates.
     - `notes/homelab/30-identity`: Active Directory domain hierarchy, OUs, service account policies, Kerberos/LDAP setups.
     - `notes/homelab/40-services`: Application inventory, port mapping matrix, SSL/TLS certificate tracker.
     - `notes/homelab/50-runbooks`: Standard Operating Procedures (SOPs) for provisioning, backups, patching, and disaster recovery.
   - Standardized templates with YAML front-matter (`doc_type`, `owner_role`, `scope`, `last_verified`) so every document is predictable.

3. **Specialized Homelab Lookup Skills**:
   - Rather than guessing or searching blindly, homelab agents have dedicated skills to locate the exact reference sheets they need (for example: an engineer checking `notes/homelab/10-network/vlan_matrix.md` before generating a VM config).
   - These lookup skills and templates belong exclusively to the homelab fleet—they do not clutter unrelated agents.

4. **Deprecating the Monolithic Hyper-V Agent in Favor of Skills & MCP**:
   - The standalone `hyperv` agent is dropped from the top-level agent roster.
   - Hyper-V operations become a capability layer: an **OpenTofu / Hyper-V MCP tool provider** and procedural **skills** (runbooks) that the `homelab-engineer` (for IaC authoring) and `homelab-admin` (for VM provisioning and operations) leverage.

5. **Single Front-of-House Visibility**:
   - In Chat Studio, only the lead `homelab` agent is visible in the dropdown. The specialized workers (`architect`, `engineer`, `admin`, `janitor`) run as internal workers under the coordinator so your chat interface remains uncluttered.

6. **Live Dogfooding of AutoReiv Refinements**:
   - The entire Homelab Fleet is created and trained using AutoReiv itself: using the Agent Studio Socratic discovery / Quick Scaffold modal, and training its skills/tools through the 8-stage Training Factory pipeline. This serves as the end-to-end live test of the CARD-197 refinements.

---

### Beat 2: What AutoReiv does now
1. **Hyper-V Agent & Tool Coupling**:
   - There are legacy hardcoded Hyper-V builders and references in `src/application/orchestration/hyperv_tool_builders.py` and `blueprint.py` treating Hyper-V as a dedicated top-level agent rather than a reusable OpenTofu skill/tool capability.
2. **Flat Agent List**:
   - Every agent in `packs/` appears in the Agent Studio list and the Chat Studio agent selector (`#chatAgentSelect`). There is no distinction between public/visible agents and internal specialist workers.
3. **Single-Agent Scope**:
   - Chat Studio interacts with one agent at a time. An agent does not currently have a built-in coordination protocol to automatically delegate a sub-task to another agent pack and receive the output.
4. **Wiki Usage Today**:
   - AutoReiv has a functioning Wiki system (`WikiService`) that stores notes under `notes/` and categories (`inbox`, `01_Projects`, `02_Areas`, `03_Resources`).
   - There is no standardized IT documentation framework or seed templates specifically under `notes/homelab/`, and no domain-specific lookup runbooks for infrastructure roles.
   - The Wiki engine itself works and must remain completely untouched.

---

### Beat 3: What will change (Proposed Architecture & Refinements)

#### 1. Agent Pack Visibility (`pack.json`)
- Add an optional `"visibility"` field to agent manifests:
  - `"visibility": "public"` (default): Visible in Chat Studio and top-level selectors.
  - `"visibility": "internal"`: Hidden from Chat Studio dropdowns; designated as a delegated worker or fleet specialist.
- Agent Studio displays internal agents under an expandable "Internal / Fleet Workers" section so they can still be inspected, trained, and tested.

#### 2. The Homelab Fleet Role Blueprint
Define starter profiles and pack definitions for the 5 homelab roles:
- **`homelab` (Lead)**:
  - System prompt: Orchestrator directive. Analyzes incoming homelab goals, reads Wiki blueprints, coordinates the fleet, requests human confirmation for destructive actions, and reports progress.
  - Tools/Skills: `delegate_to_fleet_agent`, `search_homelab_wiki`.
- **`homelab-architect`**:
  - System prompt: Architectural designer. Creates, reviews, and updates infrastructure blueprints, IP address plans, and service definitions in `wiki/homelab/`.
- **`homelab-engineer`**:
  - System prompt: Infrastructure as Code specialist. Generates and lints Terraform configs and Ansible playbooks matching architectural specs.
- **`homelab-admin`**:
  - System prompt: Infrastructure operator. Executes Terraform plans and Ansible runs against the Hyper-V host and guest environments with safety checks.
- **`homelab-janitor`**:
  - System prompt: Maintenance and hygiene operator. Scans for orphaned VHDX disks, stale snapshots, and expired logs, proposing cleanup actions.

#### 3. Standardized Homelab IT Documentation Framework & Template Library
Establish an enterprise-grade taxonomy and seed template library strictly under the existing notes directory (`notes/homelab/`):
- **Directory Hierarchy**:
  - `notes/homelab/00-governance/`: Sizing tiers (Small/Medium/Large VMs), naming standards, secret handling conventions.
  - `notes/homelab/10-network/`:
    - `vlan_matrix.md`: VLAN IDs, subnets, gateways, purpose, DHCP scopes.
    - `ipam_allocations.md`: Reserved static IPs, DHCP ranges, hypervisor IPs.
    - `dns_zones.md`: Internal domain forward/reverse lookup zones.
  - `notes/homelab/20-compute/`:
    - `hyperv_hosts.md`: Physical host hardware specs, CPU cores, RAM, storage LUNs, virtual switch names.
    - `vm_catalog.md`: Registered VMs, assigned resources, OS versions, disk locations.
  - `notes/homelab/30-identity/`:
    - `active_directory.md`: Forest root, domain naming, OU structure, service account standards.
  - `notes/homelab/40-services/`:
    - `port_matrix.md`: Allocated host and container ports, reverse proxy mappings.
    - `certificates.md`: Internal CA certificates, expirations, and domains.
  - `notes/homelab/50-runbooks/`:
    - Standard Operating Procedures (e.g., `sop-provision-vm.md`, `sop-join-domain.md`, `sop-expand-disk.md`).
- **Standard Front-Matter Metadata**:
  All homelab notes follow a strict YAML front-matter schema:
  ```yaml
  ---
  doc_type: vlan_matrix | ipam_table | host_spec | ad_plan | port_matrix | sop_runbook
  owner_role: homelab-architect | homelab-admin
  scope: global | network | compute | identity | services
  last_verified: 2026-09-09
  status: active | draft | deprecated
  ---
  ```

#### 4. Homelab-Scoped Domain Lookup Skills
Create dedicated lookup runbook skills packaged exclusively into homelab agent packs:
- `lookup-network-spec`: Teaches agents where the VLAN and IPAM documents live under `notes/homelab/10-network/` and how to extract available IPs/subnets before generating network configurations.
- `lookup-host-spec`: Teaches agents how to read Hyper-V virtual switch names and available host storage from `notes/homelab/20-compute/` before authoring VM configs.
- `lookup-service-ports`: Teaches agents how to query `notes/homelab/40-services/port_matrix.md` to prevent port collisions when deploying new applications.
- General platform agents do not receive these skills, keeping skills modular and tightly scoped.

#### 5. Fleet Delegation Protocol
- Provide a standard orchestration tool/skill for the lead `homelab` agent to execute tasks through an internal specialist pack (e.g. `invoke_specialist(agent_id, task_brief)`), injecting relevant notes context and collecting structured results.

#### 6. OpenTofu / Hyper-V Capability & MCP Transition
- Transition Hyper-V from a dedicated top-level agent into:
  1. An OpenTofu execution skill (`manage-opentofu-hyperv`) for declarative VM provisioning and state management.
  2. An MCP tool provider / local tool wrapper for direct hypervisor inspection (host specs, VM power states).
- Modularize hardcoded Hyper-V synthesis logic into reusable IaC tool definitions.

#### 7. Live Factory Dogfooding & Pipeline Verification
- Create the 5 homelab fleet agents using AutoReiv's actual Agent Studio Socratic discovery / Quick Scaffold modal.
- Train their initial skills and tools through the 8-stage Training Factory pipeline (`FactoryOrchestrator`), exercising phase duration tracking, self-healing code repair, Matt Pocock runbooks, and HITL deliverable inspection.

---

## 2. Technical Scope & Affected Components

1. **Agent Manifest & Domain**:
   - `src/domain/agents/models.py` / `pack.json`: Support `"visibility": "public" | "internal"` and `"fleet": "homelab"`.
   - `src/domain/agents/profiles.py`: Fleet profiles for `homelab`, `homelab-architect`, `homelab-engineer`, `homelab-admin`, and `homelab-janitor`.
2. **Homelab Documentation Framework & Templates**:
   - `notes/homelab/`: Standard IT directory hierarchy (`00-governance`, `10-network`, `20-compute`, `30-identity`, `40-services`, `50-runbooks`) created as standard markdown notes.
   - `notes/homelab/templates/`: Reusable markdown templates with YAML front-matter schemas for VLAN tables, IPAM sheets, host specs, and SOPs.
3. **Homelab-Specific Skills & OpenTofu Tooling**:
   - `packs/homelab/skills/` or `platform-packs/homelab/skills/`:
     - `lookup-network-spec/SKILL.md`: Targeted runbook for consulting network sheets.
     - `lookup-host-spec/SKILL.md`: Targeted runbook for consulting hypervisor/storage specs.
     - `manage-opentofu-hyperv/SKILL.md`: Runbook for OpenTofu-driven Hyper-V provisioning.
4. **Orchestration & Delegation**:
   - `src/application/orchestration/fleet_coordinator.py`: Structured handoff mechanism allowing a coordinator agent to delegate sub-tasks to internal specialist packs with notes context.
5. **Web UI**:
   - `src/web/static/modules/studios/chat.js`: Filter `#chatAgentSelect` to only display `"public"` agents.
   - `src/web/static/modules/studios/forge.js`: Group internal/fleet agents in Agent Studio.

---

## 3. Acceptance Criteria (When Scheduled for Implementation)

- [x] `pack.json` supports a `"visibility"` property (`"public"` or `"internal"`), with Chat Studio filtering out `"internal"` agents from the primary chat selector.
- [x] Agent Studio displays fleet grouping for related agents (e.g., all `homelab-*` specialists grouped under `homelab`).
- [x] Predefined role profiles and starter packs established for the 5 Homelab roles (`homelab`, `homelab-architect`, `homelab-engineer`, `homelab-admin`, `homelab-janitor`).
- [x] Monolithic Hyper-V agent decoupled in favor of OpenTofu/Hyper-V skills and MCP/tool capabilities for the homelab fleet.
- [x] Standardized Enterprise IT Homelab documentation framework created strictly under `notes/homelab/` with directories for governance, network, compute, identity, services, and runbooks.
- [x] Reusable Markdown templates with YAML front-matter schemas created for VLAN tables, IPAM allocations, host specs, and SOP runbooks.
- [x] Scoped lookup skills (`lookup-network-spec`, `lookup-host-spec`) packaged specifically for homelab fleet agents.
- [x] Delegation skill/tool allowing the lead `homelab` agent to assign scoped tasks to internal fleet agents and receive structured outputs.
- [x] Homelab fleet agents, skills, and tools trained and verified directly through AutoReiv's 8-stage Training Factory.
- [x] Automated unit tests for visibility filtering, fleet delegation, and notes template validation.
- [x] Zero lint errors via `ruff` and `eslint`.

---

## 4. Constraints & Honor Flags
- **Zero Wiki Engine Impact Invariant**: The existing Wiki system, `WikiService`, routers, database, and categories (`inbox`, `01_Projects`, `02_Areas`, `03_Resources`) remain 100% untouched. Homelab documentation strictly adds markdown note files under `notes/homelab/` using existing Wiki capabilities.
- Adheres to AGENTS.md working agreement: one primitive at a time.
- No third-party product names in cards or UI artifacts.
- Domain application data remains in `<agent_slug>_storage.db`; cognitive agent memory remains in `<agent_slug>_memory.db`.
- Shared cross-agent infrastructure knowledge lives under `notes/homelab/`.
- Homelab lookup skills are strictly scoped to the homelab pack fleet and do not pollute general platform agents.
