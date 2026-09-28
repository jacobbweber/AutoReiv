---
id: CARD-418
title: "Skill Studio Extract from Factory (Lifecycle + Tool Scoping Surface)"
status: Done
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:feat
  - area:ux
  - area:studios
  - area:skills
---

# [CARD-418] Skill Studio Extract from Factory (Lifecycle + Tool Scoping Surface)

> **Status**: Done
> **Created**: 2026-09-22  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (**Accepted** — Accept before **build**)  
> **Labels**: `type:feat`, `area:ux`, `area:studios`, `area:skills`  
> **Parent planning**: [CARD-417](./CARD-417-three-studios-agent-skill-tools-and-developer-mediated-authoring.md) (forks locked)  
> **Depends on**: CARD-411 Done; ADR-0057 Accepted

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine slice / AC — **no product code** |
| **`build`** | Implement this card on `feat/card-418-*` from `qa` after ADR-0057 Accepted |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

Promote today’s Factory **column 2 (skill workshop) + column 3 (tools/grounding)** into a first-class **Skill Studio** dock window so skill lifecycle and tool scoping have a single home. Agent brief / assigned-skill pills stay out of this studio (Agent Studio owns agent↔skill toggles in a later card).

This is slice 1 of ADR-0057 / CARD-417 build order. It does **not** implement developer mediation, Agent pills, or Tools Studio.

---

## 2. What AutoReiv does now (Beat 2)

- Factory (`studios/factory.js`, `index.html`) is a three-column scaffolder: agent brief + assigned skills (col 1), Existing skill picker + metadata + SKILL.md (col 2), tool catalog + grounding (col 3).
- CARD-411: save writes skill store + SQLite `skill_tool_bindings`; Forge Inspect opens Factory workshop.
- Dock still launches “Factory,” not “Skill Studio.”

---

## 3. What will change (Beat 3)

1. Add **Skill Studio** as an Agent Desktop window/dock entry (label: Skill Studio). Reuse Factory workshop modules (`skill_scope.js`, `workshop_meta.js`, tool catalog UI) as the Skill Studio body — col 2+3 behavior without requiring agent-brief editing on that screen.
2. **Deep links**: Forge **Open in Factory Workshop** becomes **Open in Skill Studio** (same load-by-skill-id path).
3. Factory window: either (a) become an alias/redirect to Skill Studio for skill work, or (b) remain temporarily with agent brief only + link “Edit skills in Skill Studio.” Prefer (a) or thin shell to avoid two write UIs. Document the chosen cutover in the card during build.
4. Preserve CARD-411 invariants: SQLite sole binding writer; Existing skill resolve; safety help; tier Advanced.
5. Vitest for dock open + deep-link hydrate; no regression on save bindings.

**Out of scope:** Agent toggle pills; developer Build/Review job; Tools Studio; tier removal; storage folder redesign.

---

## 4. What dies (Beat 4)

- Long-term expectation that skill authorship only exists inside the all-in-one Factory scaffolder.
- Duplicate skill-edit entry points that write bindings outside Skill Studio / CARD-411 APIs.

---

## Cutover (chosen during build)

**Thin Factory shell.** Factory stays on the dock for the agent brief and the display-only assigned-skills list (CARD-411 column 1). Skill pick/create, metadata, tool scoping, generate, and save live only in Skill Studio. Factory’s action bar is **Edit skills in Skill Studio**.

An alias that turned the Factory dock into Skill Studio was not used. The agent brief is not a skill write UI, and Agent Studio does not own it yet. Keeping the brief on Factory does not add a second binding writer.

What died in this slice:

- Factory columns 2 and 3 as an editor on the Factory screen
- Forge labels **Open in Factory Workshop** and **Author skill in Factory**
- `window.openFactoryWorkshopForSkill` (Forge calls `openSkillStudio`)
- Save requiring the agent-brief column. With no agent id, save still writes the skill store and SQLite and does not pin a pack.

## 5. Acceptance criteria (EARS)

- **[REQ-418-001]** WHEN the operator opens Skill Studio from the dock, THE SYSTEM SHALL present skill pick/create + tool scoping without requiring the Factory agent-brief column to author a skill.
- **[REQ-418-002]** WHEN Forge Inspect offers open-in-workshop, THE SYSTEM SHALL open Skill Studio and populate the selected skill fields (no Skill not found for catalog-resolvable ids).
- **[REQ-418-003]** WHEN the operator saves a skill from Skill Studio, THE SYSTEM SHALL persist body + SQLite bindings exactly as CARD-411 (no `pack.json` live tools truth).
- **[REQ-418-004]** THE SYSTEM SHALL NOT introduce a second skill write path in Forge.

---

## 6. Verification

- Vitest: `tests/unit/frontend/card_418_skill_studio.test.js` (dock open, deep-link hydrate, Factory is not a second writer).
- Pytest: `tests/unit/web/test_card_418_skill_studio_save.py` and CARD-411 binding test stay green.
- Manual live test (say **merge to qa** only after this):

1. Start the app and open the Agent Desktop dock.
2. Click **Skill Studio**. The window shows the existing-skill picker, **+ New Skill**, metadata, SKILL.md, and the tool catalog. It does not show the Factory agent-brief fields.
3. Pick a catalog skill. Name, description, and required tools fill in. You do not see “Skill not found”.
4. Tick one catalog tool and click **Save skill**. The skill store `SKILL.md` updates and `skill_tool_bindings` has that tool. `pack.json` does not gain a tools list for the skill.
5. In Agents, inspect a skill and click **Open in Skill Studio**. Skill Studio opens with that skill loaded.
6. Open **Factory**. You see the agent brief and assigned skills, plus **Edit skills in Skill Studio**. Factory has no save button for the runbook.
