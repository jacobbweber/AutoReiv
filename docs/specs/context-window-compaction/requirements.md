# Requirements Specification: Context Window Compaction & Sliding Dynamic Token Budget Strategy

> **Spec Status**: Approved  
> **Target Release**: Milestone 12 (v0.12.0)  
> **Card Reference**: [CARD-041](file:///.github/cards/CARD-041-context-window-compaction-and-dynamic-token-budget-strategy.md)  

> **Primary Component**: AutoReiv Kernel & Conversation Architecture (`src/application/kernel/context_compactor.py`, `src/application/kernel/agent_kernel.py`)

---

## 1. Executive Summary & Intent

**CARD-041** enhances the `ContextCompactor` engine with dynamic model-aware token budgeting (supporting 8k, 32k, and 128k windows), root user intent preservation (ensuring long-running multi-turn sessions never lose the initial goal), and detailed compression telemetry metrics (`CompactionMetrics`).

---

## 2. EARS User Stories & Functional Requirements

### [REQ-COMPACT-001] Model-Aware Dynamic Token Budgeting
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** determine the model's maximum context limit via `get_model_context_limit(model_name)` and compute a dynamic token threshold with a 75% safety margin ($T_{\text{max}} = 0.75 \times W_{\text{model}}$), preventing context overflow across local and cloud providers.

### [REQ-COMPACT-002] Root User Intent Preservation
- **EARS Pattern**: State-Driven
- **Requirement**: While compacting message histories exceeding the token budget, the system **shall** preserve both the `system` directive and the first `user` turn (`root_intent`) verbatim before appending intermediate turn summaries and recent turns.

### [REQ-COMPACT-003] Compaction Telemetry & Structured Metrics
- **EARS Pattern**: Event-Driven
- **Requirement**: When `compact_with_stats` is invoked, the system **shall** return both the compacted message list and a `CompactionMetrics` dataclass containing `original_tokens`, `compacted_tokens`, `turns_compacted`, `tools_truncated`, and `compression_ratio`.

### [REQ-COMPACT-004] Comprehensive Compaction & Kernel Integration Tests
- **EARS Pattern**: State-Driven
- **Requirement**: When running `pytest`, the test runner **shall** verify dynamic budget calculation, root intent preservation, tool truncation, metrics calculation, and `AgentKernel` execution with 100% passing tests.

---

## 3. Acceptance Criteria

- [ ] `AC-1`: `get_model_context_limit` returns appropriate defaults (8k for local/small, 32k for mid-tier, 128k for large cloud models).
- [ ] `AC-2`: Compacting a 20-turn conversation retains the initial user prompt and system prompt.
- [ ] `AC-3`: `compact_with_stats` returns valid `CompactionMetrics`.
- [ ] `AC-4`: `npm run preflight` passes all 6 quality gates cleanly.
