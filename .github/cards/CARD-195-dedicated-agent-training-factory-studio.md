# [CARD-195] Dedicated Agent Training Factory Studio

> **Status**: In Review
> **Created**: 2026-09-08
> **Spec Reference**: `docs/specs/agent-pack-factory/`; CARD-164; CARD-171; CARD-175; [REQ-FACT-034] - [REQ-FACT-042]
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Orchestration`

---

## 1. Three Beats

### Beat 1: What you mean
The Agent Training Factory is an industrial manufacturing plant that turns high-level operator intent into verified, sandbox-tested agent packs with tools and runbooks.

Currently, viewing the visual pipeline, inspecting phase system prompts, or tracking training runs is cramped inside an overlay drawer (`#labMonitorDrawer`) nested inside Agent Studio, while general training prompts were put into Factory Studio. This splits training across two separate places.

You want a dedicated **Factory Studio** as the single, unified home for all training operations:
1. **Agent Picker in Factory**: A dropdown in the Factory Studio top bar lets you pick either **All Agents (Platform View)** or a specific agent (e.g. `assistant`, `developer`, `finance`).
2. **Context-Aware Telemetry**: When an agent is chosen, the training runs list, pending reviews, active counts, and recent artifacts update to that agent's context.
3. **Pre-Scoped Launch Wizard**: Clicking `[ 🚀 Train Agent ]` automatically knows which agent is selected and pre-fills their intent, profile, and starter objectives.
4. **Platform Prompt Management**: Inspect, customize, save, and reset system prompt instructions and rubrics for all 8 stages (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`) anytime at the platform level.
5. **Agent Studio Consolidation**: Agent Studio (`#view-forge`) no longer splits training into a nested drawer; clicking `[Train in Lab]` or `[Lab Monitor]` transitions directly to Factory Studio with that agent pre-selected.

---

### Beat 2: What AutoReiv does now
1. **Factory Studio Header (`#factoryStudio`)**:
   - Displays title, status pill, sub-view tabs, and a generic `[ 🚀 New Training Run ]` button, but lacks an agent dropdown selector.
2. **Runs List**:
   - Shows all runs across all agents with only a free-text search box (`#factoryRunSearchInput`).
3. **Agent Studio Header (`#view-forge`)**:
   - Contains `[Train in Lab]` (`#forgeTrainAgentBtn`) and `[Lab Monitor]` (`#forgeLabMonitorBtn`), opening a slide-out drawer overlay (`#labMonitorDrawer`).

---

### Beat 3: What will change
1. **Primary Navigation Bar (`src/web/templates/index.html`)**:
   - Maintain **Factory** (`#navFactory`, `#railBtnFactory`) as a first-class studio tab.
2. **Factory Studio Header (`#factoryStudio`)**:
   - Add `<select id="factoryAgentSelect">` directly in the top bar, dynamically populated with `All Agents (Platform View)` and all loaded agents.
   - When changed, updates active scope, filters the runs list, refreshes status counters, and pre-scopes the training launch button.
3. **Agent Studio Integration (`src/web/static/modules/studios/forge.js`)**:
   - Clicking `#forgeTrainAgentBtn` or `#forgeLabMonitorBtn` smoothly navigates to Factory Studio with that agent pre-selected in `#factoryAgentSelect`.
4. **Dedicated Two-Pane Workspace & Flowchart**:
   - Seamlessly inspect 8-stage pipeline prompts and live runs within a single unified surface.

---

## 2. Visual Contract & ASCII Wireframe

```text
+---------------------------------------------------------------------------------------------------------+
| [AutoReiv]  💬 Chat  🤖 Agents  🧪 Factory  ⚡ Skills  📚 Wiki  📁 Projects  ⚙️ Settings                |
+---------------------------------------------------------------------------------------------------------+
| 🧪 FACTORY STUDIO    Agent: [ All Agents / developer v ]              [ 🚀 Train developer ]            |
| Tabs: [ 🧭 Pipeline & Phase Prompts ]  [ 📊 Training Runs & Live Monitor (1 Pending) ]                  |
+---------------------------------------------------------------------------------------------------------+
| [ Runs for "developer" ]   | RUN: dev-run-004 (Needs Review)                                            |
| 🟢 dev-run-004 (Review)    | Stepper: Intent -> Ground -> ... -> [Code Verify] -> [HITL Promotion Gate] |
| ⚪ dev-run-003 (Completed) |                                                                            |
| ⚪ dev-run-002 (Failed)    | [ ✅ Approve & Promote to Pack ]  [ ❌ Reject ]                            |
+---------------------------------------------------------------------------------------------------------+
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
- [x] **AC-8**: Factory Studio top bar renders `<select id="factoryAgentSelect">` dynamically populated with all registered agents + platform view option.
- [x] **AC-9**: Selecting an agent updates the runs list, status pill counters, active runs badge, and pre-scopes the training launch button.
- [x] **AC-10**: In Agent Studio, `#forgeTrainAgentBtn` and `#forgeLabMonitorBtn` transition smoothly into Factory Studio with the target agent pre-selected.

---

## 4. Constraints & Honor Flags
- Backlog card. Do not implement until Jacob says **build**.
- Local `qa` branch is source of truth.

