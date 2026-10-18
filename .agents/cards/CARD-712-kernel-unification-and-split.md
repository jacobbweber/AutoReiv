---
id: CARD-712
title: "Unify AgentKernel.run_turn and stream_turn onto one shared ReAct loop and decompose agent_kernel.py under 800 lines"
type: feature
status: Done
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-712-kernel-unification-and-split]
  checks: [tests/unit/kernel/test_card712_kernel_unification.py]
branch: feat/card-712-kernel-unification-and-split
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-17
completed: 2026-10-18
---

# CARD-712 Unify AgentKernel.run_turn and stream_turn onto one shared ReAct loop and decompose agent_kernel.py under 800 lines

## Problem
`src/application/kernel/agent_kernel.py` had grown to 2,045 lines and contained two copy-pasted ReAct loops (`_run_turn_inner` and `_stream_turn_inner`) that had drifted in behavior:
1. `run_turn` only checked `tool_res.error.startswith("approval_required:")` and ignored nested child HITL parks (`tool_res.output == {"status": "approval_required", "approval_id": ...}`), causing non-streaming turns to keep looping and invoke the LLM again after a child handoff parked.
2. `stream_turn` did not accept or forward `routine_id` to `_gate_tool_call`.
3. `run_turn` persisted failed tool outputs without the `"Tool Error: "` prefix used by `stream_turn`, breaking `post_tool_empty_fallback` (`_FAILED_TOOL_PREFIXES`) and UI tool status badges on non-streaming turns.
4. `agent_kernel.py` imported `OllamaProviderAdapter`, `AnthropicProviderAdapter`, and `OpenAIProviderAdapter` directly from `src.infrastructure.gateway.*` instead of delegating to `GatewayProviderFactory`.

## Cause
`run_turn` and `stream_turn` evolved as two separate loop implementations inside `src/application/kernel/agent_kernel.py`, alongside system prompt assembly, model cascade resolution, and step telemetry attribution.

## Change
- Created `src/application/kernel/react_loop.py` (786 lines) containing `execute_react_loop` and `format_tool_error_content`, unifying `AgentKernel.run_turn` (`stream=False`) and `AgentKernel.stream_turn` (`stream=True`) onto one canonical ReAct loop with identical tool gating (`routine_id`), direct + nested HITL park handling, cycle detection, capability gap detection, and `"Tool Error: "` formatting.
- Created `src/application/kernel/system_prompt_builder.py` (171 lines) containing `build_effective_system_message` and `turn_tools_and_system_message`.
- Created `src/application/kernel/model_resolver.py` (119 lines) containing `is_model_compatible_with_provider`, `resolve_agent_model`, and `ensure_agent_provider_adapter`, delegating adapter construction to `GatewayProviderFactory.create_adapter` in `src/infrastructure/gateway/factory.py`.
- Added `record_step_telemetry` and `record_failed_step_telemetry` to `src/application/kernel/telemetry_attribution.py` (297 lines).
- Reduced `src/application/kernel/agent_kernel.py` from 2,045 lines to 757 lines.

## What dies
- Duplicated `_run_turn_inner` and `_stream_turn_inner` ReAct loop implementations in `src/application/kernel/agent_kernel.py`.
- Direct imports of `OllamaProviderAdapter`, `AnthropicProviderAdapter`, and `OpenAIProviderAdapter` inside `src/application/kernel/`.

## Proof
- Journey `card-712-kernel-unification-and-split`:
  1. Verifies all kernel modules under `src/application/kernel/` are under 800 lines and exercises `AgentKernel.run_turn` (non-streaming) through `execute_react_loop`.
  2. Executes a streaming tool-calling turn (`stream_turn`) in `#view-chat` on desktop and phone and verifies tool execution, persisted messages, and responsive layout.
- Checks:
  - `tests/unit/kernel/test_card712_kernel_unification.py`

## Plan and decisions
- Phase 3 monolith decomposition.

## Findings
- Fixed `test_req_tool_budget_002_agent_kernel_uses_resolve_max_tool_chars` in `tests/unit/kernel/test_card335_tool_budget_scaling.py` by binding `max_tool_chars_fn = resolve_max_tool_chars` directly inside `AgentKernel.run_turn` and `AgentKernel.stream_turn`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-712-kernel-unification-and-split` | desktop | PASS | Verified `<800`-line kernel modules, `run_turn` tool execution (`session=bf91eb76-7d70-4aee-b770-318afa05a5bb`), and `stream_turn` tool execution in `#view-chat`. |
| `card-712-kernel-unification-and-split` | phone | PASS | Verified `<800`-line kernel modules, `run_turn` tool execution (`session=90503135-931e-4bd0-a652-52785a9c2ac2`), and `stream_turn` tool execution in `#view-chat`. |

Screenshots:
- `/tmp/autoreiv-qa/card-712/card-712-kernel-unification-and-split-desktop-01-verify-decomposed-kernel-modules-and-non-streami.png`
- `/tmp/autoreiv-qa/card-712/card-712-kernel-unification-and-split-desktop-03-verify-streaming-tool-execution-persisted-messag.png`
- `/tmp/autoreiv-qa/card-712/card-712-kernel-unification-and-split-phone-03-verify-streaming-tool-execution-persisted-messag.png`

## Release note
- Unified `AgentKernel.run_turn` and `stream_turn` onto a single ReAct execution core and split `agent_kernel.py` (2,045 lines) into focused modules under 800 lines [CARD-712].
