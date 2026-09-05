# [CARD-162] Per-Agent Context Window Control in Agent Studio and Unified Fallback Cascade

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
In Settings Studio (`#navSettings`), the platform-wide default context window can be configured to 100k+ tokens (e.g. `131,072`). However, in Chat Studio (`#navChat`), an agent using the default provider (such as Personal Finance Lead) only displays an 8,192 token limit.

This discrepancy occurs because:
1. In Agent Studio (`#navForge`), the Context Window input (`#forgeContextWindowInput`) was placed inside a hidden container (`#forgeProviderConfigContainer`) that only appears when switching the provider away from "Use Global Default". When an agent remains on "Use Global Default", the input is invisible, and the saving script actively discards the value (`if (forgeProviderSelect.value === 'default') return null;`).
2. The context limit resolution in the chat router and kernel did not check the platform-wide Settings default when an agent's model was set to `default`, falling back straight to an 8,192 baseline instead of inheriting the configured platform context window (131,072).

The user wants:
1. A per-agent context window configuration control placed directly alongside the LLM provider and model settings in Agent Studio, always visible regardless of provider.
2. A strict 3-tier fallback cascade:
   - **Tier 1 (Per-Agent Explicit)**: If an agent has a context window configured in Agent Studio, use that.
   - **Tier 2 (Per-Agent Model Default)**: If blank, and the agent has an explicit model selected, default to that model's configured limit or architecture baseline.
   - **Tier 3 (Platform-Wide Fallback)**: If the agent is set to Default provider/model, fall back to what is configured in the platform-wide Settings Studio (`default_context_window`, e.g. 131,072).

---

## 2. What to Build

### A. Agent Studio UI Layout (`src/web/templates/index.html`)
- Move `#forgeContextWindowInput` out of the conditionally hidden `#forgeProviderConfigContainer`.
- Place it directly inside **Card 4: 🧠 LLM Provider & Model Override**, visible for all agents.
- Update label and helper text:
  - Label: `Context Window (tokens)`
  - Placeholder: `e.g. 131072 (leave empty to inherit)`
  - Helper: `Leave empty to inherit from this agent's model, or fallback to platform settings.`

### B. Agent Studio Form Persistence (`src/web/static/modules/studios/forge.js`)
- Update `context_window` extraction in the save payload: remove the `forgeProviderSelect.value === 'default'` gate so any agent can have an explicit context window override.
- Ensure the input is populated whenever an agent is selected in the roster sheet, and cleared when blank.

### C. Unified Context Window Resolution Cascade (`src/application/kernel/context_compactor.py`)
- Implement a centralized helper `resolve_agent_context_limit(agent, state_store=None)`:
  1. If `agent` has `context_window` and `context_window > 0`: return `int(agent.context_window)`.
  2. If `agent` has an explicit model (not `"default"`): check `purpose_matrix.model_context_windows` or name-based heuristic via `get_model_context_limit(agent.model)`.
  3. If agent is on `"default"` provider / model:
     - Check `purpose_matrix.default_context_window` from settings. If set (>0), return it (e.g. 131,072).
     - Check platform default model from `provider_settings.default_model_id` or `purpose_matrix.default_model`.
     - Check `purpose_matrix.model_context_windows[default_model]` or `get_model_context_limit(default_model)`.
     - Final conservative fallback: `8192`.

### D. Kernel & Chat Router Alignment (`src/web/routers/chat.py`, `src/application/kernel/agent_kernel.py`)
- In `src/web/routers/chat.py`:
  - Update `GET /api/sessions/{session_id}/context` to call `resolve_agent_context_limit(agent, store)`.
  - Update `POST /api/sessions/{session_id}/compact` to call `resolve_agent_context_limit(agent, store)`.
- In `src/application/kernel/agent_kernel.py`:
  - Update `_resolve_context_limit` to use the unified cascade helper with `agent` context.

---

## 3. Wireframes

### Agent Studio: Card 4 (LLM Provider, Model, and Context Window)
```text
+-------------------------------------------------------------+
| 🧠 LLM Provider & Model Override                            |
+-------------------------------------------------------------+
| LLM Provider:                                               |
| [ Use Global Default                                      v ]|
|                                                             |
| Model:                                    [ 🔄 Refresh ]     |
| [ Use Global Default                                      v ]|
| Leave on Global Default to inherit from Settings.           |
|                                                             |
| Context Window (tokens):                                    |
| [ e.g. 131072 (leave empty to inherit)                     ]|
| Leave empty to inherit from this agent's model, or fallback  |
| to platform settings.                                       |
+-------------------------------------------------------------+
```

---

## 4. Acceptance Criteria (Definition of Done)
- [x] Agent Studio displays `#forgeContextWindowInput` when LLM Provider is set to "Use Global Default".
- [x] Saving an agent with provider = "Use Global Default" and a typed context window persists the integer in SQLite.
- [x] Leaving an agent's context window blank with a custom model inherits that model's configured or baseline limit.
- [x] Leaving an agent's context window blank on "Use Global Default" inherits the platform-wide `default_context_window` (e.g. 131,072) from Settings Studio.
- [x] Chat Studio Options Drawer (`#chatOptionsDrawer`) context budget displays `131,072` for Personal Finance Lead when on default settings.
- [x] Backend unit tests verify the 3-tier cascade (`tests/unit/kernel/test_context_compactor.py`, `tests/unit/web/test_chat_session_context.py`).
- [x] Frontend unit tests verify input visibility and payload parsing (`tests/unit/frontend/`).
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 5. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Status remains `Ready` until the human visionary says build.
