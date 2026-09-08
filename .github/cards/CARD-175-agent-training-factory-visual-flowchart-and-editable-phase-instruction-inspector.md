# [CARD-175] Agent Training Factory Visual Flowchart and Editable Phase Instruction Inspector

> **Status**: Ready
> **Created**: 2026-09-06
> **Spec Reference**: `docs/specs/agent-pack-factory/`; CARD-164; CARD-171; CARD-172
> **Labels**: `type:feature`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.HITL`

---

## 1. Three Beats

### Beat 1: What you mean
During live testing and QA of the Agent Training Factory, Jacob noted a critical visibility gap:
When the factory runs its 8-stage pipeline (`Distill` → `Ground` → `Blueprint` → `Author` → `Scenario` → `Verify` → `Optimize` → `Promote`), the system prompts and guidance rubrics given to the LLM are hardcoded deep inside Python source files.

You want complete transparency and control:
- In the **Lab Monitor** drawer, clicking any of the 8 stage tiles opens an **Instruction Inspector** directly below the stepper.
- It displays the stage's purpose, read-only helper pills showing the runtime context variables (e.g., `{{seed_intent}}`, `{{objectives}}`, `{{scenarios}}`, `{{lessons}}`) so you know what data feeds into the stage without breaking the pipeline code.
- An editable textarea displays the exact prompt instructions used by the LLM for that stage, with a `[ 💾 Save Instructions ]` button to save platform-wide customizations and a `[ 🔄 Reset to Platform Default ]` button to restore built-in guidance.
- When subsequent training jobs run or retry, they dynamically execute with your saved instructions.

### Beat 2: What AutoReiv does now
1. **Lab Monitor Stepper** (`src/web/templates/index.html:2898`):
   - Shows 8 static step tiles (`#labStep1` through `#labStep8`) showing stage name and icon.
   - The tiles are static displays; clicking them does nothing.
2. **Phase Runners & Prompts** (`src/application/agent_training_factory/phases/`):
   - System prompts and rubrics are hardcoded strings in each phase's Python file (`intent_distill.py`, `blueprint.py`, `author.py`, `scenario_verify.py`, `verify.py`, etc.).
   - There is no database table or API to inspect, edit, or reset phase instructions.

### Beat 3: What will change
1. **Interactive Stage Stepper in Lab Monitor (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`)**:
   - Make all 8 stage tiles in `#labStepperContainer` clickable buttons with active ring focus and hover states.
   - Selecting a stage tile highlights it and loads its instructions into the inspector.
2. **Phase Instruction Inspector Panel**:
   - Located directly below the stage tiles in `#labMonitorDrawer`.
   - **Header**: Shows selected stage number, name, and description (e.g., *"Stage 4: Author — Generates complete, runnable tool code, PowerShell scripts, and SKILL.md runbooks"*).
   - **Status Badge**: Displays `[Platform Default]` (emerald) or `[Custom Override]` (amber).
   - **Context Variable Pills**: Read-only tags displaying available runtime variables for that phase (e.g., `{{seed_intent}}`, `{{objectives}}`, `{{scenarios}}`, `{{lessons}}`).
   - **Editable Prompt Editor**: Textarea displaying the phase's system prompt / rubric instructions.
   - **Action Buttons**:
     - `[ 💾 Save Phase Instructions ]`: Persists custom prompt to SQLite.
     - `[ 🔄 Reset to Platform Default ]`: Deletes custom prompt and restores built-in default.
3. **Phase Prompt Registry & Persistence (`src/application/agent_training_factory/prompt_registry.py`)**:
   - `PhasePromptRegistry` defining default system prompts, descriptions, and context variables for all 8 phases.
   - SQLite table `factory_phase_instructions` in `database/autoreiv.db`: `phase_id TEXT PRIMARY KEY`, `custom_prompt TEXT NOT NULL`, `updated_at TIMESTAMP`.
   - Dynamic prompt resolution: `get_phase_system_prompt(phase_id)` returns custom prompt if present, falling back to default.
4. **REST API (`src/web/routers/agent_training_factory.py`)**:
   - `GET /api/agent_training_factory/phases/instructions`: Returns all 8 phases with active prompt, default prompt, description, context variables, and `is_custom` boolean.
   - `PUT /api/agent_training_factory/phases/{phase_id}/instructions`: Sets and persists custom prompt.
   - `DELETE /api/agent_training_factory/phases/{phase_id}/instructions`: Resets to platform default.
5. **Phase Execution Dynamic Resolution**:
   - Factory phase runners resolve their system prompt via `prompt_registry` during training execution.

---

## 2. Acceptance Criteria (Definition of Done)

- [ ] **AC-1**: All 8 stage tiles in `#labStepperContainer` are clickable, with visual active-state highlighting.
- [ ] **AC-2**: Clicking any stage opens the Phase Instruction Inspector displaying stage description and read-only context variable pills.
- [ ] **AC-3**: Operators can edit the prompt textarea and click "Save Phase Instructions" to persist platform-wide custom instructions.
- [ ] **AC-4**: Clicking "Reset to Platform Default" cleanly deletes custom instructions and restores built-in defaults.
- [ ] **AC-5**: `factory_phase_instructions` SQLite table persists overrides across application restarts.
- [ ] **AC-6**: Training factory phases dynamically use custom prompts when executed.
- [ ] **AC-7**: Automated unit and frontend tests pass cleanly (`pytest`, `npm run test:unit:frontend`).
- [ ] **AC-8**: Zero lint errors via `ruff check .`.

---

## 3. Constraints & Working Agreement

- Ready card only. Do not implement until Jacob says **build**.
- Context variables remain strictly read-only helper pills in the UI to prevent damaging the pipeline code.
- Local `qa` branch is source of truth.
