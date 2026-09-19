# Requirements Specification: Homelab Agent Fleet Architecture and Orchestration

> **Spec Status**: Approved  
> **Target Release**: CARD-198  
> **Primary Component**: AutoReiv.Fleet & AutoReiv.Orchestration

---

## 1. Executive Summary & Intent
Establish an enterprise-grade IT Homelab Agent Fleet architecture and orchestration capability for AutoReiv. Decouple the monolithic Hyper-V agent into modular OpenTofu / Hyper-V capabilities and runbook skills. Introduce agent visibility (`public` vs `internal`) and fleet grouping so only the lead `homelab` agent is exposed in Chat Studio, while 4 internal specialists (`homelab-architect`, `homelab-engineer`, `homelab-admin`, `homelab-janitor`) are orchestrated in the background. Establish an enterprise IT documentation framework and template library strictly under `notes/homelab/` with zero impact on the existing Wiki engine.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-FLEET-001]: Agent Visibility and Fleet Grouping
- **Type**: State-Driven
- **EARS Statement**: `WHILE rendering agent selection lists in Chat Studio THE SYSTEM SHALL display only public agents and hide internal fleet specialists, while grouping fleet specialists together under their fleet heading in Agent Studio.`
- **Acceptance Criteria**:
  - [ ] `AgentProfile` and `AgentPackManifest` support `visibility` (`"public"` | `"internal"`) and `fleet` string identifier.
  - [ ] Default visibility is `"public"`. When `visibility == "internal"`, `show_in_chat` is forced to `False`.
  - [ ] Agent Studio groups agents by fleet in dedicated UI sections.

### [REQ-FLEET-002]: Monolithic Hyper-V Deprecation & Chat Exemption
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL exempt and hide the legacy monolithic hyperv agent from chat selection dropdowns in favor of modular fleet capabilities.`
- **Acceptance Criteria**:
  - [ ] Legacy agent `"hyperv"` is included in `CHAT_HIDDEN_BY_ID`.
  - [ ] Chat Studio agent selector filters out `"hyperv"` even if stale local overrides exist.

### [REQ-FLEET-003]: Enterprise IT Homelab Documentation Framework
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL maintain an enterprise IT documentation framework strictly under notes/homelab/ with standard subdirectories and YAML frontmatter schemas without modifying the existing Wiki engine.`
- **Acceptance Criteria**:
  - [ ] Directory hierarchy contains `00-governance`, `10-network`, `20-compute`, `30-identity`, `40-services`, `50-runbooks`, and `templates`.
  - [ ] All markdown documents include strict YAML frontmatter (`doc_type`, `owner_role`, `scope`, `last_verified`, `status`).
  - [ ] Existing `WikiService`, routers, and database categories remain 100% untouched.

### [REQ-FLEET-004]: Homelab Fleet Roles & Starter Profiles
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL define starter profiles and platform packs for the five homelab roles adhering to the six-section system prompt blueprint.`
- **Acceptance Criteria**:
  - [ ] Profiles defined for `homelab` (Lead Coordinator, public), `homelab-architect` (internal), `homelab-engineer` (internal), `homelab-admin` (internal), `homelab-janitor` (internal).
  - [ ] System prompts contain all 6 gold-standard sections: `[IDENTITY & ROLE]`, `[DOMAIN BOUNDARIES & REFUSALS]`, `[EXECUTION PROTOCOL]`, `[SAFETY & APPROVALS]`, `[TOOL USAGE RULES]`, and `[OUTPUT FORMAT]`.
  - [ ] Pack manifests present in `platform-packs/` with valid schemas.

### [REQ-FLEET-005]: Scoped Domain Lookup and Fleet Delegation Protocol
- **Type**: Event-Driven
- **EARS Statement**: `WHEN the lead homelab coordinator receives an infrastructure task THE SYSTEM SHALL provide scoped document lookup in notes/homelab/ and delegation to internal fleet specialists with injected note context.`
- **Acceptance Criteria**:
  - [ ] `lookup_homelab_docs` retrieves notes by category, query, or `doc_type` with frontmatter parsing.
  - [ ] `delegate_to_fleet_agent` resolves specialist roles and executes handoffs with note context payloads.
  - [ ] Tools registered in `manifest.py` and `PLATFORM_SKILL_TOOLS`.

### [REQ-FLEET-006]: OpenTofu Hyper-V Capability & Safe Tool Execution
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an infrastructure operation is requested THE SYSTEM SHALL provide declarative OpenTofu and Hyper-V operations with safe dry-run simulation.`
- **Acceptance Criteria**:
  - [ ] `manage_opentofu_hyperv` supports `plan`, `apply`, `destroy`, `init`, `validate`, `state_list`, `output`, `inspect_host`, `get_vm_status`.
  - [ ] Safe simulation mode: When `dry_run=True`, operations return planned simulations without destructive mutations.
  - [ ] Returns standardized JSON execution envelope with status, action, and results.

### [REQ-FLEET-007]: Homelab Fleet Skills & Runbooks
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide domain-specific runbook skills formatted with Matt Pocock's five mandatory sections packaged into homelab packs.`
- **Acceptance Criteria**:
  - [ ] `lookup-network-spec`, `lookup-host-spec`, and `manage-opentofu-hyperv` skills packaged under `platform-packs/homelab/skills/`.
  - [ ] Each `SKILL.md` contains YAML frontmatter and all 5 mandatory sections: `## Overview`, `## Tools`, `## Order`, `## Pitfalls`, `## Done-when`.

### [REQ-FLEET-008]: Factory Pipeline Dogfooding & Pipeline Verification
- **Type**: Event-Driven
- **EARS Statement**: `WHEN training homelab fleet specialists THE SYSTEM SHALL execute AutoReiv's 8-stage Training Factory pipeline end-to-end verifying phase duration tracking, Matt Pocock formatting, and deliverable quality gates.`
- **Acceptance Criteria**:
  - [ ] `FactoryOrchestrator` steps job through all phases to `waiting_approval` at `promote`.
  - [ ] Packets record phase durations.
  - [ ] Generated runbooks adhere to Matt Pocock sections and functional tool standards.
