# Requirements: Honest Reflexion Verification

- `[REQ-VERIFY-010]`: `run_reflexion_turn` must not return `verification_passed=True` unless a verifier or builtin critic actually ran and returned `is_valid=true`.
- `[REQ-VERIFY-011]`: Empty deliverables and unparseable critic JSON fail closed (`is_valid=false`).
- `[REQ-VERIFY-012]`: Chat `self_verify` uses the builtin critic when no explicit verifier tool is supplied.
- `[REQ-VERIFY-013]`: SSE `reflexion_verified` includes the real `passed` boolean; a failed loop still emits the event with `passed=false`.
