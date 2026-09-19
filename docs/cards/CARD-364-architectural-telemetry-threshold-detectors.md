# [CARD-364] Architectural Telemetry & Threshold Detectors

> **Status**: Done  
> **Created**: 2026-09-19  
> **Spec Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [docs/specs/architectural-telemetry/](file:///d:/Projects/Active/AutoReiv/docs/specs/architectural-telemetry/)  
> **Labels**: `type:feature`, `domain:observability`, `domain:telemetry`, `architecture:autonomic-os`

---

## 1. Why / Intent

Per **ADR-0054** (Section 4.4 "The 5 God-Agent Thresholds" & Section 4.5 "The Mechanical Governance Engine & Architectural Telemetry"), runtime degradation in LLM-based autonomous systems manifests when foundational limits are crossed:
1. **Tool Entropy Limit (Rule of 7)**: Systems mounting too many tools overwhelm attention distributions and provoke hallucinations.
2. **Context Budget Limit (20% Pre-fill Rule)**: System prompt and tool schema pre-fill tax choking context windows and exploding latency.
3. **Security Boundary Collision**: Untrusted external ingestion executing in close proximity with mutating host syscalls without human approval.
4. **Lifecycle Mismatch (Unattended Daemon Drift)**: Interactive chat sessions drifting into unmonitored polling or long-running recurring jobs that belong in background routines.
5. **Cognitive Conflict (Self-Auditing)**: Code or data mutations self-critiqued by the generator rather than verified by deterministic mechanical tests.

While CARD-363 validated static `SKILL.md` runbooks, **CARD-364** provides the active runtime sensory layer: **Architectural Telemetry & Threshold Detectors**. It audits real execution spans and message transcripts, detects threshold breaches, and emits structured `ArchitecturalAlert` records to feed the downstream Architectural Proposal Inbox (CARD-365).

---

## 2. What to Build

1. **Domain Models (`src/domain/observability/models.py`)**:
   - `ArchitecturalThresholdType`: Enum covering `TOOL_BLOAT`, `CONTEXT_TAX`, `SECURITY_COLLISION`, `LIFECYCLE_MISMATCH`, and `COGNITIVE_CONFLICT`.
   - `ArchitecturalAlert`: Typed model with `id`, `threshold_type`, `severity` (`low`, `medium`, `high`, `critical`), `agent_id`, `session_id`, `evidence`, `remediation_proposal`, `occurred_at`, and `metadata`.
   - `ArchitecturalScanReport`: Summary of inspected sessions, evaluated turns, alert counts, and breakdown by threshold.

2. **Pure Domain Detector (`src/domain/observability/architectural_detector.py`)**:
   - `ArchitecturalThresholdDetector`: Implements heuristic detection for the 5 God-Agent thresholds:
     - `detect_tool_bloat`: Spans where `active_tool_count > 8` or declared tools > 6.
     - `detect_context_tax`: Spans where schema chars > 4,000 or prompt overhead > 20% of context window.
     - `detect_security_collision`: Sessions where untrusted tools (`web_search`, `read_url_content`, external fetch) run in the same session as mutating host levers (`cli_exec`, `write_project_file`, `delete_file`) without HITL approval.
     - `detect_lifecycle_mismatch`: Chat sessions running long unattended polling loops (> 5 automated turns without user interaction).
     - `detect_cognitive_conflict`: Code mutation tool calls without a subsequent verification tool call (`pytest`, checker, assertion).

3. **Application Evaluator Service (`src/application/observability/architectural_evaluator.py`)**:
   - `ArchitecturalEvaluatorService`: Loads sessions and telemetry spans from SQLite store, runs detector rules, persists alerts, and generates scan reports.

4. **REST API & CLI Dispatcher**:
   - `POST /api/observability/architectural/scan` (`src/web/routers/observability.py`): On-demand telemetry scan.
   - `GET /api/observability/architectural/alerts` (`src/web/routers/observability.py`): Fetch active alerts filterable by severity and threshold type.
   - CLI command `autoreiv scan-architecture [--days N] [--json]` (`src/cli/main.py`).

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **[REQ-ARCH-001]**: `ToolBloatDetector` flags turns where active tools exceed 8 or skill declares > 6 tools.
- [x] **[REQ-ARCH-002]**: `ContextTaxDetector` flags turns where tool schema pre-fill exceeds 4,000 characters or 20% of context window.
- [x] **[REQ-ARCH-003]**: `SecurityCollisionDetector` flags sessions co-mingling untrusted inputs with mutating host levers without HITL gating.
- [x] **[REQ-ARCH-004]**: `LifecycleMismatchDetector` flags chat sessions exhibiting unattended recurring polling behavior.
- [x] **[REQ-ARCH-005]**: `CognitiveConflictDetector` flags mutations lacking deterministic test verification.
- [x] **[REQ-ARCH-006]**: REST API endpoints `POST /api/observability/architectural/scan` and `GET /api/observability/architectural/alerts` return valid models.
- [x] **[REQ-ARCH-007]**: CLI command `autoreiv scan-architecture` executes and outputs formatted human and JSON reports.
- [x] Unit and integration test coverage across all detectors and endpoints.
- [x] Zero lint errors (`ruff check .`, `npm run lint:frontend`).
- [x] RTM updated with `[REQ-ARCH-001..007]`.

---

## 4. Constraints & Invariants

- Grounded strictly in **ADR-0054** (Section 4.4 and Section 4.5).
- Pure domain detector logic in `src/domain/observability/` completely decoupled from database queries.
- Follow strict Red-Green-Refactor TDD on branch `feat/card-364-architectural-telemetry`.
- Wait for Jacob's explicit **build** before implementing code.
