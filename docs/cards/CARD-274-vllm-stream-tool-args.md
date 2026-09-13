# [CARD-274] vLLM/OpenAI stream tool-call arg merge (Nemotron empty args)

> **Status**: In Review (live Spark proof green; await merge to qa)
> **Created**: 2026-09-13
> **Spec Reference**: Architect gateway Done bars (Design room 2026-09-13); Research vLLM/Nemotron brief
> **Labels**: `type:bug`, `gateway`, `llm-provider`, `tool-calling`
> **Branch**: `feat/vllm-stream-tool-args-274` off qa

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Spark runs Nemotron via **vLLM** (faster than Nimo/Ollama). Multistep "create a wiki note" fails with empty tool parameters.
2. Fix tool calling for vLLM/OpenAI-compatible providers without blaming Wiki or reopening the Job spine.
3. New feats branch off **qa** (synced with main); grok is retired.

### Beat 2: What AutoReiv Does Now
1. OpenAIProviderAdapter.stream() called `_parse_tool_calls` on **each SSE delta** and yielded those as StreamChunk.tool_calls.
2. agent_kernel does `collected_tool_calls.extend(chunk.tool_calls)` — no merge by OpenAI index.
3. Live AppData session `fbb2b88e-4e39-4e30-8051-0fd4e3630de7`: assistant tool_calls_json shows wiki_note_create with arguments: {}, then many call_unknown fragments with `{"raw": "{\"title\": \"NVIDIA"}` etc. Tool error: WikiTools.create_wiki_note() missing 1 required positional argument: 'title'.
4. Non-stream complete() path already parses a full function.arguments JSON string once — works when the provider returns a complete message.
5. Ollama native often returns arguments as an **object**; OpenAI/vLLM returns a **JSON string** streamed in pieces.

### Beat 3: What Will Change
1. Gateway accumulates streamed tool-call deltas **by index** (concat arguments string; merge id/name).
2. Parse JSON **once** when the stream finishes (or when the call is complete); emit one normalized ToolCall with a **dict** arguments (or {} only if truly empty after complete parse).
3. Do **not** emit incomplete mid-stream tool calls that the kernel would execute (content/reasoning deltas still stream).
4. Strip/ignore reasoning channel for tool name/args (already demuxed; do not let reasoning poison tool fields).
5. Same outbound shape to kernel for Ollama + vLLM OpenAI-compatible adapters.
6. Unit test: fragmented vLLM-style SSE deltas → single wiki_note_create with full title/content args.
7. Live proof on Spark vLLM: Standing Job / Chat create wiki note → real args → note in Inbox; short ReAct regression on same provider.

---

## 2. Acceptance Criteria

- [x] **[REQ-GW-274-001]**: Streaming OpenAI-compatible tool calls merged by index before kernel execution.
- [x] **[REQ-GW-274-002]**: Complete function.arguments JSON string → dict (never leave executable call with empty {} when stream later filled args).
- [x] **[REQ-GW-274-003]**: Incomplete mid-stream argument fragments must not become separate executable ToolCalls (call_unknown / {raw: ...}).
- [x] **[REQ-GW-274-004]**: Reasoning/reasoning_content deltas do not land in tool name or arguments.
- [x] **[REQ-GW-274-005]**: Unit test covers fragmented stream → one tool call with expected args (hermetic MockTransport SSE).
- [x] **[REQ-GW-274-006]**: Live Spark vLLM: create wiki note succeeds with non-empty title (Observe / messages show real args).
- [x] **[REQ-GW-274-007]**: Short Chat ReAct tool call still works on the same OpenAI-compatible provider (regression).
- [x] **[REQ-GW-274-008]**: No Job-spine / Formulate-Execute redesign; gateway-only change (+ tests + CHANGELOG).

---

## 3. Constraints

- Feats off qa only; do not touch main except via later merge.
- Do not reopen Job spine, Wiki tools, or HITL policy for this card.
- Prefer normalize-once in src/infrastructure/gateway/openai_adapter.py (shared helper OK under gateway).
- Strict TDD: failing stream-fragment test first, then fix.
- Update CHANGELOG.md [Unreleased].

---

## 4. Evidence (root cause)

Live messages.tool_calls_json (abbreviated): first entry name=wiki_note_create arguments={}; subsequent entries name="" arguments={"raw": "{\"title\": ..."} from per-delta json.loads failures. Matches Research brief (streaming placeholders / arg deltas) and Architect Done bars.

---

## 5. Live proof (Jarvis + Spark vLLM 2026-09-13)

- Tip `ffdf223` / `16dd181` on `feat/vllm-stream-tool-args-274`; serve restarted; provider `vllm` / `nemotron-3.5-lightning` at `192.168.1.218:8006`.
- Standing Job session `4dac7fdb…`: single `wiki_note_create` with full title/content/category (no empty `arguments={}` / no `call_unknown` raw fragments). Contrast pre-fix session `fbb2b88e…`.
- HITL approve `appr_3aeef1db0bf5` executed write to `00_Inbox/card274_nvidia_dgx_spark_vllm_tool_call_proof.md`.
- Short ReAct: `wiki_note_list` with category inbox OK.
- Evidence: `notes/card274-live-smoke.json`.

