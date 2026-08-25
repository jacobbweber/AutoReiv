# ADR-0041: Model Aware Context Compaction and Intent Preservation

## Context and Problem Statement
When running autonomous agents over extended multi-turn conversations or execution routines, accumulated message histories and verbose tool outputs risk overflowing LLM context limits. Previously, `ContextCompactor` operated on a static hardcoded token ceiling (4,000 tokens) and pruned the initial user request when summarizing intermediate turns.

## Decision Drivers
- **Model-Aware Dynamic Budgeting**: Automatically detect context limits (8k for local models, 32k for mid-tier, 128k/1M for cloud models) and apply a 75% safety margin.
- **Root User Intent Invariant**: Ensure the initial user prompt is preserved alongside system instructions so the agent never loses the primary mission during long-running tasks.
- **Telemetry & Metrics**: Structured reporting of token savings, turn summarization counts, and tool output truncations via `CompactionMetrics`.

## Considered Options
1. **Option 1**: Fixed FIFO message dropping (loses system prompts and core intent).
2. **Option 2 (Accepted)**: Model-aware dynamic thresholding, root intent preservation, intermediate turn summarization, and large tool output pruning via `ContextCompactor.compact_with_stats`.

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Robust protection against context overflow across heterogeneous model backends.
- Zero goal amnesia across multi-turn and multi-hour routine execution.
- 5 comprehensive unit tests in `tests/unit/kernel/test_context_compactor.py`.

### Negative Consequences / Trade-offs
- Heuristic-based token estimation (~4 chars/token) instead of exact BPE tokenization per model.
