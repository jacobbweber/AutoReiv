# Implementation Tasks: Observability & KPI Dashboard Backend

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-OBS-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Observability Domain Models & Filters
- [x] **Task 1.1** `[REQ-OBS-001]`, `[REQ-OBS-002]`, `[REQ-OBS-003]`: [RED] Write failing unit tests in `tests/unit/observability/test_observability_models.py` verifying `KPIDashboardSummary`, `AgentKPISummary`, `ToolReliabilityMetric`, and `TelemetryFilter`.
- [x] **Task 1.2** `[REQ-OBS-001]`, `[REQ-OBS-002]`, `[REQ-OBS-003]`: [GREEN] Implement `src/domain/observability/models.py`.

### Slice 2: SQLite Aggregation Analytics Engine
- [x] **Task 2.1** `[REQ-OBS-001]`, `[REQ-OBS-002]`, `[REQ-OBS-003]`, `[REQ-OBS-004]`, `[REQ-OBS-005]`: [RED] Write failing unit tests in `tests/unit/observability/test_telemetry_aggregations.py` testing SQL-based metric calculations.
- [x] **Task 2.2** `[REQ-OBS-001]`, `[REQ-OBS-002]`, `[REQ-OBS-003]`, `[REQ-OBS-004]`, `[REQ-OBS-005]`: [GREEN] Add aggregation methods and query indices to `src/infrastructure/memory/sqlite_store.py`.

### Slice 3: Observability Dashboard Service
- [x] **Task 3.1** `[REQ-OBS-001]`, `[REQ-OBS-002]`, `[REQ-OBS-003]`, `[REQ-OBS-004]`: [RED] Write failing unit tests in `tests/unit/observability/test_dashboard_service.py` verifying application-level query methods.
- [x] **Task 3.2** `[REQ-OBS-001]`, `[REQ-OBS-002]`, `[REQ-OBS-003]`, `[REQ-OBS-004]`: [GREEN] Implement `ObservabilityDashboardService` in `src/application/observability/dashboard_service.py`.

### Slice 4: Filtered Trace Queries & JSON Exporter
- [x] **Task 4.1** `[REQ-OBS-005]`, `[REQ-OBS-006]`: [RED] Write failing unit tests in `tests/unit/observability/test_trace_exporter.py` verifying trace filtering and JSON archive formatting.
- [x] **Task 4.2** `[REQ-OBS-005]`, `[REQ-OBS-006]`: [GREEN] Implement `TraceExporter` in `src/application/observability/exporter.py`.

### Slice 5: Verification, Traceability, & QA Gate
- [x] **Task 5.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 5.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 5.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
