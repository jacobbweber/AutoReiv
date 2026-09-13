# [CARD-090] Give Child Handoffs a Real Turn Budget

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/handoff-child-turn-budget/`
> **Labels**: `type:bug`, `area:orchestration`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Conductor handed CARD-001 to Coding and the UI said Delegation Completed / Done after ~1 turn. No files were written. Envelope `max_turns` defaulted to 5 and the engine overwrote Coding's profile budget of 10. A retry then returned `Failed to connect to Ollama` while Conductor was still using that host, because nested `complete()` shared the parent stream's httpx pool. Connection errors still painted as Done because `handoff_complete` treats `status==='completed'` as success.

## 2. What to Build
- Default envelope `max_turns` to 10. Engine child turns = `min(max(envelope, profile, 10), 15)`.
- Provider failure text (`Failed to connect`, `candidate providers failed`) maps to HandoffResult status `failed` (success False), not completed.
- Ollama connect timeout 30s. Nested `complete()` uses its own httpx client.
- Coding prompt: do the work with tools; do not return a prose plan as the whole turn.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ORCH-020]`: Envelope default 10. Engine applies at least 10, cap 15.
- [x] `[REQ-ORCH-021]`: Provider connect failures are HandoffResult failed / success False. UI Failed when status !== completed.
- [x] `[REQ-ORCH-022]`: Ollama connect timeout 30s; nested complete() does not share a stuck parent stream pool.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Do not change Conductor allowlist. Do not flip Jacob's CARD-001.
