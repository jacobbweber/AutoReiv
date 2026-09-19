# Requirements Specification: Architectural Proposal Inbox

> **Spec Status**: Approved  
> **Target Release**: v0.18.0 (Milestone 18)  
> **Primary Component**: `src/application/observability/`, `src/web/routers/observability.py`, `src/web/static/modules/studios/forge.js`  
> **Related ADR**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Work Card**: [CARD-365](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-365-architectural-proposal-inbox-in-agent-forge-studio.md)

---

## 1. Executive Summary & Intent

Per **ADR-0054**, AutoReiv enforces mechanical governance and self-evolution. CARD-364 created the threshold detectors that identify when an agent or session exhibits God-Agent degradation (`TOOL_BLOAT`, `CONTEXT_TAX`, `SECURITY_COLLISION`, `LIFECYCLE_MISMATCH`, `COGNITIVE_CONFLICT`).

**CARD-365** closes the autonomic loop by providing the **Architectural Proposal Inbox** in **Agent Forge Studio**. Rather than forcing the human operator to manually diagnose logs or re-architect agents from scratch, AutoReiv generates concrete, actionable proposals and executes them with a single click.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-ARCH-008]: Architectural Proposal Domain Model & Lifecycle
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL represent architectural proposals with typed lifecycle states, threshold associations, and executable remediation payloads.`
- **Acceptance Criteria**:
  - `ArchitecturalProposalType` enum defines `PROMOTION_ROUTINE`, `SKILL_DECOMPOSITION`, `TOOL_PRUNING`, `SECURITY_ISOLATION`, and `CONTRACT_REINFORCEMENT`.
  - `ArchitecturalProposalStatus` enum defines `PENDING`, `APPLIED`, and `DISMISSED`.
  - `ArchitecturalProposal` domain model contains `id`, `alert_id`, `proposal_type`, `status`, `title`, `description`, `agent_id`, `session_id`, `impact_summary`, `action_payload`, `created_at`, `applied_at`, and `dismissed_at`.

### [REQ-ARCH-009]: Autonomic Proposal Generation Engine
- **Type**: Event-Driven
- **EARS Statement**: `WHEN architectural threshold alerts are evaluated THE SYSTEM SHALL synthesize deduplicated, actionable proposals tailored to the specific violation type.`
- **Acceptance Criteria**:
  - Given an alert with `threshold_type == LIFECYCLE_MISMATCH`, the engine generates a `PROMOTION_ROUTINE` proposal with pre-filled routine name, prompt template, interval/cron schedule, and target agent.
  - Given an alert with `threshold_type == TOOL_BLOAT` or `CONTEXT_TAX`, the engine generates a `TOOL_PRUNING` or `SKILL_DECOMPOSITION` proposal identifying candidates for unbinding or skill splitting.
  - Given an alert with `threshold_type == COGNITIVE_CONFLICT`, the engine generates a `CONTRACT_REINFORCEMENT` proposal specifying the missing mechanical verification clause.
  - Given an alert with `threshold_type == SECURITY_COLLISION`, the engine generates a `SECURITY_ISOLATION` proposal specifying isolation of mutating tools under HITL approval.
  - The generator deduplicates proposals across identical alert signatures and excludes already applied or active proposals.

### [REQ-ARCH-010]: Durable Ledger Storage
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist architectural proposals in a durable JSON ledger under the user data telemetry directory.`
- **Acceptance Criteria**:
  - Proposals are saved to `$DATA_DIR/telemetry/architectural_proposals.json`.
  - File writes use atomic rename patterns to prevent corruption during server restarts.
  - Querying proposals supports filtering by `status`, `agent_id`, and `proposal_type`.

### [REQ-ARCH-011]: One-Click Proposal Remediation Execution
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator triggers the apply action on an architectural proposal THE SYSTEM SHALL execute the mechanical remedy and update the proposal status to APPLIED.`
- **Acceptance Criteria**:
  - For `PROMOTION_ROUTINE`: Creates a new `Routine` in the database store with the configured schedule and prompt, and sets `applied_at`.
  - For `CONTRACT_REINFORCEMENT`: Patches the target `SKILL.md` frontmatter with the deterministic verification command or creates a verified skill contract.
  - For `TOOL_PRUNING` / `SECURITY_ISOLATION`: Updates the agent configuration or marks mutating tools for HITL gating.
  - Status updates to `APPLIED` with timestamp, and updated state is persisted to disk.

### [REQ-ARCH-012]: Architectural Proposals REST API
- **Type**: Event-Driven
- **EARS Statement**: `WHEN client requests are received for architectural proposals THE SYSTEM SHALL provide query, generation, application, and dismissal endpoints.`
- **Acceptance Criteria**:
  - `GET /api/observability/architectural/proposals`: Returns proposal list with filters for `status`, `agent_id`, `proposal_type`, and `limit`.
  - `POST /api/observability/architectural/proposals/generate`: Triggers scan and proposal synthesis, returning count of new proposals.
  - `POST /api/observability/architectural/proposals/{proposal_id}/apply`: Applies the proposal remedy and returns execution result.
  - `POST /api/observability/architectural/proposals/{proposal_id}/dismiss`: Dismisses proposal and returns updated status.

### [REQ-ARCH-013]: Agent Forge Studio Architectural Proposal Inbox
- **Type**: State-Driven
- **EARS Statement**: `WHILE an operator is in Agent Forge Studio THE SYSTEM SHALL render an Architectural Proposal Inbox displaying active proposals with one-click action buttons and live feedback.`
- **Acceptance Criteria**:
  - Displays pending proposals filtered by the selected agent or for all agents.
  - Each card presents title, severity badge, God-Agent threshold tag, description, impact summary, and "Apply Remedy" / "Dismiss" buttons.
  - Clicking "Apply Remedy" triggers the REST apply endpoint, displays a success toast, and transitions the card out of pending state.
  - Provides a "Scan & Generate Proposals" trigger button.

### [REQ-ARCH-014]: Observability Studio Cross-Linking & Discovery
- **Type**: State-Driven
- **EARS Statement**: `WHILE an operator is in Observability Studio THE SYSTEM SHALL surface pending architectural proposal indicators with deep links to Agent Forge Studio.`
- **Acceptance Criteria**:
  - An indicator chip or banner in Observability Studio displays the count of pending architectural proposals.
  - Clicking the indicator navigates the operator directly to Agent Forge Studio with the Architectural Proposal Inbox open.

---

## 3. Non-Functional & Boundary Constraints

- **Execution Safety**: One-click actions must be idempotent and non-destructive.
- **Latency**: Proposal generation across 100 historical alerts must complete in < 50ms.
- **Durable File Isolation**: Telemetry files exist solely in `$DATA_DIR/telemetry/`, never in the git checkout tree.
- **Frontend Responsiveness**: Studio UI updates immediately upon user click with optimistic/animated feedback.

---

## 4. Out of Scope

- Automatic unattended application without operator approval (all proposals require human-in-the-loop one-click confirmation).
- Dynamic code generation of new arbitrary tools (tools must be synthesized via the Agent Training Factory or defined in code).
