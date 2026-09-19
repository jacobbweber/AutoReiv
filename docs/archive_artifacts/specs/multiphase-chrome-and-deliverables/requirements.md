# Requirements Specification: Multi-Phase Job Chrome Deduplication and Deliverable Preservation

> **Spec Status**: Approved  
> **Target Release**: v0.35.0  
> **Primary Component**: Chat Studio & Job Phase Orchestrator  
> **Card Reference**: `docs/cards/CARD-378-multiphase-job-chrome-and-deliverables.md`

---

## 1. Executive Summary & Intent
When users execute outcome-oriented prompts triggering multi-phase jobs (such as `Formulate` -> `Execute`), Chat Studio currently renders duplicate streaming bubbles (`streamBubble` and a separate `[data-job-chrome="inline"]` bubble), each duplicating phase strips and milestone cards. Furthermore, if a subsequent execution phase fails or times out, the honest failure summary overwrites the saved chat message, wiping the user's formulated plan from the screen upon stream completion or page reload. Finally, the orchestrator still contains obsolete routing to the retired `developer` agent, and fails to pause when Formulate produces branching options (Option A vs Option B).

This specification establishes:
1. Unified single-bubble streaming chrome with truncated goal titles.
2. Deliverable preservation so completed phase outputs (Formulate plans) are retained in the saved message even if a later phase fails or parks.
3. Pruning stale `developer` agent dispatch, keeping phases on the active session agent (`autoreiv`).
4. Human-In-The-Loop (HITL) park gating when Formulate presents operator choices.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-CHAT-015]: Chat Stream Inline Job Chrome Deduplication
- **Type**: State-Driven
- **EARS Statement**: `WHILE a multi-phase job is streaming in Chat Studio, THE SYSTEM SHALL render phase progress and milestone steps directly within the active stream bubble instead of mounting a second duplicate stream container.`
- **Acceptance Criteria**:
  - [ ] Given an active streaming turn for a multi-phase job, exactly one assistant stream bubble is present in `#messagesContainer`.
  - [ ] Given incoming `job_created`, `phase_start`, or `plan_formulated` events, phase rows and step checklists update inside the existing stream bubble.
  - [ ] Given a long user prompt with attachment paths, the milestone card header displays a clean truncated goal (maximum 80 characters) with an ellipsis instead of dumping the raw prompt.

### [REQ-CHAT-016]: Prior Phase Deliverable Preservation on Stream Completion and Failure
- **Type**: State-Driven
- **EARS Statement**: `WHEN a multi-phase job finishes or fails during a subsequent phase, THE SYSTEM SHALL preserve the completed deliverables and outputs of earlier phases (such as Phase 0 Formulate) in the saved assistant message alongside the phase status summary.`
- **Acceptance Criteria**:
  - [ ] Given Phase 0 (Formulate) completes with facts or text, and Phase 1 (Execute) fails or times out, the saved assistant message in `autoreiv.db` contains Phase 0's deliverable text followed by the honest failure claim.
  - [ ] Given a chat thread reload (`loadMessages()`), the formulated plan remains visible in the message history instead of being wiped out by the one-line failure note.
  - [ ] Given all phases succeed, the final assistant message preserves the formulated plan and the execution outcome.

### [REQ-ORCH-044]: Prune Stale Developer Specialist Agent Routing
- **Type**: Ubiquitous
- **EARS Statement**: `WHEN resolving execution agent profiles for multi-phase capabilities, THE SYSTEM SHALL assign phases to the active session agent or registered custom agents, and SHALL NOT assign phases to the retired 'developer' agent.`
- **Acceptance Criteria**:
  - [ ] Given coding or repository capabilities are matched (`repo_file_*`, `write_project_file`, `git_*`), `resolve_specialist_agent_for_capabilities` returns `default_agent_id` (or `autoreiv`) when no custom specialist is registered.
  - [ ] Given a multi-phase job executes, no phase is stamped with `assigned_agent_id="developer"`.

### [REQ-ORCH-045]: Interactive Option Park Gate for Multi-Branch Plans
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a Formulate phase produces an execution plan presenting branching options or requiring user selection, THE SYSTEM SHALL park the job with an approval/decision prompt before advancing to Phase 1 Execute.`
- **Acceptance Criteria**:
  - [ ] Given Formulate output containing option selection prompts (e.g. "Option A" / "Option B" or choices requiring operator confirmation), the orchestrator parks the job with status `waiting_approval`.
  - [ ] Given the job is parked, it does not launch Phase 1 Execute until the operator submits their decision.

---

## 3. Non-Functional & Boundary Constraints
- **Visual Invariant**: Zero duplicate `AUTOREIV STREAMING...` headers in a single turn.
- **DoD Progress Honesty**: Preserving Formulate text must NOT obscure the fact that Phase 1 failed; the `Job {job_id} FAILED during Execute` honesty claim must remain clearly stated.
- **Backwards Compatibility**: Existing unit tests for single-turn chat, routines, and standard jobs must continue to pass with 0 regressions.

---

## 4. Out of Scope
- Adding a brand-new 3D renderer inside Chat Studio (Blender rendering stays in Blender via MCP).
- Redesigning the Global Settings Studio LLM provider forms.
