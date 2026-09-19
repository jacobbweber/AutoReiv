# Implementation Tasks: Autonomous Routine Engine & Background Scheduler

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-ROUTINES-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Routine Domain Models & Pre-Configured Manifests
- [x] **Task 1.1** `[REQ-ROUTINE-001]`, `[REQ-ROUTINE-006]`: [RED] Write failing unit tests in `tests/unit/routines/test_routine_models.py` verifying `Routine`, `RoutineRun`, `ScheduleType`, and default Day-1 routine manifests.
- [x] **Task 1.2** `[REQ-ROUTINE-001]`, `[REQ-ROUTINE-006]`: [GREEN] Implement `src/domain/routines/models.py` and `src/domain/routines/manifests.py`.

### Slice 2: SQLite Routine & Run Persistence
- [x] **Task 2.1** `[REQ-ROUTINE-002]`: [RED] Write failing unit tests in `tests/unit/routines/test_routine_persistence.py` for routine CRUD and run execution logging in SQLite.
- [x] **Task 2.2** `[REQ-ROUTINE-002]`: [GREEN] Update `src/infrastructure/memory/sqlite_store.py` with `routines` and `routine_runs` table schemas and repository methods.

### Slice 3: Schedule Matcher & Due Date Calculator
- [x] **Task 3.1** `[REQ-ROUTINE-003]`: [RED] Write failing unit tests in `tests/unit/routines/test_schedule_matcher.py` testing interval-based and cron-based due time calculations.
- [x] **Task 3.2** `[REQ-ROUTINE-003]`: [GREEN] Implement `ScheduleMatcher` in `src/application/routines/matcher.py`.

### Slice 4: Routine Executor & Telemetry Link
- [x] **Task 4.1** `[REQ-ROUTINE-004]`, `[REQ-ROUTINE-005]`: [RED] Write failing unit tests in `tests/unit/routines/test_routine_executor.py` testing autonomous kernel invocation, tool dispatching, session isolation, and manual triggers.
- [x] **Task 4.2** `[REQ-ROUTINE-004]`, `[REQ-ROUTINE-005]`: [GREEN] Implement `RoutineExecutor` in `src/application/routines/executor.py`.

### Slice 5: Background Scheduler Engine
- [x] **Task 5.1** `[REQ-ROUTINE-003]`, `[REQ-ROUTINE-004]`: [RED] Write failing unit tests in `tests/unit/routines/test_routine_scheduler.py` verifying tick loop orchestration and error resilience.
- [x] **Task 5.2** `[REQ-ROUTINE-003]`, `[REQ-ROUTINE-004]`: [GREEN] Implement `RoutineScheduler` in `src/application/routines/scheduler.py`.

### Slice 6: Verification, Traceability, & QA Gate
- [x] **Task 6.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 6.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 6.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
