# [CARD-335] Dynamic Tool Output Budget Scaling

> **Status**: In Review
> **Created**: 2026-09-15
> **Spec Reference**: Kernel & Context Compactor Architecture (`src/application/kernel/context_compactor.py`)
> **Labels**: `type:feature`, `kernel`, `compaction`, `llm`, `context-budget`
> **Branch**: `feat/card-335-dynamic-tool-output-budget-scaling`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
When an agent uses tools to read substantial files or documents (such as `wiki_note_read`, `read_document_file`, diffs, or structured notes), the tool output should not be clamped to a tiny static 8,000-character ceiling (~2,000 tokens) if the model is operating with a 32k, 64k, or 131k context window. Jacob observed this when Wiki Librarian read a 15,859-character note and told him that 7,859 characters were omitted for context budget despite the model having a 131k token window. The tool character budget must scale dynamically with the model's configured context window, while still keeping a protective upper ceiling against runaway outputs.

---

### Beat 2: What AutoReiv Does Now
1. **Hardcoded Tool Output Default**: `src/application/kernel/context_compactor.py` hardcodes `max_tool_chars: int = 8000` as a default parameter in `ContextCompactor.compact()`.
2. **Disconnected Kernel Call**: In `src/application/kernel/agent_kernel.py`, the turn execution loop resolves `context_limit` (e.g. 131,072 tokens) and passes `max_tokens = int(context_limit * 0.75)` to `ContextCompactor.compact()`, but omits `max_tool_chars`.
3. **Premature Clamping**: Even on high-context models, any tool output over 8,000 characters is aggressively sliced and tagged with `... [TRUNCATED: X characters omitted for context budget] ...`.
4. **Agent Anxiety**: The agent sees this truncation marker in its ReAct observation and warns the user that it did not receive the complete file.

---

### Beat 3: What Will Change
1. **Dynamic Scaling Helper**: Introduce `resolve_max_tool_chars(context_limit: int, ...) -> int` in `src/application/kernel/context_compactor.py`:
   - Baseline floor: 8,000 characters (for <= 8,192 token windows).
   - Dynamic scaling: Allocates roughly 25% of character capacity ($\text{context\_limit} \times 4 \times 0.25 = \text{context\_limit}$ characters, or ~1 char per token of context).
   - Safe ceiling: Caps at 120,000 characters (~30,000 tokens) to guarantee that even on 1M token models, a single tool output does not monopolize the entire context.
   - For 8k context window: 8,000 characters.
   - For 32k context window: 32,768 characters (~8,000 tokens).
   - For 131k context window: 120,000 characters (~30,000 tokens).
2. **Kernel Wiring**: In `agent_kernel.py`, calculate `max_tool_chars = resolve_max_tool_chars(context_limit)` and pass it into `ContextCompactor.compact()`.
3. **Default Fallback in Compactor**: If `max_tool_chars` is not provided (or passed as `None`), `ContextCompactor.compact()` resolves it dynamically from `effective_max_tokens`.
4. **Automated Verification**: Comprehensive unit tests covering scaling boundaries, non-truncation of 15k–30k notes on >=32k contexts, and honest truncation on runaway payloads (>120k).

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-TOOL-BUDGET-001]**: `resolve_max_tool_chars(context_limit: int)` computes a dynamic tool character allowance scaled to context limit with an 8,000 character minimum floor and a 120,000 character maximum ceiling.
- [x] **[REQ-TOOL-BUDGET-002]**: `agent_kernel.py` invokes `resolve_max_tool_chars(context_limit)` and supplies `max_tool_chars` to `ContextCompactor.compact()`.
- [x] **[REQ-TOOL-BUDGET-003]**: `ContextCompactor.compact()` falls back dynamically to `resolve_max_tool_chars` when `max_tool_chars` is `None`.
- [x] **[REQ-TOOL-BUDGET-004]**: Tool outputs between 8,001 and 32,000 characters (such as the 15,859-char wiki note) are preserved without truncation on models with context limits $\ge 32,768$.
- [x] **[REQ-TOOL-BUDGET-005]**: Runaway tool outputs exceeding the scaled ceiling are still safely truncated with the honest `[TRUNCATED: ... characters omitted for context budget]` marker.
- [x] **[REQ-TOOL-BUDGET-006]**: All unit tests in `tests/unit/kernel/test_context_compactor.py` and kernel execution tests pass cleanly via `pytest`.

---

## 3. Constraints & Honor Flags
- No breaking changes to existing tests or the `CompactionMetrics` schema.
- Strict TDD (Red-Green-Refactor) on branch `feat/card-335-dynamic-tool-output-budget-scaling`.
- Zero code before Jacob says **build**.
