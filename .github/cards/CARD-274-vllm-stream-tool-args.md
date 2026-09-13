# [CARD-274] vLLM/OpenAI stream tool-call arg merge (Nemotron empty args)

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Architect gateway Done bars (Design room 2026-09-13); Research vLLM/Nemotron brief
> **Labels**: 	ype:bug, gateway, llm-provider, 	ool-calling
> **Branch**: eat/vllm-stream-tool-args-274 off qa

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Spark runs Nemotron via **vLLM** (faster than Nimo/Ollama). Multistep "create a wiki note" fails with empty tool parameters.
2. Fix tool calling for vLLM/OpenAI-compatible providers without blaming Wiki or reopening the Job spine.
3. New feats branch off **qa** (synced with main); grok is retired.

### Beat 2: What AutoReiv Does Now
1. OpenAIProviderAdapter._stream_chat / stream calls _parse_tool_calls on **each SSE delta** and yields those as StreamChunk.tool_calls.
2. gent_kernel does collected_tool_calls.extend(chunk.tool_calls) — no merge by OpenAI index.
3. Live AppData session bb2b88e-4e39-4e30-8051-0fd4e3630de7: assistant 	ool_calls_json shows wiki_note_create with rguments: {}, then many call_unknown fragments with {"raw": "{\\"title\\": \\"NVIDIA"} etc. Tool error: WikiTools.create_wiki_note() missing 1 required positional argument: 'title'.
4. Non-stream complete() path already parses a full unction.arguments JSON string once — works when the provider returns a complete message.
5. Ollama native often returns arguments as an **object**; OpenAI/vLLM returns a **JSON string** streamed in pieces.

### Beat 3: What Will Change
1. Gateway accumulates streamed tool-call deltas **by index** (concat rguments string; merge id/
ame).
2. Parse JSON **once** when the stream finishes (or when the call is complete); emit one normalized ToolCall with a **dict** rguments (or {} only if truly empty after complete parse).
3. Do **not** emit incomplete mid-stream tool calls that the kernel would execute (content/reasoning deltas still stream).
4. Strip/ignore reasoning channel for tool name/args (already demuxed; do not let reasoning poison tool fields).
5. Same outbound shape to kernel for Ollama + vLLM OpenAI-compatible adapters.
6. Unit test: fragmented vLLM-style SSE deltas → single wiki_note_create with full title/content args.
7. Live proof on Spark vLLM: Standing Job / Chat create wiki note → real args → note in Inbox; short ReAct regression on same provider.

---

## 2. Acceptance Criteria

- [ ] **[REQ-GW-274-001]**: Streaming OpenAI-compatible tool calls merged by index before kernel execution.
- [ ] **[REQ-GW-274-002]**: Complete unction.arguments JSON string → dict (never leave executable call with empty {} when stream later filled args).
- [ ] **[REQ-GW-274-003]**: Incomplete mid-stream argument fragments must not become separate executable ToolCalls (call_unknown / {raw: ...}).
- [ ] **[REQ-GW-274-004]**: Reasoning/
easoning_content deltas do not land in tool name or arguments.
- [ ] **[REQ-GW-274-005]**: Unit test covers fragmented stream → one tool call with expected args (hermetic MockTransport SSE).
- [ ] **[REQ-GW-274-006]**: Live Spark vLLM: create wiki note succeeds with non-empty title (Observe / messages show real args).
- [ ] **[REQ-GW-274-007]**: Short Chat ReAct tool call still works on the same OpenAI-compatible provider (regression).
- [ ] **[REQ-GW-274-008]**: No Job-spine / Formulate-Execute redesign; gateway-only change (+ tests + CHANGELOG).

---

## 3. Constraints

- Feats off qa only; do not touch main except via later merge.
- Do not reopen Job spine, Wiki tools, or HITL policy for this card.
- Prefer normalize-once in src/infrastructure/gateway/openai_adapter.py (shared helper OK under gateway).
- Strict TDD: failing stream-fragment test first, then fix.
- Update CHANGELOG.md [Unreleased].

---

## 4. Evidence (root cause)

Live messages.tool_calls_json (abbreviated): first entry 
ame=wiki_note_create arguments={}; subsequent entries 
ame="" arguments={"raw": "{\\"title\\": ..."} from per-delta json.loads failures. Matches Research brief (streaming placeholders / arg deltas) and Architect Done bars.
