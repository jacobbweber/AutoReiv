# Requirements Specification: Human-In-The-Loop (HITL) Interactive State Parking, Action Approval & Resume Engine

> **Spec Status**: Approved  
> **Target Release**: Milestone 13 (v0.13.0)  
> **Card Reference**: [CARD-046](file:///.github/cards/CARD-046-human-in-the-loop-interactive-state-parking-action-approval-and-resume-engine.md)  
> **Primary Component**: AutoReiv HITL (`src/domain/hitl/`, `src/application/hitl/`, `src/web/app.py`)

---

## 1. Executive Summary & Intent

**CARD-046** introduces a Human-In-The-Loop approval gate so that high-risk agent actions (flagged by the command guardrail or tool metadata) are parked in a pending queue for explicit human approval or rejection before the agent resumes execution.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-HITL-001] Domain HITL Models & Approval Status
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** define `ApprovalStatus` (`PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`), `PendingAction`, and `ApprovalDecision` domain models capturing action ID, description, risk level, requesting agent, timestamp, and human decision.

### [REQ-HITL-002] Approval Manager State Parking & Resume
- **EARS Pattern**: Event-Driven
- **Requirement**: When a tool invocation is flagged as requiring human approval, the `ApprovalManager` **shall** park the action in an in-memory pending queue and return an `asyncio.Future` that resolves when the human submits a decision via the REST API.

### [REQ-HITL-003] HITL REST API Endpoints
- **EARS Pattern**: Event-Driven
- **Requirement**: When a client calls `GET /api/hitl/pending`, the system **shall** return all pending actions awaiting approval. When a client calls `POST /api/hitl/decide`, the system **shall** resolve the corresponding parked action's future with the human's decision.

### [REQ-HITL-004] Comprehensive HITL Unit & Integration Test Suite
- **EARS Pattern**: State-Driven
- **Requirement**: When running `pytest`, the test runner **shall** verify action parking, approval resolution, rejection resolution, expiry handling, and REST endpoint integration with 100% passing tests.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `ApprovalManager.park_action()` returns a `PendingAction` and an `asyncio.Future`.
- [ ] `AC-2`: `ApprovalManager.decide(action_id, APPROVED)` resolves the future with an `ApprovalDecision`.
- [ ] `AC-3`: `ApprovalManager.decide(action_id, REJECTED)` resolves the future with a rejection decision.
- [ ] `AC-4`: `GET /api/hitl/pending` returns serialized pending actions.
- [ ] `AC-5`: `POST /api/hitl/decide` resolves a parked action and returns the decision.
- [ ] `AC-6`: `npm run preflight` passes all 6 quality gates cleanly.
