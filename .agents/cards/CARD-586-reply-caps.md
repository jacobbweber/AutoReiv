---
id: CARD-586
title: "Every model call carries a generous max-token limit (default 32768, Settings > Reply limits)"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: card/586-reply-caps
related:
  - CARD-567
  - CARD-574
labels:
  - type:feature
  - area:gateway
  - P1
needs_decision: none
milestone: M24
---

# [CARD-586] Every model call carries a generous max-token limit (default 32768, Settings > Reply limits)

> **Status**: Done (merged into qa 2026-09-29)
> **Labels**: `type:feature`, `area:gateway`, `P1`

## Why

Spark vLLM metrics on 2026-09-29: 106 of 810 requests were sent with no max-token limit, so vLLM allowed up to the rest
of the 262k window. Chat replies were capped (CARD-567, 16384), but planning and reflexion calls sent none, and child
(hand-off) turns used a fixed 8192. Helper calls ask for 250-800 tokens, which a thinking model (nemotron-3.5-lightning
spent 1500 tokens thinking on a one-paragraph ask) uses up before it answers. Jacob (2026-09-29): always send a limit,
generous (about 32768 output tokens), thinking allowed but bounded, configurable in Settings > Reply limits, not infinite.

## Change

- `reply_limits.py`: `DEFAULT_MAX_TOKENS` 16384 -> 32768 (thinking counts toward it); `HELPER_MIN_TOKENS` 4096.
- `gateway_service.py`: `_with_reply_cap()` on every `complete()` and `stream()`: a request without `max_tokens` gets the
  Settings value (`set_reply_cap_resolver`, wired in `app.py`), capped at a quarter of `num_ctx`; a non-streaming helper
  call asking for less than 4096 gets 4096. A streaming chat reply keeps the operator's own limit even if small.
- `agent_kernel.py`: child (hand-off) turns use the reply limit instead of the fixed 8192.
- Settings > Reply limits text and placeholder: 32768, includes thinking, applies to every call.

## Acceptance

- [x] Calls without a limit get the Settings value / default; capped at a quarter of the window.
- [x] Helper calls get at least 4096; chat replies keep a user-set small limit.
- [x] Child turns use the reply limit.
- [ ] Live on the throwaway :8770: vLLM request max_tokens never unbounded (see Log).

## Merge note

`reply_limits.py`, `index.html` and `settings_reply_limits.js` also change in CARD-585 (seconds default 1200) on
neighbouring lines; merging the second card needs a small conflict resolution (keep both: 32768 tokens, 1200 seconds from
the first token).

## Log

- 2026-09-29: built on the branch with tests (`tests/unit/gateway/test_card586_reply_caps.py`).
- 2026-09-29 (live, throwaway :8770, combined branch): battery ran with the caps (123 turns, no reply cut short by the limit). The vLLM `request_params_max_tokens` check could not be done: Spark vLLM was down for the whole round; Ollama does not expose request params. Live acceptance stays open.
- 2026-09-29: preflight --fast --base qa GREEN. Jacob: merge to qa (battery brief allows merging small fixes). Done; merged into qa.
