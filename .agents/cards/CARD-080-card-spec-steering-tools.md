# [CARD-080] Card Spec Steering Tools

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/card-spec-steering-tools/`
> **Labels**: `type:feature`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Cards today are only markdown in AutoReiv's repo. Conductor needs tools that work on a `project_root` so the SDLC loop can list, read, write, and status cards plus specs without inventing a second engine.

## 2. What to Build
- One skill with public tools: `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_spec`, `write_spec`, `read_steering`.
- `set_card_status` enforces Discuss | Ready | In Progress | In Review | Returned | Done and the legal transitions (Ready requires spec path; Returned increments rounds; max rounds deny).
- Optional `project_root` defaults to the AutoReiv checkout until Projects exist.
- HITL park on `write_card`, `write_spec`, `set_card_status`.
- Program spec at `docs/specs/spec-driven-sdlc-team/`.
- No UI this card except what tools need.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-010]`: `set_card_status` enforces the state machine. Illegal transitions fail. Discuss -> Ready requires a spec path. Returned at max cannot go In Progress.
- [x] `[REQ-SDLC-011]`: Frontmatter parse/write for Status, Spec Reference, review_rounds, max_review_rounds, return_reason, optional github_issue.
- [x] `[REQ-SDLC-012]`: Cards under `{root}/.github/cards/CARD-NNN-*.md`. Specs under `{root}/docs/specs/<slug>/`.
- [x] `[REQ-SDLC-020]`: write_card, write_spec, set_card_status are high-risk HITL tools.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not build a Projects studio or file-edit tools this card.
- Do not invent a second HITL or handoff engine.
- Do not give Conductor or Review `execute_code` or `cli_exec` (those agents are later cards).
- Do not push. Stay on `qa`.
