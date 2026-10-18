---
id: CARD-712
title: "Unify AgentKernel.run_turn and stream_turn onto one shared ReAct loop and decompose agent_kernel.py under 800 lines"
type: feature
status: Ready
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-712-kernel-unification-and-split]
  checks: [tests/unit/kernel/test_card712_kernel_unification.py]
branch: feat/card-712-kernel-unification-and-split
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-712 Unify AgentKernel.run_turn and stream_turn onto one shared ReAct loop and decompose agent_kernel.py under 800 lines

## Intent
`src/application/kernel/agent_kernel.py` is 1,958 lines and contains two copy-pasted ReAct loops (`run_turn` [386 lines] and `stream_turn` [641 lines]) that have drifted in behavior (routine ID policy gating, nested HITL park handling, tool error formatting, reply time limits, and skipped-parts verification), alongside system prompt assembly, provider adapter creation, and ACE reflection.

## Goal
1. `run_turn()` and `stream_turn()` share one canonical ReAct execution core so non-streaming turns (routines, subagents, verification) and streaming turns (Chat SSE) enforce identical tool gating, nested HITL parks, reply limits, and error formatting.
2. System prompt assembly (`_build_effective_system_message`), provider/model resolution (delegating adapter construction to `GatewayProviderFactory`), and ACE reflection are extracted into focused kernel modules under `src/application/kernel/`.
3. `src/application/kernel/agent_kernel.py` and all extracted modules are under the 800-line ceiling.

## Change
- Extract system prompt assembly (`_build_effective_system_message`, `_turn_tools_and_system_message`, progressive skill index & memory injection) into `src/application/kernel/system_prompt_builder.py`.
- Extract provider/model cascade resolution into `src/application/kernel/model_resolver.py` and delegate adapter creation to `GatewayProviderFactory` instead of importing `src.infrastructure.gateway.*` adapters directly inside `kernel`.
- Unify `run_turn` and `stream_turn` so `run_turn` consumes the shared step/event core (or both delegate to one shared step driver), eliminating the 350+ lines of duplicated loop code and fixing the behavioral drift between streaming and non-streaming turns.

## What dies
- Duplicated ReAct loop logic in `AgentKernel.run_turn()` (`src/application/kernel/agent_kernel.py`).
- Direct imports of `OllamaProviderAdapter`, `AnthropicProviderAdapter`, and `OpenAIProviderAdapter` inside `src/application/kernel/agent_kernel.py`.

## Proof
- Journey `card-712-kernel-unification-and-split`:
  1. Execute a multi-step tool-calling Chat turn (`stream_turn`) and a routine/non-streaming turn (`run_turn`) on desktop and phone, verifying identical tool gating and completion.
- Checks:
  - `tests/unit/kernel/test_card712_kernel_unification.py`

## Plan and decisions
- Phase 3 monolith decomposition.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-712\...`

## Release note
- Unified `AgentKernel.run_turn` and `stream_turn` onto a single ReAct execution core and split `agent_kernel.py` (1,958 lines) into focused modules under 800 lines [CARD-712].
