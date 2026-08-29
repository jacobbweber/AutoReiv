# Implementation Tasks: Control Plane Job Phase

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)
> **Traceability Key**: All tasks must reference their corresponding `[REQ-xxx]` tags.
> **Cards**: CARD-096 through CARD-101. One card per vertical slice. No feature code in the spec-open commit.

---

## Vertical Slice Breakdown

### Slice A1 â€” CARD-096 Job + Phase records and orchestrator

- [ ] **Task 1.1** `[REQ-ORCH-031]` `[REQ-ORCH-032]`: [RED] Failing tests that jobs/phases tables and columns exist and reject invalid status / missing parent job.
- [ ] **Task 1.2** `[REQ-ORCH-031]` `[REQ-ORCH-032]`: [GREEN] SQLite schema + migrations for `jobs` and `phases`.
- [ ] **Task 1.3** `[REQ-ORCH-033]`: [RED] Repository create/get/list/update survives process restart; does not use `ExecutionPlan` as store.
- [ ] **Task 1.4** `[REQ-ORCH-033]`: [GREEN] Job/Phase repository.
- [ ] **Task 1.5** `[REQ-ORCH-034]`: [RED] Orchestrator: create job â†’ run phase â†’ on DONE next or finish; PARKED/FAILED do not auto-advance.
- [ ] **Task 1.6** `[REQ-ORCH-034]`: [GREEN] Orchestrator loop only. No DAG scheduler.

### Slice A2 â€” CARD-097 Named ReAct states on SSE

- [x] **Task 2.1** `[REQ-KERNEL-001]`: [RED] AgentKernel exposes THINKING|CALLING_TOOLS|PARKED|DONE|FAILED and persists `phase.react_state`.
- [x] **Task 2.2** `[REQ-KERNEL-001]`: [GREEN] Enum overlay on the existing ReAct loop. No second runtime.
- [x] **Task 2.3** `[REQ-KERNEL-002]`: [RED] Chat SSE includes job_id, phase_id, assigned_agent_id, react_state on each transition.
- [x] **Task 2.4** `[REQ-KERNEL-002]`: [GREEN] Emit named states. FAILED is never labeled Delegation Completed.

### Slice A3 â€” CARD-098 Packet, child stream_turn, Ollama semaphore

- [ ] **Task 3.1** `[REQ-ORCH-036]`: [RED] HandoffPacket requires goal, facts, constraints, done_when, budget. Child user message is packet only.
- [ ] **Task 3.2** `[REQ-ORCH-036]`: [GREEN] Packet schema. Depth cap 2. No self-handoff. Leaf cannot hand off.
- [ ] **Task 3.3** `[REQ-ORCH-037]`: [RED] Child path calls `stream_turn` with new session, empty history, full child num_ctx. `run_turn` / nested `complete()` not used. 32k CARD-094 cap not applied on this path. Parent stream aclosed first (CARD-091).
- [ ] **Task 3.4** `[REQ-ORCH-037]`: [GREEN] Child `stream_turn` only.
- [ ] **Task 3.5** `[REQ-ORCH-038]`: [RED] Settings `max_concurrent_generations` default 1 (1â€“3). Queue extra (phase queued). Batch > cap errors; no silent truncate.
- [ ] **Task 3.6** `[REQ-ORCH-038]`: [GREEN] Global generation semaphore.

### Slice A4 â€” CARD-099 Default chat, Goal planner, Verify gate, persist

- [ ] **Task 4.1** `[REQ-ORCH-035]`: [RED] Default Chat (Goal off) creates one Job, one Phase, `stream_turn`. No planner call.
- [ ] **Task 4.2** `[REQ-ORCH-035]`: [GREEN] Default chat path.
- [ ] **Task 4.3** `[REQ-ORCH-039]` `[REQ-ORCH-040]`: [RED] Goal checkbox: no-tool planner emits linear phases; persist Job+Phases; restart still sees them. Not a DAG. No `set_goal` tool.
- [ ] **Task 4.4** `[REQ-ORCH-039]` `[REQ-ORCH-040]`: [GREEN] Planner + persist. Replace in-memory-only Goal plan.
- [ ] **Task 4.5** `[REQ-ORCH-041]`: [RED] Verify checkbox runs named checker; missing checker is an honest skip (CARD-064).
- [ ] **Task 4.6** `[REQ-ORCH-041]`: [GREEN] Checker gate.

### Slice A5 â€” CARD-100 Chat Job/Phase UI

- [ ] **Task 5.1** `[REQ-ORCH-042]`: [RED] Chat shows job status, current phase, assigned agent, react_state (including PARKED and FAILED).
- [ ] **Task 5.2** `[REQ-ORCH-042]`: [GREEN] Status strip. Goal badge/label must not say Graph or Plan Graph.

### Slice A6 â€” CARD-101 propose_followup draft job

- [ ] **Task 6.1** `[REQ-ORCH-043]`: [RED] `propose_followup` writes proposal kind `followup_job` status `draft` with `requested_by_job_id`. Does not auto-run.
- [ ] **Task 6.2** `[REQ-ORCH-043]`: [GREEN] Draft job only. No `set_goal` tool.

### Slice A7 â€” Verification, traceability, QA handoff

- [ ] **Task 7.1**: pytest + ruff on touched Python.
- [ ] **Task 7.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [ ] **Task 7.3**: Human QA on Nimo: Assistant chat; Goal 3-phase job; Conductorâ†’Coding handoff via `stream_turn`; HITL park; Ollama slot=1 under two parallel handoffs (second queues or batch errors). Do not push.

---

## Explicitly not in these tasks

LangGraph, training weights, Agent Builder UI, SkillOpt, ACE, Skills Studio, user data dir move, job-template YAML, CARD-014 DAG implementation.
