---
name: Flashcard Turn (SRS Card)
description: Run one spaced flashcard / SRS turn using mastery due items and flashcard Wiki template; durable grade path shared with quiz.
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

# Flashcard Turn (SRS Card)

Run one flashcard / SRS card turn.

## Durable contracts (exist today — honest gap note)

There is **no** separate `/api/education/flashcard/*` router. Flashcards share the mastery / SRS ledger with quiz:

- `GET /api/education/mastery/due` — due SRS items
- `POST /api/education/mastery/upsert` — upsert card state
- `POST /api/education/quiz/grade` — binary grade advances SRS (`src/application/education/srs.py` `next_due_after_grade`)
- Wiki template: `education-flashcard`

Studio surfaces due items inside `#educationQuizPanel` (`#educationDueList`, `#educationRefreshDueBtn`) rather than a dedicated flashcard panel.

## Agent tool lane

Stub relative to agent tools: no `education_flashcard_*` tool. Chat flashcard turns owned by **CARD-438**. Do not invent a flashcard backend.

## Done-when

- A due card is presented, graded, and `next_due` / interval updated in `education_mastery`.

## Successor

- Chat flashcard turns: **CARD-438**; due-review packaging: **CARD-439**


## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

If a required HTTP/tool binding is not yet callable from the agent tool lane, do not invent a fake tool. Cite the durable `/api/education/*` contract below and the owning successor card. Studio UI remains alive until CARD-442.

