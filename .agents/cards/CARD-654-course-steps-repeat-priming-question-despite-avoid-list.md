---
id: CARD-654
title: "Grounded course steps keep asking the priming question, so a course keeps one quiz item"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card654_course_quiz_retry.py]
branch: feat/card-654-course-quiz-avoid-retry
log: {minutes: 40, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-06
related:
  - CARD-650
  - CARD-653
---

# CARD-654 Grounded course steps keep asking the priming question, so a course keeps one quiz item

## Intent
In the course-filler-3 live check (2026-10-06 10:06 ET, qa ef4b0314, Spark nemotron-3.5-lightning, the Raft note topic), priming is now accepted and wrote one quiz item: "What condition must a follower's log meet to accept an AppendEntries message?". Dual coding, elaboration, construction, application and environment each came back from Spark with that exact question again. The CARD-650 dedupe correctly dropped all five (`quiz_duplicate` shows a verbatim repeat), so nothing is duplicated, but a six-step course on a note ends up with one quiz item.

The router passes the topic's earlier ledger prompts as `avoid_questions` (`_compose_current_step`), so either the avoid block doesn't reach the step prompt on this path, or Spark ignores it for a short single-note topic.

## Plan (proposal)
- Confirm with a read-only Spark probe that the avoid block is in the composed prompt for each step and see whether Spark still repeats the question.
- If it reaches the prompt and is ignored: ask once more with the duplicate named explicitly, and keep "no quiz item" when the retry repeats or isn't grounded. One extra call only on a duplicate.
- Keep grounded-or-nothing: no filler questions when the note supports only one.

## Acceptance
- On the live full-course journey with the Raft note, at least two distinct grounded quiz items, or a clear `quiz_skip_reason` per step when the note supports no new question.
- No near-duplicate questions within the course (the CARD-650 tests still pass).

## Decisions
- Jacob approved the build on 2026-10-06.
- Verification (read-only Spark probe, nemotron-3.5-lightning, the live Raft note, the real `compose_course_step` path, 2 replies per step): the avoid block was in the prompt for dual coding, elaboration, construction, application and environment, and Spark still asked the priming question in 10 of 10 replies. The avoid list reaches the model; Spark ignores it. A route test now guards that the saved priming question reaches the step prompt.
- A follow-up turn (the model's own reply, then "your question repeats ... ask about a different fact") got a new question in 4 of 6 probe replies, so that is the retry. One extra call, only on a repeat.
- When the second question repeats too, or the second reply is not usable, the step keeps its first grounded content and the CARD-650 dedupe drops its question: the note is saved without a quiz item. No filler questions.

## Change
- `grounded.call_model(..., retry=(earlier reply, correction))` makes the call a follow-up turn.
- `grounded.ask_again_if_repeated` plus `avoid_checker` / `retry_note`; `compose_step_content` and `compose_dual_coding` call it after validating the first reply, and take `duplicate_of` (default: near-repeats of the avoid list).
- The course router passes `duplicate_of` backed by `find_duplicate_item` (any saved item except the step's own), the same check the writer uses.
- Course results carry `quiz_retry` (`new_question`, `repeated` or `refused`); the full-course journey prints it.

## What dies
A course on a note keeping one quiz item because the model asks the same question at every step.

## Proof
- Checks (failing first): a repeat is asked again as a follow-up turn naming it and the new question is used; a distinct question costs one call; dual coding retries too; a second repeat saves the note with no quiz item; an unusable second reply keeps the first content without its question; never more than one extra call; the router shows the model the saved priming question.
- Live: full course on the Raft note after merge.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2692 passed, 12 skipped, 33 warnings |
| preflight --fast --base qa | GREEN | guard 188, vitest 1091 |

## Release note
Course steps that come back with a quiz question you've already been asked now ask the model once more for a different one, so a course on your note saves several distinct quiz questions instead of one.

## Follow-up (first live check, 2026-10-06 11:40 ET)
The first full-course run after merge got a new question on 1 of 4 retries (elaboration); dual coding, construction and application came back on the same fact rephrased and saved no quiz item. Read-only probe with the full duplicate check (12 repeats): naming the earlier question only got a new question 9 of 12 times; also naming the earlier answer and asking for "a different sentence of the notes, one that is not about that answer" got 12 of 12. The retry now uses that wording; `duplicate_of` returns the earlier (question, answer). One test added.

## Follow-up 2 (second live check, 2026-10-06 11:59 ET)
The journey passed but the Raft course saved 2 distinct items: once priming and dual coding had saved the follower-log and commit-index questions, every retry came back on one of those two facts. Read-only probe with both items saved (12 repeats): naming the repeat got 0 new questions, naming every saved item got 3. Pointing the retry at the note sentence least covered by the saved questions and answers (`least_covered_sentence`) gave 5 and 6 distinct items in two whole-course probe runs. The router now passes every saved (question, answer) on the topic as `asked`; without notes the retry falls back to the earlier wording. Three tests added.
