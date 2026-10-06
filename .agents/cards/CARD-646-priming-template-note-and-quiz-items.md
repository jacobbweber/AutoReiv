---
id: CARD-646
title: "Priming writes a template note and two template quiz items"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: [course-filler-2-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card646_grounded_priming.py]
branch: feat/card-646-grounded-priming
log: {minutes: 40, qa_runs: 1, findings: 1}
created: 2026-10-05
completed: 2026-10-05
related:
  - CARD-640
  - CARD-641
---

# CARD-646 Priming writes a template note and two template quiz items

## Intent
The priming step (`priming_schema.py`) writes the same outline for every topic and two quiz items: "In one sentence, what is <topic>?" answered with "<topic> is a durable concept learned via Priming schema (outline + prerequisites + goals) before deep detail.", and "Where should Priming write durable knowledge for <topic>?" answered with "Wiki schema/outline note and memory.db ledger anchors". Neither tests anything about the topic.

## Goal
Priming writes only content grounded in the topic and Jacob's notes (as CARD-640 does for dual coding), or records progress only.

## Plan and decisions
- Backlog card from the CARD-641 live course run; Jacob approved the build on 2026-10-05.
- Built third: it introduces the shared grounded modules the elaboration, lab and environment cards reuse.
- Same approach as CARD-640: one background model call (think off) with the learner's notes, a grounding check, refused replies that repeat any retired template phrase, and skip reasons no_wiki_notes / model_unavailable / model_output_invalid.
- The priming write-back API (/api/education/priming/writeback) composes the same way and answers 200 with success false and skip_reason when it cannot ground, instead of writing the template.

## Change
- New `grounded.py`: source search (learner notes only; course/priming notes excluded), one model call, JSON parse, grounding helpers and the list of retired template phrases. `dual_coding.py` now uses it (API unchanged).
- New `grounded_steps.py`: per-step specs (`StepSpec`), `validate_step_content`, `compose_step_content` and `compose_course_step` (dispatches dual coding and the spec steps). Priming spec: outline (3-6 key ideas), prerequisites (0-3), question, answer, all checked against the notes.
- `priming_schema.py`: `build_priming_schema_markdown` (fixed outline, prerequisites, goals, two template quiz items) replaced by `build_grounded_priming_markdown` (Key ideas, Before you start, Sources links, Quiz).
- `priming_ledger.priming_writeback` takes `composed`; without grounded content it writes nothing and returns `skipped` with the reason.
- `priming_seed`: a note without a Quiz section seeds no item (the made-up "What is the Priming schema outline for X?" item is gone; this also covers priming notes an agent creates through wiki_note_create).
- `course.py`: priming step passes `composed`; `complete_course_step(composed=...)` is the general grounded-content input (`dual_coding=` still works). The complete-step route composes for the current step via `compose_course_step`.

## What dies
The template priming outline and its quiz items "In one sentence, what is X?" / "Where should Priming write durable knowledge for X?" and the outline fallback item. Items already in a learner's ledger are left alone.

## Proof
- Checks (failing first): template builder and strings gone; no notes, no model, model error, template reply, non-JSON reply and ungrounded answer are skips; a grounded reply is written with source links and only its own quiz item; a course priming step without grounded content writes no note, item or fact and still advances; a note without a Quiz seeds nothing; the write-back API never writes the template.
- Spark probe (nemotron-3.5-lightning, 3 runs on a Raft note): all three grounded and accepted.
- Live: shared full-course check after CARD-642.

## Findings
- `/api/education/construction/generate` (`construction.build_study_artifact_markdown`) writes the same kind of template study artifact (fixed outline, "In one sentence, what is X?" answered "X is a durable concept you can retrieve and apply without chat fluff", a fixed Mermaid diagram). Not part of the course pipeline and no UI caller; filed as backlog.

## Results
| Check | Result | Notes |
|---|---|---|
| tests/unit/education + skills + web | pass | 859 passed (13 new; CARD-317/318/320/322 tests moved to grounded priming input) |
| full pytest | pass | 2630 passed, 12 skipped |
| preflight --fast --base qa | GREEN | ruff, guard 188, vitest 1091 |

## Release note
The priming step now outlines a topic from your own wiki notes (checked against them and linking back); with no notes on the topic or no model it writes nothing instead of the same generic outline and quiz questions for every topic.
