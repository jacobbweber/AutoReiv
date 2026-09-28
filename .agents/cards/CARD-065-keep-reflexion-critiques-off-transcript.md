# [CARD-065] Keep Reflexion Critiques Off Transcript

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/reflexion-transcript-isolation/`
> **Labels**: `type:bugfix`, `area:kernel`, `area:web`

---

## 1. Why / Intent
CARD-064 made the critic honest. Retries were still saved as USER messages (`CRITIQUE ON PREVIOUS OUTPUT`), so the transcript looked like the human sent them. Chat also only emitted `reflexion_attempt` once (1/3).

---

## 2. What to Build
- Inner reflexion turns never write to session history.
- Chat persists the original user prompt and the final assistant reply only.
- `on_progress` emits `reflexion_attempt` per try and `reflexion_critique` on each fail.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-VERIFY-014]`: Refinement prompts are never persisted as USER messages.
- [x] `[REQ-VERIFY-015]`: Session history is original user + final assistant only.
- [x] `[REQ-VERIFY-016]`: SSE fires `reflexion_attempt` per attempt and `reflexion_critique` on fail.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

---

## 4. Constraints & Honor Flags
- Do not invent a second verification stack; reuse `ReflexionLoopEngine`.
- Goal-mode inner steps already used `save_to_history=False`; keep that.
