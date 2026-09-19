# Vertical Slice Tasks: Architectural Telemetry & Threshold Detectors

> **Spec Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/architectural-telemetry/requirements.md)  
> **Card Reference**: [CARD-364](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-364-architectural-telemetry-threshold-detectors.md)

---

## Slice 1: Domain Models & Pure Threshold Detectors (`[REQ-ARCH-001]`, `[REQ-ARCH-002]`, `[REQ-ARCH-003]`, `[REQ-ARCH-004]`, `[REQ-ARCH-005]`)

- [ ] **Task 1.1**: [RED] Write unit tests in `tests/unit/observability/test_architectural_detector.py` asserting all 5 God-Agent threshold detections.
- [ ] **Task 1.2**: [GREEN] Implement domain models in `src/domain/observability/models.py` (`ArchitecturalThresholdType`, `ArchitecturalAlert`, `ArchitecturalScanReport`).
- [ ] **Task 1.3**: [GREEN] Implement `ArchitecturalThresholdDetector` in `src/domain/observability/architectural_detector.py`.

---

## Slice 2: Application Evaluator Service & Persistence

- [ ] **Task 2.1**: [RED] Author service tests for `ArchitecturalEvaluatorService` in `tests/unit/observability/test_architectural_evaluator.py`.
- [ ] **Task 2.2**: [GREEN] Implement `ArchitecturalEvaluatorService` in `src/application/observability/architectural_evaluator.py` querying telemetry store and persisting alerts.

---

## Slice 3: REST API & CLI Integration (`[REQ-ARCH-006]`, `[REQ-ARCH-007]`)

- [ ] **Task 3.1**: [RED] Author tests for `POST /api/observability/architectural/scan`, `GET /api/observability/architectural/alerts`, and `autoreiv scan-architecture` CLI.
- [ ] **Task 3.2**: [GREEN] Implement REST endpoints in `src/web/routers/observability.py`.
- [ ] **Task 3.3**: [GREEN] Implement CLI command in `src/cli/main.py`.

---

## Slice 4: Verification & Preflight Gates

- [ ] **Task 4.1**: Run `pytest tests/unit/observability/` and full test suite.
- [ ] **Task 4.2**: Run `ruff check .` and `npm run lint:frontend`.
- [ ] **Task 4.3**: Sync `docs/rtm.json` with `[REQ-ARCH-001..007]`.
- [ ] **Task 4.4**: Update `CHANGELOG.md` under `[Unreleased]`.
