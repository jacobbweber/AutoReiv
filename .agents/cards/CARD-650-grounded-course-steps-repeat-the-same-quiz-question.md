---
id: CARD-650
title: "Grounded course steps ask near-duplicate quiz questions in one course"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card650_dedupe_quiz_questions.py]
branch: feat/card-650-dedupe-quiz-questions
log: {minutes: 35, qa_runs: 0, findings: 0}
created: 2026-10-05
completed: 2026-10-06
related:
  - CARD-642
  - CARD-643
  - CARD-646
---

# CARD-650 Grounded course steps ask near-duplicate quiz questions in one course

## Intent
Each grounded course step (priming, dual coding, elaboration, environment, construction and application labs) asks the model for one quiz question from the same notes, without seeing the questions earlier steps wrote. In the Spark probes for CARD-643/644/642 the model returned almost the same question ("What condition must a follower's log meet ...") for several steps, so one course can fill the ledger with near-duplicate items.

## Goal
Pass the course's earlier quiz questions to the model and/or skip a step's quiz item when it nearly duplicates an existing item for the topic.

## Plan and decisions
- Backlog card (found in the Spark probes while building CARD-642 to CARD-644); Jacob approved the build on 2026-10-06.
- Two layers: the model is shown up to 12 questions already in the ledger for the topic and told to ask about a different fact; and before writing, a question that still nearly repeats any existing ledger item (any topic) is dropped.
- Near-duplicate = questions share at least 60% of their content words, or they overlap (at least 20%) and the answers say the same thing (one answer's words, at least three, are 80% inside the other). Tuned on the five near-identical questions from the CARD-642 live run.
- A dropped question keeps the step's note (without its Quiz section) and writes no quiz item; the result says quiz_skip_reason: duplicate_question. Re-running a course step replaces its own item, so that item is not counted as a duplicate.
- complete-step results now also surface graded, grounding_skip_reason and quiz_skip_reason (they were computed but not returned).

## Change
- `grounded.py`: `is_near_duplicate`, `find_duplicate_item`, `drop_duplicate_quiz`, `ledger_items`, `avoid_block`.
- `grounded_steps.compose_step_content` / `compose_course_step` and `dual_coding.compose_dual_coding` take `avoid_questions`; the router's `_compose_current_step` passes the topic's existing ledger prompts (minus the step's own item).
- `course._write_step_artifact` drops a duplicate question before any writer runs; dual coding, elaboration, labs, environment and priming notes omit the Quiz section and write no item when the question was dropped. `priming_writeback` applies the same check for the standalone priming route.
- `complete_course_step` returns `graded`, `grounding_skip_reason`, `quiz_skip_reason`.

## What dies
Near-identical quiz items from one course. Items already in a learner's ledger are left alone.

## Proof
- Checks (failing first): the live run's variants are near-duplicates and a different question is not; a duplicate keeps the note but writes no quiz item and says why; a distinct question is written; re-running a step replaces its own item; a duplicate of another topic's item is skipped; priming drops a duplicate question from its note and ledger; the model prompt lists the questions already asked.
- Live: shared full-course check after CARD-653.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2678 passed, 12 skipped, 33 warnings |
| preflight --fast --base qa | GREEN | guard 188, vitest 1091 |

## Release note
A course no longer fills your quiz with near-identical questions: each step is told which questions you already have, and a question that still repeats one is left out (the step's note is kept).
