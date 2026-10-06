---
id: CARD-654
title: "Grounded course steps keep asking the priming question, so a course keeps one quiz item"
type: bug
status: Ready
priority: P3
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
