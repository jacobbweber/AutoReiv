---
id: CARD-515
title: "Skill Studio still renders an assigned-skills list into the removed Factory brief; Factory-named leftovers in Agent Studio"
status: Done
completed: 2026-09-29
created: 2026-09-26
branch: qa
related:
  - CARD-496
  - CARD-419
  - CARD-497
labels:
  - type:cleanup
  - area:skills
  - area:frontend
  - P3
needs_decision: none
milestone: M21
---

# [CARD-515] Skill Studio renders into the removed Factory brief; Factory-named leftovers

> **Status**: Done (in CARD-577). Built in CARD-577: dead assigned-skills render and factoryAssignedSkillChrome removed; ids renamed to studioOpenSkillStudioBtn / forge-open-skill-studio.
> **Related**: CARD-496 (removed `#view-factory`), CARD-419 (assigned-skill chrome), CARD-497 (backend rename of `factory_escalation`)
> **Labels**: `type:cleanup`, `area:skills`, `area:frontend`, `P3`

## Problem

1. **Dead render in Skill Studio.** `skill_studio.js` L76-77 looks up `#factoryCurrentSkillsList` and `#factoryAssignedSkillsCount`, and `skill_studio/skill_scope.js` `renderAssignedSkills()` (L100-148, called from `skill_studio.js` L147 and L351) fills them with `factoryAssignedSkillChrome()` rows (L70). Both elements lived only in the Factory window's agent brief, which CARD-496 removed. The lookups now return null and the function returns early, so it is harmless dead code. CARD-419 tests (`card_419_skill_toggle_pills.test.js`) still unit-test `factoryAssignedSkillChrome`.
2. **Factory-named ids for Skill Studio links in Agent Studio.** `#studioOpenFactoryBtn` / `data-testid="forge-open-factory"` (`index.html` L1633, `forge/runbook.js` L276-291) is the "Author skill in Skill Studio" button. The label is right; only the id and test id say Factory.
3. **Old names.** `data-section="needs-training-backlog"` on `#agentTrainingBacklogCard` (`index.html` L1342) and the docstring "Capability Gaps & Needs Training Backlog" in `src/domain/orchestration/capability_gaps.py` L2. The on-screen label is already "Capability gaps" (CARD-496 D4).

## Change

- Delete `renderAssignedSkills`, `factoryAssignedSkillChrome` and the two lookups, and update the CARD-419 tests. Agent Studio's skill pills (CARD-419) remain the one place to see and toggle assigned skills.
- Rename `#studioOpenFactoryBtn` / `forge-open-factory` to Skill-Studio names (for example `#studioOpenSkillStudioBtn` / `forge-open-skill-studio`) and update tests.
- Rename `data-section` to `capability-gaps` (check CSS/tests first) and fix the docstring.
- Keep Skill Studio's editor `factory*` ids (ADR-0060 D5) and the `/api/agent_training_factory/*` Skill Studio routes until CARD-497.

## Done when

No frontend code writes into elements that do not exist; no Agent Studio id or test id says Factory; the Skill Studio editor ids and routes are unchanged; Vitest and smoke pass.

## Log
- 2026-09-29: Built in CARD-577: dead assigned-skills render and factoryAssignedSkillChrome removed; ids renamed to studioOpenSkillStudioBtn / forge-open-skill-studio.
- 2026-09-29: Done with CARD-577 (merged into qa).
