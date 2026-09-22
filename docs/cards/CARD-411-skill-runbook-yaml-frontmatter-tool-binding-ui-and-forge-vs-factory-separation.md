---
id: CARD-411
title: "Skill Runbook YAML Frontmatter, Tool Binding UI, and Forge vs Factory Separation"
status: In Review
created: 2026-09-21
updated: 2026-09-22
adr: ADR-0056
labels:
  - type:feat
  - type:refactor
  - area:ux
  - area:skills
  - area:forge
---

# [CARD-411] Skill Runbook YAML Frontmatter, Tool Binding UI, and Forge vs Factory Separation

> **Status**: In Review  
> **Created**: 2026-09-21  
> **Decided**: 2026-09-22 — Option A, full scope (Jacob). ADR-0056 is Accepted; CARD-414 wiki/SQLite cutover is on `qa`. The old "blocked until ADR-0056" banner is retired.  
> **UX pass**: 2026-09-22 — Factory layout (assigned skills → col 1; existing-skill picker → col 2; quiet Tier; safety help). Selecting an Existing skill loads via the workshop resolver (skill store, pack skills, platform-packs, bundled seeds). Still In Review; do not mark Done until retest.  
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md) Hybrid C+  
> **Labels**: `type:feat`, `type:refactor`, `area:ux`, `area:skills`, `area:forge`  

Do not mark Done until Jacob live-tests. Do not merge to `qa` from this card's working branch until he says **merge to qa**.

---

## 1. Why / Intent (Beat 1: What Jacob Means)

Skill runbooks need structured metadata (name, description, required tools, tier, safety) instead of hand-edited YAML. Agent Studio (Forge) is for **who the agent is**. The Agent Training Factory is the **only** place that authors a skill and binds catalog tools to it.

---

## 2. What AutoReiv Does Now (Beat 2: Before this card)

- Forge `#studioRunbookEditor` saved `SKILL.md` with `PUT /api/skills/user-packs/{id}` (name, blurb, body). Frontmatter tools were not structured controls. Archive, delete, and "New runbook" also lived in Forge.
- Factory could generate and pin a skill, and it wrote `requires_tools` into AppData `pack.json` `skills[].tools`. That file was a second live binding source. `resolve_scoped_tools` read it when a skill was active.

---

## 3. What Will Change (Beat 3: Locked — Option A)

Decided 2026-09-22. Do not reopen Option B.

### Agent Studio (Forge) — identity and RBAC

- Identity prompt, model, tone, context budget, and which skills this agent may run stay here.
- **Inspect** opens a read-only runbook: name, description, tier, safety, required-tool chips, body.
- **Open in Factory Workshop** (and **Author skill in Factory**) switches to Factory and loads that skill when one is open.
- No write path for skill body, frontmatter, or `requires_tools`.

### Agent Training Factory — sole capability workshop

- Structured controls: name, description (trigger), tier (`platform` / `pack` / `user`), safety (`read_only`, `requires_hitl`, `untrusted_input_allowed`).
- **Layout (live-test UX pass 2026-09-22)**: Column 1 = agent brief + **Assigned Skills** under Role Persona (scope chips only). Column 2 = **Skill Workshop** with Existing skill picker + **+ New Skill** (one runbook at a time). Column 3 = tools/catalog + grounding. Tier is collapsed under Advanced (legacy taxonomy; does not change agent↔skill scoping). Safety checkboxes show short operator help text.
- Column 3 catalog checkboxes are the only tool multi-select. Adding or removing a tool rewrites `requires_tools` in the SKILL.md textarea. Ids that are not in the platform tool catalog are dropped in the editor and rejected by save (`400`).
- Save writes the same SKILL.md bytes to the skill store (`{data}/skills/<id>/SKILL.md`) and the agent pack home (`{data}/packs/<agent>/skills/<id>/SKILL.md`).
- Tool bindings are replaced in operational SQLite (`skill_binding_meta` + `skill_tool_bindings`). An empty tool list still writes a meta row so removals stick.
- `pack.json` may list the skill id for export identity. It does **not** store `skills[].tools` for a Factory save. If SQLite has a meta row, turn-time scoping ignores `pack.json` tools for that skill.
- Agents that have the skill (`allowed_skill`, or the skill active this turn) gain those catalog tools on the next tool resolution.

### Wireframe

```text
Forge skill row
  [x] skill-id     description
                   [ Inspect ]
  Inspector (read-only)
    Name | Description | Tier | Safety
    Required tools: [chip] [chip]
    Body (readonly)
    [ Open in Factory Workshop ] [ Validate ] [ Cancel ]

Factory column 1
  Target agent | Name | Role Persona
  Assigned Skills (active on agent)   <-- scope only, not the editor

Factory column 2
  Existing skill picker | [ + New Skill ]
  Name | Skill id | Description | Intent
  Safety (+ help) | Required tools chips
  Advanced: Tier (legacy)
  SKILL.md textarea

Factory column 3
  Catalog tool checkboxes  <-- single add/remove lever
  Grounding notes
  [ Save & Pin ] (top action bar)
```

### API

- `POST /api/agent_training_factory/scaffold/save`  
  Body adds optional `name`, `description`, `tier`, `safety`, `requires_tools`.  
  `200` `{ binding_store: "sqlite", requires_tools, skill_store_path, markdown_content, ... }`  
  `400` unknown catalog tool id or invalid tier. No skill file and no SQLite row are written.
- `GET /api/agent_training_factory/skills/{skill_id}?agent_id=`  
  Returns frontmatter plus SQLite `requires_tools` when a binding row exists (`binding_source: "sqlite"`). `404` when the runbook is missing.

### Failure modes

- Unknown tool id: save returns 400, disk and SQLite stay unchanged.
- Removing every tool: `requires_tools: []` in the file and an empty SQLite list. A stale `pack.json` tools array does not put the tool back.
- Factory workshop not initialized: Forge shows "Factory workshop is not ready yet" instead of writing the skill.

---

## 4. What Dies Today (Beat 4: The Prune List)

Executed on this branch:

- Forge **Save runbook**, **Archive**, **Unarchive**, **Delete**, and **New runbook** (`#studioRunbookSaveBtn`, `#studioRunbookArchiveBtn`, `#studioRunbookUnarchiveBtn`, `#studioRunbookDeleteBtn`, `#studioNewRunbookBtn`, `#studioNewRunbookSlug`).
- Forge `PUT /api/skills/user-packs/{id}` from the inspector, and the pre-save "save anyway?" confirm.
- Factory save writing `skills[].tools` into AppData `pack.json`.
- Turn-time use of `pack.json` tools for a skill that already has a SQLite binding row.

Still present, on purpose: `PUT /api/skills/user-packs/{id}` remains for non-Forge callers (proposals, scaffold spine). It is not an Agent Studio lever. Skill archive/delete HTTP routes remain for those callers; Forge does not call them.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-411-001] Structured Runbook Metadata UI**:
  - *Ubiquitous*: THE SYSTEM SHALL render structured metadata controls (name, description, required tools multi-select, tier, safety) when inspecting or editing a skill runbook.
  - Met: Forge inspector is read-only; Factory controls edit the same fields.
- **[REQ-411-002] Tool-to-Skill Binding Affordance**:
  - *Event-Driven*: WHEN an operator adds or removes a tool in the skill editor, THE SYSTEM SHALL automatically update `requires_tools` in the YAML frontmatter with valid catalog tool identifiers.
  - Met: picker and chips call `applyWorkshopMetadata`. Save rejects ids outside the tool registry.
- **[REQ-411-003] Single Lever Studio Alignment**:
  - *Ubiquitous*: THE SYSTEM SHALL establish a single canonical path for skill/tool modification according to the agreed division between Forge and Factory.
  - Met: Factory `POST /scaffold/save` is the writer. Forge has no save/archive/delete/new-runbook control.

---

## 6. Constraints & Verification Plan

### Automated proof

- `tests/unit/skills/test_runbook_frontmatter.py` — add/remove tools, body and `verification` preserved, unknown id raises.
- `tests/unit/web/test_card_411_factory_skill_bindings.py` — 400 does not write; save writes skill store + SQLite; `pack.json` skill row has no `tools`; stale pack.json tools do not scope; clearing tools removes them from the next `get_tools_for_agent` call.
- `tests/unit/frontend/skill_frontmatter.test.js` and `tests/unit/frontend/card_411_forge_factory_split.test.js`.

### Live test (Jacob)

1. Start serve from this branch (`feat/card-411-forge-factory-skill-bindings`). Open Agent Studio.
2. Confirm a skill row says **Inspect**, not Edit Runbook. There is no Save, Archive, Delete, or New runbook.
3. Inspect a skill. Name, description, tier, safety, and required tools are visible and not editable. **Open in Factory Workshop** lands in Factory with that skill loaded.
4. In Factory column 1: Assigned Skills sit under Role Persona (empty for a new agent). Chips are scope labels, not the editor.
5. In Factory column 2: use **Existing skill** to load a runbook, or **+ New Skill** to clear the form. Assigned Skills must not appear at the top of column 2.
6. Confirm Safety help text under each checkbox, and Tier only under **Advanced: Tier (legacy taxonomy)**.
7. Tick one catalog tool that this skill did not have. The SKILL.md box gains that id under `requires_tools`. Untick it and the id leaves the frontmatter.
8. Tick a real catalog tool, **Save & Pin Skill to Agent**.
9. Open `{data}/skills/<skill_id>/SKILL.md` and confirm `requires_tools` lists that tool. Confirm `packs/<agent>/pack.json` does not list that tool under `skills[].tools`.
10. Optional SQL: `SELECT tool_id FROM skill_tool_bindings WHERE skill_id = '<skill_id>';` returns the tool.
11. Start a chat turn with an agent that has this skill. The tool is available (or the binding is the row from step 10).

Reply **merge to qa** after that passes.
