# [CARD-378] Multi-Phase Job Chrome Deduplication, Deliverable Preservation, and Stale Specialist Pruning

> **Status**: Done  
> **Created**: 2026-09-19  
> **Spec Reference**: `docs/specs/multiphase-chrome-and-deliverables/requirements.md`  
> **Labels**: `type:feature`, `domain:chat`, `domain:orchestration`, `domain:ui`

---

## 1. Why / Intent
Fix chat duplicate streaming strips, preserve completed formulate deliverables on failure or stream reload, prune stale developer agent dispatch, and park for operator decisions.

---

## 2. What to Build
- **`src/application/orchestration/job_phase_orchestrator.py`**: Prune stale `"developer"` return in `resolve_specialist_agent_for_capabilities()`, defaulting to `default_agent_id` or `"autoreiv"` `[REQ-ORCH-044]`. Add HITL option parking when Formulate produces branching options `[REQ-ORCH-045]`.
- **`src/web/routers/chat.py`**: In `execute_goal_job_phases`, accumulate completed phase deliverables and save composite content on subsequent phase failure or stream completion so completed plans are never lost `[REQ-CHAT-016]`.
- **`src/web/static/modules/studios/chat.js`**: Deduplicate inline job chrome to reuse the active `streamBubble` rather than appending a duplicate `AUTOREIV STREAMING...` card, and truncate long goal strings in the milestone card header `[REQ-CHAT-015]`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-CHAT-015]`: Exactly one assistant stream bubble is present during multi-phase streaming with truncated milestone goal.
- [x] `[REQ-CHAT-016]`: Completed phase deliverables are preserved in `autoreiv.db` and remain visible in chat history even if later phases fail.
- [x] `[REQ-ORCH-044]`: Coding capabilities resolve to `autoreiv` and never the retired `"developer"` agent.
- [x] `[REQ-ORCH-045]`: Formulate phases with branching options park for operator selection.
- [x] Automated tests green via `pytest` and `vitest`.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/card-378-multiphase-job-chrome-and-deliverables` branch cut from `qa`.
