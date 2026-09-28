---
id: CARD-567
title: "A runaway model reply stops at a reply limit instead of hanging"
type: bug
status: In Review
priority: P1
milestone: M24
needs_decision: none
proof:
  journeys: [card-567-reply-limits]
  checks: [tests/unit/kernel/test_card567_reply_limits.py]
branch: fix/card-567-reply-limits
log: {minutes: 50, qa_runs: 1, findings: 1}
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
- (to findings list) The limits have an API (`/api/settings/reply-limits`) but no Settings UI field yet.
- The stop is shown through the existing failed-reply path: a "Reply failed: Stopped: ..." alert and toast, plus the saved chat row.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-567-reply-limits | desktop | PASS (run 1) | 200 tokens: stopped with the reply-limit message (52 s, Spark); limits cleared: "pong" in 25 s; 5 s: stopped with the time-limit message in 8.6 s; chat idle after each |

Checks: test_card567_reply_limits.py (7; 6 failing first, the endless-stream one hung until the test's own timeout); full not-slow
suite 2169 passed, 3 pre-existing card354 failures; fast preflight GREEN.

## Test it (Jacob)
1. In PowerShell: `irm -Method Put http://127.0.0.1:8000/api/settings/reply-limits -ContentType application/json -Body '{"max_tokens":200}'`.
2. Ask Architect a long "think step by step" question: the reply stops within about a minute with "Stopped: the model reached the reply limit of 200 tokens ..." and the chat is usable.
3. Clear it: same command with `'{"max_tokens":null,"max_seconds":null}'` (back to 16384 tokens / 600 s); a normal question answers as before.

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-567\...`

## Release note
CARD-567: a model reply that never ends now stops at a reply limit (default 16384 tokens or 600 s per model call, setting `reply_limits`) with a clear message instead of hanging the chat.
