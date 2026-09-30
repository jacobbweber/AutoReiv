---
id: CARD-584
title: "Model plan: Spark agents on nemotron-3.5-lightning, Architect on qwen3.8-27b-fp8, Developer on Nimo"
status: In Review
created: 2026-09-29
branch: card/584-model-plan
related:
  - CARD-585
labels:
  - type:chore
  - area:models
  - P1
needs_decision: gateway swap (see Risk)
milestone: M24
---

# [CARD-584] Model plan: Spark agents on nemotron-3.5-lightning, Architect on qwen3.8-27b-fp8, Developer on Nimo

> **Status**: In Review
> **Labels**: `type:chore`, `area:models`, `P1`

## Why

2026-09-29 Spark check: qwen3.8-27b-fp8 (dense 27B) decodes at 7.7 tokens/s on the Spark, so agent rounds took ~94 s
and tasks 10-50 min. Jacob (2026-09-29): AutoReiv, Tutor, Toolsmith and the platform default use nemotron-3.5-lightning
via the Spark gateway :8099; Architect stays on qwen3.8-27b-fp8; Developer stays on Nimo Ollama qwen3.8:latest 262144;
context = what the gateway reports.

## Change

- `scripts/apply_model_plan.py`: applies the plan through the app's API (dry-run supported), never touches Spark/Nimo:
  default provider vllm (`http://192.168.1.218:8099/v1`) with default model `nemotron-3.5-lightning`; matrix default
  model the same; model context windows `nemotron-3.5-lightning` = the reported max_model_len (gateway listing, then vLLM
  behind it; 262144 on 2026-09-29) and `qwen3.8-27b-fp8` = 262144; Architect override `vllm` / `qwen3.8-27b-fp8` /
  262144; AutoReiv, Tutor, Toolsmith, Direct inherit the default; Developer only checked.
- On "merge to qa": run it against the real serve (`--base http://127.0.0.1:8000`), then restart and health-check.

## Checks (live, 2026-09-29)

- nemotron-3.5-lightning through :8099: 135 tokens/s (1500 tokens in 11.1 s) vs 7.7 for qwen3.8-27b; tool calling
  works (`get_weather` call, finish_reason tool_calls, 0.6 s); vLLM reports max_model_len 262144.
- It thinks a lot (1500 tokens of reasoning before any answer on a one-paragraph ask), so small max-token caps fail;
  see CARD-586.

## Risk (Jacob's decision)

The Spark gateway is a swap gateway: it serves one model at a time. Asking for another model unloads the current one
and loads the new one, which took about 5 minutes (334 s) on 2026-09-29. With Architect on qwen3.8 and the other agents
on nemotron, every switch between them costs a swap. Something outside AutoReiv also asks the gateway for qwen3.8
(the gateway swapped back to it at 21:58 ET with the real serve idle), so the two will keep swapping each other out.

## Log

- 2026-09-29: script written; dry-run against the real serve shows the planned changes (nothing applied there).
