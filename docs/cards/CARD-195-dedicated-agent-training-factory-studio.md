# [CARD-195] Dedicated Agent Training Factory Studio

> **Status**: Done
> **Created**: 2026-09-08
> **Spec Reference**: `docs/specs/agent-pack-factory/`; CARD-164; CARD-171; CARD-175; [REQ-FACT-034] - [REQ-FACT-045]
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Orchestration`

---

## 1. Three Beats

### Beat 1: What you mean
The Agent Training Factory is an industrial manufacturing plant that turns operator intent into verified agent packs with tools and runbooks.

You want complete consolidation of all training-related operations into Factory Studio, with a clean architectural separation between **Agent Creation** and **Agent Training**:
1. **Creating a New Agent Belongs to AutoReiv**: An agent's identity, brief (instructions/system prompt), purpose, and tone must be thought out *before* training begins. Clicking `[ + New Agent ]` (`#factoryNewAgentBtn`) in Factory Studio initiates a conversational session with AutoReiv in Chat Studio to author the new agent's brief and profile.
2. **Factory Training Strictly Targets Existing Agents**: The Factory agent selector (`#factoryAgentSelect`) lists only real existing agents (strictly excluding `agent_builder`). When you select an agent (e.g. `Developer`), the launch button is `[ 🚀 Train Developer ]`. Clicking it opens `#trainAgentHandshakeModal` already locked to Developer with on-disk pack verification (`packs/developer/`, skill count, tool count) and **zero secondary dropdowns**. Pick once in the Factory UI, and work directly.
3. **Agent Studio is Pure Configuration**: Remove `[Train in Lab]` and `[Lab Monitor]` from Agent Studio header (`#view-forge`). Agent Studio is exclusively for configuring profiles, tools, instructions, and memory.
4. **Move "Needs Training" Backlog to Factory**: Move the capability gap backlog (`#agentTrainingBacklogCard`) out of Agent Studio and into Factory Studio, showing queued gaps for the selected agent (or all agents in platform view) with one-click training triggers.

---

### Beat 2: What AutoReiv does now
1. **Agent Studio Header & Tabs (`#view-forge`)**:
   - Displays `[Train in Lab]` (`#forgeTrainAgentBtn`) and `[Lab Monitor]` (`#forgeLabMonitorBtn`).
   - Holds `#agentTrainingBacklogCard` inside the Agent Studio configuration tabs.
2. **Factory Studio Header (`#factoryStudio`)**:
   - Lacks `[ + New Agent ]` button.
   - Includes `agent_builder` (internal system agent) in the `#factoryAgentSelect` dropdown.
3. **Training Modal (`#trainAgentHandshakeModal`)**:
   - Contains a second dropdown (`#trainAgentTargetSelect`), making the operator pick an agent twice.

---

### Beat 3: What will change
1. **Factory Studio Header (`#factoryStudio`, `factory.js`, `index.html`)**:
   - Add `[ + New Agent ]` button (`#factoryNewAgentBtn`) next to `#factoryAgentSelect` that triggers `callbacks.onStartNewAgentPack()` to converse with AutoReiv in Chat.
   - Filter out `agent_builder` and `agent-builder` from `#factoryAgentSelect`.
2. **Single Pick, Zero Redundant Modal Dropdowns (`chat.js`, `factory.js`, `index.html`)**:
   - Remove `<select id="trainAgentTargetSelect">` and `#trainAgentNameGroup` from `#trainAgentHandshakeModal`.
   - The modal inherits the selected agent from `#factoryAgentSelect`, displaying a verified target header (`Target: <Agent> (packs/<agent_id>/)`) with live skill/tool counts.
   - In Platform View (`All Agents`), clicking `[ 🚀 Train Agent ]` prompts the operator with a toast to select an agent to train first.
3. **Agent Studio Cleanup (`forge.js`, `index.html`)**:
   - Remove `#forgeTrainAgentBtn` and `#forgeLabMonitorBtn`.
   - Remove `#agentTrainingBacklogCard` from Agent Studio.
4. **Factory Studio Backlog (`factory.js`, `index.html`)**:
   - Relocate `#agentTrainingBacklogCard` into Factory Studio's Runs & Monitor view.
   - Loads and renders capability gaps scoped to the active agent in `#factoryAgentSelect` (or all gaps in Platform View).

---

## 2. Visual Contract & ASCII Wireframe

```text
+---------------------------------------------------------------------------------------------------------+
| [AutoReiv]  💬 Chat  🤖 Agents  🧪 Factory  ⚡ Skills  📚 Wiki  📁 Projects  ⚙️ Settings                |
+---------------------------------------------------------------------------------------------------------+
| 🧪 FACTORY STUDIO    Agent: [ Developer v ]    [ + New Agent ]                [ 🚀 Train Developer ]    |
| Tabs: [ 🧭 Pipeline & Phase Prompts ]  [ 📊 Training Runs & Live Monitor (1 Pending) ]                  |
+---------------------------------------------------------------------------------------------------------+
| [ Runs for "Developer" ]   | RUN: dev-run-004 (Needs Review)                                            |
| 🟢 dev-run-004 (Review)    | Stepper: Intent -> Ground -> ... -> [Code Verify] -> [HITL Promotion Gate] |
| ⚪ dev-run-003 (Completed) |                                                                            |
|                            | [ ✅ Approve & Promote to Pack ]  [ ❌ Reject ]                            |
| -------------------------- | -------------------------------------------------------------------------- |
| ⚡ Needs Training Backlog  | Identified Capability Gaps for Developer:                                  |
| [2 Queued Gaps]            | - "Manage Hyper-V virtual switches"               [ 🚀 Train in Lab ]       |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **AC-1**: Navigation bar contains "Factory" (`#navFactory`) navigating cleanly to `#factoryStudio`.
- [x] **AC-2**: Factory Studio provides full visibility into all 8 pipeline phases, their descriptions, and read-only context variable helper pills.
- [x] **AC-3**: Operators can view, edit, save, and reset phase system prompts at the platform level without needing an active run selected.
- [x] **AC-4**: Factory Studio includes a dedicated Training Runs view displaying run history, packet logs, artifact previews, and HITL deployment approval.
- [x] **AC-5**: Redundant `[Train in Lab]` and `[Lab Monitor]` buttons removed from Agent Studio (`#view-forge`).
- [x] **AC-6**: Automated frontend and router tests pass 100% cleanly.
- [x] **AC-7**: Zero lint errors via `ruff check .` and `npm run lint:frontend`.
- [x] **AC-8**: Factory Studio top bar renders `<select id="factoryAgentSelect">` dynamically populated with all registered specialist agents + platform view option, strictly excluding `agent_builder`.
- [x] **AC-9**: Factory Studio top bar includes `[ + New Agent ]` (`#factoryNewAgentBtn`) triggering conversational authoring with AutoReiv in Chat Studio.
- [x] **AC-10**: Capability gap backlog (`#agentTrainingBacklogCard`) lives inside Factory Studio, displaying gaps scoped to the selected agent (or all gaps in Platform View) with one-click training.
- [x] **AC-11**: `#trainAgentHandshakeModal` has zero redundant dropdowns; it targets the agent chosen in `#factoryAgentSelect`, displaying a verified target badge (`Target: <Agent>`) with on-disk pack verification (`packs/<agent_id>/`).

---

## 4. Constraints & Honor Flags
- Backlog card. Do not implement until Jacob says **build**.
- Local `qa` branch is source of truth.

