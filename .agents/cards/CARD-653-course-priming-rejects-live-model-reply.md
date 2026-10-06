---
id: CARD-653
title: "Course priming step rejected the real model's reply in the live check"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card653_priming_accepts_grounded_reply.py]
branch: feat/card-653-priming-accepts-grounded-reply
log: {minutes: 30, qa_runs: 1, findings: 0}
created: 2026-10-05
completed: 2026-10-06
related:
  - CARD-642
  - CARD-646
---

# CARD-653 Course priming step rejected the real model's reply in the live check

## Intent
In both runs of the full-course live check (card-642-full-course-grounded-or-empty, Spark nemotron-3.5-lightning, a topic with a learner note), the priming step wrote nothing with `skip_reason: model_output_invalid`, while dual coding, elaboration, both labs and environment were grounded from the same note. The CARD-646 Spark probe had accepted 3 of 3 priming replies, so the course path's priming prompt or its validator (Key ideas / Before you start / question / answer) rejects replies the probe accepted.

## Goal
Find out which check rejects the live priming reply (log the reason), and make priming write grounded content when the model gives it, still writing nothing when it doesn't.

## Plan and decisions
- Backlog card (found in the CARD-642 full-course live check); Jacob approved the build on 2026-10-06.
- Diagnosis (read-only Spark probe, nemotron-3.5-lightning, the live check's Raft note, the course priming prompt, 4 replies): the outline, question and answer were grounded in every reply, but in 2 of 4 the prerequisites (e.g. "Understanding of distributed consensus concepts", "Knowledge of log-based replication mechanisms") failed the per-list grounding check, which refused the whole reply. Prompt and parsing were fine; the check was over-strict for a list that by definition names things outside the notes.
- Fix: prerequisites are an optional context list; items not taken from the notes are dropped instead of refusing the reply. Key ideas, question and answer keep the same grounding rules, so an ungrounded reply is still refused.
- A refusal now logs which check failed and course results carry skip_detail, so a live refusal can be diagnosed without a probe.

## Change
- `grounded_steps.StepSpec.filtered_lists`; priming sets it to `prerequisites`. `validate_step_content` skips the list-grounding check for filtered lists and `compose_step_content` drops their ungrounded items after validation; refusals are logged with the step and reason.
- `course._nothing_written` and `complete_course_step` return `skip_detail` (the refusal reason).
- Full-course journey notes print skip detail and quiz skip reason per step.

## What dies
Refusing a grounded priming reply because its prerequisites mention things the notes rely on but don't state.

## Proof
- Checks (failing first): a Spark reply refused before this card is accepted with its outside prerequisites dropped; the course writes the priming note and its one quiz item without them; ungrounded key ideas are still refused; the refusal detail is returned in the course result and logged.
- Spark probe after the fix (same note and prompt, 6 replies through `compose_step_content`): 6 of 6 accepted.
- Live: shared full-course check after merge.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | __PYTEST__ |
| preflight --fast --base qa | GREEN | __FAST__ |

## Release note
The course priming step now writes its note from your notes when the model's key ideas are grounded, instead of throwing the whole reply away because a "before you start" item wasn't in your notes (those items are just left out).
