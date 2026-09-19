# Implementation Tasks: Developer Agent End-to-End Verification & SDLC Optimization

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks reference their corresponding `[REQ-DEVVER-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Core Service & Probe Models
- [x] **Task 1.1** `[REQ-DEVVER-002]`: [RED] Write failing unit test for Status enums, probe configurations, and result models in `agentic-test/tests/test_models.py`.
- [x] **Task 1.2** `[REQ-DEVVER-002]`: [GREEN] Implement probe models and validations in `agentic-test/src/sentinel/models.py`.
- [x] **Task 1.3** `[REQ-DEVVER-002]`: [REFACTOR] Ensure clean SRP and immutability.

### Slice 2: SQLite Health Journal Storage
- [x] **Task 2.1** `[REQ-DEVVER-003]`: [RED] Write failing integration test for journal schema creation, record persistence, and retrieval in `agentic-test/tests/test_storage.py`.
- [x] **Task 2.2** `[REQ-DEVVER-003]`: [GREEN] Implement SQLite health journal in `agentic-test/src/sentinel/storage.py`.
- [x] **Task 2.3** `[REQ-DEVVER-003]`: [REFACTOR] Apply transactional boundaries and index optimization.

### Slice 3: Network & Port Probe Engine
- [x] **Task 3.1** `[REQ-DEVVER-004]`: [RED] Write failing test for HTTP and TCP socket probe execution with mock servers in `agentic-test/tests/test_probes.py`.
- [x] **Task 3.2** `[REQ-DEVVER-004]`: [GREEN] Implement standard-library HTTP and TCP port probes in `agentic-test/src/sentinel/probes.py`.
- [x] **Task 3.3** `[REQ-DEVVER-004]`: [REFACTOR] Ensure OCP/LSP compliance via Probe protocol.

### Slice 4: Degradation & Anomaly Rule Engine
- [x] **Task 4.1** `[REQ-DEVVER-005]`: [RED] Write failing unit test for latency spike detection, consecutive failures, and flapping in `agentic-test/tests/test_rules.py`.
- [x] **Task 4.2** `[REQ-DEVVER-005]`: [GREEN] Implement rule engine in `agentic-test/src/sentinel/rules.py`.
- [x] **Task 4.3** `[REQ-DEVVER-005]`: [REFACTOR] Separate state evaluation from alert triggering.

### Slice 5: Multi-Channel Alert Dispatcher
- [x] **Task 5.1** `[REQ-DEVVER-006]`: [RED] Write failing test for console ANSI, JSON log, and mock webhook alerts in `agentic-test/tests/test_alerts.py`.
- [x] **Task 5.2** `[REQ-DEVVER-006]`: [GREEN] Implement alert dispatcher in `agentic-test/src/sentinel/alerts.py`.
- [x] **Task 5.3** `[REQ-DEVVER-006]`: [REFACTOR] Use ISP for sink interfaces.

### Slice 6: Sandboxed Self-Healing Runbooks
- [x] **Task 6.1** `[REQ-DEVVER-007]`: [RED] Write failing test for runbook execution, timeouts, and logging in `agentic-test/tests/test_remediation.py`.
- [x] **Task 6.2** `[REQ-DEVVER-007]`: [GREEN] Implement remediation runner in `agentic-test/src/sentinel/remediation.py`.
- [x] **Task 6.3** `[REQ-DEVVER-007]`: [REFACTOR] Ensure process safety and error capture.

### Slice 7: Circuit Breaker & Outage Cooldown Shield
- [x] **Task 7.1** `[REQ-DEVVER-008]`: [RED] Write failing test for alert suppression and backoff timers in `agentic-test/tests/test_circuit_breaker.py`.
- [x] **Task 7.2** `[REQ-DEVVER-008]`: [GREEN] Implement circuit breaker in `agentic-test/src/sentinel/circuit_breaker.py`.
- [x] **Task 7.3** `[REQ-DEVVER-008]`: [REFACTOR] Thread-safe / stateless cooldown evaluation.

### Slice 8: Incident Diagnostic Snapshot Collector
- [x] **Task 8.1** `[REQ-DEVVER-009]`: [RED] Write failing test for system metrics and process snapshot collector in `agentic-test/tests/test_diagnostics.py`.
- [x] **Task 8.2** `[REQ-DEVVER-009]`: [GREEN] Implement snapshot collector in `agentic-test/src/sentinel/diagnostics.py`.
- [x] **Task 8.3** `[REQ-DEVVER-009]`: [REFACTOR] Clean fallback for missing OS utilities.

### Slice 9: Historical SLA & Uptime Reporting
- [x] **Task 9.1** `[REQ-DEVVER-010]`: [RED] Write failing test for uptime percentage, MTTR, and markdown/JSON output in `agentic-test/tests/test_reporter.py`.
- [x] **Task 9.2** `[REQ-DEVVER-010]`: [GREEN] Implement reporter in `agentic-test/src/sentinel/reporter.py`.
- [x] **Task 9.3** `[REQ-DEVVER-010]`: [REFACTOR] Clean mathematical calculations and report templates.

### Slice 10: Unified CLI Operator Console
- [x] **Task 10.1** `[REQ-DEVVER-011]`: [RED] Write failing CLI invocation tests in `agentic-test/tests/test_cli.py`.
- [x] **Task 10.2** `[REQ-DEVVER-011]`: [GREEN] Implement CLI commands and runner in `agentic-test/src/sentinel/cli.py` & `main.py`.
- [x] **Task 10.3** `[REQ-DEVVER-011]`: [REFACTOR] Clean argparse structure and status codes.

### Slice 11: SDLC Supervision, Optimization, & QA Verification
- [x] **Task 11.1** `[REQ-DEVVER-012]`: Verify all tests in `agentic-test` pass via `pytest tests/`.
- [x] **Task 11.2**: Inspect tool performance and developer agent skill interactions; patch any identified friction in AutoReiv core.
- [ ] **Task 11.3**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py`.
- [ ] **Task 11.4**: Update `CHANGELOG.md` under `[Unreleased]` and mark CARD-192 `In Review`.
