---
id: CARD-522
title: "Capability gap 'Open in Skill Studio' opens an empty form; prefill it from the gap and steer missing-tool gaps to Ask Developer"
status: Done
completed: 2026-10-04
created: 2026-09-26
branch: feat/card-516-522-mcp-start-errors-and-gap-prefill
related:
  - CARD-496
  - CARD-497
  - CARD-418
labels:
  - type:feature
  - area:studios
  - P3
needs_decision: none
milestone: M25
---

# [CARD-522] Prefill Skill Studio from a capability gap

> **Status**: Done (2026-10-04, merged to qa from `feat/card-516-522-mcp-start-errors-and-gap-prefill`). Found by Jacob live-testing CARD-497 on serve, 2026-09-26.
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

## Built (2026-10-03, branch `feat/card-516-522-mcp-start-errors-and-gap-prefill`)
- The gap rides along: the gap row calls `openGapInSkillStudio(agentId, callbacks, gap)`, which calls `openSkillStudio(agentId, null, { gap })`; `app.js` passes it to `queueDeepLink(agentId, skillId, { gap })`. `planSkillStudioDeepLink` carries `gap` only when no skill id is given. The gap is held until a Skill Studio load finishes, so a second load cannot drop it.
- New `skill_studio/gap_prefill.js` builds the draft: name from `identified_capability` (title case, capitals kept: `inventory_lookup` becomes "Inventory Lookup"), slug from the name with Skill Studio's own `toSnakeCase` (`inventory_lookup`, not kebab case, so it matches what typing the name produces), description "<Name>. Use when the user asks for something like: \"<turn_text>\"" kept under the 200-character soft limit, intent (gap id, agent, what the user asked, the missing tool), and a starter runbook (When to use, three Steps).
- The suggested tool is ticked only when it is in the capabilities catalog. When it is not, nothing is ticked, the runbook step says the tool does not exist yet, and an amber note above the form reads "This gap needs a tool that does not exist yet (<tool>). A skill can only use existing tools: Ask Developer to build it first." with an **Ask Developer** button (the CARD-496 `askDeveloperAboutGap` path). Otherwise a blue note says "Prefilled from the capability gap <name>. Review it, then Save."
- In Agent Studio's gap list, when the suggested tool is not in the catalog the row shows "(not built yet)" and **Ask Developer** comes first as the primary button; Open in Skill Studio becomes secondary. Rows whose tool exists keep the old order.
- No clobbering: when the form already holds a name, description, intent or runbook, Skill Studio asks "Replace what is in Skill Studio now with a new skill for this capability gap? Unsaved changes will be lost." Cancel keeps the draft (toast "Kept your draft. The capability gap is still listed in Agent Studio.").
- Taken ids: Save overwrites a skill with the same id, so when the prefilled slug is already a skill (for example a gap named `diagnostics`, a shipped skill), the draft becomes "Diagnostics 2" / `diagnostics_2` and the note says which skill already exists. The general New-skill path still overwrites: CARD-628.
- The gap stays pending (Skill Studio does not change it); linking the saved skill id on the gap (optional item 4) is not built.
- app.js v2.0.107 (shared with CARD-516).
- Tests: Vitest `card_522_gap_prefill.test.js` (9: draft fields, missing tool, existing tool ticked, length and title case, taken ids, draft detection, payload, deep link, gap-row button order), CARD-496 Vitest unchanged and passing; smoke TC-51 desktop and phone (seeded gap, fields filled, note and Ask Developer shown, nothing ticked, Cancel keeps an edited draft, OK replaces it).

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| Agent Studio > AutoReiv > Capability gaps | desktop | pass | `inventory_lookup` (tool `get_tc49_inventory`, not built): "(not built yet)", buttons Ask Developer, Open in Skill Studio, Dismiss; `session_status_report` (tool `get_session_info`, exists): old order |
| Open in Skill Studio on `inventory_lookup` | desktop | pass | "Inventory Lookup" / `inventory_lookup`, description and intent from the gap, runbook starts `# Inventory Lookup`; 0 of 110 tools ticked; amber note with Ask Developer; badge "New skill from gap" |
| Ask Developer from the note | desktop | pass | Toolsmith chat opened with the gap draft (tool `get_tc49_inventory`, target autoreiv); Nemotron answered in about 21 s and asked to approve `attach_tool_to_skill` (left unapproved) |
| Open in Skill Studio on `session_status_report`, OK to replace, Save | desktop | pass | confirm text as above; `get_session_info` ticked; saved and pinned to autoreiv; `GET /api/skill_studio/skills/session_status_report` has the name, description and tools |
| Edited draft, Open in Skill Studio, Cancel | desktop | pass | name "Jacob draft in progress" kept, note hidden, toast "Kept your draft..." |
| Gap named `diagnostics` (a shipped skill), Save | desktop | pass | draft "Diagnostics 2" / `diagnostics_2` with the note; saved as a user skill; shipped `diagnostics` unchanged (source shipped, not edited) |
| Gap list, Open in Skill Studio | phone | pass | same rows; form filled, note and Ask Developer visible; `diagnostics` gap offered `diagnostics_3` once `_2` existed |

Live on :8770 (sandbox of `fb89c37a`, then `15645c26`), nemotron-3.5-lightning (Spark), 2026-10-03 11:05-11:10 PM ET. Gaps seeded through `POST /api/agents/autoreiv/gaps` (the TC49 gap from the card does not exist in the throwaway data). No console errors.

Screenshots (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003k\`): `04-desktop-agent-studio-gap-rows.png`, `05-desktop-skill-studio-prefilled-missing-tool.png`, `05b-desktop-skill-studio-prefilled-fields.png`, `06-desktop-ask-developer-chat-nemotron.png`, `07-desktop-skill-studio-prefilled-tool-ticked.png`, `08-desktop-skill-saved.png`, `09-desktop-edited-draft-kept.png`, `14-desktop-gap-renamed-to-avoid-shipped-skill.png`, `15-desktop-existing-tool-ticked.png`, `11-phone-gap-rows.png`, `12-phone-skill-studio-prefilled.png`, `13-phone-skill-studio-runbook.png`, `16-phone-gap-renamed.png`.

## Findings
- (from this build and live check, 2026-10-03; docs/findings.md)
- A New skill whose slug is already a skill id silently replaces it on Save: CARD-628.
- `POST /api/agents/{id}/gaps` accepts `context_summary` but the gap row does not keep it, so the draft's intent has only the user's words. Not carded (minor).

## Release note
"Open in Skill Studio" on a capability gap now fills in a new skill from the gap. A gap that needs a tool that does not exist yet points you to Ask Developer.

Full suite on `3ef03c3c`: pytest 2467 passed, 12 skipped (full sequential run on `f440f068`, the same code; the preflight's parallel pytest on `3ef03c3c` agrees); preflight GREEN: ruff, eslint (0 errors), vitest 1046, smoke 83/83. Earlier on this branch TC-39 (desktop) failed 5 of 8 runs (the CARD-621 flake, made more frequent here); the smoke's openGaps now reopens Agents when the restored layout minimized it, and TC-39 + TC-44 desktop passed 12 of 12.
