# [CARD-010] Sandbox Security Guardrails and HITL Approvals

> **Status**: Done
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/sandbox-security-and-hitl-approvals/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Provide ephemeral temp-dir execution sandboxing, dangerous command guardrails, and a persistent human-in-the-loop approval state machine with stream cancellation

---

## 2. What to Build
SandboxedSubprocessWorker, is_high_risk tool flags, pending_approvals SQLite table, PAUSED_AWAITING_APPROVAL state, and REST approval resume endpoints

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Requirement 1: ...
- [x] Requirement 2: ...
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
