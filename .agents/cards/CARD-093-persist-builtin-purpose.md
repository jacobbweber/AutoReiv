# [CARD-093] Persist Builtin Agent Purpose

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/persist-builtin-purpose/`
> **Labels**: `type:bug`, `area:forge`, `area:agents`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---
## 1. Why / Intent
Forge save of Coding purpose (Task Execution -> General Assistant) snaps back. `PUT /api/agents/{id}` validates purpose on the profile, then for builtins stores `AgentCustomization` without a purpose field. Registry overlay never applies purpose, so the next GET reloads `CODING_PROFILE.purpose = task_execution`.

## 2. What to Build
- `AgentCustomization.purpose` optional string.
- Builtin save writes `purpose`.
- Registry overlay applies a valid `ModelPurpose`.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-FORGE-020]`: Saving Coding purpose `general` survives GET `/api/agents/coding`.
- [x] `[REQ-FORGE-021]`: Invalid purpose strings are ignored; baseline purpose stays.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Do not delete builtin profiles. Override only.
