# [CARD-374] Dogfood Capability Gap Closed Loop Lifecycle

> **Status**: In Review  
> **Created**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:dogfooding`, `capabilities`, `kernel`, `factory`, `closed-loop`

---

## 1. Why / Intent
Dogfood and live-validate the closed-loop capability gap lifecycle: from in-flight missing capability detection during chat conversations $\rightarrow$ automatic recording in `capability_gap_repo` $\rightarrow$ surfacing in Factory Studio's backlog $\rightarrow$ one-click seeding of a training job $\rightarrow$ promotion and resolution of the gap.

---

## 2. Three Beats

### Beat 1: What Jacob Means
When a conversation requires a capability the agent currently lacks, AutoReiv must cleanly log the gap to the factory backlog rather than failing silently or attempting unverified in-flight code generation. In Factory Studio, the operator can see the backlog, click to train the missing capability, and upon job promotion, the gap is automatically marked resolved and the new capability is ready.

### Beat 2: What AutoReiv Does Now
- CARD-368 streamlined capability gap routing so that `AgentKernel` sends missing capabilities directly to `capability_gap_repo.create_gap`.
- While the repository and the router have unit tests, the complete round-trip (kernel detection $\rightarrow$ repository persistence $\rightarrow$ backlog API $\rightarrow$ job creation with gap linkage $\rightarrow$ promotion sync) has not been verified in an end-to-end dogfooding run.

### Beat 3: What Will Change
- Author an automated end-to-end dogfooding test suite (`tests/integration/capabilities/test_dogfood_capability_gap_loop.py`).
- Simulate a conversation turn where a missing capability is detected.
- Assert that a structured gap is persisted in SQLite with `status="pending"`.
- Query `GET /api/agent_training_factory/gaps` to verify that the gap appears with its session context and intent.
- Create a Factory job referencing `capability_gap_id`.
- Complete and promote the job, verifying that `_sync_linked_gap_status` transitions the gap to `resolved`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Missing capability detection in kernel writes a structured gap record to SQLite.
- [x] Factory Studio backlog endpoint surfaces the pending gap with agent ID and intent details.
- [x] Creating a Factory job with `capability_gap_id` associates the job with the gap.
- [x] Promoting the completed training job updates the gap status to `resolved` and links the new agent pack.
- [x] Failing or rejecting the job updates the gap status honestly without dangling references.
- [x] Automated regression tests pass via `pytest tests/integration/capabilities/test_dogfood_capability_gap_loop.py`.
- [x] Zero lint errors via `ruff check src tests`.
- [x] All 7 preflight gates pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero checkout database pollution.
- Single isolated `feat/card-374-dogfood-capability-gap-loop` branch cut from `qa` upon Jacob's `build` approval.
