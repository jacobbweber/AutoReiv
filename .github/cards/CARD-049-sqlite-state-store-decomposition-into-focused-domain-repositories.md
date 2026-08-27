# [CARD-049] SQLite State Store Decomposition into Focused Domain Repositories

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/sqlite-store-decomposition/
> **Labels**: `type:refactor`, `quality-gate`

---

## 1. Why / Intent
Decompose the monolithic 1,559-line `SQLiteStateStore` into focused domain repositories (`SessionRepository`, `FactRepository`, `SettingsRepository`, `RoutineRepository`, `ApprovalRepository`, `TelemetryRepository`, `TaskRepository`) while maintaining a unified `SQLiteStateStore` façade for seamless 100% backwards compatibility with all existing service callers and test suites.

---

## 2. What to Build
1. **Base Connection Manager & Schema Migrations**:
   - `src/infrastructure/memory/schema.py`: Consolidated DDL statements, indexes, and PRAGMA configurations.
   - `src/infrastructure/memory/connection.py`: Thread-safe SQLite connection manager with WAL mode and `:memory:` pooling.
2. **Domain Repository Mixins / Classes** under `src/infrastructure/memory/repositories/`:
   - `sessions.py`: Session CRUD and message history sequence numbering (`[REQ-KERNEL-004]`).
   - `facts.py`: Episodic facts persistence, confidence scoring, and semantic keyword search (`[REQ-EPISODIC-001]`).
   - `settings.py`: JSON key-value settings, agent customizations, and custom agent profiles (`[REQ-SET-001]`, `[REQ-FORGE-006]`).
   - `routines.py`: Autonomous routines and execution run logging (`[REQ-ROUT-001]`).
   - `telemetry.py`: Telemetry spans, KPI rollups, and tool reliability metrics (`[REQ-OBS-001]`).
   - `approvals.py`: HITL pending approvals and resolution logging (`[REQ-HITL-002]`).
   - `tasks.py`: Task management CRUD.
3. **Unified SQLiteStateStore Façade**:
   - `src/infrastructure/memory/sqlite_store.py`: Composes the repositories and exposes the exact public API for 100% backwards compatibility.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] [REQ-REPO-001]: SQLite DDL and PRAGMAs isolated to `schema.py`.
- [x] [REQ-REPO-002]: Focused domain repositories created under `src/infrastructure/memory/repositories/`.
- [x] [REQ-REPO-003]: `SQLiteStateStore` acts as a clean façade delegating to modular repository classes (reduced from 1,559 lines to 34 lines).
- [x] All 314 existing unit and integration tests pass cleanly via `pytest`.
- [x] Zero linting errors via `ruff check .`.
- [x] RTM validated via `python .agents/skills/rtm-sync/scripts/verify_rtm.py`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests or database schema.
- Single isolated `feat/*` branch cut from `qa`.

