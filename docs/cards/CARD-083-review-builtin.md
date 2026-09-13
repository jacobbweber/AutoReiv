# [CARD-083] Review Builtin

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/review-builtin/`
> **Labels**: `type:feature`, `area:agents`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Review judges Coding against the spec only. Pass marks Done. Fail returns the same card with a concrete gap. Review does not edit product files or cards.

## 2. What to Build
- Builtin `id=review`, name Review.
- Allowlist ONLY: list_cards, read_card, read_spec, read_steering, list_project_dir, read_project_file, set_card_status, handoff_to_agent, lookup_agents.
- NO execute_code, write_card, write_spec, write_project_file, cli_exec.
- Pin: set_card_status.
- lookup aliases: qa, tester, review.
- Tests: deny writes/execute_code; can set Returned/Done from In Review.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-031]`: Review allowlist is exactly those 9 tools. Writes and execute_code are denied.
- [x] `[REQ-SDLC-035]`: Aliases qa, tester, review resolve to Review. Review can `set_card_status` In Review -> Done | Returned.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- No product edits. No second HITL engine.
- Do not give Review execute_code or cli_exec.
- Do not push. Stay on `qa`.
