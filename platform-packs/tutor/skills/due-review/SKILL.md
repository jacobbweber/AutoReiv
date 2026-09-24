---
name: Due Review (SRS + Retention Routine)
description: Surface and complete due mastery / SRS reviews and optionally run the retention routine from Tutor education mode.
version: 1.1.0
tier: platform
requires_tools:
  - education_due_review_list
  - education_due_review_complete
  - education_mastery_due
  - education_retention_run
  - education_quiz_grade
  - education_flashcard_grade
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
  rule: Education-mode Tutor invokes due-review; lists from education_due_review_list / mastery due; completes via education_due_review_complete into education_mastery; empty queue is honest; never invent success on tool failure.
---

# Due Review (SRS + Retention Routine)

Surface due reviews and complete them with durable Learning OS grading from Tutor education mode / Study.

## Turn shape (Tutor education mode)

1. **List due** - call `education_due_review_list` (or `education_mastery_due`). If `empty` is true / `empty_state` is "No due reviews.", tell the operator honestly - do **not** invent items.
2. **Present** - pick one due item; show `prompt` (Socratic method OK inside this skill). Hide expected answer until after the attempt.
3. **Complete** - when the learner answers, call `education_due_review_complete` with `item_id` + `answer`.
4. **Report honestly** - only claim pass/miss / `next_due` / `left_due_queue` from the tool return. If `success` is false, the grade did **not** persist.
5. **Optional retention** - `education_retention_run` mints standing Jobs for due items (`POST /api/education/retention/run`). Chat toast is never Done. If the tool returns failure / `no_orchestrator`, say so - never invent job ids.

## Exact agent tools (CARD-439)

| Tool | Role | HTTP twin |
|---|---|---|
| `education_due_review_list` | Due set from ledger (+ empty state) | `GET /api/education/mastery/due` |
| `education_mastery_due` | Same due ledger list | `GET /api/education/mastery/due` |
| `education_due_review_complete` | Durable grade + due-queue delta | `POST /api/education/quiz/grade` |
| `education_quiz_grade` / `education_flashcard_grade` | Shared grade path (CARD-438) | `POST /api/education/quiz/grade` |
| `education_retention_run` | Retention routine (due -> standing Jobs) | `POST /api/education/retention/run` |

Supporting Wiki tools: `wiki_note_read`, `wiki_note_search`, `wiki_note_list`, `wiki_template_list`.

## Durable contracts

- Ledger: `education_mastery` in agent `memory.db`
- SRS: `srs.next_due_after_grade`
- Retention: `src/application/education/retention_routine.py` `run_education_retention`
- **Delivery profiles do not replace ledger/SRS.**

## Studio chrome map (kept)

- `#educationRefreshDueBtn`, `#educationDueList`, `#educationRunRetentionBtn` remain (ADR-0059 / Studio players = CARD-446 later).

## Done-when

- Due set is listed from the ledger; completing a review writes durable grade/SRS and the item leaves or reschedules on refresh.
- Empty due queue shows an explicit empty state.
- Retention run (when invoked) writes honest job output or honest failure - not toast-only Done.

## Hard rails (CARD-436 / CARD-435)

Education-mode Tutor **must** use a named Learning OS skill (this skill or a sibling Learning OS skill id). Open vibes and freeform chat without a named Learning OS skill are **non-product**. `socratic-tutoring` is the dialogue method used *inside* Learning OS turns; it is not a bypass of these rails.

Never invent a successful durable grade or minted retention job when tools fail.
