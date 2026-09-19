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

## Phase 3: Deterministic Performance Audit Service [REQ-AUDIT-001]
- [x] Task 3.1 (RED): Write unit tests in `tests/unit/observability/test_audit_service.py` verifying report generation from spans for a job, session, and time window.
- [x] Task 3.2 (GREEN): Implement `src/application/observability/audit_service.py`.
- [x] Task 3.3 (REFACTOR): Ensure clean markdown tables, warnings for >50% tool bloat, and cost calculations.

## Phase 4: Observe Studio Audit & Inbox Export [REQ-AUDIT-002]
- [x] Task 4.1 (RED): Write unit tests in `tests/unit/observability/test_observability_endpoints.py` for `/api/observability/sessions`, `/api/observability/audit`, and `/api/observability/audit/export`.
- [x] Task 4.2 (GREEN): Implement backend endpoints in `src/web/routers/observability.py`.
- [x] Task 4.3 (GREEN): Integrate Observe Studio frontend in `src/web/templates/index.html` and `src/web/static/modules/studios/observability.js` (agent->session picker, KPI summary, attribution table, report generation to `00_Inbox/`).
- [x] Task 4.4: Run full pre-flight verification (`ruff check .`, pytest, npm run lint:frontend, npm run test:unit:frontend).
- [x] Task 4.5: Update CHANGELOG.md, RTM, and CARD-337 status to In Review.
