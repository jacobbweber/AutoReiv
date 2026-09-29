---
id: CARD-576
title: "Full context for qwen3.8: Developer and QA at 262144, nested runs use the agent's own window"
type: chore
status: In Progress
priority: P2
milestone: M24
needs_decision: none
proof: "Nimo ollama ps shows qwen3.8:latest at context 262144 and it stays there through a live hand-off on a throwaway serve (no model load in the Ollama log); Developer's real setting reads context_window 262144; test_agent_kernel.py: run_turn sends the agent's context window."
branch: fix/card-576-full-context
created: 2026-09-29
related: [CARD-575, CARD-566, CARD-001]
---

# CARD-576 Full context for qwen3.8: Developer and QA at 262144, nested runs use the agent's own window

> **Status**: In Progress

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

## Log
- 2026-09-29: Jacob approved (Nimo full context, Developer and QA at 262144, no nested cap). Building.
