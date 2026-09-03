---
id: CARD-136
title: "Per-Chat Debug Inspector & Turn Payload Viewer"
status: In Review
priority: Medium
created: 2026-09-02
owner: Antigravity
description: "Per-conversation debug view and slide-over panel allowing developers and operators to inspect raw LLM payloads, system prompts, tool call arguments, token usage, and latency breakdown for each chat turn."
---

# CARD-136: Per-Chat Debug Inspector & Turn Payload Viewer

## 1. Context & Motivation
While Observability Studio (`#view-observability`) provides macro telemetry across the entire system, operators and developers pair-programming with agents often need immediate, turn-by-turn visibility inside the active chat without switching tabs:
- What exact system prompt and assembled message history went to the provider?
- What raw JSON parameters did the model pass to a tool call?
- How many tokens were spent (prompt vs. completion tokens) on this turn?
- What was the provider latency / stream duration?

## 2. Invariants & UI Contract
- **Access Point**: A toggle switch or icon button (`#chatDebugToggleBtn`) in the chat top bar (`#view-chat`).
- **Turn Debug View**:
  - Message-level "Inspect" badge or side-by-side debug drawer.
  - Tabs for:
    1. **Raw Messages**: JSON list of messages formatted for OpenAI / Gemini / Anthropic.
    2. **Tool Payloads**: Exact arguments and return payloads for every tool call in that turn.
    3. **Turn Metrics**: Provider, model name, prompt tokens, completion tokens, total cost estimate, latency (ms).
    4. **System Prompt Excerpt**: Active persona instructions and injected context facts.
- **Copy to Clipboard**: One-click JSON copy for quick debugging and prompt engineering.

## 3. Vertical Slices

### Slice 1: Backend Turn Metadata Surface
- Ensure `ChatMessage` or session history retrieval includes token usage metrics, latency, and resolved model names where available.
- Endpoint `GET /api/chat/sessions/{session_id}/debug` returning turn-level diagnostic envelopes.

### Slice 2: Frontend Debug Slide-Over Panel
- Slide-over debug inspector pane (`#chatDebugPane`) attached to the right side of `#view-chat`.
- Clean syntax-highlighted JSON viewer with copy buttons and token counters.

### Slice 3: Verification & Automated Tests
- Unit tests for debug payload formatting.
- Vitest tests for debug drawer toggling and copy functionality.
