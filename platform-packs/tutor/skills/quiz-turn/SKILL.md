---
name: Quiz Turn (Durable Retrieval Grade)
description: Run one Learning OS quiz / retrieval turn with durable binary grading into the mastery ledger.
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

# Quiz Turn (Durable Retrieval Grade)

Execute a single retrieval quiz turn with durable grading.

## Durable contracts (exist today)

- `POST /api/education/quiz/extract` — extract items from Wiki (`quiz_engine.extract_quiz_items_from_note`)
- `GET /api/education/quiz/next` — next quiz item
- `POST /api/education/quiz/grade` — binary grade + mastery upsert (`quiz_engine.grade_answer_binary`)
- `POST /api/education/course/mastery/grade` — course-scoped mastery grade
- Ledger: `education_mastery` in agent `memory.db`

## Wiki

- Template: `education-quiz` (`data/wiki/02_Resources/_Templates/education-quiz.md`)

## Agent tool lane

No `education_quiz_*` agent tool yet. Chat-durable quiz UX is **CARD-438**. Until then, Education Studio `#educationQuizPanel` is the live operator path. Do not invent a grading tool.

## Done-when

- Attempt is binary-graded and written to `education_mastery` (not chat-only theatre).

## Successor

- Chat quiz turns + durable grading surface: **CARD-438**


## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

If a required HTTP/tool binding is not yet callable from the agent tool lane, do not invent a fake tool. Cite the durable `/api/education/*` contract below and the owning successor card. Studio UI remains alive until CARD-442.

