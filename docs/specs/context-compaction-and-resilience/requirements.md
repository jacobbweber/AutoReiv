# Requirements Specification: Context Compaction, Episodic Memory & Resilience Hardening

> **Spec Status**: Approved  
> **Target Release**: Milestone 9 (v0.9.0)  
> **Primary Component**: `AutoReiv.Memory` & `AutoReiv.Gateway`  
> **Applicable ADRs**: `docs/adr/0010-context-compaction-episodic-memory-and-gateway-resilience-hardening.md`  
> **Linked Work Card**: `.github/cards/CARD-009-context-compaction-episodic-memory-and-resilience-hardening.md`

---

## 1. Executive Summary & User Story
As an operator interacting with AutoReiv over long conversational sessions,  
I want the agent to automatically compact past conversation turns and remember cross-session facts,  
So that conversations never crash from context window overflow, facts persist across sessions, and transient network errors self-heal with backoff and connection pooling.

---

## 2. EARS Functional Requirements

### `[REQ-MEMORY-001]` Context Window Compaction & Sliding Window
- **Ubiquitous**: THE `ContextCompactor` SHALL ensure that any conversation history exceeding `max_context_tokens` is compacted such that the initial `system` prompt is preserved, intermediate turns are condensed into a single summary message, and the most recent $N$ turns are retained verbatim.

### `[REQ-MEMORY-002]` Large Tool Output Pruning
- **Event-driven**: WHEN a tool result exceeds `max_tool_chars` (default: 8,000 characters) during compaction, THE `ContextCompactor` SHALL truncate the output with a clear `[TRUNCATED: N chars omitted]` indicator.

### `[REQ-MEMORY-003]` Episodic Fact Memory Store
- **Ubiquitous**: THE `SQLiteStateStore` SHALL maintain an `episodic_facts` table storing discrete `(id, entity, key, value, confidence, source_session_id, updated_at)` records allowing agents to save and query persistent facts.

### `[REQ-MEMORY-004]` Gateway Exponential Backoff & Jitter
- **Event-driven**: WHEN a provider execution encounters a transient connection error or HTTP 429/5xx status code, THE `MultiProviderGateway` SHALL retry up to `max_retries` times with exponential backoff and randomized jitter before failing over to the next candidate model.

### `[REQ-MEMORY-005]` HTTP Connection Pooling
- **Ubiquitous**: THE `OllamaProviderAdapter` and `OpenAIProviderAdapter` SHALL maintain singleton, pooled `httpx.AsyncClient` instances with keepalive limits to prevent TCP socket exhaustion.

### `[REQ-MEMORY-006]` Streaming Cycle Detection & Stream Telemetry
- **State-driven**: WHILE `stream_turn` is executing, THE `AgentKernel` SHALL detect repeating identical tool execution signatures ($n \ge 3$) and halt execution with a cycle trap warning, while recording Time-To-First-Token (TTFT) and Tokens-Per-Second (TPS) metrics.
