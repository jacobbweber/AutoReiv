---
id: CARD-395
title: "Dead Code Scavenger Orphaned Workflows Pruning and Git Hygiene"
status: In Review
created: 2026-09-21
adr: none
labels:
  - type:refactor
  - area:hygiene
  - domain:core
---

# [CARD-395] Dead Code Scavenger Orphaned Workflows Pruning and Git Hygiene

> **Status**: In Review  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:refactor`, `area:hygiene`, `domain:core`  

---

## 1. Why / Intent (Beat 1)

Clean up technical debt and dead code paths across frontend and backend:
1. Prune the orphaned, retired standalone `skills.js` studio file.
2. Excise the legacy `workflows` backend subsystem (superseded since CARD-215 / ADR-0054 by the `JobPhaseOrchestrator` runtime and platform runbooks; has zero frontend callers).
3. Retire the deprecated `POST /api/chat/goal` endpoint in `chat.py`.
4. Fix the overly broad `core` pattern in `.gitignore` which was accidentally ignoring `tests/unit/core/`, restore and commit the orphaned regression test `test_dead_code_shims_scavenger_385.py`.

---

## 2. What AutoReiv Does Now (Beat 2)

- `src/web/static/modules/studios/skills.js` sits in the repository (367 lines) with zero importers and references dead DOM IDs (`skillsPackList`, etc.) that were removed from `index.html` in CARD-118.
- `src/web/routers/workflows.py` (206 lines), `src/application/orchestration/workflow_service.py` (103 lines), `src/infrastructure/memory/repositories/workflows.py` (77 lines), and `src/domain/orchestration/workflow.py` (28 lines) exist in the backend and mount on `app.py`, but have zero callers from any UI or client surface.
- `POST /api/chat/goal` in `src/web/routers/chat.py` is an obsolete endpoint returning `{"deprecated": True}` while all standing chat goes through `POST /api/chat/stream`.
- `.gitignore` line 120 has unanchored `core`, causing `tests/unit/core/` to be ignored, leaving `tests/unit/core/test_dead_code_shims_scavenger_385.py` untracked.

---

## 3. What Will Change (Beat 3)

- Delete `src/web/static/modules/studios/skills.js`.
- Excise `src/web/routers/workflows.py`, `src/application/orchestration/workflow_service.py`, `src/infrastructure/memory/repositories/workflows.py`, and `src/domain/orchestration/workflow.py`. Unmount `workflows_router` from `src/web/app.py`.
- Remove `POST /api/chat/goal` and `GoalChatRequest` from `src/web/routers/chat.py`.
- Clean up obsolete workflow copy helpers (`_copy_workflows_out`, `_copy_workflows_in`) in `src/application/agent_packs/service.py`.
- Fix `.gitignore` line 120 from `core` to `/core` (root-anchored).
- Track and commit `tests/unit/core/test_dead_code_shims_scavenger_385.py`.
- Replace legacy workflow tests with negative assertions verifying that orphaned workflow endpoints and modules cannot be loaded.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Deleted Files**:
  - `src/web/static/modules/studios/skills.js`
  - `src/web/routers/workflows.py`
  - `src/application/orchestration/workflow_service.py`
  - `src/infrastructure/memory/repositories/workflows.py`
  - `src/domain/orchestration/workflow.py`
  - `tests/unit/web/test_workflow_api.py`
  - `tests/unit/orchestration/test_workflow_recipe.py`
- **Deleted Routes / Handlers**:
  - `GET /api/agents/{agent_id}/workflows`
  - `POST /api/agents/{agent_id}/workflows/from-job`
  - `GET /api/agents/{agent_id}/workflows/{workflow_id}`
  - `POST /api/agents/{agent_id}/workflows`
  - `PUT /api/agents/{agent_id}/workflows/{workflow_id}`
  - `DELETE /api/agents/{agent_id}/workflows/{workflow_id}`
  - `POST /api/agents/{agent_id}/workflows/{workflow_id}/instantiate`
  - `POST /api/chat/goal`
- **Deleted Methods**:
  - `AgentPackService._copy_workflows_out`
  - `AgentPackService._copy_workflows_in`

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL route all chat execution through `POST /api/chat/stream` and multi-phase orchestrator without legacy goal-mode endpoints.
- **Ubiquitous**: THE SYSTEM SHALL maintain zero orphaned files in `src/web/static/modules/studios/` that lack canonical imports in `app.js`.
- **Ubiquitous**: THE SYSTEM SHALL track and run all unit tests in `tests/unit/core/` without git-ignore masking.
- **Negative Assertion**: Automated tests shall explicitly assert that `src/web/static/modules/studios/skills.js` does not exist on disk.
- **Negative Assertion**: Automated tests shall explicitly assert that `src/web/routers/workflows.py` and `POST /api/chat/goal` return 404 or cannot be imported.
- **Negative Assertion**: Automated tests shall explicitly assert that `WorkflowStore` cannot be imported from `src.infrastructure.memory.repositories.workflows`.

---

## 6. Constraints & Verification Plan

- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Feature branch cut from `qa`: `feat/card-395-dead-code-scavenger`.
- Unified preflight passes: `python -m pytest tests/unit`, `npm run test:unit:frontend`, `ruff check .`, `npm run lint:frontend`.
