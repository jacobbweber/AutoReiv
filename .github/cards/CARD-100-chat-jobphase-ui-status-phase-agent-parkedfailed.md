# [CARD-100] Chat Job/Phase UI (status, phase, agent, PARKED/FAILED)

> **Status**: Ready
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-job-phase/`
> **Labels**: `type:feature`, `area:web`, `area:orchestration`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Chat must show the durable job, not only the transcript: job status, current phase, assigned agent, and react_state (including PARKED and FAILED). Relabel the Goal badge off "Plan Graph" / Graph. Linear phases are not a graph.

## 2. What to Build
- Chat status strip: job status Â· current phase name Â· assigned agent Â· react_state.
- PARKED and FAILED are named in the strip.
- Goal checkbox/badge label must not say "Plan Graph" or "Graph".

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-ORCH-042]`: Active Chat job shows status, phase, agent, and react_state including PARKED and FAILED.
- [ ] `[REQ-ORCH-042]`: Goal control label does not include Graph or Plan Graph.
- [ ] Automated tests green via `pytest` / frontend checks on touched UI.
- [ ] Zero lint errors on touched files.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- No LangGraph view. No mind-map for jobs in this card.
- Spec: `docs/specs/control-plane-job-phase/`.
