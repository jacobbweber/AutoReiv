---
id: CARD-591
title: "Helper calls get 16384 tokens of room (4096 cut nemotron's thinking)"
status: In Review
created: 2026-09-30
branch: card/591-helper-token-floor
related:
  - CARD-586
labels:
  - type:bug
  - area:gateway
  - P2
needs_decision: none
milestone: M24
---

# [CARD-591] Helper calls get 16384 tokens of room (4096 cut nemotron's thinking)

> **Status**: In Review
> **Labels**: `type:bug`, `area:gateway`, `P2`

## Why

2026-09-30 battery on nemotron-3.5-lightning (Spark): vLLM metrics for 155 requests show 133 with max_tokens 32768
(replies) and 22 with 4096 (helper calls raised to `HELPER_MIN_TOKENS`); 4 requests ended with finish_reason `length`
and no request generated more than 5000 tokens, so those 4 were helper calls (memory extraction, detection, planning)
cut at 4096 while still thinking. Jacob prefers generous, bounded limits.

## Change

- `HELPER_MIN_TOKENS` 4096 -> 16384.
- The helper floor is capped at a quarter of the request's context window (`reply_token_limit`), like replies, so a
  small window never gets prompt + max_tokens over its size. A helper's own larger limit is kept.
- Tests: `tests/unit/gateway/test_card591_helper_token_floor.py`; CARD-586 test uses 20000 for the "kept" case.

## Acceptance

- [x] Helper calls below 16384 get 16384 (or a quarter of a smaller window); larger helper limits and chat limits kept.
- [ ] Live: no `length` finishes for helper calls in a nemotron battery (see Log).

## Log

- 2026-09-30: built on the branch with tests.
