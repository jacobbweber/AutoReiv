---
id: CARD-642
title: "Environment course step writes a generic note and a filler quiz item"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [card-642-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card642_grounded_environment.py]
branch: feat/card-642-grounded-environment
log: {minutes: 25, qa_runs: 1, findings: 5}
created: 2026-10-05
completed: 2026-10-05
related:
  - CARD-640
  - CARD-641
---

# CARD-642 Environment course step writes a generic note and a filler quiz item

## Intent
The environment course step writes a note from the active delivery profile and a quiz item "What delivery profile and runtime constraints frame learning for <topic>?" whose expected answer is "<profile> profile with single-brain memory.db invariants". The note and the question are the same for every topic and test nothing about it.

## Goal
The environment step writes only content about the topic and Jacob's real setup, or records progress only (as CARD-641 does for steps without a writer).

## Plan and decisions
- Backlog card from CARD-640/641; Jacob approved the build on 2026-10-05.
- Built last, on the shared grounded modules.
- The environment step asks the model for 2-4 ways to practise the topic taken from the notes, plus one question and answer; the active delivery profile is kept as a single line of fact in the note, never as the content.
- No grounded content: progress only, nothing written. The fixed 'delivery profile and runtime constraints' quiz item is gone.

## Change
- `grounded_steps.py`: environment spec (practice 2-4, question, answer).
- `environment.py`: `build_environment_framing` (the same framing text for every topic) removed; `build_environment_note_content(topic, composed, profile)` writes the profile line, Where to practise, Sources and Quiz from the grounded content.
- `course.py`: the environment writer records progress only unless the step is grounded; its quiz item is the grounded question.
- Router: `/course/environment/preview` returns grounded content (with `profile`) or the skip reason; `environment/complete` composes the current step.
- New journey `card-642-full-course-grounded-or-empty` runs a whole course with and without topic notes and checks every written note and quiz item against the retired templates.

## What dies
The per-topic environment framing note and the "What delivery profile and runtime constraints frame learning for X?" quiz item. Items already in a learner's ledger are left alone.

## Proof
- Checks (failing first): template framing gone; no notes records progress only; template and ungrounded replies refused; a grounded reply writes a note with practice, profile line, source link and one grounded quiz item; environment preview API never returns a template.
- Spark probe (nemotron-3.5-lightning, 3 runs on a Raft note): all grounded and accepted.
- Live (2026-10-05 23:58 ET, :8770, Spark nemotron-3.5-lightning, desktop): card-642-full-course-grounded-or-empty PASS. Topic with a note: dual coding, elaboration, both labs and environment grounded in the note (priming skipped, model_output_invalid, filed as CARD-653); retrieval/retention progress only. Topic without notes: priming, dual coding and environment wrote nothing (no_wiki_notes); elaboration and labs kept only the learner's own text (one quiz item from the learner's explanation); no template quiz items or notes anywhere. Screenshots in %TEMP%\autoreiv-qa\course-filler-2.

## Findings
Filed as backlog CARD-648 to CARD-652: construction/generate template study artifact; lenient lab grader; near-duplicate quiz questions across grounded steps; growth portfolio template lines and self-quiz; knowledge-artifact template sections.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | 2659 passed, 12 skipped (7 new; CARD-325 test moved to grounded input) |
| preflight --fast --base qa | GREEN | guard 188, vitest 1091 |

## Release note
The environment course step now suggests where to practise from your own wiki notes on the topic. With no notes it just records progress instead of writing the same framing note and quiz question for every topic.
