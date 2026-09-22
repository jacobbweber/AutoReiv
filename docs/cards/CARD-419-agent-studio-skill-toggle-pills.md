---
id: CARD-419
title: "Agent Studio Skill Toggle Pills (Agent↔Skill Scoping Only)"
status: Done
created: 2026-09-22
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:feat
  - area:ux
  - area:studios
  - area:agents
  - area:skills
---

# [CARD-419] Agent Studio Skill Toggle Pills (Agent↔Skill Scoping Only)

> **Status**: Done  
> **Created**: 2026-09-22  
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md) (**Accepted**)  
> **Labels**: `type:feat`, `area:ux`, `area:studios`, `area:agents`, `area:skills`  
> **Parent planning**: [CARD-417](./CARD-417-three-studios-agent-skill-tools-and-developer-mediated-authoring.md)  
> **Depends on**: [CARD-418](./CARD-418-skill-studio-extract-from-factory.md) Done (Skill Studio is the skill write surface)

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine AC / UX — **no product code** |
| **`build`** | Implement on `feat/card-419-*` from `qa` |
| **`merge to qa`** | After In Review + live test |

---

## 1. Why / Intent (Beat 1)

ADR-0057 locks Agent Studio as **agent identity + skill on/off only**. Jacob prefers **toggle pills** for which skills an agent may run. Skill body / tool binding edits stay in **Skill Studio** (CARD-418).

After CARD-418, Factory still shows a display-only assigned-skills list; Agent Studio (Forge) still uses whatever allowlist chrome exists today (checkboxes / chips / mixed). Operators need one clear Agent Studio control: pill on = skill in the agent’s allowlist; pill off = removed. Tapping a pill must **not** open a skill editor.

---

## 2. What AutoReiv does now (Beat 2)

- Skill authorship lives in Skill Studio (`skill_studio.js`); Forge Inspect is read-only + **Open in Skill Studio**.
- Agent↔skill allowlist is persisted via agent pack / SQLite profile (`allowed_skill` / equivalent) — CARD-411 / ADR-0056 paths.
- Forge UI still presents skills in a form that can feel like “manage capabilities” rather than pure toggles.
- Factory thin shell still lists assigned skills for the agent brief context (display / link), not the long-term Agent Studio lever.

---

## 3. What will change (Beat 3)

1. In **Agent Studio (Forge)**, replace skill scoping chrome with **toggle pills** for available skills (platform + agent-scoped catalog as today).
2. On = skill allowed for this agent; Off = not allowed. Persist through the existing durable allowlist API (SQLite / pack projection per ADR-0056 — no new dual truth).
3. Pills are **scope-only**: no edit-runbook, no tool picker, no Save skill. Optional small link **Open in Skill Studio** beside a pill or section header for authors.
4. Align Factory’s assigned-skills strip with the same mental model (display-only + link), or remove duplicate chrome if Forge pills make it redundant — prefer one operator lever in Agent Studio.
5. Vitest for toggle → allowlist payload; hard refresh keeps pill state.

**Out of scope:** developer Build/Review mediation; Tools Studio; tier removal; Skill Studio save-path changes; storage folder redesign.

---

## 4. What dies (Beat 4)

- Agent Studio skill chips/checkboxes that open editors or imply skill authorship.
- Agent Studio **Inspect** button and the inline runbook viewer (`#studioRunbookEditor`). Skill detail stays in Skill Studio.
- Expectation that Factory assigned-skills strip is the primary place to turn skills on/off for an agent.

---

## 5. Acceptance criteria (EARS)

- **[REQ-419-001]** WHEN the operator views an agent in Agent Studio, THE SYSTEM SHALL present skill scoping as toggle pills (on/off), not as a skill editor.
- **[REQ-419-002]** WHEN a skill pill is turned on or off and the agent profile is saved (or auto-persisted per existing Forge save path), THE SYSTEM SHALL update the durable agent↔skill allowlist accordingly.
- **[REQ-419-003]** WHEN the operator activates a skill pill, THE SYSTEM SHALL NOT open Skill Studio or a runbook editor unless they explicitly use an **Open in Skill Studio** affordance.
- **[REQ-419-004]** AFTER browser refresh, THE SYSTEM SHALL show pill on/off state matching the persisted allowlist.
- **[REQ-419-005]** WHEN the operator views skills in Agent Studio, THE SYSTEM SHALL NOT present an Inspect control or an inline runbook viewer. **Open in Skill Studio** remains the control that opens the skill.

---

## 6. Verification

- Vitest: `tests/unit/frontend/card_419_skill_toggle_pills.test.js` — pill toggle updates the `allowed_skill` payload; pill activation does not open an editor; persisted allowlist restores pressed state. Related Forge/Factory studio tests stayed green.
- Durable path: pills read and write the existing agent `allowed_skill` list on profile save (`PUT/POST /api/agents`). No second store.
- Skill Studio save (`POST /api/agent_training_factory/scaffold/save`) is unchanged.
- Factory assigned-skills strip is display-only (`role="status"`) plus a separate **Open in Skill Studio** link. It is not an on/off control.
- Live test (2026-09-22): pills and Open in Skill Studio passed. Jacob then dropped Inspect from Agent Studio on this branch.
- Re-verify on Jarvis:

1. Open Agent Studio and select an agent.
2. The skills section shows toggle pills and **Open in Skill Studio**. There is no **Inspect** button and no inline runbook panel.
3. Click a pill. Skill Studio does not open. Pill state still saves with the agent.
4. Click **Open in Skill Studio** on a skill. Skill Studio opens on that skill. Skill Studio view and save are unchanged.
5. Open Factory. The allowed-skills strip still only displays the list and links to Skill Studio.
