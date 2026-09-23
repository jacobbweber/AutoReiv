---
name: Progress Summary (Trustable Learning OS State)
description: Summarize durable course, mastery, depth, and learner progress from Learning OS stores — not ephemeral Studio labels.
version: 1.0.0
tier: platform
requires_tools:
  - wiki_note_read
  - wiki_note_search
  - wiki_note_list
  - wiki_template_list
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Education-mode Tutor invokes this named Learning OS skill; durable Learning OS APIs or Wiki templates are cited; no invented backend.
---

# Progress Summary (Trustable Learning OS State)

Report progress the operator can trust from durable Learning OS state.

## Durable contracts (exist today)

- `GET /api/education/course` (+ depth via `GET /api/education/course/depth`)
- `GET /api/education/mastery`, `GET /api/education/mastery/due`
- `GET /api/education/learner`
- `GET /api/education/analysis` (+ `/errors`, `/patterns`)
- Application: `course.course_chrome_snapshot`, `learner_model`, `analysis`, `depth`

## Studio chrome map

- `#educationCourseChrome`, mastery badge / academic rank / progress bar / next milestone
- `#educationGrowthPortfolioBtn` → portfolio create
- Analysis panel `#educationAnalysisPanel`

## Agent tool lane

No `education_progress_*` agent tool yet. Non-Studio progress surface is **CARD-441**. Until then, summarize only from tool/API facts you actually have; never invent mastery percentages.

## Done-when

- Summary cites durable fields (course status/step, mastery grades/due, depth progress) with sources.

## Successor

- Progress you can trust on non-Studio surfaces: **CARD-441**


## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

If a required HTTP/tool binding is not yet callable from the agent tool lane, do not invent a fake tool. Cite the durable `/api/education/*` contract below and the owning successor card. Studio UI remains alive until CARD-442.

