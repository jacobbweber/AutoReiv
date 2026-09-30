---
id: CARD-585
title: "Generation slots per provider plus a background pool; reply time limit from the first token (20 min)"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: card/585-provider-slot-pools
related:
  - CARD-579
  - CARD-567
labels:
  - type:feature
  - area:gateway
  - P1
needs_decision: none
milestone: M24
---

# [CARD-585] Generation slots per provider plus a background pool; reply time limit from the first token (20 min)

> **Status**: Done (merged into qa 2026-09-29)
> **Labels**: `type:feature`, `area:gateway`, `P1`

## Why

2026-09-29 battery: one process-wide slot pool covered every provider. Slow Spark turns held the slots, so the Developer
on Nimo waited up to 335 s before its model was even called (dev-02 took 3.7x longer), a hand-off child sat queued, and
background calls took the same slots. The 600 s reply limit also counted that queue time (an Architect turn hit 600 s
with its first token at 281 s). Jacob (2026-09-29): separate pools per provider (Spark vs Nimo) plus a background pool;
the reply limit starts at the model's first token and is raised to 1200 s; abort generation on disconnect if feasible.

## Change

- `generation_semaphore.py`: `GenerationPools` = one `GenerationSemaphore` per provider endpoint (host:port of the
  adapter's base URL, so the default vLLM provider and an agent override on the same gateway share one pool) plus a
  background pool (1 slot). The Settings cap (max concurrent generations, 1-3) applies to each provider pool.
- `gateway_service.py`: `complete()` / `stream()` take the slot from `generation_slot_for(request)`: background pool when
  `request.background`, else the pool of the provider that serves `request.model`.
- `CompletionRequest.background` (new, default False). Set on memory extraction, capability detection, Teach
  distillation and Studio helper calls.
- `agent_kernel.py`: the reply deadline is set at the first token (content, thinking or tool call); before that the
  provider's read timeout bounds silence. `reply_limits.DEFAULT_MAX_SECONDS` 600 -> 1200; the stop message says the
  seconds count from the first token. Settings > Reply limits text and placeholder updated.
- Disconnect/abort: checked. Stop (abort) cancels the worker, and cancel or the time limit closes the provider HTTP
  stream; live check on Spark: closing a stream through the gateway :8099 drops vLLM's running requests to 0 within 3 s,
  so the server stops generating. Chat SSE disconnect (phone locked, tab closed) intentionally keeps the job running
  (CARD-530 design), so it does not abort. Tests pin both close paths.

## Acceptance

- [x] A Spark reply holding the only slot does not block a Nimo call; same-provider calls still queue at the cap.
- [x] Background calls run while a chat reply holds its provider slot.
- [x] Slot wait and a slow start before the first token do not count toward the time limit; after the first token the
      limit still stops the reply and closes the stream.
- [x] Default reply time limit 1200 s.
- [x] Live on the throwaway :8770 (see Log).

## Log

- 2026-09-29: built on the branch with tests (`tests/unit/gateway/test_card585_slot_pools.py`).
- 2026-09-29 (live, throwaway :8770, combined branch): Developer on Nimo started replies in 3-5 s while every Spark call was stuck (gateway swap/outage), so provider pools are separate live. Architect + Developer + 4 Spark agents moved to Nimo shared the Nimo pool (cap 3) for ~2 h with no deadlocks; 122/123 turns ok. Closing a stream through :8099 dropped vLLM running requests to 0 (earlier check).
- 2026-09-29: preflight --fast --base qa GREEN. Jacob: merge to qa (battery brief allows merging small fixes). Done; merged into qa.
