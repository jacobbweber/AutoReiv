---
id: CARD-584
title: "Model plan: one model per machine (Spark nemotron-3.5-lightning; Nimo qwen3.8 for Architect + Developer)"
status: In Review
created: 2026-09-29
branch: card/584-model-plan
related:
  - CARD-585
  - CARD-588
labels:
  - type:chore
  - area:models
  - P1
needs_decision: none
milestone: M24
---

# [CARD-584] Model plan: one model per machine (Spark nemotron-3.5-lightning; Nimo qwen3.8 for Architect + Developer)

> **Status**: In Review
> **Labels**: `type:chore`, `area:models`, `P1`

## Why

2026-09-29 Spark check: qwen3.8-27b-fp8 (dense 27B) decodes at 7.7 tokens/s on the Spark, so agent rounds took ~94 s
and tasks 10-50 min. Jacob (2026-09-29): AutoReiv, Tutor, Toolsmith and the platform default use nemotron-3.5-lightning
via the Spark gateway :8099; context = what the gateway reports. Correction the same evening: each machine serves ONE
model only and nothing may ever cause a model swap. Spark = nemotron-3.5-lightning only; Nimo = qwen3.8:latest
(Ollama) only; Architect moves to Nimo qwen3.8:latest 262144 (same as Developer); no agent uses qwen3.8-27b-fp8 on
Spark anymore.

## Change

- `scripts/apply_model_plan.py` applies the plan through the app's API (`--dry-run`, `--check`); never touches
  Spark/Nimo:
  - default provider vllm (`http://192.168.1.218:8099/v1`), default model `nemotron-3.5-lightning`; matrix default the
    same; AutoReiv, Tutor, Toolsmith, Direct inherit it;
  - Architect and Developer: `ollama` / `qwen3.8:latest` / `http://192.168.1.29:11434` / 262144 (they share the Nimo
    generation pool, CARD-585);
  - context windows: nemotron = reported max_model_len (gateway listing, then vLLM behind it; 262144 on 2026-09-29),
    `qwen3.8:latest` = 262144; `qwen3.8-27b-fp8` entries and purposes are removed;
  - `plan_problems()` / `--check` lists anything that would make either machine load a second model (another model on
    an agent, a purpose, the default); the apply run fails if any remain.
- Tests: `tests/unit/scripts/test_card584_model_plan.py`.
- On "merge to qa": run it against the real serve (`--base http://127.0.0.1:8000`), then `--check`, restart and
  health-check.

## Checks (live, 2026-09-29)

- nemotron-3.5-lightning through :8099: 135 tokens/s (1500 tokens in 11.1 s) vs 7.7 for qwen3.8-27b; tool calling
  works (`get_weather` call, finish_reason tool_calls, 0.6 s); vLLM reports max_model_len 262144.
- It thinks a lot (1500 tokens of reasoning before any answer on a one-paragraph ask), so small max-token caps fail;
  see CARD-586.

## Swap history (why one model per machine)

The Spark gateway serves one model at a time; asking for another unloads the current one (a swap took 334 s on
2026-09-29). Something outside AutoReiv also asked it for qwen3.8 (it swapped back at 21:58 ET with the real serve
idle). After the 22:02 ET swap request for nemotron, vLLM behind the gateway (:8006) stayed down (connection refused,
`loaded_model: null`) for 40+ min and a 25-min request was never served; Spark needs a look (not touched here).

## Acceptance

- [x] Plan applies Spark nemotron default, Architect + Developer on Nimo qwen3.8:latest 262144, no qwen3.8-27b-fp8.
- [x] `--check` names every swap risk; plan is idempotent (tests).
- [ ] Live on the throwaway :8770: all 5 agents answer, a tool round works on nemotron (see Log).

## Log

- 2026-09-29: script written; dry-run against the real serve shows the planned changes (nothing applied there).
- 2026-09-29: plan changed to one model per machine (Architect to Nimo), plan check and tests added.
