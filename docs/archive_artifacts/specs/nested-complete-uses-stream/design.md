# Design

Child handoff calls `kernel.run_turn` -> `gateway.complete`. Parent Chat calls `stream_turn` -> `gateway.stream`. Ollama `stream=false` with 131k `num_ctx` waits for a full buffered JSON and times out. `complete()` now consumes `stream()` so TTFT resets the read timeout per chunk, then acloses the generator.
