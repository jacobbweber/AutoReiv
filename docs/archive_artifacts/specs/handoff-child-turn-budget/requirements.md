# Requirements

- REQ-ORCH-020: `HandoffEnvelope.max_turns` defaults to 10. The isolation engine sets the child profile budget to `min(max(envelope.max_turns, specialist.max_turns, 10), 15)` so a normal handoff is not silently 5 turns.
- REQ-ORCH-021: If child `run_turn` raises, or the result text looks like a provider failure (`Failed to connect`, `All N candidate providers failed`), `HandoffResult.status` is `failed` and `success` is False. Chat `handoff_complete` must not treat that as Done.
- REQ-ORCH-022: Ollama connect timeout is 30s (read stays 180s). Nested `complete()` uses a dedicated httpx client so it is not starved by the parent stream's shared pool.
