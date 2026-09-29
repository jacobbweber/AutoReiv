---
id: CARD-576
title: "Full context for qwen3.8: Developer and QA at 262144, nested runs use the agent's own window"
type: chore
status: Done
priority: P2
milestone: M24
needs_decision: none
proof: "Nimo ollama ps shows qwen3.8:latest at context 262144 and it stays there through a live hand-off on a throwaway serve (no model load in the Ollama log); Developer's real setting reads context_window 262144; test_agent_kernel.py: run_turn sends the agent's context window."
branch: fix/card-576-full-context
created: 2026-09-29
completed: 2026-09-29
related: [CARD-575, CARD-566, CARD-001]
---

# CARD-576 Full context for qwen3.8: Developer and QA at 262144, nested runs use the agent's own window

> **Status**: Done

## Why
Jacob wants qwen3.8 served at its full context (262144) on Nimo and Spark. Spark's vLLM already serves
qwen3.8-27b-fp8 at max_model_len 262144. On Nimo, Ollama loads the model at whatever num_ctx a request sends, so
Developer (65536), QA (65536) and nested runs (capped at 32768) each made it reload at a different size.

## Change
- Nimo (done by Jacob's approval, outside the repo): the `ollama` container was recreated with the same arguments plus
  `OLLAMA_CONTEXT_LENGTH=262144`; the old `docker inspect` is saved in `~/ollama-inspect-backup-20260929.json` on Nimo.
- Jacob's real settings: Developer `context_window` 262144 (model qwen3.8:latest, ollama, http://192.168.1.29:11434).
- `scripts/live_qa.py`: `DEFAULT_NUM_CTX = 262144` (env `AUTOREIV_QA_NUM_CTX` still overrides); test and live-qa skill updated.
- `agent_kernel.py`: `NESTED_COMPLETE_MAX_CTX` (32768) removed; nested `run_turn` (routines, plans, resumes, hand-off
  fallback) sends the agent's own context window, like `stream_turn`. The reply stays capped by `NESTED_COMPLETE_MAX_TOKENS`.
- `ollama_adapter.py`: sends `num_ctx` only when the request sets one. Found live: background calls without num_ctx
  (memory extractor, distillation, detectors) got a guessed 32768 for qwen3.8 and made Ollama drop the 262144 load.
  They now use the server default (OLLAMA_CONTEXT_LENGTH).

## Results (2026-09-29)
- Nimo: container recreated (same args + OLLAMA_CONTEXT_LENGTH=262144, local :rocm image, Ollama 0.32.13); preload at
  262144 in 7 s; `ollama ps`: qwen3.8:latest 18 GB, 100% GPU, context 262144, Forever. Other containers untouched.
- Live hand-off (journey card-566-hand-off-follows-autorun, throwaway serve, Architect and Developer on Nimo qwen3.8):
  - run 1 (before the adapter fix): PASS, but at the end one call asked for num_ctx 32768; Ollama dropped the 262144
    load to reload, and the load was cancelled when the serve stopped (nothing loaded). The run was also flagged because
    this card file was written in the real checkout during it.
  - run 2 (with the fix): PASS in 2.4 min, 0 approval prompts, CARD-3 In Review on its branch; 19 Ollama calls, all at
    n_ctx 262144, no model load, longest call 17 s; `ollama ps` still 262144; real checkout unchanged.
- Checks: test_agent_kernel.py (run_turn sends the agent window), test_card576_ollama_num_ctx.py (2),
  test_card575_live_qa_num_ctx.py (262144); full not-slow suite 2042 passed, 13 skipped; vitest 957; fast preflight GREEN.

## Log
- 2026-09-29: Jacob approved (Nimo full context, Developer and QA at 262144, no nested cap). Building.
- 2026-09-29: Built; checks green; live hand-off PASS with no reload. Jacob: merge to qa. Done; merged into qa.
