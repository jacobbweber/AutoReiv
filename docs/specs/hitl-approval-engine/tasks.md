# Task Breakdown: Human-In-The-Loop (HITL) Interactive State Parking, Action Approval & Resume Engine

> **Spec Status**: Implemented  
> **Target Release**: Milestone 13 (v0.13.0)  
> **Card Reference**: [CARD-046](file:///.github/cards/CARD-046-human-in-the-loop-interactive-state-parking-action-approval-and-resume-engine.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/hitl-approval-engine/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/hitl-approval-engine/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Domain HITL Models
- [x] **Task 1.1**: Create `src/domain/hitl/models.py` with `ApprovalStatus`, `PendingAction`, and `ApprovalDecision` (`[REQ-HITL-001]`).

### Slice 2: Approval Manager & State Parking
- [x] **Task 2.1**: Implement `src/application/hitl/approval_manager.py` with `park_action`, `decide`, `list_pending`, and `get_action` (`[REQ-HITL-002]`).

### Slice 3: REST API Endpoints
- [x] **Task 3.1**: Add `GET /api/hitl/pending` and `POST /api/hitl/decide` to `src/web/app.py` (`[REQ-HITL-003]`).

### Slice 4: Verification, Pre-Flight & Gate Closure
- [x] **Task 4.1**: Author unit and integration tests in `tests/unit/hitl/test_approval_manager.py` (`[REQ-HITL-004]`).
- [x] **Task 4.2**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates (`[REQ-HITL-004]`).
- [x] **Task 4.3**: Author ADR-0046 and sync `docs/rtm.json` with `[REQ-HITL-001]` through `[REQ-HITL-004]`.
- [x] **Task 4.4**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session. Mark Milestone 13 complete.
