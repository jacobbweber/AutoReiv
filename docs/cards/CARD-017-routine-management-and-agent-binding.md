# [CARD-017] Routine Management and Agent Binding

> **Status**: Done  
> **Created**: 2026-08-23  
> **Spec Reference**: `docs/specs/routine-management-and-agent-binding/`  
> **Labels**: `type:feature`, `component:routines`, `component:web`

---

## 1. Why / Intent
Provide operators with low-cognitive-friction routine management across the Control Plane, displaying dual cron/human-readable schedules, supporting full CRUD & pause/resume controls, and binding standing routines directly to agent character sheets in Agent Forge Studio.

---

## 2. What to Build
- Dual Cron Schedule Humanizer & Next-Run Calculator (`src/application/routines/humanizer.py`).
- Routine REST API CRUD, Toggle, and Trigger Endpoints (`src/web/app.py` & `src/infrastructure/memory/sqlite_store.py`).
- Routines Studio Management UI & Modal Editor (`src/web/templates/index.html` & `src/web/static/app.js`).
- Agent Forge "Assigned Routines" Character Sheet Card (`src/web/templates/index.html` & `src/web/static/app.js`).

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ROUT-001]` Dual Cron Syntax & Human-Readable Schedule Translation (`cron_to_human`, `compute_next_run_eta`).
- [x] `[REQ-ROUT-002]` Full Routine Lifecycle REST API (CRUD & Pause/Resume with built-in protection).
- [x] `[REQ-ROUT-003]` Lead-Agent Routine Binding & Filtered Queries (`GET /api/routines?agent_id=...`).
- [x] `[REQ-ROUT-004]` Routines Studio Management UI & Modal Editor with presets and live preview.
- [x] `[REQ-ROUT-005]` Agent Forge Assigned Routines Character Sheet Card with direct execution links.
- [x] Automated tests green via `pytest` (199/199 passing).
- [x] Zero lint errors via `ruff check .`.
- [x] RTM verified via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight` (101/101 requirements passing).

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
