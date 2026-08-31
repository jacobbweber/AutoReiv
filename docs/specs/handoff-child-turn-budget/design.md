# Design

Conductor `handoff_to_agent` builds a `HandoffEnvelope` with no `max_turns` arg, so the default is the child budget. Coding's profile is 10, but the engine used to overwrite it with `min(max(1, envelope.max_turns), 10)` which made the silent default 5.

New bound is `min(max(envelope, profile, 10), 15)`. Coding (and any specialist with a 10-turn profile) gets a real ReAct budget. Explicit 3-turn envelopes still floor at 10 so Conductor cannot accidentally starve Coding.

Child `run_turn` uses gateway `complete()` while the parent is still streaming. Sharing one AsyncClient meant connect/pool waits hit the 15s timeout even though Ollama was up. `complete()` now opens its own client unless a test injected one. Connect timeout is 30s.

If the child returns provider-failure text instead of raising, the engine still marks `failed`. Kernel `HANDOFF_COMPLETE` inspects the same markers so the Chat badge is Failed, not Done.

## Out of this slice

Conductor allowlist. Flipping live CARD-001. Cloning the Ollama adapter. Push.
