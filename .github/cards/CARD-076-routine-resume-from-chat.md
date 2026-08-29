# [CARD-076] Routine Resume From Chat

> **Status**: Ready
> **Created**: 2026-08-28
> **Spec Reference**: none (leftover; no product this slice)
> **Labels**: `type:leftover`, `area:routines`, `area:web`

---

## 1. Why / Intent
CARD-073 resumes Chat after Approve. Routines also park via `run_turn`, but the operator has no Chat path to decide them.

## 2. Inspection
- `RoutineExecutor` creates an ephemeral session and calls `run_turn`. A park returns JSON and is recorded as a successful run. That session is not the Chat session the operator is looking at.
- Chat Approve/Reject only appear on the live SSE `approval_required` card (`submitHitlDecision`). There is no pending-approvals inbox and Routines Studio has only `approval_mode` ask|run — no Approve card.
- **Blocked on UI path.** Do not invent a second HITL inbox or a fake Chat approve surface.

## 3. Leftover
When (if) Chat can show and decide a routine park on a session the operator can see, resume that routine session with the same `resume` idea as CARD-073. Until then this stays Deferred.

## 4. Constraints & Honor Flags
- Do not invent a second HITL inbox.
- No fake product, no empty resume code, no spec, no CHANGELOG line.
