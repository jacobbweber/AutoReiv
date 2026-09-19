# Requirements Specification: Homelab Domain Orchestration

> **Spec Status**: In Review  
> **Target Release**: CARD-206  
> **Primary Component**: Homelab Fleet Orchestrator & OpenTofu IaC Engine

---

## 1. Executive Summary & Intent
Enable end-to-end multi-agent fleet coordination and compiler-guided self-learning in AutoReiv to autonomously provision an isolated Windows Domain homelab (DCs + single File Server) on Hyper-V using OpenTofu and PowerShell, ensuring the physical host remains unchanged and safe.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-HOMELAB-001]: Phased Fleet Relay Orchestration
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a homelab domain deployment goal is triggered, THE SYSTEM SHALL sequence the homelab fleet across four distinct lifecycle chapters (Audit -> Architecture -> IaC -> Validation) without accumulating conversational context across chapters.`
- **Acceptance Criteria**:
  - [ ] Given a domain deployment request, when the job starts, then Chapter 1 is assigned to `homelab-admin` to audit available host compute and memory.
  - [ ] When Chapter 1 completes, then Chapter 2 is assigned to `homelab-architect` with the audit payload to generate the IPAM and sizing blueprint.
  - [ ] When Chapter 2 completes, then Chapter 3 is assigned to `homelab-engineer` to generate the OpenTofu HCL and PowerShell automation.
  - [ ] When Chapter 3 completes, then Chapter 4 executes validation and dry-run simulation (`tofu plan`).

### [REQ-HOMELAB-002]: Isolated Hyper-V Virtual Switch & Network Safety Invariant
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL enforce that all generated Hyper-V domain network configurations attach exclusively to a private internal virtual switch and never alter physical network adapters or Docker/WSL2 bindings.`
- **Acceptance Criteria**:
  - [ ] Given any domain IaC configuration, when the virtual switch is created, then its switch type must be `Internal` or `Private`.
  - [ ] When network plans are generated, then IP allocations must reside on the isolated subnet `10.10.10.0/24` with no overlap with host LAN (`192.168.1.0/24`) or Docker (`172.17.0.0/16`).

### [REQ-HOMELAB-003]: OpenTofu Hyper-V Multi-VM HCL Generation
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL generate valid OpenTofu declarative configurations that define Domain Controller(s) and a single File Server as Generation 2 virtual machines.`
- **Acceptance Criteria**:
  - [ ] Given sizing tier specifications, when generating `main.tf`, then Domain Controllers (DC01, DC02) are configured with 2 vCPUs, 4GB static RAM, and SCSI VHDX.
  - [ ] When generating the File Server (FS01), then it is configured with 2 vCPUs, 4GB RAM, and a secondary data disk attachment.
  - [ ] When generating configuration blocks, then valid OpenTofu Hyper-V provider syntax (`required_providers`) is included.

### [REQ-HOMELAB-004]: Compiler-Guided Self-Learning & Diagnostic Feedback Loop
- **Type**: State-Driven
- **EARS Statement**: `WHILE validating OpenTofu configurations, IF the compiler reports syntax or schema errors, THE SYSTEM SHALL return structured diagnostic line and error information to the agent and codify verified working blocks into the skill repository.`
- **Acceptance Criteria**:
  - [ ] Given an invalid HCL syntax block, when `manage_opentofu_hyperv(action="validate")` runs, then the tool returns the exact error line, attribute name, and compiler message.
  - [ ] When validation succeeds with exit code 0, then the verified pattern is eligible for codification into `skills/opentofu-hyperv/SKILL.md`.

### [REQ-HOMELAB-005]: Online ACE False-Positive Filtering on HITL Approvals
- **Type**: Complex
- **EARS Statement**: `WHEN a tool invocation yields an approval_required status, THE SYSTEM SHALL NOT record the turn as a failed execution and SHALL NOT generate an ACE skill modification proposal.`
- **Acceptance Criteria**:
  - [ ] Given a parked tool call requiring operator approval, when the status is returned, then `_ace_record_tool_result` ignores the event.
  - [ ] Given an approval resolution in HITL, when the turn resumes, then no extraneous SOP modification proposals are created for `SKILL.md`.

### [REQ-HOMELAB-006]: Reusable Domain Deployment Workflow Recipe
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL register a canonical, reusable Workflow Recipe for homelab domain deployment that can be instantiated across different domain and VM parameters.`
- **Acceptance Criteria**:
  - [ ] Given the workflow registry, when queried for `homelab-domain-deployment`, then the 4-phase recipe is retrieved.
  - [ ] When instantiated with a specific goal, then a new `Job` with corresponding `Phase` rows is created.

---

## 3. Non-Functional & Boundary Constraints
- **Safety**: Pure dry-run simulation mode by default; live `tofu apply` requires explicit HITL approval.
- **Context Hygiene**: Subagent handoffs must pass structured summary packets rather than raw conversational transcripts.
- **Idempotency**: Re-running validation on existing configurations produces consistent plan outputs.

---

## 4. Out of Scope
- Modifying physical router/switch configurations or home LAN DHCP.
- Downloading unverified external ISOs or unauthorized binary downloads.
- Direct destructive host rebooting or host OS reinstallation.
