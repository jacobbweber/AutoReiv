# [CARD-350] Agent Forge: Decouple Tools and Skills UI & Scoping

> **Status**: Done  
> **Created**: 2026-09-17  
> **Spec Reference**: `docs/adr/0052-skill-and-tool-scoping-and-specialist-dispatch.md`, CARD-339  
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Frontend`, `domain:tools`, `domain:skills`  

---

## 1. Locked Decisions (from Jacob)

1. **Forge Studio Layout (Option B)**: Two full-width stacked sections — Allowed Skills on top, Allowed Tools directly below it.
2. **Skill-to-Tool Helper Affordance (Option A)**: When an operator checks a Skill (or clicks the helper), a subtle helper button/link (*"Select recommended tools"*) checks recommended domain tools for convenience without locking or entangling them.
3. **Platform Primitives Presentation (Option A)**: Display the 4 mandatory platform primitives (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `get_session_info`) in a locked, read-only "Platform Required (Always Active)" chip group at the top, leaving the tool checklist focused on domain tools.

---

## 2. Three Beats

### Beat 1: What Jacob means
In Agent Forge, tools and skills must be treated as independent peer primitives. Tools are callable functions ("hands"), and skills are procedural SOP runbooks ("brain"). The operator must be able to configure an agent's tool permissions and skill runbooks separately. Tools must not be nested inside skill dropdown accordions, and agents must strictly receive only the tools and skills explicitly assigned to them, preventing context bloat and permission leaks.

### Beat 2: What AutoReiv does now
* In `src/web/static/modules/studios/forge.js`, tools are rendered *inside* each skill row within an expandable accordion (`<div class="forge-skill-tools">`).
* In `schema.py`, `PLATFORM_SKILL_TOOLS` hardcodes static lists of tools per skill ID.
* This visual presentation makes it look like skills own tools. Operators cannot easily see the agent's total tool inventory at a glance without expanding multiple skill rows.

### Beat 3: What will change
1. **Agent Forge UI Refactor (`forge.js`, `templates/index.html`)**:
   * Remove the nested `<div class="forge-skill-tools">` accordion from skill rows.
   * Split the agent capability configuration area into two clear, peer panels:
     * **Panel A: Allowed Tools ("Hands")**: Searchable list/grid of all registered tools (platform native + discovered MCP). Each tool card displays its name, category, short description, and permission checkbox.
     * **Panel B: Allowed Skills ("Brain")**: List of available `SKILL.md` runbooks with checkboxes, descriptions, and an "Edit Runbook" button.
2. **Independent Agent Permissions**:
   * Agent manifest (`pack.json`) and agent API payload continue to maintain separate, independent arrays: `allowed_tool_names` and `allowed_skills`.
   * Saving an agent persists tool permissions without requiring a skill binding, and vice versa.
3. **Context Window Protection (Dynamic Scoping)**:
   * Maintain the CARD-339 / ADR-0052 two-layer scoping engine in `src/application/agent_packs/schema.py`:
   * Tools not ticked on the agent are **never** visible to the model and can never be invoked.
   * On any given turn, the model only carries the ~4 platform primitives plus the active domain tools, keeping prompt overhead under ~1,200 tokens (<10% of context).

---

## 3. Acceptance Criteria (Definition of Done)

- [x] Agent Forge configuration tab renders two distinct, unnested panels: **Allowed Tools** and **Allowed Skills**.
- [x] Tools are no longer nested as children inside skill accordion rows.
- [x] Ticking a tool grants that tool to the agent independently of any skill.
- [x] Ticking a skill grants that runbook to the agent independently of tool checkboxes.
- [x] Saving an agent updates `allowed_tool_names` and `allowed_skills` correctly via `/api/agents/{id}`.
- [x] Agent turn execution verifies that unticked tools are never mounted in context schemas.
- [x] Frontend tests in `tests/unit/frontend/forge_platform_skills.test.js` and `forge_allowlist.test.js` updated and passing.
- [x] Zero regressions in backend agent pack service tests.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Strict RBAC: No agent may ever receive tools not explicitly granted to it.
- No code without Jacob's explicit `build` instruction.
