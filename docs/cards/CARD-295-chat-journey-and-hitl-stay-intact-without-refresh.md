# [CARD-295] Chat journey and HITL stay intact without refresh

> **Status**: Ready  
> **Branch**: `feat/super-marathon-ui`
> **Priority**: P0
> **Created**: 2026-09-13
> **Spec Reference**: docs/cards/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Operator sees Formulate/Execute strips and HITL approve in the same live chat without browser refresh; refresh currently reveals HITL but loses journey chrome (progress honesty failure).

---

## 2. What to Build
Bind Chat UI journey chrome + HITL park to the same job_id/SSE through Formulate to Execute to waiting_approval; durable transcript; live smoke without refresh.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Requirement 1: ...
- [ ] Requirement 2: ...
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Done bar (anti-theatre)

1. Trigger a Chat path that parks HITL (chit-chat or multi-phase job) **without** refreshing the browser.
2. Operator sees Formulate/Execute (or equivalent journey strips) **and** the HITL Approve/Deny control in the **same** live chat thread.
3. Journey chrome remains bound to the same `job_id` / SSE through park; refresh is not required to reveal HITL.
4. After Approve/Deny, journey continues or closes honestly (no silent wait).
5. Automated or scripted live smoke artifact under `scratch/` (not AppData laundry in repo).

