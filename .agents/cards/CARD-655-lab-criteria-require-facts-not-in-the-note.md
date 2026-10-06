---
id: CARD-655
title: "Lab criteria can require facts the note doesn't state, so a correct submission fails"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card655_drop_ungrounded_lab_criteria.py]
branch: feat/card-655-drop-ungrounded-lab-criteria
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-06
related:
  - CARD-645
  - CARD-649
---

# CARD-655 Lab criteria can require facts the note doesn't state, so a correct submission fails

## Intent
In the CARD-654 live check (2026-10-06 11:40 ET, qa 3d7632c3, Spark nemotron-3.5-lightning, the Raft note), the application lab's criteria included "The follower responds with an AppendEntries response indicating success." The note never mentions responses or success. The criterion passed lab validation because it names note terms (follower, AppendEntries), and the CARD-649 grader then required "responds, indicating, success". The submission covered everything the note says, but it failed and the course halted at application.

The labs are meant to be grounded in the learner's note, so a criterion should only ask for what the note supports.

## Plan (proposal, pick one)
- Grader: count only a criterion's key terms that appear in the lab's source notes (or the lab's own tasks/objective). Terms from outside the notes can't be required. Small and keeps the CARD-649 coverage rule.
- Or the lab writer: refuse or drop criteria whose key terms are mostly not in the notes (as priming does for prerequisites, CARD-653), keeping 2 or more criteria.

## Acceptance
- The live criterion above no longer fails the journey's submission; a submission that skips a note fact a criterion names still fails.
- The full-course journey on the Raft note gets past application with Spark.

## Decisions
- Jacob approved the build on 2026-10-06 and chose dropping ungrounded criteria when writing the lab over grading only the words that match.
- A criterion is kept only when about half of its key terms (same bar as the CARD-649 grader) appear in the notes. The live invented criterion ("The follower responds with an AppendEntries response indicating success") fails that and is dropped; criteria that are facts from the notes are kept.
- After dropping, a reply left with fewer than two grounded criteria is refused (`too few criteria`), so the step writes nothing rather than a weak lab.
- The lab prompt now says each criterion must be a fact stated in the notes and must not invent outcomes, responses or checks the notes do not describe.

## Change
- `labs.criterion_in_notes(text, note_vocab)`: true when enough key terms are in the notes.
- Lab `StepSpec.filtered_lists=("criteria",)`; `compose_step_content` drops criteria that fail `criterion_in_notes` and refuses when fewer than two remain.
- Lab system prompt: criteria must be facts stated in the notes.

## What dies
A lab whose criteria invent facts the note never states, so a correct submission that covers the note still fails.

## Proof
- Checks (failing first): the live invented criterion is not supported by the note; it is dropped and the rest are kept; a reply left with one grounded criterion is refused; the journey submission fails against the raw Spark criteria and passes once the invented one is gone; a thin submission that skips a note fact still fails.
- Live: Raft-note course construction and application labs pass with grounded criteria only.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2701 passed, 12 skipped, 33 warnings |
| preflight --fast --base qa | GREEN | guard 188, vitest 1091 |

## Release note
Course labs now drop grading criteria that invent facts your notes never state, so a submission that covers what you wrote is graded against what your notes actually say.
