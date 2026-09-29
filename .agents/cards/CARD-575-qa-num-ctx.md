---
id: CARD-575
title: "Live QA asks Nimo Ollama for Developer's context size (num_ctx 65536)"
type: chore
status: Done
priority: P3
milestone: M22
needs_decision: none
proof: "live_qa.py check-model on Nimo leaves qwen3.8:latest loaded at context 65536 (ollama ps before/after, no model load in the Ollama log); a throwaway start sets matrix default_context_window and model_context_windows[qwen3.8:latest] to 65536. Checks: tests/unit/scripts/test_card575_live_qa_num_ctx.py."
branch: fix/card-575-qa-num-ctx
created: 2026-09-29
completed: 2026-09-29
related: [CARD-532, CARD-559, CARD-562, CARD-574]
---

# CARD-575 Live QA asks Nimo Ollama for Developer's context size (num_ctx 65536)

> **Status**: Done

## Why
Jacob's Developer runs qwen3.8:latest on Nimo with num_ctx 65536. Live QA called Nimo through `/v1`, which loads the
model at the server default (262144), so QA and Developer could keep reloading the model at different sizes.

## Change
- `scripts/live_qa.py`: `DEFAULT_NUM_CTX = 65536`, env `AUTOREIV_QA_NUM_CTX` overrides (0 = off).
- check-model on an Ollama host uses the native `/api/chat` with `options.num_ctx` (and num_predict 5); other hosts keep
  the `/v1` call.
- `start` (throwaway data, Ollama host) keeps the current matrix and sets `default_context_window` and
  `model_context_windows[<model>]` to the QA size, so the serve's Ollama calls send the same num_ctx.
- live-qa skill notes the setting. No host added; Nimo config untouched.

## Results (2026-09-29)
- Nimo `ollama ps` before and after check-model: qwen3.8:latest, context 65536; the call took about 1 s in the Ollama
  log with no model load.
- Throwaway start: "Ollama context 65536 set: HTTP 200"; matrix shows default_context_window 65536 and
  model_context_windows {qwen3.8:latest: 65536}.
- tests/unit/scripts 47 passed (5 new); fast preflight --base qa GREEN.

## Log
- 2026-09-29: Asked for as engineering cleanup (pre-approved merge to qa). Built; checks green; Done; merged into qa.
