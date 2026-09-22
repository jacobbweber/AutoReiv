---
id: CARD-418
title: "Skill Studio Extract from Factory (Lifecycle + Tool Scoping Surface)"
status: Ready
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:feat
  - area:ux
  - area:studios
  - area:skills
---

# [CARD-418] Skill Studio Extract from Factory (Lifecycle + Tool Scoping Surface)

> **Status**: Ready  
> **Created**: 2026-09-22  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (**Proposed** — Accept before **build**)  
> **Labels**: `type:feat`, `area:ux`, `area:studios`, `area:skills`  
> **Parent planning**: [CARD-417](./CARD-417-three-studios-agent-skill-tools-and-developer-mediated-authoring.md) (forks locked)  
> **Depends on**: CARD-411 Done; ADR-0057 Accepted (or Jacob explicitly **build** with Proposed risk acknowledged)

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine slice / AC — **no product code** |
| **`build`** | Implement this card on `feat/card-418-*` from `qa` after ADR-0057 Accept (preferred) |
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

## 5. Acceptance criteria (EARS)

- **[REQ-418-001]** WHEN the operator opens Skill Studio from the dock, THE SYSTEM SHALL present skill pick/create + tool scoping without requiring the Factory agent-brief column to author a skill.
- **[REQ-418-002]** WHEN Forge Inspect offers open-in-workshop, THE SYSTEM SHALL open Skill Studio and populate the selected skill fields (no Skill not found for catalog-resolvable ids).
- **[REQ-418-003]** WHEN the operator saves a skill from Skill Studio, THE SYSTEM SHALL persist body + SQLite bindings exactly as CARD-411 (no `pack.json` live tools truth).
- **[REQ-418-004]** THE SYSTEM SHALL NOT introduce a second skill write path in Forge.

---

## 6. Verification

- Vitest: Skill Studio mount / deep-link populate.
- Manual: dock → pick skill → tick tool → save → skill store + SQLite row; Forge Inspect → Open in Skill Studio.
