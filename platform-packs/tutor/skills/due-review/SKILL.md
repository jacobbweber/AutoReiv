---
name: Due Review (SRS + Retention Routine)
description: Surface and run due mastery / SRS reviews and the retention routine from Learning OS rails.
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

# Due Review (SRS + Retention Routine)

Surface due reviews and optionally run the retention routine.

## Durable contracts (exist today)

- `GET /api/education/mastery/due`
- `GET /api/education/mastery`
- `POST /api/education/retention/run` — `src/application/education/retention_routine.py` `run_education_retention`
- Course step `retention` in `DEFAULT_COURSE_STEPS`

## Studio chrome map

- `#educationRefreshDueBtn`, `#educationDueList`, `#educationRunRetentionBtn` inside quiz section
- Environment panel notes SRS due calculation

## Agent tool lane

No `education_retention_*` agent tool yet. Tutor education-mode due-review UX is **CARD-439**. Do not fake a retention tool.

## Done-when

- Due set is listed from the ledger; a retention run (when invoked) writes honest job output, not a toast-only Done.

## Successor

- Due reviews in Tutor education mode: **CARD-439**


## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

If a required HTTP/tool binding is not yet callable from the agent tool lane, do not invent a fake tool. Cite the durable `/api/education/*` contract below and the owning successor card. Studio UI remains alive until CARD-442.

