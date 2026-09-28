# [CARD-064] Honest Reflexion Verification

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/honest-reflexion-verification/`
> **Labels**: `type:bugfix`, `area:kernel`, `area:web`

---

## 1. Why / Intent
Self-verify / reflexion always reports success. The engine returns verified when no verifier tool is passed, and chat hard-codes `passed: true`. That badge is theater.

---

## 2. What to Build
- Stop treating a missing verifier as a pass.
- When Chat `self_verify` is on, run a builtin JSON critic (`is_valid` / `discrepancies`) and fail closed on empty output or bad JSON.
- SSE `reflexion_verified.passed` must match the engine result.
- Tests for skip, critic pass, critic fail, and unparseable critic output.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-VERIFY-010]`: No verifier/critic cannot yield `verification_passed=true`.
- [x] `[REQ-VERIFY-011]`: Empty output and invalid critic JSON fail closed.
- [x] `[REQ-VERIFY-012]`: `self_verify` invokes the builtin critic.
- [x] `[REQ-VERIFY-013]`: SSE `passed` matches the engine.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Do not invent a second verification stack; reuse `ReflexionLoopEngine`.
- Reads/tools already HITL-gated stay gated.
