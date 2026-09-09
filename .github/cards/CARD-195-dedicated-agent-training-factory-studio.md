# [CARD-195] Dedicated Agent Training Factory Studio

> **Status**: In Review
> **Created**: 2026-09-08
> **Spec Reference**: `docs/specs/agent-pack-factory/`; CARD-164; CARD-171; CARD-175
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Orchestration`

---

## 1. Three Beats

### Beat 1: What you mean
The Agent Training Factory is an industrial manufacturing plant that turns high-level operator intent into verified, sandbox-tested agent packs with tools and runbooks.

Currently, viewing the visual pipeline, inspecting phase system prompts, or tracking training runs is cramped inside an overlay drawer (`#labMonitorDrawer`) nested inside Agent Studio. Operators must open an existing agent and find a past run just to inspect or edit platform instructions.

You want a dedicated **Factory Studio** as a first-class studio tab in the main navigation bar alongside Chat, Agents, Skills, Wiki, Projects, and Settings.

In this dedicated Factory Studio:
1. **Platform Prompt Management**: Inspect, customize, save, and reset system prompt instructions and rubrics for all 8 stages (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`) at the platform level anytime—without needing to select an agent or open an old run.
2. **Visual Pipeline Flowchart**: An expansive visual flowchart representing the factory manufacturing pipeline, displaying phase descriptions, read-only runtime context variable helper pills, and quality gates.
3. **Dedicated Run Management**: View active and historical training runs, packet feeds, artifact previews, and HITL deployment approval gates in a spacious, dedicated two-pane studio view.
4. **Clean Launch Wizard**: Start new training runs for any target agent with clean intent inputs and deliverable configuration.

---

### Beat 2: What AutoReiv does now
1. **Nested Overlay Drawer (`src/web/templates/index.html:2850`)**:
   - The Lab Monitor exists only as a slide-out drawer (`#labMonitorDrawer`) accessible via buttons in Agent Studio (`#forgeLabMonitorBtn`).
   - Phase prompt customization is bound to the drawer, meaning operators must open an agent and an existing run to access instructions.
2. **Navigation Bar**:
   - Navigation bar links exist for Chat (`#navChat`), Agents (`#navForge`), Skills (`#navSkills`), Wiki (`#navWiki`), Projects (`#navProjects`), Routines (`#navRoutines`), and Settings (`#navSettings`).
   - There is no top-level Studio for the Agent Training Factory.

---

### Beat 3: What will change
1. **Primary Navigation Bar (`src/web/templates/index.html`)**:
   - Add **Factory** (`#navFactory`) with a flask/beaker icon to the main navigation bar.
2. **Factory Studio Workspace (`#factoryStudio`)**:
   - Create a dedicated studio screen with two primary views / tabs:
     - **Pipeline & Prompts Inspector**: Visual 8-stage pipeline flowchart with the Phase Instruction Inspector, allowing platform-wide prompt inspection, customization, and defaults resetting.
     - **Training Runs & Monitor**: Two-pane workspace with Runs List on the left and Live Packet Activity Feed + Artifact Previews + HITL Deployment Gate on the right.
3. **Studio Module (`src/web/static/modules/studios/factory.js`)**:
   - Dedicated controller module managing phase prompt inspection, run selection, live polling, and promotion deployment.
4. **Agent Studio Cleanup**:
   - Remove redundant `[Train New]` button from Agent Studio (`Agent Forge`) header.
   - Keep `[Train in Lab]` on the active agent as a quick shortcut that opens the Factory Studio pre-scoped to that agent.

---

## 2. Visual Contract & ASCII Wireframe

```text
+-----------------------------------------------------------------------------------------+
| [AutoReiv]  💬 Chat  🤖 Agents  🧪 Factory  ⚡ Skills  📚 Wiki  📁 Projects  ⚙️ Settings |
+-----------------------------------------------------------------------------------------+
| FACTORY STUDIO                                                [ 🚀 New Training Run ]    |
| Tabs: [ 🧭 Pipeline & Phase Prompts ]  [ 📊 Training Runs & Live Monitor ]               |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
| 1. Intent       2. Ground       3. Blueprint    4. Author       ...    8. Promote       |
| [Active Ring]   [Default]       [Default]       [Override]             [Default]        |
|                                                                                         |
| +-------------------------------------------------------------------------------------+ |
| | Stage 1: Intent Distill                   [Platform Default]  [Reset] [💾 Save]     | |
| | Distills operator brief into structured answers and Reflexion lessons.             | |
| |                                                                                     | |
| | AVAILABLE CONTEXT VARIABLES (READ-ONLY)                                              | |
| | [{{target_agent_id}}] [{{seed_intent}}] [{{objectives}}] [{{failure_lessons}}]     | |
| |                                                                                     | |
| | System Prompt Instructions                                                          | |
| | +---------------------------------------------------------------------------------+ | |
| | | You are the Intent Distill phase of the Agent Training Factory...               | | |
| | +---------------------------------------------------------------------------------+ | |
| +-------------------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **AC-1**: Navigation bar contains "Factory" (`#navFactory`) navigating cleanly to `#factoryStudio`.
- [x] **AC-2**: Factory Studio provides full visibility into all 8 pipeline phases, their descriptions, and read-only context variable helper pills.
- [x] **AC-3**: Operators can view, edit, save, and reset phase system prompts at the platform level without needing an active run selected.
- [x] **AC-4**: Factory Studio includes a dedicated Training Runs view displaying run history, packet logs, artifact previews, and HITL deployment approval.
- [x] **AC-5**: Redundant `[Train New]` button removed from Agent Studio.
- [x] **AC-6**: Automated frontend and router tests pass 100% cleanly.
- [x] **AC-7**: Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Backlog card. Do not implement until Jacob says **build**.
- Local `qa` branch is source of truth.
