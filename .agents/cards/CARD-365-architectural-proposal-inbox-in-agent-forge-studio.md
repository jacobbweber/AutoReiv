# [CARD-365] Architectural Proposal Inbox in Agent Forge Studio

> **Status**: Done  
> **Created**: 2026-09-19  
> **Spec Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [docs/specs/architectural-proposals/](file:///d:/Projects/Active/AutoReiv/docs/specs/architectural-proposals/)  
> **Labels**: `type:feature`, `domain:observability`, `domain:forge`, `architecture:autonomic-os`

---

## 1. Why / Intent

Per **ADR-0054** (Section 4.5 "The Mechanical Governance Engine & Architectural Telemetry" and Section 6 "Implementation Plan"), detecting God-Agent degradation via runtime telemetry (CARD-364) is only the sensory half of the autonomic loop. For an operating system to be truly autonomic, it must turn passive observations into concrete, actionable architectural evolutions.

When runtime telemetry flags threshold breaches—such as an interactive chat loop running unattended polling (`LIFECYCLE_MISMATCH`), an agent mounting 15 tools (`TOOL_BLOAT`), or code mutations without test assertions (`COGNITIVE_CONFLICT`)—AutoReiv must not simply dump log lines. It must synthesize concrete **Architectural Proposals** into an operator inbox in **Agent Forge Studio**. With one click, the operator can accept the proposal:
1. Promoting chat polling loops directly into scheduled **Routines** (daemons).
2. Pruning unneeded tools or staging skill decomposition.
3. Enforcing deterministic test contracts in `SKILL.md`.
4. Isolating untrusted ingress into sandboxed execution profiles.

---

## 2. What to Build

1. **Domain Models (`src/domain/observability/models.py`)**:
   - `ArchitecturalProposalType`: Enum covering `PROMOTION_ROUTINE`, `SKILL_DECOMPOSITION`, `TOOL_PRUNING`, `SECURITY_ISOLATION`, and `CONTRACT_REINFORCEMENT`.
   - `ArchitecturalProposalStatus`: Enum covering `PENDING`, `APPLIED`, `DISMISSED`.
   - `ArchitecturalProposal`: Model with `id`, `alert_id`, `proposal_type`, `status`, `title`, `description`, `agent_id`, `session_id`, `impact_summary`, `action_payload`, `created_at`, `applied_at`, `dismissed_at`.

2. **Application Service (`src/application/observability/architectural_proposals.py`)**:
   - `ArchitecturalProposalService`:
     - Synthesizes proposals from active `ArchitecturalAlert` instances.
     - Persists proposals in durable ledger `$DATA_DIR/telemetry/architectural_proposals.json`.
     - Executes one-click remedies via `apply_proposal(proposal_id)`:
       - `PROMOTION_ROUTINE`: Automatically generates and registers a `Routine` in the database.
       - `CONTRACT_REINFORCEMENT`: Patches the target `SKILL.md` frontmatter with a deterministic verification contract.
       - `TOOL_PRUNING` / `SECURITY_ISOLATION`: Updates tool policy / agent profile settings.
     - Handles `dismiss_proposal(proposal_id)` with status tracking.

3. **REST API (`src/web/routers/observability.py`)**:
   - `GET /api/observability/architectural/proposals`: Query proposals with status, agent_id, and type filtering.
   - `POST /api/observability/architectural/proposals/generate`: Trigger proposal generation from current alerts.
   - `POST /api/observability/architectural/proposals/{proposal_id}/apply`: Execute one-click remedy.
   - `POST /api/observability/architectural/proposals/{proposal_id}/dismiss`: Dismiss a proposal.

4. **Agent Forge Studio UI (`src/web/templates/index.html` & `src/web/static/modules/studios/forge.js`)**:
   - Add **Architectural Governance & Proposal Inbox** card/section in Agent Studio (`#view-agents`).
   - Renders pending proposals for the selected agent (or all agents) with severity chips, threshold breach tags, impact summary, and one-click "Apply Remedy" / "Dismiss" buttons.
   - Live updates UI upon action execution with toast notification and state refresh.

5. **Observability Studio Discovery (`src/web/static/modules/studios/observability.js`)**:
   - Display active architectural proposal count badge and link to open Agent Forge Studio Inbox.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **[REQ-ARCH-008]**: `ArchitecturalProposal` domain model and lifecycle enums defined with typed action payloads.
- [x] **[REQ-ARCH-009]**: `ArchitecturalProposalService.generate_proposals` maps `ArchitecturalAlert` breaches into deduplicated, actionable proposals.
- [x] **[REQ-ARCH-010]**: Proposals persist in `$DATA_DIR/telemetry/architectural_proposals.json` with thread-safe atomic file I/O.
- [x] **[REQ-ARCH-011]**: `apply_proposal` executes one-click remedies (creating `Routine` for daemon promotion, patching verification contract into `SKILL.md`, pruning excessive tools).
- [x] **[REQ-ARCH-012]**: REST API endpoints for proposal listing, generation, application, and dismissal return valid JSON schemas.
- [x] **[REQ-ARCH-013]**: Agent Forge Studio renders the Architectural Proposal Inbox with interactive "Apply" and "Dismiss" controls and live feedback.
- [x] **[REQ-ARCH-014]**: Observability Studio surfaces pending proposal count with deep link to Agent Forge Studio.
- [x] Full unit and integration test coverage across proposal generator, application handlers, and REST APIs.
- [x] Zero lint errors (`ruff check .`, `npm run lint:frontend`).
- [x] RTM synchronized with `[REQ-ARCH-008..014]`.

---

## 4. Constraints & Honor Flags

- Grounded strictly in **ADR-0054** (Section 4.5 and Section 6.5).
- Single isolated feature branch: `feat/card-365-architectural-proposals`.
- Follow strict Red-Green-Refactor TDD cycle.
- Do not write implementation code before Jacob's explicit **build**.
