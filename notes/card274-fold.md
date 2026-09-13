# CARD-274 fold / CHANGELOG snippet

## Branch tip (GitHub)
See `git ls-remote origin feat/vllm-stream-tool-args-274`

## CHANGELOG [Unreleased] Fixed (paste under Unreleased if missing)

### Fixed
- **vLLM/OpenAI stream tool-call arg merge [CARD-274 / REQ-GW-274-001..005]**: `OpenAIProviderAdapter.stream()` accumulates tool_call SSE deltas by index (concat `function.arguments` string fragments; merge id/name) and emits complete `ToolCall` dicts only on finish — no mid-stream empty/`{raw: fragment}` executable calls. Fixes Nemotron-on-Spark wiki_note_create missing title. Non-stream `complete()` unchanged.

## Jarvis fold (machineId dadba06c…)

```powershell
cd D:\Projects\Active\AutoReiv
git fetch origin
git checkout feat/vllm-stream-tool-args-274
git pull --ff-only origin feat/vllm-stream-tool-args-274
.\\scripts\\restart_serve.ps1
.venv\\Scripts\\python -m pytest tests/unit/gateway/test_openai_adapter.py tests/unit/gateway/test_openai_stream_tool_args_274.py -q
```

## Live Spark proof still open
REQ-GW-274-006 / 007 — create wiki note via Nemotron/vLLM streaming; confirm non-empty title.
