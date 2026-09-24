---
name: Flashcard Turn (SRS Card)
description: Run one spaced flashcard / SRS turn using mastery due items and flashcard Wiki template; durable grade path shared with quiz.
version: 1.1.0
tier: platform
requires_tools:
  - education_flashcard_next
  - education_flashcard_grade
  - education_mastery_due
  - education_mastery_upsert
  - wiki_note_read
  - wiki_note_search
  - wiki_note_list
  - wiki_template_list
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Education-mode Tutor invokes this named Learning OS skill; grades via education_flashcard_grade into education_mastery; never invent success on tool failure.
---

# Flashcard Turn (SRS Card)

Run one flashcard / SRS card turn.

## Turn shape (Tutor education mode)

1. **Select card** — call `education_flashcard_next` (or `education_mastery_due`). If empty, seed with `education_mastery_upsert` from an `education-flashcard` Wiki note / known prompt+answer.
2. **Prompt learner** — show the card front (`prompt`); hide expected answer until after the attempt.
3. **Grade** — call `education_flashcard_grade` with `item_id` + learner `answer`.
4. **Report honestly** — surface `grade`, `interval_stage`, `next_due` from the tool. On `success=false`, do **not** claim a durable SRS update.

## Exact agent tools (CARD-438)

| Tool | Role | HTTP twin |
|---|---|---|
| `education_flashcard_next` | Next due SRS / flashcard item(s) | `GET /api/education/mastery/due` |
| `education_mastery_due` | Full due list | `GET /api/education/mastery/due` |
| `education_mastery_upsert` | Seed / upsert a card | `POST /api/education/mastery/upsert` |
| `education_flashcard_grade` | Binary grade + SRS advance (shared path) | `POST /api/education/quiz/grade` |

There is **no** `/api/education/flashcard/*` router. Flashcards share the mastery / SRS ledger with quiz (`srs.next_due_after_grade`).

Supporting Wiki tools: `wiki_note_read`, `wiki_note_search`, `wiki_note_list`, `wiki_template_list`.

## Wiki

- Template: `education-flashcard` (`data/wiki/02_Resources/_Templates/education-flashcard.md`)

## Done-when

- A due card is presented, graded via `education_flashcard_grade`, and `next_due` / interval updated in `education_mastery`.

## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

Never invent a successful durable grade when `education_flashcard_grade` fails.

## Successor

- Due-review packaging / queue UX: **CARD-439**
