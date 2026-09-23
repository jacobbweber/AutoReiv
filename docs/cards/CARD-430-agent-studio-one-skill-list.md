---
id: CARD-430
title: "Agent Studio one skill list"
status: Done
created: 2026-09-23
adr: docs/adr/0057-three-studios-and-developer-mediated-authoring.md
labels:
  - type:cleanup
  - area:ux
  - area:agents
  - area:skills
---

# [CARD-430] Agent Studio one skill list

> **Status**: Done
> **Created**: 2026-09-23
> **Found during**: [CARD-429](./CARD-429-classification-simplification.md)
> **ADR Reference**: [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md)
> **Parent**: [CARD-429](./CARD-429-classification-simplification.md)

Built on `feat/card-429-classification-simplification` because Jacob said **build** on that branch. Say **merge to qa** after a live look. Do not merge from this card alone.

---

## Gate language

| Jacob reply | Meaning |
| --- | --- |
| **`continue`** | Refine this card. No product code. |
| **`build`** | Done on `feat/card-429-classification-simplification` (stacked with CARD-429). |
| **`merge to qa`** | After In Review and a live test. |

---

## 1. Why / Intent (Beat 1)

Agent Studio shows the same kind of control three times: a skill the agent may run, with on and off. The three headings (Platform, Operator, Custom Agent Pack) look like three different products. Jacob wants one skill list. The folders on disk stay where they are.

---

## 2. What AutoReiv does now (Beat 2)

Assigned Skills in `src/web/templates/index.html` (`#forgeSkillsSection`) has three boxes under the OS baseline chips:

- `#forgePlatformBox` / `#forgeSkillsGrid` — platform runbooks, rendered by `renderPlatformSkills` in `src/web/static/modules/studios/forge/runbook.js`. Empty copy says “No platform runbooks in the skills data dir.” Archived skills sit in this box.
- `#forgeOperatorBox` / `#forgeOperatorSkillsGrid` — operator skill store, `renderOperatorSkills`.
- `#forgePackBox` / `#forgeRunbooksGrid` — this agent’s pack skills, `renderPackSkills`. Title text is “Custom Agent Pack Skills & Tools”.

Each row is a toggle pill (`data-home` is `platform`, `operator`, or `pack`) plus Open in Skill Studio. The allowlist write is the same pill path. OS baseline chips (`#forgeBaselineGrid`) are required tools, not skills. Direct still mounts no tools (CARD-429).

---

## 3. What will change (Beat 3)

One list inside Assigned Skills. Each row keeps its toggle and Open in Skill Studio. A short home label on the row says Platform, Operator, or Pack so Jacob can still see where the file lives. Archived rows stay in that same list, marked Archived.

Recommended: one grid, one render function that concatenates the three sources and stamps the home label. The three heading blocks go away. `data-home` stays on the row so save logic does not need a new store.

---

## 4. What dies today (Beat 4)

- The three headings and wrappers: `#forgePlatformBox`, `#forgeOperatorBox`, `#forgePackBox` (and `#forgePackBoxTitle`).
- The three empty-state paragraphs that only exist because the boxes are separate.
- Separate caption lines (“Toggle a platform skill…”, “Skill store…”, “Dedicated runbooks…”).

Kept: OS baseline chips, the allowlist, Skill Studio as the editor, and the three disk homes.

---

## 5. Acceptance criteria (EARS)

- **[REQ-430-001]** WHEN Agent Studio shows Assigned Skills THE SYSTEM SHALL list platform, operator, and pack skills in one list AND SHALL show a home label on each row.
- **[REQ-430-002]** WHEN the operator turns a skill on or off THE SYSTEM SHALL update that agent’s allowlist the same way the three boxes do today.
- **[REQ-430-003]** THE SYSTEM SHALL NOT copy a skill file between `$DATA_DIR/skills/` and `packs/<id>/skills/`.
- **[REQ-430-004]** THE SYSTEM SHALL keep the seven platform required-tool chips, AND SHALL keep Direct mounting no tools.
- **[REQ-430-005]** WHEN a home has no skills THE SYSTEM SHALL NOT show an empty box with its own heading.

---

## 6. Human verification runbook

After **build**:

1. Open Agent Studio on Developer. Assigned Skills is one list. Rows that came from the pack say Pack. Rows from the skill store say Operator. Rows from the platform skill dir say Platform.
2. Turn one skill off and on. Reload the agent. The same skills are on or off.
3. Open the pack folder and `$DATA_DIR/skills/`. Nothing moved.
4. Open Direct. The skill list can still show skills. Direct chat still mounts no tools. The seven baseline chips are still there on AutoReiv.

---

## 7. Out of scope

- Merging `$DATA_DIR/skills/` with `packs/<id>/skills/`. Blocked by [CARD-203](./CARD-203-pure-platform-skill-isolation-and-pack-boundary-guardrails.md) and [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md).
- Changing how Skill Studio saves a runbook.
- Removing the OS baseline tool chips.
- MCP servers and the credential vault cards under Agent Studio.
