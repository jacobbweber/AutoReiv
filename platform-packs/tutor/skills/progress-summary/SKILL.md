---
name: Progress Summary (Trustable Learning OS State)
description: Summarize durable course, mastery, depth, and learner progress from Learning OS stores - not ephemeral Studio labels.
version: 1.1.0
tier: platform
requires_tools:
  - wiki_note_read
  - wiki_note_search
  - wiki_note_list
  - wiki_template_list
  - education_progress_summary
  - education_progress_courses
  - education_progress_mastery
  - education_mastery_due
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Education-mode Tutor invokes this named Learning OS skill; durable Learning OS APIs or Wiki templates are cited; no invented backend; mastery_pct only when graded ledger rows exist.
---

# Progress Summary (Trustable Learning OS State)

Report progress the operator can trust from durable Learning OS state. **CARD-441** ships the non-Studio surface (Tutor education-mode Progress strip + agent tools). Education Studio course chrome stays (ADR-0059 / CARD-446 player).

## Durable contracts

- Aggregate: `GET /api/education/progress` (tool `education_progress_summary`)
- Course: `GET /api/education/course` (+ `education_progress_courses` / `list_education_courses`)
- Mastery: `GET /api/education/mastery` (`education_progress_mastery`)
- Due: `GET /api/education/mastery/due` (`education_mastery_due`)
- Learner: `GET /api/education/learner` (included in progress summary when available)
- Application helpers: `build_progress_summary`, `course_chrome_snapshot`, `learner_model`, depth

## Operator surface (non-Studio)

- Tutor education-mode strip **Progress** button → `#chatEducationModeProgressPanel`
- Shows course / mastery counts / due without opening `#view-education`
- After refresh, reflects CARD-438 grades and CARD-439 due completions
- API failure → error/empty with `mastery_pct=null` — never a fake 100%

## Studio chrome map (retained)

- `#educationCourseChrome`, mastery badge / academic rank / progress bar / next milestone
- `#educationGrowthPortfolioBtn` → portfolio create
- Analysis panel `#educationAnalysisPanel`
- Studio is **not** required to view progress; player rebuild is CARD-446

## Agent tool lane

- `education_progress_summary` — primary; cites `GET /api/education/progress`
- `education_progress_courses` — course list/current
- `education_progress_mastery` — pass/miss/unseen counts (`mastery_pct` only when graded > 0)
- `education_mastery_due` — due count twin

Never invent mastery percentages. Empty ledger → honest empty_state.

## Done-when

- Summary cites durable fields (course status/step, mastery grades/due, depth progress) with sources.
- Operator can see progress from Tutor education mode without Education Studio panels.

## Hard rails (CARD-436 / CARD-435 / CARD-441)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling). Open vibes without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method inside Learning OS turns; it is not a bypass of these rails.

If a required HTTP/tool binding fails, return `success=false` / empty — do not decorate with fake progress. Studio UI remains alive (ADR-0059); it is not the only progress path.
