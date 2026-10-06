---
id: CARD-645
title: "Course step notes show their metadata as a paragraph and the wrong document type"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: [course-filler-2-full-course-grounded-or-empty]
  checks: [tests/unit/education/test_card645_course_note_front_matter.py]
branch: feat/card-645-course-note-front-matter
log: {minutes: 20, qa_runs: 0, findings: 0}
created: 2026-10-05
completed: 2026-10-05
related:
  - CARD-640
---

# CARD-645 Course step notes show their metadata as a paragraph and the wrong document type

## Intent
Course step notes (dual coding, elaboration, environment, analysis and the rest) write lines such as "tags: [...]", "kind: education_course_step", "step: ...", "topic: ..." and "created: ..." at the top of the note body. The Wiki renders them as one run-on paragraph above the content, and the Wiki meta line labels the note `priming_schema` (the document type every course step note inherits from the priming note writer).

## Goal
Course step metadata lives only in the note's front matter, and each course step note carries a document type that matches its step.

## Plan and decisions
- Backlog card from CARD-640; Jacob approved the build on 2026-10-05.
- Built second so the priming, elaboration, lab and environment rewrites (CARD-646, 644, 643, 642) write the new format from the start.
- Priming keeps document type `priming_schema` (it is the priming schema note); the growth portfolio note (same inherited type) becomes `growth_portfolio`.

## Change
- `priming_wiki_io.create_priming_note` and `construction.create_study_artifact_note` take `document_type` and `extra_frontmatter` (defaults unchanged for their other callers).
- `course.py`: every course step note is written with `document_type: course_<step>` and front matter `kind: education_course_step`, `step`, `course_topic` (helper `_course_note_meta`).
- Removed the body metadata: the dual coding `tags/kind/step/topic/created` lines and the `> **Topic:** / **Pedagogy Phase:** / **Generated:**` blocks at the top of the elaboration, lab, analysis and environment notes. The scorecard keeps a one-line "Scored <time>" and the environment note a one-line delivery profile.
- `depth.py`: growth portfolio note typed `growth_portfolio`.

## What dies
The run-on metadata paragraph at the top of course notes and the `priming_schema` label on non-priming course notes.

## Proof
- Checks (failing first): dual coding, analysis and construction notes have no body metadata lines, the right document type and kind/step in front matter; no `Course ...` note is typed `priming_schema`.
- Live: covered by the shared full-course check after CARD-642.

## Findings
- None new.

## Results
| Check | Result | Notes |
|---|---|---|
| tests/unit/education + skills + web | pass | 848 passed (4 new, failing first) |
| preflight --fast --base qa | GREEN | ruff, guard 188, vitest 1091 |

## Release note
Course notes no longer start with a run-on paragraph of tags and dates; that information is in the note's properties, and each course note is labelled with its own step instead of "priming_schema".
