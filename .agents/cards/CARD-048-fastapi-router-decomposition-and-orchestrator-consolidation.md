# [CARD-048] FastAPI Router Decomposition and Orchestrator Consolidation

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/router-decomposition-and-cleanup/
> **Labels**: `type:refactor`, `quality-gate`

---

## 1. Why / Intent
Decompose the monolithic 1,340-line `src/web/app.py` into dedicated modular FastAPI routers and consolidate multi-agent delegation into a single clean `SupervisorOrchestrator` pattern without breaking any existing API contracts, WebSocket/SSE endpoints, or tests.

---

## 2. What to Build
1. **Modular FastAPI Routers** under `src/web/routers/`:
   - `chat.py`: Sessions, messages, SSE streaming `/api/chat/stream`, `/api/chat/verified`, `/api/chat/goal`.
   - `agents.py`: Agent catalog, custom agent CRUD, `/api/agents/delegate`.
   - `wiki.py`: Notes CRUD, `/api/wiki/graph`, `/api/wiki/mindmap`, `/api/wiki/export`, `/api/wiki/inbox/triage`.
   - `settings.py`: Provider configs, model discovery `/api/settings/models`, hardware RAM calculator.
   - `routines.py`: Autonomous routines CRUD, trigger execution, interval matchers.
   - `observability.py`: Telemetry metrics, spans, tool health matrix, system logs.
   - `hitl.py`: Human-In-The-Loop approval queue and decision resolution.
   - `system.py`: System Info topics and documentation browser.
2. **Lean Application Factory** (`src/web/app.py`):
   - Life-cycle manager (`lifespan`), CORS middleware, static file mounts, index.html template rendering, and router inclusions.
3. **Orchestration Clean-up**:
   - Standardize on `SupervisorOrchestrator` + `DelegateSubtaskSkill` across all tests and web routes.
   - Clean up redundant references to `HandoffIsolationEngine`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] [REQ-ROUTER-001]: All ~50 REST and SSE endpoints decomposed into `src/web/routers/*.py` with 100% path and status code compatibility.
- [x] [REQ-ROUTER-002]: `src/web/app.py` acts as a clean application factory under 180 lines (reduced from 1,342 lines).
- [x] [REQ-ROUTER-003]: `SupervisorOrchestrator` is the sole delegation orchestrator across web endpoints and unit tests.
- [x] All 314 existing unit and integration tests pass cleanly via `pytest`.
- [x] All 50 frontend unit tests pass cleanly via `npm run test:unit:frontend`.
- [x] Zero linting errors via `ruff check .` and `npm run lint:frontend`.
- [x] RTM validated via `python .agents/skills/rtm-sync/scripts/verify_rtm.py`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests or frontend API endpoints.
- Single isolated `feat/*` branch cut from `qa`.

