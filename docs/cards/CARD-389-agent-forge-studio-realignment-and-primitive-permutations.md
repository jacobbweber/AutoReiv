---
id: CARD-389
title: "Uniform Skill-First Architecture and Agent Forge Realignment"
status: Ready
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:forge
  - domain:agents
  - domain:skills
  - area:web
---

# [CARD-389] Uniform Skill-First Architecture and Agent Forge Realignment

> **Status**: Ready  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:forge`, `domain:agents`, `domain:skills`, `area:web`  

---

## 1. Why / Intent (Beat 1)

In our architectural realignment, we resolved two fundamental principles for managing agents and capabilities outside the Factory:

1. **Uniform Skill-First Capability Architecture (Zero Naked Tools)**:
   - Handing raw, un-runbooked tools to an LLM is an anti-pattern: the model has no Standard Operating Procedure (SOP) explaining when to invoke them, what order to use, or how to verify outcomes.
   - Tools (Python callables and MCP tools) can exist in the registry, but they are **never mounted directly or looked up directly**. Every capability requires a `SKILL.md` runbook declaring `requires_tools: [...]`.
   - The only tools always active in context are the lightweight **Platform Required** primitives (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `lookup_agents`, `get_session_info`).
   - In Agent Forge Studio, operators configure agents by selecting **Skills** ("Brain & SOPs"), which automatically mount their declared tools ("Hands").

2. **Unified Agent Pack Sovereignty & Display Names**:
   - Retire the artificial "Platform Pack vs Custom Pack" dichotomy. Everything in `$DATA_DIR/packs/<id>/` is simply an **Agent Pack**.
   - An operator can freely edit the **Display Name** (`agent.name`) of *any* agent in Forge Studio (custom or seeded) to personalize the application, while the backend immutably preserves the **Slug** (`agent.id`) for storage, database names, and routing.

3. **Specialty Database Architecture (`<slug>_storage.db`)**:
   - Every agent always gets its own `<agent>_memory.db` for universal episodic facts.
   - For domain specialists that manage structured records (e.g. Finance, Inventory), Forge provides an explicit toggle: `[x] Dedicated Storage Database (<slug>_storage.db)`.
   - Enabling storage automatically binds the Tier 1 **`sqlite-storage`** skill runbook (providing `query_agent_database`, `execute_agent_database` and SQL guardrails) and allows assigning a Tier 2 **Domain Schema Runbook** (e.g. `personal-finance-ledger`).

---

## 2. What AutoReiv Does Now (Beat 2)

1. `src/web/static/modules/studios/forge.js` exceeds 3,500 lines and exposes confusing raw tool checklists that let operators check off naked tools with no runbooks.
2. In `src/web/routers/agents.py`, `AgentCustomization` omits `name` for `is_builtin` agents, blocking operators from customizing the display names of seeded agents.
3. `storage_enabled` exists as an ad-hoc boolean that quietly injects naked SQL tools without binding the `sqlite-storage` SOP runbook or linking a domain schema.
4. Legacy packet feeds, training compiler tabs, and dead shadow functions clutter the Forge interface.

---

## 3. What Will Change (Beat 3)

1. **Skill-First Capability Configuration**:
   - Replace the raw tool checkbox grid in Agent Forge with an **Assigned Skills** checklist.
   - Selecting a skill displays its description and declared tool chips (`3 tools: read_project_file, write_project_file, git_status`).
   - Agents cleanly divide into two archetypes:
     - **Conversational Agent**: Zero skills assigned (pure prompt reasoning, tone translation, counseling).
     - **Capability Agent**: Assigned domain skills with their declared tools.
2. **Display Name Customization & Readonly Slug**:
   - In Agent Forge, `#forgeNameInput` allows editing `name` for any agent.
   - `#forgeIdInput` is strictly `readonly` for existing agents to prevent broken file/database references.
   - Update `PUT /api/agents/{id}` and `AgentCustomization` to persist `name` across all agents.
3. **Specialty Storage Database Toggle**:
   - Add checkbox in Agent Forge: `[x] Dedicated Storage Database (<slug>_storage.db)`.
   - When checked:
     - Manifest sets `storage_enabled: true`.
     - Automatically attaches the Tier 1 `sqlite-storage` skill runbook.
     - Surfaces a selector for Tier 2 Domain Schema Runbooks.
4. **Codebase Hygiene & Dead Code Pruning**:
   - Excise dead packet feed formatters (`formatLabPacketFeedLines`, `collectPacketArtifacts`) and obsolete compiler tabs from `forge.js`.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Delete raw naked-tool checklists in Agent Forge Studio.
- Excise `is_builtin` blocking logic in `src/web/routers/agents.py` that ignored display name updates.
- Delete obsolete training packet feed helpers in `forge.js`.
- Remove legacy compiler tab leftovers inside Agent Forge.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-389-001] (Ubiquitous)**: THE SYSTEM SHALL configure agent capabilities strictly through assigned `SKILL.md` runbooks, mounting only declared tools when a skill is active.
- **[REQ-389-002] (Event-Driven)**: WHEN an operator updates an agent's display name in Agent Forge, THE SYSTEM SHALL persist the new name and display it across all UI dropdown pickers while preserving the immutable `id` slug.
- **[REQ-389-003] (Event-Driven)**: WHEN an operator enables `storage_enabled` on an agent, THE SYSTEM SHALL automatically bind the `sqlite-storage` skill runbook to that agent.
- **[REQ-389-004] (State-Driven)**: WHILE an agent is configured with zero skills, THE SYSTEM SHALL mount only the Platform Required primitives during chat turns, avoiding all unneeded tool schemas.
- **[REQ-389-005] (Negative Assertion)**: Automated tests shall explicitly assert that naked tools without a companion `SKILL.md` runbook cannot be bound to an agent, and that updating an agent's display name does NOT alter its underlying directory or database slug.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-389-agent-forge-realignment` cut from `qa`.
- Unit tests: `tests/unit/frontend/forge_agent_select.test.js`, `tests/unit/web/test_agent_forge_api.py`.
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/sdd-workflow/scripts/preflight.py`.
