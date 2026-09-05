# [CARD-153] Replace Purpose Matrix with Per-Agent LLM Provider and Model Configuration

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `type:refactor`, `AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings`

---

## 1. Why / Intent

The Purpose Matrix (Settings Studio > "Purpose-Based Model Routing") assigns models to abstract purpose slots (General, Reasoning, Task Execution, Vision, Auxiliary, Fast). Each agent then has a "Purpose Slot" dropdown in Agent Studio that indirectly maps the agent to a model through this matrix.

This is overly complicated for users. The indirection of "pick a purpose slot, then separately configure the matrix in Settings" makes it hard to understand which model an agent actually uses. Most users just want to set a global default LLM provider and model, then optionally override the provider and model directly on any specific agent.

The simpler model:
- **Settings Studio** keeps a **Global Default** LLM provider and model (already exists as "LLM Providers & Active Model").
- **Agent Studio** gets a per-agent **LLM Provider** and **Model** selector directly on the agent's roster sheet, defaulting to "Use Global Default".
- The Purpose Matrix panel and the `ModelPurpose` enum / `purpose` field are retired.

---

## 2. What to Build

1. **Agent Studio Per-Agent LLM Config (`src/web/templates/index.html`, `agent_studio.js`)**:
   - Replace the "Primary Purpose Slot (Purpose Matrix)" dropdown (`#forgePurposeSelect`) and "Explicit Model Override" (`#forgeModelSelect`) with:
     - **LLM Provider** dropdown (`#forgeProviderSelect`): `Use Global Default`, Ollama, LM Studio, Gemini, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, etc.
     - **Model** dropdown (`#forgeAgentModelSelect`): `Use Global Default`, plus live-discovered models from the selected provider.
     - Short helper text: *"Leave on Global Default to inherit from Settings. Or pick a specific provider and model for this agent."*
   - Wire Save Profile to persist `provider` and `model` on the agent record.
2. **Domain Model Changes (`src/domain/kernel/models.py`, `src/domain/settings/models.py`)**:
   - Add `provider: str = "default"` to `AgentProfile` (where "default" means inherit global).
   - Keep `model: str = "default"` (already exists).
   - Remove `purpose: ModelPurpose` from `AgentProfile` (or deprecate, keeping backward-compat parsing).
   - Deprecate `ModelPurposeMatrix` and `ModelPurpose` enum (keep in code for migration but stop using in resolution).
3. **Pack Schema Update (`docs/agent-packs.md`, `pack.json`)**:
   - Add optional `provider` field to pack.json.
   - Remove `purpose` from pack schema docs.
4. **Model Resolution Simplification (`src/application/kernel/agent_kernel.py`)**:
   - Simplify `_resolve_model()` cascade:
     1. Agent explicit `provider` + `model` (if not "default").
     2. Global default provider + model from Settings.
     3. Gateway fallback.
   - Remove Purpose Matrix lookup steps (steps 3 and 4 of the current cascade).
5. **Settings Studio Cleanup (`src/web/templates/index.html`, `settings.js`)**:
   - Remove the "Purpose-Based Model Routing" panel (the 6-slot matrix grid and Save Matrix button).
   - Keep the "LLM Providers & Active Model" panel as the **Global Default** configuration.
   - Keep the "Hardware Fit" panel as-is.
6. **API & Persistence (`src/web/routers/`, `src/infrastructure/`)**:
   - `GET/PUT /api/agents/{id}`: Serialize/deserialize `provider` field.
   - Clean up `purpose_matrix` settings key usage.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-MODEL-001]`: Agent Studio displays per-agent LLM Provider and Model selectors with "Use Global Default" as the default option.
- [x] `[REQ-MODEL-002]`: Saving an agent profile persists the per-agent provider and model to the database.
- [x] `[REQ-MODEL-003]`: Model resolution cascade is: agent override > global default > gateway fallback. No Purpose Matrix lookup.
- [x] `[REQ-MODEL-004]`: Pack export/import includes the agent's `provider` field and no longer includes `purpose`.
- [x] `[REQ-MODEL-005]`: The Purpose-Based Model Routing panel is removed from Settings Studio.
- [x] `[REQ-MODEL-006]`: Existing agents with `purpose` set continue to function (graceful deprecation: treated as "default").
- [x] `[REQ-MODEL-007]`: Automated unit and integration tests pass cleanly via `pytest` and `npm test`.
- [x] `[REQ-MODEL-008]`: Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to running agents: any agent with `purpose` set today must still resolve a model (fall through to global default).
- Settings Studio "LLM Providers & Active Model" panel and Hardware Fit panel remain unchanged.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
