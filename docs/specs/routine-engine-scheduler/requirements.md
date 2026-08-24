# Requirements Specification: Autonomous Routine Engine & Background Scheduler

> **Spec Status**: Implemented  
> **Target Release**: Milestone 4 (v0.4.0)  
> **Primary Component**: `AutoReiv.Routines`  
> **Applicable ADRs**: `docs/adr/0005-autonomous-routine-engine-and-async-background-scheduler.md`

---

## 1. Executive Summary & Intent

Milestone 4 introduces the **Autonomous Routine Engine**, allowing AutoReiv agents to execute autonomous scheduled activities without waiting for real-time human chat input. It enables recurring workflows such as the General Assistant's morning brief, Linux Sysadmin's daily hardware audit, Librarian's nightly wiki maintenance, and System Agent's hourly SRE health pulse.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-ROUTINE-001]: Routine Manifest & Schedule Model
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL define declarative Routine manifests containing unique ID, name, description, target agent ID, schedule (cron or interval seconds), execution prompt, enabled flag, and metadata.`
- **Acceptance Criteria**:
  - [ ] Given a `Routine` object, when validated, then it enforces valid agent binding and non-empty prompt.

### [REQ-ROUTINE-002]: SQLite Persistence for Routines & History
- **Type**: Event-Driven
- **EARS Statement**: `WHEN routine configurations or execution runs occur THE SYSTEM SHALL persist routine definitions and chronological execution runs (timestamp, status, duration, output, error) in SQLite.`
- **Acceptance Criteria**:
  - [ ] Given `create_routine()` / `update_routine()`, when executed, then routine state is updated in SQLite.
  - [ ] Given a routine execution completion, when finished, then a record is appended to `routine_runs` table.

### [REQ-ROUTINE-003]: Cron & Interval Schedule Matcher
- **Type**: State-Driven
- **EARS Statement**: `WHILE the scheduler tick runs THE SYSTEM SHALL evaluate whether each enabled routine is due for execution according to its cron expression or interval seconds.`
- **Acceptance Criteria**:
  - [ ] Given an interval-based routine (e.g. 3600 seconds) whose `last_run_at` was > 3600 seconds ago, when evaluated, then `is_due()` returns `True`.
  - [ ] Given a disabled routine, when evaluated, then `is_due()` returns `False`.

### [REQ-ROUTINE-004]: Autonomous Kernel Execution & Telemetry
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a routine triggers THE SYSTEM SHALL invoke the target agent's AgentKernel without active human chat input, execute authorized tools, record execution results, and capture telemetry spans.`
- **Acceptance Criteria**:
  - [ ] Given an autonomous trigger, when executed, then an isolated autonomous session is created and executed by `AgentKernel.run_turn()`.
  - [ ] Given tool calls during the routine, when executed, then tools run via `ScopedToolRegistry` and results are captured in the execution output.

### [REQ-ROUTINE-005]: Manual One-Shot Routine Trigger
- **Type**: Event-Driven
- **EARS Statement**: `WHEN a user or operator requests immediate execution of a routine THE SYSTEM SHALL execute the routine out-of-schedule and return the full execution report.`
- **Acceptance Criteria**:
  - [ ] Given `trigger_routine(routine_id)`, when called, then it executes immediately regardless of scheduled next run time.

### [REQ-ROUTINE-006]: Pre-Configured Day-1 Agent Routines
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL provide default routine configurations for Morning Briefing (General Assistant), Daily System Info (Linux Sysadmin), Nightly Note Hygiene (Librarian), and Hourly SRE Pulse (System Agent).`
- **Acceptance Criteria**:
  - [ ] Given `BuiltinRoutineRegistry`, when loaded, then all 4 Day-1 routines are available and registered.

---

## 3. Non-Functional & Boundary Constraints

- **Async & Non-Blocking**: The scheduler tick loop runs as an `asyncio` task and never blocks HTTP or Gateway event loops.
- **Fail-Safe Isolation**: An error or exception in one routine run does not crash the scheduler or prevent subsequent routines from executing.
- **Hermetic Testing**: Unit tests use in-memory SQLite tables and mock LLM providers without relying on real clock sleeps.

---

## 4. Out of Scope

- Mobile Push Notifications (Milestone 7 / Future).
- Web UI Routine Editor pages (Milestone 5 / 7).
