# [CARD-081] Project File Tools

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/project-file-tools/`
> **Labels**: `type:feature`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Coding's `execute_code` sandbox is ephemeral and cannot edit a real project. Review cannot see a diff without reads. File tools must be jailed under `project_root`.

## 2. What to Build
- Tools: `list_project_dir`, `read_project_file`, `write_project_file`.
- Jail: resolve every path under `project_root` (later the selected project). Reject `..` escapes.
- HITL on `write_project_file`.
- Grant later: read to Conductor+Review+Coding; write to Coding only. Do not grant this card if it would bloat live allowlists.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-021]`: Paths resolve under `project_root`. `..` and outside-root paths are denied.
- [x] `[REQ-SDLC-022]`: `list_project_dir`, `read_project_file`, `write_project_file` are registered. Write parks on existing HITL.
- [x] Tests: jail deny, read/write under root.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not build a Projects studio this card.
- Do not give Conductor or Review `write_project_file`, `execute_code`, or `cli_exec`.
- Reuse `src/application/sdlc/paths.py`. Do not invent a second jail.
- Do not push. Stay on `qa`.
