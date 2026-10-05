---
id: CARD-628
title: "Skill Studio: saving a New skill whose id already exists silently replaces that skill (a shipped one is shadowed by the new copy)"
type: bug
status: In Progress
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-628-new-skill-id-taken]
  checks: [tests/unit/web/test_card628_new_skill_id_taken.py]
branch: feat/card-628-new-skill-id-taken
log: {minutes: 30, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-522
  - CARD-611
  - CARD-570
---

# CARD-628 Skill Studio: saving a New skill whose id already exists silently replaces that skill

## Problem
Found while building CARD-522 (2026-10-03). In Skill Studio, **+ New Skill** derives the read-only slug from the name (`toSnakeCase`). If that slug is already a skill id, Save writes over it with no warning:
- a shipped skill (for example typing the name "Diagnostics" gives `diagnostics`, the shipped "Platform Diagnostics & SRE"): Save writes `$DATA_DIR/skills/diagnostics/SKILL.md`, which wins over the shipped copy at load time (CARD-570), so every agent that uses `diagnostics` silently gets the new, unrelated runbook and tools;
- a user skill: its SKILL.md is overwritten.

CARD-611 stopped writes into `platform/`; it did not add a check for an id that is taken. CARD-522 avoids taken ids for gap drafts only (`<name> 2`); the general New-skill path still overwrites.

## Cause
`handleSaveSkill` (`skill_studio.js`) posts the slug to `POST /api/skill_studio/save`; `persist_workshop_skill` (`src/application/skills/workshop.py`) writes the user copy unconditionally. Neither side knows whether the form is a new skill or an edit of that id.

## Change
- Skill Studio sends whether this is a new skill; the save route refuses (409, with the existing skill's name) when a new skill's id is taken, and the form offers a free id (`<id>_2`) or opening the existing skill.
- Editing a loaded skill (including a shipped one) keeps working as today.

## What dies
New skills that silently replace a built-in or saved skill.

## Proof
- Journey `card-628-new-skill-id-taken`: New skill named "Diagnostics" on desktop and phone; Save is refused with a clear message; the shipped Diagnostics skill is unchanged; Save as `diagnostics_2` works.
- pytest: the route refuses a taken id for a new skill and accepts an edit of the same id.

## Plan and decisions
- Save payload sends `is_new`; route returns 409 with existing name + `suggested_id` (`<id>_2`).
- Form offers Use id / Open existing; editing a loaded skill still overwrites as today.

## Findings
- (from the CARD-522 build, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Skill Studio no longer lets a new skill silently replace an existing skill with the same name.
