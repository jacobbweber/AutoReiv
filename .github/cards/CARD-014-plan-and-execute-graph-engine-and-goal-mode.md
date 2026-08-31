# [CARD-014] Plan-and-Execute Graph Engine and Goal Mode

> **Status**: Parked
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/plan-and-execute-graphs/
> **Labels**: `type:feature`, `needs-triage`

---

_Parked 2026-08-29. Superseded: control-plane Job/Phase (CARD-096-101, `docs/specs/control-plane-job-phase/`) replaces the DAG / Goal-mode graph idea. Do not implement this card. Not deleted._

## 1. Why / Intent
Decompose complex multi-phase user goals into structured step-by-step DAG checklists, executing sequentially with live visual UI progress

---

## 2. What to Build
PlanAndExecuteEngine, PlanningSkill, visual plan step tracker in Web UI, and /goal mode toggle

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
