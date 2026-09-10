# [CARD-213] Google Gemini Provider Compatibility and Tool Message Sanitization

> **Status**: Done
> **Created**: 2026-09-10
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `domain:gateway`, `domain:chat`, `domain:settings`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Chatting with Google Gemini Should Work Just Like Ollama**:
   - When Jacob selects **Google Gemini** as the active LLM provider in Settings Studio, asking questions in Chat Studio (`#view-chat`) should stream assistant responses immediately without freezing or failing silently.
2. **Support Existing Conversation History**:
   - Switching an active chat session that previously used Ollama or another provider to Google Gemini should continue seamlessly, even if the conversation history includes tool executions, routine steps, or approval gates.

---

### Beat 2: What AutoReiv Does Now
1. **Unresponsive / Dead Model Selected**:
   - The saved Gemini default model in settings was set to `models/gemini-3.8-flash`. Google Gemini's server hangs on this model (`httpx.ReadTimeout`), causing AutoReiv to time out with `ProviderUnavailableError`.
   - `presets.py` lists non-existent recommendations (`gemini-3.5-flash`, `gemini-3.5-flash-lite`).
2. **Strict Function Calling Validation Rejection**:
   - In sessions containing previous tool executions (e.g. `wiki_note_create`, `handoff_to_agent`), tool results are saved to the message history with `role: "tool"`.
   - Ollama is lenient and allows orphan `role: "tool"` messages.
   - Google Gemini's OpenAI-compatible endpoint strictly validates `role: "tool"` messages against the immediately preceding `assistant` message. If any tool message lacks a matching `tool_call_id` in the preceding turn, Google Gemini rejects the entire request with HTTP 400: `function_response.name: Name cannot be empty`.

---

### Beat 3: What Will Change
1. **Message History Tool Sanitization in Gateway Adapter**:
   - In `src/infrastructure/gateway/openai_adapter.py` (`_format_messages`):
     - Track active `tool_call_id`s from the immediately preceding `assistant` message.
     - If a `role: "tool"` message is orphaned (not in the preceding assistant's tool calls), convert it into a standard context note (`role: "user"`) so that conversation context is preserved without violating Google Gemini's strict function-calling schema.
     - Ensure the message list never begins with a `role: "tool"` message.
2. **Updated Gemini Recommended Models Catalog**:
   - In `src/application/settings/presets.py`, update Gemini's `recommended_models` to proven, currently active models:
     - `gemini-3.6-flash` (Fast, recommended default)
     - `gemini-3.7-flash` (Advanced reasoning)
     - `gemini-3.1-flash-lite-preview` (Ultra-lightweight)
3. **Database Migration / Hydration**:
   - If `provider_settings` contains `gemini` with an obsolete or hanging model (`gemini-3.8-flash`, `gemini-2.5-flash`, or `gemini-3.5-flash`), auto-fallback or update to `gemini-3.6-flash`.
4. **Automated Verification**:
   - Unit/integration test in `tests/integration/test_gateway_gemini_sanitization.py` validating that multi-turn histories with orphan tool messages and approval stops format cleanly and execute successfully without HTTP 400.

---

## 2. Acceptance Criteria (Definition of Done)
- [x] **AC-1 (Tool Message Sanitization)**: `OpenAIProviderAdapter._format_messages()` converts unlinked or orphan `role: "tool"` messages into user context notes, preventing HTTP 400 `function_response.name: Name cannot be empty` errors on Google Gemini.
- [x] **AC-2 (Working Preset Models)**: `presets.py` recommends verified responsive models (`gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.1-flash-lite-preview`).
- [x] **AC-3 (Hanging Model Fallback)**: The gateway and settings migration fallback cleanly if an obsolete model (`gemini-3.8-flash`, `gemini-3.5-flash`) is stored.
- [x] **AC-4 (All Quality Gates Green)**: Pytest, Vitest, ESLint, Ruff, Playwright, and RTM preflight checks all pass.

---

## 3. Constraints & Invariants
- Follow the 5 Hard Invariants from AGENTS.md.
- Feature branch `feat/gemini-provider-sanitization` cut from `qa`.
- Card stays `Ready` until Jacob says **build**.
