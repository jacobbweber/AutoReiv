---
id: CARD-614
title: "Skill Studio cuts a skill description to 60 characters on load; relax to about 200 and show the full text"
type: improvement
status: In Review
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-614-long-skill-description]
  checks: [tests/unit/web/test_card614_skill_description_limit.py, tests/unit/frontend/card_614_skill_description_limit.test.js]
branch: feat/card-612-613-614-reply-honesty
log: {minutes: 45, qa_runs: 1, findings: 1}
created: 2026-10-03
related:
  - CARD-611
  - CARD-418
  - CARD-497
---

# CARD-614 Skill Studio cuts a skill description to 60 characters on load; relax to about 200 and show the full text

## Problem
Skill Studio says a skill description is "<= 60 chars", but the API (`POST /api/skill_studio/save`, `PUT /api/skills/user-skills`) accepts any length. The form cuts the loaded value to 60 (`workshop_meta.js` slices it), so opening a longer description shows it truncated, and a Save from the form drops the rest. Found in the CARD-611 live QA (docs/findings.md, 2026-10-03).

## Cause
- `src/web/static/modules/studios/skill_studio/workshop_meta.js`: `.slice(0, 60)` on load; counter `/60`.
- `src/web/static/modules/studios/skill_studio.js`: counter `/60`, warning toast "(<= 60 chars)".
- `src/web/templates/index.html`: label "Description (trigger, <= 60 chars)", `maxlength="60"`, editor placeholder.
- `src/web/routers/skill_studio.py`: the runbook-generator prompt says "strictly <= 60" and cuts the trigger to 60.

## Change
- A soft limit of 200 characters (engineering call; Jacob prefers generous limits). Nothing is cut on load or save; the API stays unlimited.
- The description box is a 3-row text box (`maxlength="200"` for typing), so the whole text is visible; line breaks become spaces in the front matter.
- Label, counter (`N/200`, amber near the limit), toast, editor placeholder and the generator prompt say 200.

### Built (2026-10-03)
- `workshop_meta.js`: `SKILL_DESCRIPTION_LIMIT = 200`, `descriptionCounter` (amber over 190), `cleanDescription` (collapses whitespace); no cut on load.
- Skill Studio: 3-row textarea, maxlength 200, label "Description (when to use it, up to about 200 chars)", counter `N/200`, toast and editor placeholder updated; `app.js?v=2.0.103`.
- `skill_studio.py`: generator prompt says at most 200 characters; trigger capped at 200. The 60-char line is gone from docs/findings.md.
- Tests: `tests/unit/web/test_card614_skill_description_limit.py` (4), `tests/unit/frontend/card_614_skill_description_limit.test.js`.

## What dies
Silent truncation of skill descriptions in Skill Studio; the 60-character wording.

## Proof
- Journey `card-614-long-skill-description`: open a skill with a ~180-character description in Skill Studio; the full text shows; Save; reopen; the full text is still there.
- Checks: save then open keeps the full description; the generator gets the whole description and the prompt says 200; load never cuts (even over 200); counter text and warn flag.

## Plan and decisions
- Soft limit, not enforced server-side: existing longer descriptions keep working.

## Findings
- `distillation_service.py` still caps distilled skill descriptions at 60 characters (out of scope; separate card if wanted).
## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-614 long skill description | desktop | Pass | 173-char description opened in full (173/200); edited to 192 (amber), saved, API returns full text, reopened in full. `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\skill-studio-long-description-opened-desktop.png`, `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003f\skill-studio-long-description-saved-desktop.png` |

## Release note
Skill descriptions in Skill Studio can be up to about 200 characters and are shown in full; nothing is cut off when you open or save a skill.
