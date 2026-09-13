# [CARD-094] Cap Nested Complete Context

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/nested-complete-ctx-cap/`
> **Labels**: `type:bug`, `area:orchestration`, `area:gateway`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---
## 1. Why / Intent
Live on Jarvis: Ollama is up. Direct Coding chat pongs in 7s. Nested pong handoff completes in 8s. CARD-001 nested handoff is silent then Ollama timed out. Direct Ollama CARD-001+write_project_file at num_ctx=131072 sent zero bytes for 90s. 8k/32k returned a tool call. 4096 max_tokens still takes ~3 min at this 27B (over the 180s read timeout). Chat 131k stays. Nested complete must be a small tool-calling call.

## 2. What to Build
- run_turn num_ctx min(limit, 32768), max_tokens 1024, think=false.
- Conductor task_intent is card id + spec slug.
- Coding first tool is read_card/read_spec.

## 3. Acceptance Criteria
- [x] REQ-ORCH-028 run_turn caps ctx 32768 and max_tokens 1024.
- [x] REQ-ORCH-029 complete() think=false.
- [x] pytest + ruff green.
