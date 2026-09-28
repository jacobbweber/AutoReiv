# [CARD-097] Named ReAct states on AgentKernel streamed to Chat SSE

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-job-phase/`
> **Labels**: `type:feature`, `area:kernel`, `area:orchestration`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Name the existing ReAct loop for debug: THINKING, CALLING_TOOLS, PARKED, DONE, FAILED. Enum overlay, not a new runtime. Stream those states to Chat SSE so PARKED/FAILED are visible without reading the transcript.

## 2. What to Build
- `ReactState` enum on AgentKernel.
- Persist `phase.react_state`.
- Chat SSE event with job_id, phase_id, assigned_agent_id, react_state on each transition.
- Provider/tool failure â†’ FAILED, never "Delegation Completed".

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-KERNEL-001]`: State is exactly one of THINKING|CALLING_TOOLS|PARKED|DONE|FAILED and is persisted on the phase. No second runtime.
- [x] `[REQ-KERNEL-002]`: Chat SSE emits job_id, phase_id, assigned_agent_id, react_state on each change.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Overlay only. Do not invent a fourth loop.
- Spec: `docs/specs/control-plane-job-phase/`.
