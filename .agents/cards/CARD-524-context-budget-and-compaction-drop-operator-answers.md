---
id: CARD-524
title: "When compaction runs it can drop the operator's latest answer (keep-rule) and the unconfigured baseline is 8192"
type: bug
status: In Progress
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-524-compaction-keeps-answers]
  checks:
    - tests/unit/kernel/test_context_compactor.py::test_compaction_keeps_latest_user_answer_and_skill_runbook
    - tests/unit/kernel/test_context_compactor.py::test_unconfigured_baseline_and_nemotron_window
branch: feat/card-524-compaction-drops-latest-answer
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-09-26
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
- (fixed) none yet
- (to findings list) none

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-524\...`

## Release note
Fix context compaction dropping latest operator answers and loaded skill runbooks in tool-heavy turns, and raise unconfigured context baseline to 32k.
