---
id: CARD-386
title: "3-Column Agent and Skill Scaffolder and Capabilities Workshop"
status: In Review
created: 2026-09-20
adr: none
labels:
  - type:feature
  - domain:factory
  - domain:skills
  - domain:tools
  - domain:agents
---

# [CARD-386] 3-Column Agent and Skill Scaffolder and Capabilities Workshop

> **Status**: In Review  
> **Created**: 2026-09-20  
> **ADR Reference**: ADR-0048, ADR-0052  
> **Labels**: `type:feature`, `domain:factory`, `domain:skills`, `domain:tools`, `domain:agents`

---

## 1. Why / Intent (Beat 1)

### What Jacob Means
Jacob wants to replace the high-friction, failure-prone 8-phase synthetic code factory with an intuitive, unified **Capabilities & Scaffolding Workshop**.

Instead of an LLM trying to compile synthetic Python tool code from scratch through rigid waterfall phases (Ground $\rightarrow$ Blueprint $\rightarrow$ Author $\rightarrow$ Verify $\rightarrow$ Optimize $\rightarrow$ Promote), the system must acknowledge that:
1. **Tools are external capabilities**: Tools already exist (either as built-in primitives or external MCP servers like Blender with 24 tools). They sit dormant in the registry until an agent possesses a skill that requires them.
2. **Skills are procedural runbooks**: Skills are `SKILL.md` SOP playbooks (Matt Pocock standard) that teach an agent *how, when, and in what order* to sequence tools (or pure knowledge with zero tools).
3. **Scaffolding applies to New OR Existing Agents**: When Jacob selects an existing agent (like `autoreiv` or `coder`), he can immediately author new skills for that specialist. Saving a skill automatically pins it as active for that agent, which is immediately visible and toggleable in Agent Studio.

---

## 2. What AutoReiv Does Now (Beat 2)

- The Factory Studio (`#view-factory` in `index.html` and `factory.js`) is coupled to an 8-phase synthetic tool compiler.
- It attempts to invent raw Python tools from vague intents, resulting in timeouts (210s), guessing with `curl.exe`, and generating dummy boilerplate wiki files.
- It is disconnected from existing agents: you cannot open Factory, pick an existing agent (like `autoreiv`), and scaffold a new skill directly for it.
- There is no live inspection of dormant tools (like connected MCP servers) during skill authoring, forcing manual guesswork.
- Newly authored skills require complex promotion steps instead of auto-pinning directly to the target agent pack.

---

## 3. What Will Change (Beat 3)

### 3.1 Backend: Scaffolding & Capabilities API (`src/web/routers/agent_training_factory.py`)
1. **`GET /api/agent_training_factory/capabilities`**:
   - Queries `ScopedToolRegistry` to list all registered tools and connected MCP servers.
   - Groups capabilities into namespaces: `MCP Tools` (e.g. `mcp:blender`), `Platform Optional Tools` (`wiki`, `sandbox`, `worker`), and `Built-in Tools`.
   - Returns tool names, parameter schemas, and descriptions for grounding.
2. **`POST /api/agent_training_factory/scaffold/runbook`**:
   - Accepts: `agent_id`, `skill_id`, `skill_name`, `trigger_description` (<=60 chars), `intent_notes`, `selected_tools` (schemas), and `source_context` (documentation/cheat sheets).
   - Uses the LLM to generate a compliant Matt Pocock standard `SKILL.md` runbook with YAML frontmatter (`name`, `description`, `requires_tools`) and sequential procedure steps.
3. **`POST /api/agent_training_factory/scaffold/save`**:
   - Writes the `SKILL.md` to `packs/<agent_id>/skills/<skill_id>/SKILL.md`.
   - If the agent is new, creates the pack directory and initial `pack.json`.
   - Appends `<skill_id>` to the agent's `allowed_skill` list in `pack.json` (auto-pinning it).
   - Triggers `AgentPackService` cache reload so the new skill is immediately active.

### 3.2 Frontend: 3-Column Workshop UI (`#view-factory` in `index.html` & `factory.js`)
Transform `#view-factory` into a 3-column split view:

```
+---------------------------------------------------------------------------------------------------+
| CAPABILITIES & SCAFFOLDING WORKSHOP                                                               |
+------------------------------------+--------------------------------+-----------------------------+
| COLUMN 1: AGENT BRIEF              | COLUMN 2: SKILLS & RUNBOOK     | COLUMN 3: CAPABILITIES &    |
|                                    |                                |           SOURCE CONTEXT    |
| [ Select Agent: autoreiv v ]       | [ Current Assigned Skills ]    | [ Capabilities Inspector ]  |
| - or [+ New Agent]                 |   - wiki (active)              |   [x] Blender MCP (24 tools)|
|                                    |   - coding (active)            |   [ ] Wiki Vault (8 tools)  |
| Agent ID: autoreiv                 |                                |   [ ] Sandbox (1 tool)      |
| Display Name: AutoReiv Host        | [+ Author New Skill]           |                             |
| Role Persona / System Prompt:      | - Skill Name: 3D Scene Builder | [ External Source Context ] |
| [ Enter prompt instructions... ]   | - Trigger: <60 chars trigger   | [ Paste API docs, cheat     |
|                                    | - Operator Intent / Notes:     |   sheets, command examples] |
| Default Model: [ gemini-2.5-pro v] |   [ What this skill does... ]  |                             |
|                                    |                                |                             |
|                                    | [ ✨ Generate Runbook ]         |                             |
|                                    | [ Live SKILL.md Editor/Preview]|                             |
|                                    | [ 💾 Save & Pin to Agent ]     |                             |
+------------------------------------+--------------------------------+-----------------------------+
```

### 3.3 Seamless Bridge to Agent Studio
- When a skill is saved in the Factory, it is automatically pinned to that agent's `allowed_skill` list.
- Navigating to Agent Studio immediately shows the new skill under that agent's skill list with its toggle switch ON.

---

## 4. What Dies Today (The Prune List - Beat 4)

1. **Obsolete 8-Phase Synthetic Compiler UI**:
   - Delete legacy 8-phase flowchart SVG/HTML in `index.html` (`#factoryPhasePipeline`, `#factoryFlowchartContainer`).
   - Delete question battery modal and obsolete step-instruction editor modal in `index.html`.
   - Delete legacy delivery diff editor (`#factoryTabDiffBtn`, `#factoryTabToolBtn`).
2. **Dead Code in `factory.js`**:
   - Prune legacy 8-phase polling routines (`pollJob`, `refreshPackets`, `renderFlowchart`, `renderQuestionBattery`).
   - Prune obsolete synthetic tool compilation event listeners.
3. **Dead Endpoints in `agent_training_factory.py`**:
   - Retire the fallback synthetic tool compilation path that forcibly flipped deliverable type from skill to native tool.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL provide a 3-Column Capabilities & Scaffolding Workshop in `#view-factory`.
- **Event-Driven**: WHEN the user selects an existing agent in Column 1, THE SYSTEM SHALL populate Column 1 with that agent's metadata and display their currently assigned skills in Column 2.
- **Event-Driven**: WHEN the user clicks `[+ New Agent]` in Column 1, THE SYSTEM SHALL clear the fields and allow authoring a brand-new agent pack.
- **Event-Driven**: WHEN the user opens the Capabilities Inspector in Column 3, THE SYSTEM SHALL list all live registered tools and connected MCP servers with their tool counts.
- **Event-Driven**: WHEN the user clicks `[✨ Generate Runbook]`, THE SYSTEM SHALL invoke `/api/agent_training_factory/scaffold/runbook` with the selected tools and source context, generating a valid Matt Pocock compliant `SKILL.md` (trigger <= 60 chars, clear procedural steps).
- **Event-Driven**: WHEN the user clicks `[💾 Save & Pin to Agent]`, THE SYSTEM SHALL write the `SKILL.md` to disk, append the skill ID to the agent's `pack.json`, reload the runtime agent pack cache, and return a success confirmation.
- **State-Driven**: WHILE viewing the agent in Agent Studio, THE SYSTEM SHALL display the newly saved skill in that agent's skill list with its active toggle set to ON.
- **Negative Assertion**: Automated tests shall explicitly assert that the scaffolder does NOT invoke synthetic Python tool code compilation or write arbitrary code stubs when authoring skills.
- **Negative Assertion**: Automated tests shall verify that saving a skill to an existing agent does NOT overwrite or delete existing skills in `pack.json`.

---

## 6. Constraints & Verification Plan

### Automated Tests
- Unit tests in `tests/unit/agent_training_factory/test_scaffolder_endpoints.py`:
  - Test `GET /api/agent_training_factory/capabilities` returns registered tools and MCP tools.
  - Test `POST /api/agent_training_factory/scaffold/runbook` produces valid YAML frontmatter and markdown body.
  - Test `POST /api/agent_training_factory/scaffold/save` writes `SKILL.md`, pins to `pack.json`, and preserves existing skills.
- Integration tests in `tests/integration/factory/test_scaffolder_lifecycle.py`:
  - Test end-to-end scaffolding for an existing agent (e.g. `autoreiv`).
  - Test end-to-end scaffolding for a net-new agent pack.
- Frontend verification:
  - `npm run lint:frontend` passes with 0 errors and 0 warnings.
  - Verify 3-column layout renders correctly in browser.

### Manual Verification Runbook
1. Open AutoReiv serve (`http://127.0.0.1:8000`).
2. Switch to Factory tab (`#tab-factory`).
3. Select `autoreiv` from the Agent Dropdown in Column 1. Observe Column 1 and 2 populate.
4. In Column 3, inspect connected capabilities. Select an MCP or platform tool.
5. In Column 2, click `[+ Author New Skill]`, type Name: `Test Scaffolder Skill`, Intent: `Verify runbook generation`.
6. Click `[✨ Generate Runbook]`. Observe generated `SKILL.md`.
7. Click `[💾 Save & Pin to Agent]`.
8. Switch to Agent Studio tab (`#tab-agents`), inspect `autoreiv`, and verify `test-scaffolder-skill` is present and toggled ON.
