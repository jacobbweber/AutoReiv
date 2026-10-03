---
id: CARD-524
title: "When compaction runs it can drop the operator's latest answer (keep-rule) and the unconfigured baseline is 8192"
type: bug
status: Done
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: []
  checks:
    - tests/unit/kernel/test_context_compactor.py::test_compaction_keeps_latest_user_answer_and_skill_runbook
    - tests/unit/kernel/test_context_compactor.py::test_unconfigured_baseline_and_nemotron_window
    - tests/unit/kernel/test_context_compactor.py::test_compaction_never_leaves_a_tool_return_without_its_call
    - tests/unit/kernel/test_context_compactor.py::test_summary_keeps_newest_lines_with_an_omission_marker
    - tests/unit/kernel/test_context_compactor.py::test_unrecognised_custom_model_defers_to_platform_default_window
branch: feat/card-524-compaction-drops-latest-answer
log: {minutes: 45, qa_runs: 1, findings: 1}
created: 2026-09-26
completed: 2026-10-02
---

# CARD-524 When compaction runs it can drop the operator's latest answer (keep-rule) and the unconfigured baseline is 8192

## Problem
In multi-turn conversations where an agent executes multiple tools (e.g. agent authoring intake or diagnostic workflows), `ContextCompactor.compact` discards the operator's latest answer message and the loaded `skill_view` runbook from the prompt context. As a result, the model repeatedly asks the same answered questions or loses the skill instructions. Furthermore, when context limits are unconfigured, `get_model_context_limit()` defaults to an outdated 8,192 tokens and lacks recognition for `nemotron` models.

## Cause
1. In `src/application/kernel/context_compactor.py`, `ContextCompactor.compact_with_stats` computes `keep_msg_count = max(2, keep_last_n_turns * 2)` and slices `turns[-keep_msg_count:]`. When an assistant turn generates multiple tool calls and tool returns, those last messages consist entirely of tool messages, placing the user's latest turn in `intermediate_turns`.
2. Intermediate messages are summarized using `summary_lines[:8]` (the oldest 8 messages), dropping the latest intermediate messages and any loaded `skill_view` bodies.
3. Unconfigured models and `default` fall back to `8192` in `get_model_context_limit`, and `nemotron` is missing from the architecture default heuristics.

## Change
1. Partition turns by user turns (delimited by `Role.USER`) rather than raw message pairs; ensure the latest user message is always preserved in `compacted`.
2. Explicitly preserve the most recent `skill_view` tool return (along with its assistant tool call) from intermediate history into the prompt payload.
3. Summarize the most recent intermediate messages (e.g. `summary_lines[-10:]` with an earlier-turns omission marker) rather than the oldest 8 messages.
4. Raise unconfigured context baseline in `get_model_context_limit` and `resolve_agent_context_limit` from `8192` to `32768`, and recognize `nemotron` (262,144 tokens).
5. Add unit tests for compaction preservation and baseline resolution; create e2e journey `card-524-compaction-keeps-answers.mjs`.

## What dies
Hardcoded `8192` unconfigured baseline and `summary_lines[:8]` oldest-slice compaction logic.

## Proof
- Journey `card-524-compaction-keeps-answers`: multi-turn session with tool calls verifies compaction retains the user's latest response and loaded skill context.
- Checks:
  - `tests/unit/kernel/test_context_compactor.py::test_compaction_keeps_latest_user_answer_and_skill_runbook`: asserts tool-heavy second turn preserves the second user message and skill runbook. Negative assertion: neither is dropped or summarized away.
  - `tests/unit/kernel/test_context_compactor.py::test_unconfigured_baseline_and_nemotron_window`: asserts default resolves to 32,768 and `nemotron-3.5-lightning` resolves to 262,144.

## Plan and decisions
- Count turns by `Role.USER` boundaries so an assistant's multi-step tool execution does not push the initiating user prompt out of the recent context window.
- Ensure the active `skill_view` runbook found in intermediate history is retained in the prompt.
- `needs_decision: none` (pure technical bug fix).

## Findings
- (fixed) Tier 2 of `resolve_agent_context_limit` treated any model whose limit came out as 8192 as unrecognised, so an explicit `*-8k` tag fell through to the platform default window. It now asks the override/family lookup directly (`_override_context_limit` / `_family_context_limit`).
- (fixed) The recent window could open on a tool return whose assistant call had been compacted away; the split now steps back to the call.
- (to findings list) none

## Results
What changed (`src/application/kernel/context_compactor.py`):
- Keep-rule: the latest user message and the latest `skill_view` call + return that fall outside the recent window are kept verbatim, in order; a pinned assistant message keeps only its `skill_view` call so no call is left without a return. Unpinned runs are summarized separately.
- The recent window never starts on an orphan tool return.
- Summaries keep the newest 10 lines with an "N older messages omitted" marker (was the oldest 8).
- Unconfigured / unrecognised baseline is 32768 (`UNCONFIGURED_CONTEXT_BASELINE`); `nemotron` resolves to 262144; `*-8k` and `llama3.2` stay 8192.

| Check | Result | Notes |
|---|---|---|
| `tests/unit/kernel/test_context_compactor.py` | PASS | 12 passed (3 stale 8192/keep-rule failures fixed, 3 new) |
| Full pytest | PASS | 2282 passed, 12 skipped |
| Fast preflight (`--base origin/qa`) | PASS | ruff, pytest guard 188, changed 12, mapped 12, vitest 944 |

Journey: none. Compaction is not reachable live on the current plan (AutoReiv/Tutor on Spark nemotron, 262k window), so the proof is the unit checks above; the planned `card-524-compaction-keeps-answers` journey was dropped.

## Release note
Fix context compaction dropping latest operator answers and loaded skill runbooks in tool-heavy turns, and raise unconfigured context baseline to 32k.
