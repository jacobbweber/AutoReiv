---
id: CARD-618
title: "Distilled skill descriptions are still cut to 60 characters; use the ~200 limit from CARD-614"
type: improvement
status: Ready
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-618-distilled-description-not-cut]
  checks: [tests/unit/skills/test_card618_distill_description.py]
branch: feat/card-618-distilled-skill-description-200
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-614
---

# CARD-618 Distilled skill descriptions are still cut to 60 characters; use the ~200 limit from CARD-614

## Problem
CARD-614 lets a skill description be about 200 characters in Skill Studio, but skills made by distillation still get a description cut to 60 characters, so their "when to use it" text is clipped mid-word.

## Cause
`src/application/skills/distillation_service.py`: the prompt asks for "Short summary under 60 characters" (L264) and the code cuts with `[:60]` (L366, L437, L483).

## Change
- Use one shared limit (200, as in `src/web/routers/skill_studio.py` `SKILL_DESCRIPTION_LIMIT`): the prompt says at most 200 characters (when to use the skill), and the cut is at 200 on a word boundary.

## What dies
The 60-character cut in distillation.

## Proof
- Journey `card-618-distilled-description-not-cut`: distil a skill from a chat on nemotron; the description is shown in full in Skill Studio (<= 200).
- Checks: a 150-character model description is kept whole; a 300-character one is cut to <= 200 on a word boundary; the prompt says 200.

## Plan and decisions

## Findings
- (from CARD-614, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Skills made from a chat keep a description of up to about 200 characters instead of being cut at 60.
