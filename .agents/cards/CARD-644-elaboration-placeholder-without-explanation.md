---
id: CARD-644
title: "Elaboration step without a learner explanation writes a placeholder note and a topic-name answer"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card644_grounded_elaboration.py]
branch: feat/card-644-grounded-elaboration
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-05
completed: 2026-10-05
related:
  - CARD-640
  - CARD-641
---

# CARD-644 Elaboration step without a learner explanation writes a placeholder note and a topic-name answer

## Intent
When the elaboration step is completed without a learner explanation, it writes a note with "[Learner self-explanation to be added during review]" and a quiz item "How would you explain the core mechanism of <topic> in your own words?" whose expected answer is just the topic name, so grading against it is meaningless.

## Goal
Without a learner explanation the elaboration step writes nothing (or asks for the explanation); with one, the quiz item's expected answer is grounded in what Jacob wrote.

## Plan and decisions
- Backlog card from CARD-640/641; Jacob approved the build on 2026-10-05.
- Built fourth, on the shared grounded modules from CARD-646.
- No explanation: the step writes nothing (skip_reason no_learner_explanation) and advances. With an explanation: the note always holds it (it is the learner's own words); follow-up questions and a quiz item are added only when one model call returns content grounded in the explanation (the answer must use the learner's words) and their notes, if any. Otherwise the result carries grounding_skip_reason.

## Change
- `grounded_steps.py`: elaboration spec (probes 2-4, question, answer); `StepSpec.needs_learner_text` and `learner_grounded`; `compose_step_content(..., learner_text=)` puts the learner's text in the prompt and the grounding vocabulary, and works with no notes when there is learner text.
- `elaboration.py`: `build_elaboration_note_content(topic, learner_explanation=, composed=)` writes Your explanation / Questions to push further / Sources / Quiz; the placeholder, template probes, analogy, edge-case and fixed quiz sections are gone. `build_elaboration_preview` returns only the ask (no template probes).
- `course.py`: elaboration writer as above; the quiz item is the grounded question and answer.
- Router: complete-step and elaboration/complete compose with the learner's explanation; elaboration/preview takes an optional explanation and returns grounded probes or the skip reason.

## What dies
The "[Learner self-explanation to be added during review]" note, the "How would you explain the core mechanism of X in your own words?" item with the topic name as its answer, and the template probe, analogy and quiz text.

## Proof
- Checks (failing first): template text gone; no explanation writes nothing and advances; compose needs an explanation; a grounded reply adds probes and one quiz item from the explanation; explanation without notes can still ground; an answer not from the explanation, the old template and non-JSON are refused; explanation without a grounded reply keeps only the explanation (no quiz); preview API has no template probes.
- Spark probe (nemotron-3.5-lightning, 3 runs with a note, 3 without): all grounded and accepted; answers taken from the explanation.
- Live: shared full-course check after CARD-642.

## Findings
- None new.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2640 passed, 12 skipped (10 new; CARD-322/323 tests updated) |
| preflight --fast --base qa | GREEN | ruff, guard 188, vitest 1091 |

## Release note
The elaboration step now saves your own explanation; follow-up questions and a quiz question are added only when they can be drawn from what you wrote. Without an explanation it saves nothing instead of a placeholder note.
