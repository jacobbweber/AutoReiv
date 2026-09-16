# Vertical Slice Tasks: Granular Telemetry Attribution & Performance Audit

> **Spec Status**: Approved  
> **Card Reference**: CARD-337

---

## Phase 1: Platform `direct` Agent Manifest [REQ-TEL-001]
- [x] Task 1.1 (RED): Write unit test verifying `direct` agent profile is registered and mounts zero tools / skills.
- [x] Task 1.2 (GREEN): Seed platform pack manifest `platform-packs/direct/pack.json` and ensure bootstrap copies it to user data.
- [x] Task 1.3 (REFACTOR): Verify agent registry lists `direct` with empty tools.

## Phase 2: Granular Token & Timing Attribution Engine [REQ-TEL-002, REQ-TEL-003]
- [x] Task 2.1 (RED): Write unit tests in `tests/unit/kernel/test_telemetry_attribution.py` verifying discrete component token calculation (user, persona, tools, skills, memory, tool dumps).
- [x] Task 2.2 (GREEN): Implement `src/application/kernel/telemetry_attribution.py` with fast token estimation.
- [x] Task 2.3 (RED): Write unit test in `tests/unit/kernel/test_agent_kernel_attribution.py` verifying `record_turn_span` receives `metadata.token_breakdown` and `metadata.timing_breakdown`.
- [x] Task 2.4 (GREEN): Wire attribution calculation into `AgentKernel.run_turn` and `AgentKernel.stream_turn`.
- [x] Task 2.5 (REFACTOR): Clean up formatting and error handling.

## Phase 3: Performance & Cost Audit Service & Tool [REQ-AUDIT-001, REQ-AUDIT-002]
- [x] Task 3.1 (RED): Write unit tests in `tests/unit/observability/test_audit_service.py` verifying report generation from spans for a job, session, and time window.
- [x] Task 3.2 (GREEN): Implement `src/application/observability/audit_service.py`.
- [x] Task 3.3 (RED): Write unit test for `audit_performance_and_cost` tool in `tests/unit/tools/test_audit_tool.py`.
- [x] Task 3.4 (GREEN): Implement and register `audit_performance_and_cost` tool with wiki export handoff.
- [x] Task 3.5 (REFACTOR): Ensure clean markdown tables, warnings for >50% tool bloat, and cost calculations.

## Phase 4: Pre-configured Audit Routine & Pre-flight [REQ-AUDIT-003]
- [x] Task 4.1: Add `Daily Performance & Cost Audit` routine seed.
- [x] Task 4.2: Run full pre-flight verification (`ruff check .`, unit tests).
- [x] Task 4.3: Update CHANGELOG.md and CARD-337 status to In Review.
