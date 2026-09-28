---
id: CARD-567
title: "A runaway model reply stops at a reply limit instead of hanging"
type: bug
status: Ready
priority: P1
milestone: M24
needs_decision: none
proof:
  journeys: [card-567-reply-limits]
  checks: [tests/unit/kernel/test_card567_reply_limits.py]
branch: fix/card-567-reply-limits
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-09-28
---

# CARD-567 A runaway model reply stops at a reply limit instead of hanging

## Problem
A model reply can stream without end and the chat hangs: Architect on Nimo streamed reasoning with no end in CARD-563 round 1
(finding moved here from docs/findings.md, M24). Nothing stops it; the operator can only wait or reload.

## Cause
The kernel's streaming call (`AgentKernel.stream_turn`, src/application/kernel/agent_kernel.py) sends no output limit:
`CompletionRequest.max_tokens` is unset, so Ollama gets no `num_predict` (Ollama default -1 = unbounded, with context shift it can
generate forever) and vLLM generates up to the rest of the context window. The adapters' httpx read timeout (200 s) only bounds
silence between chunks, so a model that keeps streaming reasoning never times out, and there is no per-call wall-clock limit.

## Change
- New `src/application/kernel/reply_limits.py`: `resolve_reply_limits(store)` reads setting `reply_limits`
  (`{"max_tokens": int, "max_seconds": int}`), then env `AUTOREIV_MAX_REPLY_TOKENS` / `AUTOREIV_MAX_REPLY_SECONDS`,
  then defaults 16384 tokens / 600 s. max_tokens is also capped at a quarter of the context window (compaction keeps the
  prompt under 75%, so vLLM never rejects the request), floor 1024.
- stream_turn sets `max_tokens` on every streaming request (Ollama `num_predict`, vLLM `max_tokens`) and wraps the stream in a
  wall-clock deadline (also bounds silence).
- On the deadline, or on `finish_reason == "length"` with no answer and no tool call: stop the turn, save and show a plain
  message ("Stopped: the model reached the reply limit ... Settings: reply_limits"). A truncated answer keeps its text plus a
  one-line note that it was cut.
- `GET/PUT /api/settings/reply-limits` to read and change the limits (no UI in this card).

## What dies
Unbounded model replies in chat turns.

## Proof
- Journey `card-567-reply-limits` (live QA, throwaway data, real Spark): set reply-limits to 200 tokens, ask Architect for a
  long step-by-step answer: the turn ends with the "reply limit" message, the chat is usable, and the next turn (limits back to
  default) answers normally. Then max_seconds 5 with a long ask: the turn stops with the time-limit message.
- Checks: `test_card567_reply_limits.py`: the streaming request carries max_tokens (failing first); a stream that never ends is
  stopped by max_seconds with the message (failing first: it hangs, guarded by a test timeout); finish_reason length with only
  reasoning gives the message; setting > env > default resolution; a normal reply is unchanged (negative).

## Plan and decisions
Technical defaults, configurable; not a product decision. No Spark/Nimo server config changes. A Settings UI field is left out.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\\Users\\jacob\\AppData\\Local\\Temp\\autoreiv-qa\\card-567\\...`

## Release note
CARD-567: a model reply that never ends now stops at a reply limit (default 16384 tokens or 600 s per model call, setting `reply_limits`) with a clear message instead of hanging the chat.
