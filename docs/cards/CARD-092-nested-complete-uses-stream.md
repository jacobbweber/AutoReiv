# [CARD-092] Nested Complete Uses Stream

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/nested-complete-uses-stream/`
> **Labels**: `type:bug`, `area:gateway`, `area:orchestration`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---
## 1. Why / Intent
Conductor Chat streams to Ollama and works. Coding handoff uses `run_turn` -> `gateway.complete()` which POSTed `stream=false` with `num_ctx=131072`. Ollama buffers the whole JSON and times out. Assistant/AutoReiv look fine because they are parent Chat (`stream_turn`), not nested `complete()`. Not an allowlist/RBAC miss. Purpose slot is a separate persist bug (CARD-093).

## 2. What to Build
- Ollama `complete()` consumes `stream()` (`stream=true`) and assembles `CompletionResponse`.
- Stream done-chunk carries usage. Generator is aclosed after accumulate.
- Nested handoff and parent Chat share one HTTP shape.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ORCH-026]`: `complete()` POSTs `/api/chat` with `stream=true` and concatenates chunk content/tool_calls.
- [x] `[REQ-ORCH-027]`: Timeout/connect/404 still raise the same provider errors. Usage is taken from the done chunk.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Do not weaken HITL.
- Do not change Coding's default purpose here (CARD-093 persists Forge edits).
