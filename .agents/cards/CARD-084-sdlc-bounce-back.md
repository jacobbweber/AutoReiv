# [CARD-084] SDLC Bounce Back

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/sdlc-bounce-back/`
> **Labels**: `type:feature`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Bounce-back is the CARD-080 state machine plus `handoff_to_agent`. Do not invent a second workflow engine. Coding may only move In Progress -> In Review. Conductor returns Returned cards to Coding until max rounds.

## 2. What to Build
- Coding `set_card_status` is In Progress -> In Review only (use in-flight agent id).
- Grant Coding the SDLC read/write file tools + card read + set_card_status. Drop wiki reads to stay under 12.
- Prompt text on Conductor and Coding for the one-card loop.
- Tests: Returned with rounds < max can go In Progress; at max cannot. Coding cannot set Done.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-006]`: Loop is documented. No second workflow engine.
- [x] `[REQ-SDLC-033]`: Coding may set In Progress -> In Review only. Other status writes are denied.
- [x] Tests cover max-rounds deny and Coding restriction.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not invent a second HITL or handoff engine.
- Do not give Conductor or Review execute_code or cli_exec.
- Do not push. Stay on `qa`.
