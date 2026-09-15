# [CARD-336] Specialist Intake Dispatch and Standing Job Delegation

> **Status**: Ready
> **Created**: 2026-09-15
> **Spec Reference**: none
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Orchestration`, `AutoReiv.A2A`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **No Silent Drops or Dead Ends**: When the operator asks an agent (like Assistant) to perform a task owned by a specialist (e.g., *"Please reorganize the wiki vault and create a feynman note for quantum physics."*), the system should ensure the specialist agent (`wiki`) is called to execute the work, rather than having the front-of-house agent fail closed and skip the outcome.
2. **Phrasing and Mode Awareness**: The operator wants to understand and harmonize how phrasing affects routing:
   - Conversational questions trigger single-turn ReAct chat (where `handoff_to_agent` is available in the agent profile).
   - Action verbs ("reorganize", "create", "build") trigger multi-phase Standing Job Graphs (`StandingRoute.MULTI_STEP_JOB_GRAPH`).
3. **Seamless Agent-to-Agent Execution**: Whether an ask runs as a single chat turn or a multi-phase job graph, multi-agent collaboration should feel cohesive: the right specialist gets the job.
4. **Not this card**: Rewriting existing single-turn chat handoff protocols or reverting the CARD-332 security scrub.

### Beat 2: What AutoReiv Does Now
1. **Intake Blindness**: `route_standing_chat()` in `src/web/routers/chat.py` detects multi-step action intent and invokes `orch.create_job_from_catalog_resolve()`.
2. **Fixed Agent Assignment**: Even though the capability resolver correctly identifies that the request requires specialist capabilities (`tool.wiki_note_*`), the job orchestrator stamps `assigned_agent_id = active_agent` (`assistant`) for all phases (`Formulate`, `Execute`).
3. **Phase Tool Clamping**: During phase execution, the agent's available tools are strictly limited to the matched catalog capabilities. Orchestration tools (`handoff_to_agent`, `lookup_agents`) are not in the phase working set.
4. **Fail-Closed Stalemate**: When `assistant` executes the phase, `tool_policy_blocked` correctly prevents it from using `wiki_note_*`. Because `assistant` cannot delegate mid-phase, it documents the failure honestly and parks the sub-goal, resulting in no note being created.

### Beat 3: What Will Change
Design and evaluate architectural options for cross-agent execution during multi-step tasks:

- **Option A (Intake Specialist Dispatch — "Right Agent at the Door")**:
  During `create_job_from_catalog_resolve()`, if the resolved capabilities predominantly belong to a specialist pack (e.g., `wiki`), automatically assign the Job Graph to that specialist (`assigned_agent_id='wiki'`), or notify the operator.
- **Option B (Multi-Agent Phase Graphs — "Specialist Execution Phase")**:
  Allow Job Graphs to support heterogeneous agent assignment across phases (e.g., Phase 1 Formulate assigned to `assistant`, Phase 2 Execute assigned to `wiki`), passing the formulated plan via the durable output packet.
- **Option C (In-Phase Handoff Semantics)**:
  Expose `handoff_to_agent` as an authorized primitive during phase execution, allowing an agent to reassign the active phase or spin off an authorized sub-phase to a specialist without violating CARD-265 same-job invariants.

---

## 2. Technical Discussion Points for Future Effort

1. **Intake Dispatch vs. In-Flight Handoff**:
   - Is it cleaner to route the job to the correct specialist before Phase 1 begins, or should Assistant formulate the plan and then hand Phase 2 to Wiki?
2. **Operator Visibility & Consent**:
   - When switching agents automatically, how should the UI in Chat Studio and Observe Studio signal the handoff?
3. **Privilege & Safety Invariants (CARD-221 / CARD-265)**:
   - Ensure that delegating a phase to a specialist respects the human-in-the-loop (HITL) gates for high-risk write operations (`wiki_note_create`, `repo_file_write`).

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] **[REQ-INTAKE-001]**: Architecture decision record (ADR) selected between Intake Dispatch (Option A), Phase-Level Assignment (Option B), or In-Phase Handoff (Option C).
- [ ] **[REQ-INTAKE-002]**: User requests matching specialist capabilities (e.g. Wiki) result in the specialist executing the capability rather than a blocked fail-closed no-op.
- [ ] **[REQ-INTAKE-003]**: Observe Studio and Chat Studio accurately reflect agent transitions and phase ownership without orphan jobs.
- [ ] **[REQ-INTAKE-004]**: Automated regression tests covering multi-phase specialist dispatch.
- [ ] **[REQ-INTAKE-005]**: Preflight and honesty smoke gates pass.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing single-turn chat or CARD-332 allowlist policies.
- Single isolated `feat/*` branch cut from `qa`.

