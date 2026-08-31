# Design

Parent Conductor `stream_turn` async-for `gateway.stream`, which wraps `provider.stream` via the reasoning demuxer. `ollama_adapter.stream` holds `async with client.stream(...)` until the async generator is aclosed. Python `async for` does not aclose on `break`, and after `done: true` the generator can still sit inside `aiter_lines()` with the HTTP request open.

Child handoff uses `run_turn` → `complete()` while that parent request is in flight. Ollama (or the shared host) then stalls the second request. CARD-090 mapped `TimeoutException` (including pool=15s) to `Failed to connect to Ollama at {base_url}`, so a busy server looked identical to a down one. Nested `complete()` also built `AsyncClient(base_url=self.base_url)` and POSTed the absolute `{base_url}/api/chat`.

Fix: bind the stream generator, consume until `is_finished`, `aclose()` in `finally`, then run tools. Gateway acloses the inner provider generator the same way. Ollama uses relative `/api/chat` / `/api/tags` when the client has `base_url`. Pool timeout 30s. Timeouts say timed out.

## Out of this slice

Conductor allowlist. HITL policy. Flipping live CARD-001. Push.
