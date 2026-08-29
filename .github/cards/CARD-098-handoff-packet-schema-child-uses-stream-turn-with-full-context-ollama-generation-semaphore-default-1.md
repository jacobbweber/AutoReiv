# [CARD-098] Handoff packet schema; child uses stream_turn with full context; Ollama generation semaphore default 1

> **Status**: Ready
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-job-phase/`
> **Labels**: `type:feature`, `area:orchestration`, `area:gateway`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Child handoffs get a packet (goal, facts, constraints, done_when, budget), not the parent transcript. Child MUST `stream_turn` with the child's full 131k context â€” no `run_turn` / nested `complete()`, no CARD-094 32k cap on that path. Parent stream is aclosed first (CARD-091). Global Ollama generation semaphore default 1 so Nimo VRAM is not stampeded.

## 2. What to Build
- `HandoffPacket` schema: goal, facts, constraints, done_when, budget. Child user message is the packet. New session id, empty history.
- Child path: `stream_turn` only. Full child num_ctx. Depth cap 2. No self-handoff.
- Settings `max_concurrent_generations` default 1 (range 1â€“3). Queue extra (phase queued). If a handoff batch exceeds the cap, error â€” do not silent-truncate.

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-ORCH-036]`: Packet requires goal/facts/constraints/done_when/budget. Child gets zero parent transcript. Missing field fails closed.
- [ ] `[REQ-ORCH-037]`: Child uses `stream_turn` with full context. No nested `complete()`. No 32k `run_turn` cap on this path. CARD-091 aclose still holds.
- [ ] `[REQ-ORCH-038]`: Semaphore default 1. Extra work queues. Batch > cap errors; no silent truncate.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Hardware: local Ollama on Nimo. VRAM is the constraint.
- Do not weaken HITL. Do not re-open nested complete under a live parent stream.
- Spec: `docs/specs/control-plane-job-phase/`.
