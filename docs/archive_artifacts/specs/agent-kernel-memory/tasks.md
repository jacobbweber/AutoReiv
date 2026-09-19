# Implementation Tasks: Agent Kernel, Scoped Memory & Telemetry Engine

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-KERNEL-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Agent Profile Models & Tone Formatter
- [x] **Task 1.1** `[REQ-KERNEL-001]`: [RED] Write failing unit tests in `tests/unit/kernel/test_agent_profile.py` for `AgentProfile`, `AgentTone`, and tone prompt injection.
- [x] **Task 1.2** `[REQ-KERNEL-001]`: [GREEN] Implement `AgentProfile`, `AgentTone`, and domain exceptions in `src/domain/kernel/models.py` and `src/domain/kernel/errors.py`.
- [x] **Task 1.3** `[REQ-KERNEL-001]`: [REFACTOR] Ensure tone prompt injector produces deterministic prompt suffixes.

### Slice 2: Scoped Tool Registry & RBAC Permissions
- [x] **Task 2.1** `[REQ-KERNEL-002]`: [RED] Write failing unit tests in `tests/unit/kernel/test_tool_registry.py` for tool registration, allowed tool scoping, unauthorized execution denial, and execution timing.
- [x] **Task 2.2** `[REQ-KERNEL-002]`: [GREEN] Implement `ScopedToolRegistry` in `src/application/kernel/tool_registry.py`.
- [x] **Task 2.3** `[REQ-KERNEL-002]`: [REFACTOR] Standardize `ToolResult` schemas and error sanitization.

### Slice 3: SQLite WAL State Store & Checkpointer
- [x] **Task 3.1** `[REQ-KERNEL-004]`: [RED] Write failing unit tests in `tests/unit/memory/test_sqlite_state_store.py` for session CRUD, chronological message persistence, and WAL mode verification.
- [x] **Task 3.2** `[REQ-KERNEL-004]`: [GREEN] Implement `SQLiteStateStore` in `src/infrastructure/memory/sqlite_store.py`.
- [x] **Task 3.3** `[REQ-KERNEL-004]`: [REFACTOR] Optimize message serialization and sequence indexing.

### Slice 4: Telemetry Spans & Reliability Collector
- [x] **Task 4.1** `[REQ-KERNEL-005]`: [RED] Write failing unit tests in `tests/unit/telemetry/test_telemetry_collector.py` for span recording, per-agent KPI queries, and tool success/failure metrics.
- [x] **Task 4.2** `[REQ-KERNEL-005]`: [GREEN] Implement `TelemetryCollector` in `src/application/telemetry/collector.py`.
- [x] **Task 4.3** `[REQ-KERNEL-005]`: [REFACTOR] Ensure telemetry writes are non-blocking and fail-safe.

### Slice 5: Agent ReAct Kernel & Streaming Events
- [x] **Task 5.1** `[REQ-KERNEL-003]`, `[REQ-KERNEL-006]`: [RED] Write failing unit tests in `tests/unit/kernel/test_agent_kernel.py` for single-turn, multi-turn tool loops, turn limits, cycle detection, and streaming event emissions.
- [x] **Task 5.2** `[REQ-KERNEL-003]`, `[REQ-KERNEL-006]`: [GREEN] Implement `AgentKernel` orchestrator in `src/application/kernel/agent_kernel.py`.
- [x] **Task 5.3** `[REQ-KERNEL-003]`: [REFACTOR] Polish cycle detection heuristics and conversation history truncation.

### Slice 6: Verification, Traceability, & QA Gate
- [x] **Task 6.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 6.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 6.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
