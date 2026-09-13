# [CARD-297] Desktop Organize Windows always on top

> **Status**: Ready  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: scratch/jacobs-walk-braindump.txt
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Organize Windows button must stay above all open studio windows so the operator can always reach it.

---

## 2. What to Build
Raise z-order / stacking for Organize Windows control so it never sits under open windows.

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

## Design lock (UI/UX — marathon)
- Organize Windows always highest z-index above open windows.
