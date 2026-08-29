# Design

`approval_mode` is ask (park high-risk tools) or run (skip park).

Chat Auto-run toggle is a per-turn request flag, same shape as Self-Verify.

`HandoffEnvelope.approval_mode` is copied from tool context and passed to the child `run_turn`.

Routines persist the value in `metadata.approval_mode`. The executor passes it to `run_turn`.
