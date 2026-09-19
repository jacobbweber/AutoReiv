# Requirements Specification: Architectural Telemetry & Threshold Detectors

> **Spec Status**: Approved (Draft for Review)  
> **Target Release**: v0.18.0 (Milestone 18 — Autonomic OS & Mechanical Governance)  
> **Primary Components**: `ArchitecturalThresholdDetector` (`src/domain/observability/architectural_detector.py`), `ArchitecturalEvaluatorService` (`src/application/observability/architectural_evaluator.py`), Observability Router (`src/web/routers/observability.py`), and CLI (`src/cli/main.py`)  
> **Grounding**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [CARD-364](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-364-architectural-telemetry-threshold-detectors.md)

---

## 1. Executive Summary & Intent

Per **ADR-0054**, AutoReiv establishes mechanical governance over runtime autonomous behavior. While `autoreiv lint-skills` (CARD-363) ensures static runbooks obey the Rule of 7 and declare deterministic verification before promotion, runtime execution can still degrade if:
1. Tool entropy budget is breached at runtime (`active_tool_count > 8`).
2. Tool schema and prompt pre-fill overhead exceeds 20% of context window.
3. Untrusted external input runs concurrently with mutating syscalls without operator approval.
4. An interactive Chat session acts as an unmonitored polling daemon.
5. Mutations are validated only by LLM self-grading rather than mechanical assertions.

**CARD-364** implements the **Architectural Telemetry & Threshold Detectors**, actively inspecting execution telemetry spans and conversation transcripts to raise structured alerts that feed into the Architectural Proposal Inbox (CARD-365).

---

## 2. EARS Functional Requirements

### [REQ-ARCH-001]: Tool Entropy Threshold Detector
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL evaluate agent execution turn spans and flag any turn where active tool count exceeds 8 or where active tools contain more than 6 domain tools, generating a TOOL_BLOAT architectural alert.`
- **Acceptance Criteria**:
  - [ ] Given a turn telemetry span with `active_tool_count > 8`, an alert with `threshold_type=TOOL_BLOAT` and severity `high` is created.
  - [ ] The alert evidence indicates the exact tool count and recommends skill decomposition or demand-paging.

### [REQ-ARCH-002]: Context Tax Threshold Detector
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL evaluate pre-fill prompt metrics and flag turns where tool schema characters exceed 4,000 characters or where pre-fill prompt tokens exceed 20% of the active context window, generating a CONTEXT_TAX architectural alert.`
- **Acceptance Criteria**:
  - [ ] Given a span with `tool_schema_chars > 4000`, an alert with `threshold_type=CONTEXT_TAX` is generated.
  - [ ] Alert provides estimated token tax and suggests compact index representation.

### [REQ-ARCH-003]: Security Boundary Collision Detector
- **Type**: State-Driven
- **EARS Statement**: `WHILE inspecting session transcripts, THE SYSTEM SHALL detect when untrusted input tools (web_search, read_url_content, fetch) and mutating host tools (cli_exec, write_project_file, execute_code, delete_file) are invoked within the same session without human-in-the-loop approval, generating a SECURITY_COLLISION architectural alert.`
- **Acceptance Criteria**:
  - [ ] If an untrusted tool call is followed or preceded by a mutating tool call in the same session without `hitl_paused` or user confirmation, emit `SECURITY_COLLISION` with severity `critical`.

### [REQ-ARCH-004]: Lifecycle Mismatch (Daemon Drift) Detector
- **Type**: State-Driven
- **EARS Statement**: `WHILE evaluating chat sessions, THE SYSTEM SHALL identify sessions displaying recurring polling loops or high automated turn sequences (>5 consecutive turns without user message), generating a LIFECYCLE_MISMATCH architectural alert recommending promotion to a background Routine.`
- **Acceptance Criteria**:
  - [ ] Flags chat sessions running automated polling loops or unattended multi-turn chains.
  - [ ] Recommends factoring the recurring workflow into an unattended AutoReiv Routine daemon.

### [REQ-ARCH-005]: Cognitive Conflict (Self-Auditing) Detector
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL detect when code or file mutations occur without subsequent mechanical test execution (e.g. pytest, git status, external checker), generating a COGNITIVE_CONFLICT architectural alert.`
- **Acceptance Criteria**:
  - [ ] If a mutating tool executes and the turn completes without any verification tool or checker invoked, an alert with `threshold_type=COGNITIVE_CONFLICT` is emitted.

### [REQ-ARCH-006]: REST API for Architectural Alerts & Scan
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator sends a POST request to '/api/observability/architectural/scan' or GET to '/api/observability/architectural/alerts', THE SYSTEM SHALL execute threshold detection and return structured alert records.`
- **Acceptance Criteria**:
  - [ ] `POST /api/observability/architectural/scan` accepts optional `days_lookback` and returns `ArchitecturalScanReport`.
  - [ ] `GET /api/observability/architectural/alerts` returns active alerts with filtering by threshold type and severity.

### [REQ-ARCH-007]: Unified CLI Subcommand `autoreiv scan-architecture`
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an operator executes 'autoreiv scan-architecture [--days N] [--json]', THE SYSTEM SHALL scan historical session traces and output detected architectural breaches.`
- **Acceptance Criteria**:
  - [ ] Outputs formatted terminal diagnostics or machine-readable JSON report.
  - [ ] Exits with code 0 on clean scan or code 1 if critical alerts are detected.
