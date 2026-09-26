---
id: CARD-522
title: "Capability gap 'Open in Skill Studio' opens an empty form; prefill it from the gap and steer missing-tool gaps to Ask Developer"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-496
  - CARD-497
  - CARD-418
labels:
  - type:feature
  - area:studios
  - P3
---

# [CARD-522] Prefill Skill Studio from a capability gap

> **Status**: Ready (found by Jacob live-testing CARD-497 on serve, 2026-09-26 ~10:50 AM ET, branch tip `9a858322`).
> **Related**: CARD-496 (REQ-496-003 added the button), CARD-497 (runbook step corrected to point at Ask Developer), CARD-418 (Skill Studio fields)
> **Labels**: `type:feature`, `area:studios`, `P3`

## Problem

Agent Studio > AutoReiv > Capability gaps > **Open in Skill Studio** opens Skill Studio pinned to the agent with every field empty: no name, slug, trigger/description, intent or runbook, and no tools ticked. The gap row already has the data (TC49 `gap_c5d4dcc6af35`: `turn_text` "Look up TC49 inventory counts", `identified_capability` `inventory_lookup`, `suggested_tool_name` `get_tc49_inventory`).

Not a CARD-497 regression. The prefill was never built:

- `forge/tools.js` `openGapInSkillStudio(agentId, callbacks)` calls `callbacks.openSkillStudio(agentId)` only; `app.js` `openSkillStudio(agentId, skillId)` and `skill_studio.js` `queueDeepLink(agentId, skillId)` have no gap payload.
- REQ-496-003 only asked to "open Skill Studio for that gap's agent". Before CARD-496, "Open Training Factory" also passed only the agent id (CARD-306); `factory.js` `applyBacklogGapToIntake` existed but was never called.
- Tests could not catch it: the CARD-496 Vitest asserts `openSkillStudio('autoreiv')`, its smoke asserts `#view-skill-studio` is visible, and TC-43 covers New skill, not gaps.
- Repro (read-only, `scratch/c497_gapopen.cjs`, desktop 1280x800 and phone 390x844): after the click, `factorySkillNameInput`, `factorySkillIdInput`, `factorySkillTriggerInput`, `factorySkillIntentInput`, `factorySkillMarkdownEditor` are all `""`, 104 tool checkboxes, 0 ticked; requests are only `GET /api/tools_studio/capabilities` and `/api/skill_studio/skills` (200).

## Change (to refine)

1. Pass the gap to Skill Studio: `openGapInSkillStudio(agentId, callbacks, gap)` calls `openSkillStudio(agentId, null, { gap })`; `queueDeepLink` carries a `draft`.
2. Prefill a **new** skill (never overwrite an open, edited draft without asking):
   - name from `identified_capability` / `missing_capability` (title case), slug from the same (kebab case);
   - description/trigger from the gap title plus `turn_text`;
   - intent and a starter runbook from `turn_text` and `context_summary`;
   - tick `suggested_tool_name` only if it exists in the capabilities catalog.
3. **Steer missing-tool gaps to Ask Developer.** When `suggested_tool_name` is set and not in the catalog, show a note in Skill Studio ("This gap needs a tool that does not exist yet (`get_tc49_inventory`). A skill can only use existing tools: Ask Developer to build it first.") with an Ask Developer button (the CARD-496 `askDeveloperAboutGap` path). In the gap row, make Ask Developer the primary button for such gaps.
4. Keep the gap pending until the skill is saved or the operator dismisses it; optionally link the saved skill id on the gap.

## Done when

- Vitest: the gap payload reaches Skill Studio; fields are prefilled; an existing draft is not clobbered; a missing suggested tool shows the Ask Developer note and does not tick anything.
- Smoke (desktop and phone): seed a gap, click Open in Skill Studio, the name/slug/description/runbook are filled.
- Live on serve with TC49 `gap_c5d4dcc6af35`.
