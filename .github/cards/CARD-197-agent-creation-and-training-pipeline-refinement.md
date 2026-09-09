# [CARD-197] Agent Creation and Training Pipeline Refinement

> **Status**: Ready
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Three Beats

### Beat 1: What you mean
Creating a new specialist agent and training its skills should feel like a continuous, cohesive journey without dead ends or confusion about who does what.

You want to refine and polish two connected parts of the platform:
1. **Agent Creation Flow**:
   - Creating an agent should be crystal clear: AutoReiv helps define the persona, brief, instructions, and boundaries.
   - The operator should have both an assisted chat route (talking with AutoReiv) and a fast-scaffold form (for quickly creating an agent when you already know its name and role).
   - Once the agent is created on disk, there should be an **instant handoff** to the Agent Training Factory so the operator can immediately train its capabilities without having to hunt through menus.
2. **Training Pipeline Refinement**:
   - The 8-stage Agent Training Factory pipeline (`Intent Distill` ➔ `Ground` ➔ `Blueprint` ➔ `Author` ➔ `Scenario` ➔ `Code Verify` ➔ `Optimize` ➔ `Promote`) should be hardened and easier to inspect.
   - **Pre-Promotion Diff & Code Preview**: Before hitting "Approve & Promote", the operator should see a clean preview of exactly what `SKILL.md` runbooks, native Python tools, or MCP configs were generated.
   - **Self-Healing Code Verification**: If `Code Verify` hits a syntax or import error, the pipeline should automatically retry once or twice with the traceback before marking the job failed.
   - **Phase Timing & Diagnostics**: Show how long each phase took to run and highlight any warnings.

---

### Beat 2: What AutoReiv does now
1. **Agent Creation Today**:
   - In Factory Studio, clicking `[ + New Agent ]` redirects to Chat Studio with a starter prompt `@autoreiv I want to create a new specialist agent...`.
   - In Agent Studio (`#view-forge`), there is no fast-creation form; agent definitions must be created via agent chat or manually placing files in `packs/`.
   - After an agent is created, there is no automatic transition or prompt suggesting: "Now let's train this agent in the Factory". The operator must manually navigate to Factory Studio and locate the new agent in the dropdown.
2. **Training Pipeline Today**:
   - The 8-stage pipeline executes sequentially via `FactoryOrchestrator`.
   - If Stage 6 (`Code Verify`) encounters a syntax or runtime error, the job immediately enters `Failed` status with no automatic self-correction attempt.
   - The HITL Promote stage allows one-click approval, but the artifact preview modal only shows raw text dumps without structured file tree diffing.
   - Phase durations are not tracked or displayed on the visual stepper nodes.

---

### Beat 3: What will change (Proposed Architecture & Refinements)

#### 1. Streamlined Agent Creation & Onboarding Flow
- **Dual Creation Modalities**:
  - *Conversational Creation*: Keep the smooth redirect from `[ + New Agent ]` in Factory Studio to Chat Studio with `@autoreiv`, guiding the operator through name, role, system prompt, and capabilities.
  - *Quick Scaffold Modal (`#forgeNewAgentModal`)*: Add a quick-scaffold modal option directly in Factory Studio and Agent Studio for operators who want to quickly spin up a pack skeleton (Agent Name, Slug, Short Purpose, System Prompt, and Tone).
- **Post-Creation Factory Handoff Card**:
  - When an agent pack is successfully created and written to `packs/<agent_slug>/`, render an interactive handoff card:
    ```text
    +---------------------------------------------------------+
    | 🎉 Agent "<Agent Name>" Created Successfully!           |
    | Location: packs/<slug>/ (Manifest & DB initialized)      |
    | [ 🚀 Launch Training in Factory ]   [ ⚙️ Open in Studio ] |
    +---------------------------------------------------------+
    ```
  - Clicking `[ 🚀 Launch Training in Factory ]` automatically switches the workspace to Factory Studio, selects the new agent in `#factoryAgentSelect`, and opens the Training Launcher modal pre-loaded with the agent's context.

#### 2. Training Pipeline Engine Refinements
- **Auto-Healing Loop in Code Verify (Stage 6 ➔ Stage 4/7)**:
  - If `Code Verify` fails execution or syntax tests, feed the Python traceback back into the Author/Optimize runner for up to 2 automated repair attempts before halting.
  - Display a "Self-correcting code syntax (Attempt 1/2)..." badge in the Live Monitor activity feed.
- **Rich Pre-Promotion File Tree & Diff Inspector (Stage 8 HITL)**:
  - Expand the promotion preview modal to display:
    - Target pack destination (`packs/<agent_slug>/`).
    - Clean tabbed or tree view of generated deliverables:
      - 📘 `skills/<skill_name>/SKILL.md` (Runbook preview with markdown rendering)
      - 🐍 `skills/<skill_name>/tools.py` (Syntax-highlighted Python tool code)
      - ⚙️ `pack.json` (Diff showing added tool bindings)
- **Phase Execution Telemetry & Duration**:
  - Record start and end timestamps per phase in SQLite `factory_training_jobs`.
  - Display duration badges (e.g. `12s`, `4.2s`) below each node in the 8-stage stepper and flowchart.
- **Pack Integrity Guard**:
  - Validate that new tool function names do not collide with existing tools in the agent pack before writing files to disk.

---

## 2. Technical Scope & Affected Components

1. **Frontend**:
   - `src/web/templates/index.html`: Quick-scaffold modal markup and enhanced HITL promotion preview modal.
   - `src/web/static/modules/studios/factory.js`: Post-creation handoff listener, duration badges on 8-stage stepper, and tabbed code preview.
   - `src/web/static/modules/studios/forge.js`: Quick-scaffold trigger and creation form validation.
2. **Backend / Orchestration**:
   - `src/application/agent_training_factory/orchestrator.py`: Self-healing retry loop in `Code Verify`, phase duration calculation, and pack collision validation.
   - `src/application/agent_training_factory/runners/code_verify.py`: Structured error traceback capture for self-healing loops.
   - `src/application/agent_training_factory/runners/promote.py`: Deliverable file tree builder and manifest patcher.
   - `src/web/routers/agent_training_factory.py`: REST endpoint enhancements for artifact diff previews and job phase telemetry.

---

## 3. Acceptance Criteria (When Scheduled for Implementation)

- [ ] Dual agent creation paths: guided conversational creation via AutoReiv agent chat and quick-scaffold modal in Factory/Agent Studio.
- [ ] Post-creation handoff card with one-click direct transition into pre-scoped Factory Studio training.
- [ ] Self-healing verification retry loop (up to 2 attempts with traceback) before failing a training job.
- [ ] Tabbed deliverable preview in HITL Promote modal showing runbooks, Python code, and pack manifest diffs.
- [ ] Per-phase execution duration metrics tracked and displayed in the visual progress stepper.
- [ ] Name collision guard preventing duplicate tool method names in target agent packs.
- [ ] Automated unit tests for self-healing orchestrator loop, duration recording, and collision guards.
- [ ] Zero lint errors via `ruff` and `eslint`.
