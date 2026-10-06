---
id: CARD-655
title: "Lab criteria can require facts the note doesn't state, so a correct submission fails"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build approval
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: []
branch: ""
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-06
completed: ""
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
