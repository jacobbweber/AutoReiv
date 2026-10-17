---
id: CARD-697
title: "Exercise and harden end-to-end self-development on AutoReiv"
type: feature
status: Ready
priority: P2
milestone: M29
needs_decision: none
proof:
  journeys: [card-697-exercise-and-harden-end-to-end]
  checks: [tests/unit/skills/test_card697_self_development_skills.py]
branch: feat/card-697-exercise-and-harden-end-to-end
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-16
---

# CARD-697 Exercise and harden end-to-end self-development on AutoReiv

## Intent
Exercise `AutoReiv`'s consolidated `project-cards` and `software-development` Agora skills end-to-end inside the running app, review any friction or gaps encountered during the self-development workflow, and harden the skills and tools based on those findings.

## Goal
`AutoReiv` can manage projects (`create_project`, `detect_drift`, `align_project`), pick and plan a card via `project-cards`, implement and test a change via `software-development` (`run_project_checks`, `run_journey`), and move a card to `In Review` smoothly from Chat and Projects Studio.

## Change
- Bind `create_project`, `detect_drift`, and `align_project` into `platform/skills/project-cards/SKILL.md` (`docs/findings.md` M25).
- Exercise the full self-development flow (`project-cards` + `software-development`) through `AutoReiv` in Chat against a throwaway project/card, identify friction points (tool schemas, prompt instructions, error reporting, or Projects Studio integration), and fix them directly on this card.
- Update `docs/findings.md` to remove resolved self-development items.

## What dies
- Unbound project management tools (`create_project`, `detect_drift`, `align_project` finding in `docs/findings.md`) and any self-development workflow friction discovered during live execution.

## Proof
- Journey `card-697-exercise-and-harden-end-to-end`:
  1. In Chat, have `AutoReiv` load `project-cards` and `software-development` via `skill_view`, inspect project cards/drift, edit a target file and test in an isolated project workspace, run `run_project_checks`, and update the card status.
  2. Verify the updated card and project state in `#view-projects` on desktop and phone.
- Checks:
  - `tests/unit/skills/test_card697_self_development_skills.py`

## Plan and decisions
- Technical only (`needs_decision: none`).

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- Bound project alignment tools into `project-cards` and hardened `AutoReiv`'s end-to-end self-development workflow across Chat and Projects Studio [CARD-697].
