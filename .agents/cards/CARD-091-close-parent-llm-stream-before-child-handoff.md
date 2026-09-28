# [CARD-091] Close Parent LLM Stream Before Child Handoff

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/close-parent-llm-stream-before-child-handoff/`
> **Labels**: `type:bug`, `area:orchestration`, `area:gateway`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Conductor Chat can talk to Ollama at `http://192.168.1.29:11434`, but `handoff_to_agent` coding fails with `[ollama] Failed to connect to Ollama at http://192.168.1.29:11434` before the child thinks. Parent `stream_turn` left the LLM HTTP stream open while executing tools. Child `run_turn` → `complete()` then hit a pool/connect timeout that CARD-090 mislabeled as a down server. Nested `complete()` also POSTed an absolute URL on a `base_url` client.

## 2. What to Build
- `stream_turn` binds the gateway stream, async-for, acloses it (and breaks on `is_finished`) BEFORE tool execution.
- `gateway.stream` acloses the inner `provider.stream` in `finally`.
- Ollama `complete`/`stream` POST relative `/api/chat`. Pool timeout 30s.
- `TimeoutException` → `Ollama timed out at ...` (never lie with Failed to connect).
- Timeout/connect failures still map to HandoffResult `failed`.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-ORCH-023]`: Parent stream is aclosed before nested complete()/tools. Fake adapter stream stays open until aclose; child complete is not called while it is open.
- [x] `[REQ-ORCH-024]`: Gateway acloses inner provider.stream. Ollama uses relative `/api/chat` on a base_url client. Pool timeout 30s.
- [x] `[REQ-ORCH-025]`: TimeoutException is labeled timed out, not Failed to connect. Connect/timeout still status=failed.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Do not weaken HITL. Auto-run still skips parks for non-high-risk; `write_project_file` stays high-risk unless already listed.
- Do not flip Jacob's CARD-001.
