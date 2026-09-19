# Implementation Tasks: Architectural Proposal Inbox

> **Component**: Architectural Governance & Proposal Inbox  
> **Card**: [CARD-365](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-365-architectural-proposal-inbox-in-agent-forge-studio.md)  
> **Target Release**: v0.18.0 (Milestone 18)

---

## Task Checklist

- [x] **Task 1: Domain Models & Proposal Types** [REQ-ARCH-008]
  - Add `ArchitecturalProposalType` and `ArchitecturalProposalStatus` enums in `src/domain/observability/models.py`.
  - Add `ArchitecturalProposal` Pydantic model with typed fields (`id`, `alert_id`, `proposal_type`, `status`, `title`, `description`, `agent_id`, `session_id`, `impact_summary`, `action_payload`, timestamps).
  - Add unit tests verifying schema validation, serialization, and status defaults.

- [x] **Task 2: Autonomic Proposal Generation Engine** [REQ-ARCH-009]
  - Implement `ArchitecturalProposalGenerator` in `src/application/observability/architectural_proposals.py`.
  - Implement alert-to-proposal synthesis for each threshold:
    - `LIFECYCLE_MISMATCH` -> `PROMOTION_ROUTINE`
    - `TOOL_BLOAT` -> `TOOL_PRUNING` / `SKILL_DECOMPOSITION`
    - `CONTEXT_TAX` -> `TOOL_PRUNING`
    - `COGNITIVE_CONFLICT` -> `CONTRACT_REINFORCEMENT`
    - `SECURITY_COLLISION` -> `SECURITY_ISOLATION`
  - Implement deduplication logic ensuring duplicate proposals are not generated for the same alert or target.
  - Unit test generator rules with parameterized fixtures.

- [x] **Task 3: Durable Ledger Storage & Service Lifecycle** [REQ-ARCH-010]
  - Implement `ArchitecturalProposalService` in `src/application/observability/architectural_proposals.py`.
  - Add ledger persistence writing to `$DATA_DIR/telemetry/architectural_proposals.json` with atomic rename.
  - Implement querying proposals with filtering by `status`, `agent_id`, `proposal_type`, and `limit`.
  - Unit test persistence, concurrent writes, and query filtering.

- [x] **Task 4: One-Click Proposal Remediation Execution Engine** [REQ-ARCH-011]
  - Implement `apply_proposal(proposal_id)`:
    - For `PROMOTION_ROUTINE`: Create and save `Routine` in database via `store.save_routine`.
    - For `CONTRACT_REINFORCEMENT`: Patch target `SKILL.md` frontmatter with `verification` directive.
    - For `TOOL_PRUNING`: Update agent configuration / pack tools list.
    - For `SECURITY_ISOLATION`: Set HITL approval or isolate sandboxing profile.
  - Implement `dismiss_proposal(proposal_id)`:
    - Transition status to `DISMISSED` with timestamp.
  - Unit test execution pathways and state transitions.

- [x] **Task 5: REST API Endpoints in Observability Router** [REQ-ARCH-012]
  - Add `GET /api/observability/architectural/proposals` in `src/web/routers/observability.py`.
  - Add `POST /api/observability/architectural/proposals/generate`.
  - Add `POST /api/observability/architectural/proposals/{proposal_id}/apply`.
  - Add `POST /api/observability/architectural/proposals/{proposal_id}/dismiss`.
  - Integration test endpoints with FastAPI test client.

- [x] **Task 6: Agent Forge Studio Architectural Proposal Inbox UI** [REQ-ARCH-013]
  - Add Architectural Governance & Proposal Inbox markup in `src/web/templates/index.html` within `#view-agents`.
  - Implement dynamic rendering, "Apply Remedy", "Dismiss", and "Scan & Refresh" event listeners in `src/web/static/modules/studios/forge.js`.
  - Provide instant UI feedback via toasts and card removals upon application.

- [x] **Task 7: Observability Studio Discovery & Cross-Linking** [REQ-ARCH-014]
  - Add proposal status badge / indicator card in `src/web/templates/index.html` within `#view-observability`.
  - Wire click handler in `src/web/static/modules/studios/observability.js` to switch to Agent Forge Studio with Proposal Inbox highlighted.

- [x] **Task 8: End-to-End Verification & Preflight Gates**
  - Run full test suite (`pytest tests/`).
  - Run linters (`ruff check .`, `npm run lint:frontend`).
  - Synchronize `docs/rtm.json` with `[REQ-ARCH-008..014]`.
  - Update `CHANGELOG.md` under `[Unreleased]`.
  - Run linters (`ruff check .`, `npm run lint:frontend`).
  - Synchronize `docs/rtm.json` with `[REQ-ARCH-008..014]`.
  - Update `CHANGELOG.md` under `[Unreleased]`.
