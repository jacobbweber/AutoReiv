# Implementation Tasks: Context Compaction, Episodic Memory & Resilience Hardening

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-MEMORY-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Context Compactor & Sliding Window Truncation
- [x] **Task 1.1** `[REQ-MEMORY-001]`, `[REQ-MEMORY-002]`: [RED] Write unit tests in `tests/unit/kernel/test_context_compactor.py` validating sliding window preservation, intermediate turn summarization, and large tool output pruning.
- [x] **Task 1.2** `[REQ-MEMORY-001]`, `[REQ-MEMORY-002]`: [GREEN] Implement `ContextCompactor` in `src/application/kernel/context_compactor.py` and integrate into `AgentKernel`.

### Slice 2: Episodic Fact Memory Store
- [x] **Task 2.1** `[REQ-MEMORY-003]`: [RED] Write unit tests in `tests/unit/memory/test_episodic_memory.py` validating saving, querying, updating, and deleting facts across sessions.
- [x] **Task 2.2** `[REQ-MEMORY-003]`: [GREEN] Add `episodic_facts` table and CRUD methods in `src/infrastructure/memory/sqlite_store.py` and create `EpisodicMemorySkill` in `src/application/skills/memory_skill.py`.

### Slice 3: Gateway Exponential Backoff with Jitter & Client Pooling
- [x] **Task 3.1** `[REQ-MEMORY-004]`, `[REQ-MEMORY-005]`: [RED] Write unit tests in `tests/unit/gateway/test_gateway_resilience.py` verifying localized retries with backoff and persistent HTTP client pooling.
- [x] **Task 3.2** `[REQ-MEMORY-004]`, `[REQ-MEMORY-005]`: [GREEN] Implement `_execute_with_retry` with exponential backoff + jitter in `src/application/gateway/gateway_service.py` and connection pooling in `OllamaProviderAdapter` & `OpenAIProviderAdapter`.

### Slice 4: Streaming Cycle Detection & Stream Telemetry
- [x] **Task 4.1** `[REQ-MEMORY-006]`: [RED] Write unit tests in `tests/unit/kernel/test_streaming_cycle_detector.py` verifying cycle detection in `stream_turn` and TTFT/TPS telemetry calculation.
- [x] **Task 4.2** `[REQ-MEMORY-006]`: [GREEN] Extract `CycleDetector` into `src/application/kernel/cycle_detector.py`, integrate into `run_turn` & `stream_turn`, and add TTFT/TPS to `TelemetryCollector`.

### Slice 5: Verification, Traceability, & PR Gate
- [x] **Task 5.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 5.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 5.3**: Conclude Milestone 9 and merge into `qa`.
