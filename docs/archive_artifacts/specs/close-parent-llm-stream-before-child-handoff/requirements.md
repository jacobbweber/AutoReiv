# Requirements

- REQ-ORCH-023: `stream_turn` must aclose the parent LLM stream (break on `is_finished`) before executing tools, including `handoff_to_agent`. Nested `complete()` must not run while that stream context is open.
- REQ-ORCH-024: `gateway.stream` acloses the inner `provider.stream` in `finally`. Ollama `complete` and `stream` POST relative `/api/chat` when the httpx client already has `base_url`. Pool timeout is 30s (connect stays 30s, read stays 180s).
- REQ-ORCH-025: `httpx.TimeoutException` is raised as `Ollama timed out at {base_url}`, not `Failed to connect`. Connect and timeout failures still map to HandoffResult status `failed`.
