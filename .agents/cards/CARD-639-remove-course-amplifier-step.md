---
id: CARD-639
title: "Courses skip the removed visual amplifier step; no filler wiki notes or quiz items"
type: bug
status: Done
completed: 2026-10-05
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: [card-639-course-skips-amplifier-step]
  checks: [tests/unit/education/test_card639_course_amplifier_step_removed.py]
branch: feat/card-639-remove-course-amplifier-step
log: {minutes: 45, qa_runs: 1, findings: 2}
created: 2026-10-05
related:
  - CARD-638
  - CARD-328
  - CARD-320
---

# CARD-639 Courses skip the removed visual amplifier step; no filler wiki notes or quiz items

## Intent
Jacob chose to abandon Lumina. The Education course pipeline's "amplifiers" step (CARD-328) uses Lumina to write a wiki note and a mastery-ledger quiz item. For any topic that is not one of four built-in lessons, that note is generic filler ("Topic Core, Operational Dynamics, Observable Output") and the quiz item asks "How does the visual amplifier model the core flow of the topic?" with the answer "Through flow topology connecting constituent mechanisms".

## Goal
Courses simply skip the visual amplifier step. Nothing can produce that filler wiki note or filler mastery-ledger item any more, including courses that were started before this change and still list the step.

## Change
- `course.py`: remove "amplifiers" from the default and ordered course steps and from the steps you can jump to; add a retired-step list so a stored course that still lists "amplifiers" moves past it; completing a course whose current step is "amplifiers" writes nothing and advances; jumping to it is refused; the course chrome no longer lists it.
- Remove the amplifier branch of the step writer and its Lumina import, plus the "amplifiers" entries in the step template and knowledge-type maps.
- Remove the "Send to Education Course" hookup: the button in the Lumina stage, its click handler and CSS rule, and the `/api/lumina/send-to-course` route. The rest of Lumina Studio goes in CARD-638.
- The Retrieval-backed visual amplifiers of CARD-249 (Mermaid taken from an existing note and attached to an existing quiz item) are not filler and stay.

## What dies
The course "amplifiers" step and its filler note and filler quiz item.

## Proof
- Journey `card-639-course-skips-amplifier-step`: on a throwaway server, start a course and complete steps through the API until "environment"; the next step is "retention", no "Course Visual Amplifiers" note and no amplifier quiz item exist.
- Checks (failing first): default and ordered steps have no "amplifiers"; a stored course on the "amplifiers" step advances to "retention" without a wiki write or ledger row (negative: no note, no `course_*_amplifiers` item, no `course_step_amplifiers` fact); a stored step list containing "amplifiers" skips it after "environment"; jumping to "amplifiers" is refused; the chrome snapshot omits it.

## Plan and decisions
- Built before CARD-638 so that removing `lumina.py` never breaks courses.
- Existing filler notes and ledger items in Jacob's live data are listed in the report, not deleted.

## Findings
- `build_dual_coding_preview` (the dual coding step) still writes a template diagram that is the same for every topic. Not part of this card; worth its own card if Jacob wants the course pipeline audited for templates.
- Steps without a dedicated writer fall through to a generic note ("Course X: topic") and a generic quiz item ("What Learning OS step did you just complete..."). Also out of scope here.
- Live data check (read only, 2026-10-05): the wiki at `C:\Users\jacob\AppData\Local\AutoReiv\wiki` has no note mentioning a visual amplifier or Lumina; the four agent memory databases (architect, autoreiv, developer, tutor) have no amplifier or Lumina rows (all four mastery ledgers are empty); `database\autoreiv.db` has no matching text. Nothing to clean up.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-639-course-skips-amplifier-step | desktop | pass | live_qa :8770; Education Set active creates a course whose steps end environment > retention; completing environment moves to retention; jump to amplifiers gives 422 "course step removed"; retention completes the course; ledger has 2 items, 0 amplifier filler |
| card-639-course-skips-amplifier-step | phone | pass | same |
| tests/unit/education | - | pass | 222 passed (7 new checks, failing first) |
| preflight --fast --base qa | - | GREEN | ruff, eslint, guard 188, vitest 1092 |

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-639\`
- `card-639-course-skips-amplifier-step-desktop-01-education-course-active.png`
- `card-639-course-skips-amplifier-step-desktop-04-education-after-course.png`
- `card-639-course-skips-amplifier-step-phone-01-education-course-active.png`

## Release note
Education courses no longer have a visual amplifier step, so they stop writing generic "visual amplifier" wiki notes and quiz items; courses already on that step move straight to retention.
