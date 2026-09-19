# Implementation Tasks: Multi-Phase Job Chrome Deduplication and Deliverable Preservation

> **Spec Reference**: `docs/specs/multiphase-chrome-and-deliverables/requirements.md`  
> **Card Reference**: `docs/cards/CARD-378-multiphase-job-chrome-and-deliverables.md`

---

## Phase 1: Prune Stale Specialist Routing & Option Gating (Backend Orchestration)
- [x] `[TASK-001]`: Add unit test in `tests/unit/orchestration/test_specialist_agent_resolution.py` asserting coding capabilities resolve to `autoreiv` and never `"developer"`.
- [x] `[TASK-002]`: Update `resolve_specialist_agent_for_capabilities` in `src/application/orchestration/job_phase_orchestrator.py` to prune `"developer"` and default to `default_agent_id` or `"autoreiv"` `[REQ-ORCH-044]`.
- [x] `[TASK-003]`: Add unit test asserting that a Formulate phase presenting multiple options parks with status `waiting_approval` before Phase 1 `[REQ-ORCH-045]`.

## Phase 2: Preserve Phase Deliverables Across Job Failures & Stream Reloads (Backend Chat Router)
- [x] `[TASK-004]`: Add unit test in `tests/unit/web/test_chat_multiphase_deliverable_preservation.py` verifying that when Phase 0 completes and Phase 1 fails, the persisted assistant message in `store` contains both Phase 0's deliverable text and the Phase 1 failure honesty statement `[REQ-CHAT-016]`.
- [x] `[TASK-005]`: Update `execute_goal_job_phases` in `src/web/routers/chat.py` to accumulate completed phase deliverables and persist composite content on failure `[REQ-CHAT-016]`.

## Phase 3: Deduplicate Stream Bubbles & Clean Milestone Card Headers (Frontend Chat Studio)
- [x] `[TASK-006]`: Update `src/web/static/modules/studios/chat.js` to reuse `streamBubble` for inline job chrome during active turns instead of appending a second independent bubble `[REQ-CHAT-015]`.
- [x] `[TASK-007]`: Update `formatInlineJobChromeHtml` in `chat.js` to truncate the milestone card goal to 80 characters cleanly `[REQ-CHAT-015]`.
- [x] `[TASK-008]`: Add frontend Vitest tests in `tests/unit/frontend/chat_multiphase_chrome_dedup.test.js` asserting zero duplicate streaming headers and truncated card goals `[REQ-CHAT-015]`.

## Phase 4: Verification & Definition of Done
- [x] `[TASK-009]`: Run complete test suite (`pytest`, `npm run test:unit:frontend`).
- [x] `[TASK-010]`: Verify linters clean (`python -m ruff check .`, `npm run lint:frontend`).
- [x] `[TASK-011]`: Update `docs/rtm.json` and `CHANGELOG.md` `[Unreleased]`.
