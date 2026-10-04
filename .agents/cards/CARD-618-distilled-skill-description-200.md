---
id: CARD-618
title: "Distilled skill descriptions are still cut to 60 characters; use the ~200 limit from CARD-614"
type: improvement
status: Done
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-618-distilled-description-not-cut]
  checks: [tests/unit/skills/test_card618_distill_description.py]
branch: feat/card-616-618-question-wait-and-distill-limit
log: {minutes: 30, qa_runs: 1, findings: 0}
created: 2026-10-03
completed: 2026-10-03
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

### Built (2026-10-03)
- `SKILL_DESCRIPTION_LIMIT = 200` and `clip_description` (one line, cut on a word boundary) live in `src/domain/skills/user_skill.py`; Skill Studio imports the limit from there.
- `distillation_service.py`: the prompt asks for "When to use this skill, at most 200 characters"; the model, fallback and frontmatter descriptions use `clip_description` instead of `[:60]`; the frontmatter value is quoted when it would break YAML (`: `, ` #`, leading indicator) and unquoted again on read.

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
| card-618 run 3: Teach Agent on a gardening chat (nemotron), Adopt | desktop | PASS | Description 199 characters, whole sentence, shown in full in the proposal and in Skill Studio (199/200). `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-3-proposal-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003h\run-3-skill-studio-desktop.png` |

## Release note
Skills made from a chat keep a description of up to about 200 characters instead of being cut at 60.
