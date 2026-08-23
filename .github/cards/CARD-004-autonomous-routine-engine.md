# [CARD-004] Autonomous Routine Engine & Background Scheduler

> **Status**: Completed (Merged to `qa`)  
> **Milestone**: Milestone 4 (v0.4.0)  
> **Primary Component**: `AutoReiv.Routines`  
> **Spec Reference**: `docs/specs/autonomous-routine-engine/`  
> **ADR Reference**: [`docs/adr/0005-autonomous-routine-engine-and-background-scheduler.md`](file:///d:/Projects/Active/AutoReiv/docs/adr/0005-autonomous-routine-engine-and-background-scheduler.md)  
> **Requirements**: `[REQ-ROUTINE-001]` to `[REQ-ROUTINE-006]`

---

## 1. Why / Intent
Agents must execute scheduled and event-driven autonomous workflows (daily morning briefs, nightly note hygiene, periodic system health checks) without requiring human chat interaction. The engine must support standard cron expressions and interval triggers, persist run history locally in SQLite, and prevent concurrent overlapping runs.

---

## 2. What Was Built
- **Domain Models**: `RoutineManifest`, `RoutineExecutionRecord`, `RoutineSchedule`, `ScheduleType` (Cron vs Interval).
- **`ScheduleMatcher`**: Zero-dependency cron expression and interval evaluation engine.
- **`RoutineExecutor`**: Autonomous turn executor with lock management, telemetry logging, and output archiving.
- **`RoutineScheduler`**: Async background tick loop with start/stop lifecycle management.
- **4 Built-in Day 1 Routines**:
  1. *Morning Briefing* (General Assistant, 08:00 daily).
  2. *Daily System Info* (Linux Sysadmin, 09:00 daily).
  3. *Nightly Note Hygiene* (Librarian, 23:00 daily).
  4. *Hourly SRE Pulse* (System Agent, hourly).

---

## 3. Acceptance Criteria & Automated Proof
- [x] `[REQ-ROUTINE-001]`: Cron and interval matching verified with time calculations.
- [x] `[REQ-ROUTINE-002]`: Autonomous routine execution without human intervention verified.
- [x] `[REQ-ROUTINE-003]`: Execution record persistence and output archiving in SQLite verified.
- [x] `[REQ-ROUTINE-004]`: Concurrent execution locking (anti-overlap) verified.
- [x] `[REQ-ROUTINE-005]`: Automated unit test suite passing (`tests/unit/routines/`).
- [x] `[REQ-ROUTINE-006]`: 100% RTM traceability compliance.
