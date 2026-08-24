# ADR-0010: Context Compaction, Episodic Memory, and Gateway Resilience Hardening

## Status
Accepted

## Date
2026-08-23

## Context
As conversational sessions expand over multiple turns, loading full uncompressed message histories into the LLM context window causes:
1. Context overflow and token budget exhaustion on local and cloud models.
2. Latency degradation and linear compute cost increases.
3. Loss of discrete cross-session facts (user preferences, system settings) since memory was previously bounded to ephemeral session chat logs.
4. Gateway fragility during transient 429 rate limits and network jitter, and socket exhaustion from unpooled HTTP clients.

## Decision Drivers
- **Deterministic Token Safety**: Automatically enforce context budget boundaries before sending prompts to models.
- **Cross-Session Fact Persistence**: Enable agents to recall discrete user and environment facts across independent sessions.
- **Transient Network Resilience**: Implement exponential backoff with full jitter and persistent HTTP client connection pooling.
- **Cycle Safety in Streaming**: Ensure real-time streaming turns prevent repetitive tool loops.

## Considered Options
1. **Unbounded History + Client-Side Truncation**: High memory usage, risks context overflow on server, loses critical system instructions.
2. **Deterministic Multi-Tier Compactor + SQLite Episodic Facts + Gateway Resilience**:
   - `ContextCompactor`: Retains System Message, summarizes intermediate turns, and keeps the most recent $N$ turns intact.
   - `episodic_facts` table: Key-value fact entity store with confidence and source session tracking.
   - Localized Exponential Backoff + Jitter ($2^{\text{attempt}} + \text{uniform}(0.1, 0.5)$) and singleton `httpx.AsyncClient` connection pools.

## Decision Outcome
Adopt Option 2.

## Consequences
- **Positive**: Zero context overflow crashes; long-running conversations automatically condense; persistent facts survive session resets; transient errors recover without failing over.
- **Negative**: Summarization consumes an auxiliary LLM call or fallback deterministic character truncation when an LLM summarizer is unavailable.
