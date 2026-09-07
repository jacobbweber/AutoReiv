# [CARD-175] Agent Training Factory Visual Flowchart and Editable Phase Instruction Inspector

> **Status**: Ready
> **Created**: 2026-09-06
> **Spec Reference**: docs/specs/agent-pack-factory/; CARD-164; CARD-171; CARD-172
> **Labels**: `type:feature`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.HITL`

---

## 1. Why / Intent

During live testing and QA, Jacob noted a critical visibility gap:
- When the Training Factory runs its multi-phase loop, the reasoning instructions, system prompts, and rubrics are executed deep inside Python code.
- As the Visionary and Product Owner, Jacob cannot easily see what instructions were given to the LLM during a specific phase, nor can he tweak the instructions without asking an AI coding agent to modify Python source files.

**Solution**: Provide a visual flowchart in the Lab Monitor UI with interactive nodes. Clicking any phase displays the exact instructions and system prompts used for that phase, with an editable text box allowing Jacob to customize and save the guidance directly from the browser. The backend code focuses on the mechanical plumbing, while the operator retains full control over the reasoning directives.

---

## 2. What Jacob Sees & Controls (UI / UX)

```
+-----------------------------------------------------------------------------+
| [Lab Monitor] Agent Training Factory                                        |
| Active Job: [ Hyper-V Administrator (job_482) v ]                           |
|                                                                             |
| +--- Visual Phase Flow ---------------------------------------------------+ |
| | [1. Distill] -> [2. Ground] -> [3. Blueprint] -> [4. Author]            | |
| |       ^                                                |                | |
| |       | (Outer Rinse)                                  v                | |
| |       +----------- [6. Verify] <- [5. Scenario] <------+                | |
| |                         |                                               | |
| |                         v                                               | |
| |                   [7. Optimize] -> [8. Promote]                         | |
| +-------------------------------------------------------------------------+ |
|                                                                             |
| [ Selected Node: 4. Author ]                                                |
| +--- Phase Instruction Inspector -----------------------------------------+ |
| | Description: Authors tools, PowerShell scripts, and SKILL.md runbooks   | |
| | Injected Variables: {{seed_brief}}, {{operating_manual}}, {{scenarios}}  | |
| |                                                                         | |
| | Prompt / Guidance Template:                                             | |
| | +---------------------------------------------------------------------+ | |
| | | You are the Author phase. Generate complete, runnable tool code...  | | |
| | | Require strict parameter typing and error handling. Do not omit...  | | |
| | +---------------------------------------------------------------------+ | |
| |                                                                         | |
| | [ 💾 Save Phase Instructions ]   [ 🔄 Reset to Platform Default ]      | |
| +-------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+
```

1. **Visual Phase Flow**:
   - Interactive flowchart canvas inside `#labMonitorDrawer`.
   - Node status lights: Idle (gray), Running (pulsing blue), Succeeded (green), Rinse/Retry (amber), Failed (red).
2. **Phase Instruction Inspector**:
   - Clicking any phase node opens its instruction panel.
   - Shows:
     - Phase role and objective.
     - Available template context variables (e.g. `{{ seed_brief }}`, `{{ lessons }}`).
     - Editable prompt / rubric textarea (`#labPhasePromptInput`).
     - Actions: `[Save Phase Instructions]` and `[Reset to Default]`.

---

## 3. Core Architecture & Primitives

1. **`PhasePromptRegistry` (`src/application/agent_training_factory/prompt_registry.py`)**:
   - Maintains the canonical system prompts and rubrics for all 8 phases.
   - Reads user customizations from persistent storage; falls back to defaults.
2. **Persistence (`factory_phase_instructions` table)**:
   - SQLite table storing `phase_id`, `prompt_template`, `updated_at`.
3. **REST Endpoints (`src/web/routers/agent_training_factory.py`)**:
   - `GET /api/agent_training_factory/phases/instructions`: Returns all phase prompts and available template variables.
   - `PUT /api/agent_training_factory/phases/{phase_id}/instructions`: Updates custom prompt template.
   - `DELETE /api/agent_training_factory/phases/{phase_id}/instructions`: Resets to platform default.

---

## 4. Acceptance Criteria

- [ ] [REQ-ATF-UI-001] Lab Monitor displays an interactive 8-stage visual flowchart of the Training Factory pipeline.
- [ ] [REQ-ATF-UI-002] Clicking any phase node renders the Phase Instruction Inspector with current instructions.
- [ ] [REQ-ATF-UI-003] Operators can edit and save custom instructions per phase with immediate persistence.
- [ ] [REQ-ATF-UI-004] Factory phases use the customized prompt templates during subsequent job executions.
- [ ] [REQ-ATF-UI-005] "Reset to Platform Default" restores factory default instructions cleanly.
- [ ] [REQ-ATF-UI-006] Unit tests verify prompt override cascade and API endpoints.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Work strictly on local `qa` branch.
