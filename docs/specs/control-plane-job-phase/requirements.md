# Requirements Specification: Control Plane Job Phase

> **Spec Status**: Draft
> **Target Release**: Slice A / control-plane kernel
> **Primary Component**: KERNEL / ORCHESTRATION
> **Hardware**: Local Ollama on Nimo (qwen3.8 / qwen3.6, context 131kâ€“262k). VRAM is the constraint. Frontier providers must not be required.

---

## 1. Executive Summary & Intent

Durable **Job** + **Phase** is the parent of a user goal. One named ReAct loop runs per assigned agent. Default Chat is one job, one phase, one `stream_turn`. Goal checkbox asks a **no-tool** planner for a linear phase list (not a DAG). Verify checkbox is a named checker gate with an honest skip. Child handoffs receive a packet, not the parent transcript, and **must** `stream_turn` with the child's full context. A global Ollama generation semaphore (default 1) queues extra work instead of stampeding VRAM.

This spec replaces the CARD-014 plan-and-execute DAG idea. In-memory `ExecutionPlan` / `PlanStep` is not the source of truth once Job/Phase persist.

---

## 2. User Stories & EARS Functional Requirements

Every requirement uses EARS syntax and a unique identifier. ORCH ids continue after REQ-ORCH-030.

### [REQ-ORCH-031]: Jobs table

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist a jobs row with id, goal, status (queued|running|waiting_approval|done|failed|cancelled), budget_max_phases, budget_max_handoffs, budget_max_ollama_slots, current_phase_id, template_id, created_at, updated_at, session_id, and agent_id.`
- **Acceptance Criteria**:
  - [ ] Given a new user goal, when a job is created, then a SQLite `jobs` row exists with those columns.
  - [ ] Given an unknown status string, when persist is attempted, then the repository rejects the write.

### [REQ-ORCH-032]: Phases table

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist a phases row with id, job_id, name, index, assigned_agent_id, status, success_rule, verify_checker, input_packet_json, output_packet_json, parent_phase_id, max_turns, and react_state.`
- **Acceptance Criteria**:
  - [ ] Given a job, when a phase is added, then a SQLite `phases` row is keyed by `job_id` and `index`.
  - [ ] Given a missing parent job, when a phase is written, then the repository rejects the write.

### [REQ-ORCH-033]: Job/Phase repository

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL expose a Job/Phase repository that creates, reads, updates status, and lists phases by job without going through the in-memory ExecutionPlan store.`
- **Acceptance Criteria**:
  - [ ] Given a process restart, when the repository loads a job id, then status, current_phase_id, and phases come from SQLite.
  - [ ] Given only the planning `ExecutionPlan` models, when Slice A ships, then Chat Goal does not treat them as the durable plan.

### [REQ-ORCH-034]: Orchestrator loop

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a job is created THE SYSTEM SHALL run the current phase and WHEN that phase reaches DONE THE SYSTEM SHALL start the next phase by index or mark the job done.`
- **Acceptance Criteria**:
  - [ ] Given a job with phases 0..n, when phase k is DONE, then phase k+1 becomes current or the job is `done` if none remain.
  - [ ] Given a phase FAILED or PARKED, when the orchestrator observes it, then it does not silently advance to the next phase.
  - [ ] Given job status `waiting_approval`, when HITL is unresolved, then the orchestrator does not run the next phase.

### [REQ-KERNEL-001]: Named ReAct states

- **Type**: State-Driven
- **EARS Statement**: `WHILE an agent assignment is running THE SYSTEM SHALL overlay ReAct state as exactly one of THINKING, CALLING_TOOLS, PARKED, DONE, FAILED and SHALL persist that value on the phase as react_state.`
- **Acceptance Criteria**:
  - [ ] Given AgentKernel is in the model call, when observed, then `react_state` is THINKING.
  - [ ] Given tools are executing, when observed, then `react_state` is CALLING_TOOLS.
  - [ ] Given HITL park, when observed, then `react_state` is PARKED and job status is `waiting_approval`.
  - [ ] Given a normal finish, when observed, then `react_state` is DONE.
  - [ ] Given provider or tool failure, when observed, then `react_state` is FAILED (never labeled Delegation Completed).
  - [ ] This is an enum overlay on the existing loop. No second runtime is introduced.

### [REQ-KERNEL-002]: ReAct states on Chat SSE

- **Type**: Event-Driven
- **EARS Statement**: `WHEN react_state changes THE SYSTEM SHALL emit a Chat SSE event that includes job_id, phase_id, assigned_agent_id, and react_state.`
- **Acceptance Criteria**:
  - [ ] Given a live Chat stream, when state changes THINKING -> CALLING_TOOLS -> DONE, then the client receives those named states in order.
  - [ ] Given PARKED or FAILED, when emitted, then the event is visible without reading the transcript alone.

### [REQ-ORCH-035]: Default chat is one job, one phase, stream_turn

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the user sends a Chat message without Goal mode THE SYSTEM SHALL create one Job and one Phase assigned to the selected agent and SHALL execute that phase with stream_turn.`
- **Acceptance Criteria**:
  - [ ] Given Goal unchecked and Verify unchecked, when the user sends a message, then exactly one job and one phase are persisted and the phase uses `stream_turn`.
  - [ ] Given that path, when the turn starts, then no planner LLM call runs.

### [REQ-ORCH-036]: Handoff packet schema

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL require a handoff packet with fields goal, facts, constraints, done_when, and budget and SHALL give the child zero parent transcript.`
- **Acceptance Criteria**:
  - [ ] Given a handoff, when the child session starts, then the user message is the packet only (Hermes: subagents know nothing).
  - [ ] Given a missing required packet field, when handoff is invoked, then the call fails closed.
  - [ ] Depth cap is 2. No self-handoff. Leaf children cannot hand off; an orchestrator role may, within depth.

### [REQ-ORCH-037]: Child MUST stream_turn with full context

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a child phase or handoff runs THE SYSTEM SHALL use stream_turn on a new session id with empty history, the packet as the user message, and the child's own max context, and THE SYSTEM SHALL NOT call run_turn or nested complete() on that path.`
- **Acceptance Criteria**:
  - [ ] Given a child handoff, when the child thinks, then the call is `stream_turn`, not `run_turn` / `complete()`.
  - [ ] Given CARD-094's 32768 `run_turn` cap, when the child uses `stream_turn`, then that 32k cap is not applied. Chat 131k windows stay.
  - [ ] Given CARD-091, when the parent is still streaming, then the parent provider stream is aclosed before tools/child work. Never nest blocking `complete()` under a live parent stream.
  - [ ] Child session id is new. History is empty.

### [REQ-ORCH-038]: Ollama generation semaphore

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL gate every Ollama generation behind a global semaphore whose default max_concurrent_generations is 1 (setting range 1-3) and SHALL queue extra phases when a slot is unavailable and SHALL error if a handoff batch requests more concurrent children than the cap.`
- **Acceptance Criteria**:
  - [ ] Given settings default, when two generations are requested, then the second waits in queue (phase status `queued`), not a fake timeout.
  - [ ] Given `handoff_to_agent` batch size greater than the cap, when invoked, then the system returns an error. It does not silent-truncate the batch.
  - [ ] Given a cloud provider selected, when the setting is raised to 3, then at most 3 generations run. The setting is a throttle, not a truncate.
  - [ ] VRAM on Nimo is the design driver. Default stays 1.

### [REQ-ORCH-039]: Goal checkbox is a no-tool linear planner

- **Type**: Event-Driven
- **EARS Statement**: `WHEN Goal mode is checked THE SYSTEM SHALL call a no-tool planner LLM that emits a linear list of phases and SHALL persist those as Job + Phases and THE SYSTEM SHALL NOT build a DAG.`
- **Acceptance Criteria**:
  - [ ] Given Goal checked, when the planner runs, then it has no tools mounted (optional cheaper/faster model).
  - [ ] Given planner output, when persisted, then phases are a linear index 0..n. No graph edges.
  - [ ] Given the Chat Goal badge, when rendered, then it must not say Graph or Plan Graph.
  - [ ] There is no `set_goal` tool.

### [REQ-ORCH-040]: Persist plan as Job + Phases

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the planner emits phases THE SYSTEM SHALL persist them as Job + Phases in SQLite and SHALL treat that store as the only plan source of truth.`
- **Acceptance Criteria**:
  - [ ] Given Goal mode, when phases are produced, then they are visible after restart via the Job/Phase repository.
  - [ ] In-memory-only `ExecutionPlan` is not the Goal-mode store.

### [REQ-ORCH-041]: Verify checkbox is a named checker gate

- **Type**: Event-Driven
- **EARS Statement**: `WHEN Verify is checked and a phase names a checker THE SYSTEM SHALL run that checker as a gate before the phase is DONE and WHEN no checker is named THE SYSTEM SHALL skip the gate and record an honest skip.`
- **Acceptance Criteria**:
  - [ ] Given Verify checked and `verify_checker` set, when the phase finishes work, then DONE requires the checker to pass.
  - [ ] Given Verify checked and no checker, when the phase finishes, then the gate is skipped and the skip is recorded (CARD-064: do not claim verification_passed).
  - [ ] Given checker failure, when observed, then phase `react_state` is FAILED or the phase retries per budget, never a fake pass.

### [REQ-ORCH-042]: Chat Job/Phase UI

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a Chat job is active THE SYSTEM SHALL show job status, current phase name, assigned agent, and react_state including PARKED and FAILED.`
- **Acceptance Criteria**:
  - [ ] Given a running job, when the user looks at Chat, then they see job status, phase, agent, and react_state without reading the transcript only.
  - [ ] Given PARKED or FAILED, when displayed, then those words appear as named states.
  - [ ] Given the Goal control, when labeled, then it does not say Plan Graph or Graph.

### [REQ-ORCH-043]: propose_followup draft job

- **Type**: Event-Driven
- **EARS Statement**: `WHEN propose_followup is invoked THE SYSTEM SHALL create a draft job (proposal kind followup_job) and THE SYSTEM SHALL NOT auto-run that job.`
- **Acceptance Criteria**:
  - [ ] Given a mid-flight discovery, when `propose_followup` runs, then a proposal row exists with status `draft` and `requested_by_job_id` set.
  - [ ] Given that draft, when created, then no phase starts until a human starts it.
  - [ ] There is no `set_goal` tool as an alternative.

---

## 3. Non-Functional & Boundary Constraints

- **Hardware**: Primary runtime is local Ollama on Nimo (128GB unified). One named ReAct loop per assignment. Fresh context per phase. Isolation is the timeout fix, not shrinking tools. Compression is a last-resort rail.
- **Concurrency**: Global Ollama slot default 1. Parallel agents queue. Error if a batch exceeds the cap.
- **Context**: Chat and child `stream_turn` keep the 131k window. The CARD-094 32k cap applies only to leftover `run_turn` / nested `complete()` paths, which this spec forbids for children.
- **Reliability**: Provider failure maps to phase FAILED. Slot wait maps to phase `queued`, not a fake timeout.
- **Security**: Child gets packet only. No parent transcript leak. HITL parks stay parks.
- **Backup**: Jobs live in the same SQLite tree as the rest of user data (backup = zip/copy that tree). Slice A may still use the current app DB.

---

## 4. Out of Scope

- LangGraph (no graph runtime this epic).
- `set_goal` tool.
- Training weights.
- Agent Builder UI (later epic).
- SkillOpt / nightly SkillOpt-Sleep (later slice).
- ACE playbook deltas (later slice).
- User data dir move and Skills Studio (Slice B).
- `propose_skill` / `propose_tool` / `propose_workflow` (Slice C).
- Rewriting Conductor/Coding SDLC cards into Job in the first slice.
- Implementing CARD-014's DAG / Plan-and-Execute graph engine.

