# [CARD-351] Factory Studio: Intake & Training Steering Workbench

> **Status**: Ready  
> **Created**: 2026-09-17  
> **Spec Reference**: `docs/specs/agent-pack-factory/`, CARD-195  
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Orchestration`  

---

## 1. TODO Before Work Starts (Discussion & Alignment)

Before calling `build` on this card, align on these three decisions with Jacob:
1. **Sub-View Tab Structure**: Should Factory Studio have 3 tabs: `[ 🛠️ Capability Intake ]` (Default landing view), `[ 📊 Training Runs & Monitor ]`, and `[ ⚙️ Pipeline & Phase Prompts ]` (Advanced administrator view)?
2. **Chat Turn Import Bridge**: Should the Intake Workbench feature a button or picker: *"Pre-fill from Recent Chat Friction"*, allowing you to select a recent chat session and turn to seed the training intent automatically?
3. **Modal vs. In-Page Launch**: With the full Intake Workbench rendered directly on the main canvas, can we retire the popup `#trainAgentHandshakeModal` entirely in favor of launching runs directly from the page?

---

## 2. Three Beats

### Beat 1: What Jacob means
When opening Factory Studio, the operator needs an obvious, first-class workspace to steer and provide instructions on what the agent should be trained to do. The screen must not look like an internal developer IDE for editing pipeline phase prompts. Instead, the front door of Factory Studio must be a **Capability Intake & Training Workbench** where the operator defines the training goal, specifies objectives, attaches reference materials, selects the deliverable type, and launches the run.

### Beat 2: What AutoReiv does now
* Navigating to Factory Studio (`#view-factory`) defaults to the `Pipeline & Phase Prompts` sub-view.
* The main canvas displays the 8-phase flowchart and a system prompt editor (`Phase System Prompt & Guidance Rubric`), which is meta-configuration for how the factory runs, not where you train an agent.
* The only place to provide training input is buried inside `#trainAgentHandshakeModal`, which only opens if the operator spots and clicks the green `Train AutoReiv` button in the top navigation bar.

### Beat 3: What will change
1. **New Default Sub-View: Capability Intake Workbench (`factory.js`, `templates/index.html`)**:
   * Make the front view an interactive **Capability Training Workbench**:
     * **Target Agent Card**: Displays active agent identity, icon, current tool count, skill count, and pack directory.
     * **Training Intent & Purpose**: Full-width textarea for describing what capability or task the agent must learn.
     * **Starter Objectives**: Bulleted list of 1 to 3 verifiable tasks.
     * **Reference Materials & Context**: Attachment area for pasting API docs, directory rules, sample code, or error logs.
     * **Deliverable Architecture Selector**: Radio pills for `Auto-detect`, `Native Atomic Tool (Python)`, `MCP Server`, or `Procedural Skill Only`.
     * **Primary Action**: Prominent `[ 🚀 Launch Capability Manufacturing ]` button.
2. **Relocate Pipeline Prompt Editor to "Advanced"**:
   * Move the 8-phase system prompt editor (Stage 01–08 rubrics) to an `Advanced / Platform Prompts` tab or collapsible panel.
3. **Runs & Monitor Integration**:
   * Clicking `Launch Capability Manufacturing` transitions immediately to the `Training Runs & Live Monitor` view, tracking the 8-phase progress and packet stream in real time.

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] Factory Studio lands by default on the **Capability Intake Workbench** on the main canvas.
- [ ] Operators can enter Seed Intent, Starter Objectives, and Reference Materials directly on-page without opening a modal.
- [ ] Deliverable Architecture selector is clearly visible on the workbench canvas.
- [ ] Clicking launch validates inputs, dispatches `POST /api/agent_training_factory/jobs`, and transitions seamlessly to the live monitor view.
- [ ] 8-phase prompt rubric editor relocated to an Advanced / Platform Rubrics sub-tab.
- [ ] Responsive layout: works cleanly on desktop and tablet/mobile viewports.
- [ ] Frontend unit tests for Factory Studio updated and passing in `tests/unit/frontend/factory_studio.test.js`.
- [ ] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Preserve all existing factory runner orchestration and packet logging protocols.
- No code without Jacob's explicit `build` instruction.
