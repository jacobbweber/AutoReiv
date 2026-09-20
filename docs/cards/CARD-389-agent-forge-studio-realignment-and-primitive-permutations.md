---
id: CARD-389
title: "Agent Forge Studio Realignment and Primitive Permutations"
status: Ready
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:forge
  - domain:agents
  - area:web
---

# [CARD-389] Agent Forge Studio Realignment and Primitive Permutations

> **Status**: Ready  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:forge`, `domain:agents`, `area:web`  

---

## 1. Why / Intent (Beat 1)

Outside of Factory Studio (which scaffolds agents and skills via a 3-column workshop), operators need to author, inspect, and configure agents directly in **Agent Forge Studio** (`#view-forge`).

In our architectural realignment discussions (detailed in Part 1 of `D:\Projects\research\autoreiv-architecture-realignment-conways-law-and-autonomic-os.md`), we formalized the 4 foundational permutations of the Agent Primitive Matrix:
1. **Agent without Skills or Tools**: A pure conversational reasoner, tone translator, or brainstorming partner (relies solely on pre-trained parametric weights and system prompts).
2. **Agent with Skills without Tools**: A strategic advisor or SOP compliance auditor (operates strictly on procedural rules and guidelines without external environmental mutation).
3. **Agent with Tools without Skills**: A low-level executor given atomic primitives without prescribed SOP runbooks (composes tools dynamically via ReAct).
4. **Agent with Skills bundling Tools**: A cohesive operational unit where the skill provides the domain procedure and declares the necessary tools.

Currently, Agent Forge Studio has accumulated legacy complexity (3,500+ lines in `forge.js`), lingering packet-feed viewers, and outdated workflows that obscure these 4 clean combinations. Jacob wants Forge Studio realigned to this 3-primitive model with a clear, modern editing surface.

---

## 2. What AutoReiv Does Now (Beat 2)

1. `src/web/static/modules/studios/forge.js` exceeds 3,500 lines and contains legacy artifacts from earlier iterations (packet feed viewers, compiler tabs, fragmented tool accordions).
2. Creating an agent without tools or skills, or creating a skills-only advisory agent, feels unnatural in the current UI because validation and layout expect both or default to heavy tool sets.
3. The boundary between Agent Forge Studio (direct agent configuration) and Factory Studio (scaffolding and training) has blurred, leading to duplicate tabs and controls.

---

## 3. What Will Change (Beat 3)

1. **Modernized Agent Forge Layout**:
   - Clean, unified agent editor with identity fields: Display Name, auto-generated `readonly` `snake_case` Slug, System Prompt, Purpose (Fast, Reasoning, Coding, Vision, Task, Auxiliary), and Default Provider/Model.
   - Distinct, unentangled capability panels:
     - **Panel 1: Assigned Skills ("Brain / SOPs")**: Searchable checklist of available `SKILL.md` runbooks with description tooltips and an "Inspect Runbook" drawer.
     - **Panel 2: Assigned Tools ("Hands / Syscalls")**: Searchable checklist of atomic callable tools (platform + MCP).
2. **First-Class Permutation Presets**:
   - Add a quick permutation selector:
     - `[ 💬 Conversational Reasoner ]` (Clears tools and skills; focuses on system prompt).
     - `[ 📋 Procedural Auditor ]` (Enables skills selection; zero tools).
     - `[ ⚡ Direct ReAct Executor ]` (Enables tools selection; zero skills).
     - `[ 🛠️ Specialist Operator ]` (Enables both skills and tools).
3. **Monolith Decomposition & Scavenger Pass**:
   - Split `forge.js` or excise dead compiler/packet code, ensuring single-lever persistence via `POST /api/agents` and `PUT /api/agents/{id}`.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Delete dead packet feed formatting helpers in `forge.js` (`formatLabPacketFeedLines`, `collectPacketArtifacts`).
- Remove obsolete training and compiler tabs inside Forge that duplicate Factory Studio.
- Excise old nested tool accordions inside skill rows.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-389-001] (Ubiquitous)**: THE SYSTEM SHALL allow creating and saving an agent with any of the 4 primitive permutations (no tools/skills, skills-only, tools-only, skills+tools) without validation errors.
- **[REQ-389-002] (Event-Driven)**: WHEN an operator enters an agent display name in Agent Forge, THE SYSTEM SHALL auto-generate a valid `snake_case` slug in the readonly slug input.
- **[REQ-389-003] (Event-Driven)**: WHEN an operator selects a permutation preset, THE SYSTEM SHALL automatically configure the skills and tools panels to match that permutation.
- **[REQ-389-004] (State-Driven)**: WHILE an agent is configured as "skills-only", THE SYSTEM SHALL persist empty `allowed_tool_names` and the selected `allowed_skills` without injecting default tools.
- **[REQ-389-005] (Negative Assertion)**: Automated tests shall explicitly assert that saving an agent in Forge does NOT require tools if only skills are selected, and does NOT require skills if only tools are selected.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-389-agent-forge-realignment` cut from `qa`.
- Unit tests: `tests/unit/frontend/forge_agent_select.test.js`, `tests/unit/web/test_agent_forge_api.py`.
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/sdd-workflow/scripts/preflight.py`.
