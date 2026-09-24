---
name: Quiz Turn (Durable Retrieval Grade)
description: Run one Learning OS quiz / retrieval turn with durable binary grading into the mastery ledger.
version: 1.1.0
tier: platform
requires_tools:
  - education_quiz_extract
  - education_quiz_next
  - education_quiz_grade
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
  rule: Education-mode Tutor invokes this named Learning OS skill; grades via education_quiz_grade into education_mastery; never invent success on tool failure.
---

# Quiz Turn (Durable Retrieval Grade)

Execute a single retrieval quiz turn with durable grading.

## Turn shape (Tutor education mode)

1. **Select item** — call `education_quiz_next` (optional `topic`). If empty, `education_quiz_extract` from a Wiki note (`education-quiz` template / `## Quiz` section) with `persist=true`.
2. **Prompt learner** — present `prompt` in chat (Socratic method OK inside this skill).
3. **Grade** — when the learner answers, call `education_quiz_grade` with `item_id` + `answer`.
4. **Report honestly** — only claim pass/miss / `next_due` from the tool return. If `success` is false, tell the operator the grade did **not** persist (no bubble theatre).

## Exact agent tools (CARD-438)

| Tool | Role | HTTP twin |
|---|---|---|
| `education_quiz_next` | Next retrieval item(s) from ledger | `GET /api/education/quiz/next` |
| `education_quiz_extract` | Extract Q/A from Wiki + optional upsert | `POST /api/education/quiz/extract` |
| `education_quiz_grade` | Binary grade + durable mastery / SRS write | `POST /api/education/quiz/grade` |

Supporting Wiki tools: `wiki_note_read`, `wiki_note_search`, `wiki_note_list`, `wiki_template_list`.

## Durable contracts

- Ledger: `education_mastery` in agent `memory.db`
- Grader: `quiz_engine.grade_answer_binary` (binary external — not LLM self-score)
- Course-scoped alternative (Studio / course chrome): `POST /api/education/course/mastery/grade` (not required for this chat turn path)

## Wiki

- Template: `education-quiz` (`data/wiki/02_Resources/_Templates/education-quiz.md`)

## Done-when

- Attempt is binary-graded and written to `education_mastery` via `education_quiz_grade` (not chat-only theatre).
- Hard-refresh still reflects the item in mastery / due / quiz next.

## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

Never invent a successful durable grade when `education_quiz_grade` fails.
