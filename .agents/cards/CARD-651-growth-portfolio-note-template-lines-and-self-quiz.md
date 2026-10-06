---
id: CARD-651
title: "Growth portfolio note has template lines and a quiz item about its own level"
type: bug
status: Done
priority: P3
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/education/test_card651_growth_portfolio_note.py]
branch: feat/card-651-portfolio-note
log: {minutes: 20, qa_runs: 0, findings: 0}
created: 2026-10-05
completed: 2026-10-06
related:
  - CARD-642
  - CARD-643
  - CARD-646
---

# CARD-651 Growth portfolio note has template lines and a quiz item about its own level

## Intent
`depth.create_growth_portfolio_note` writes a note whose body repeats metadata in a `> **Topic:** / **Generated:**` block (what CARD-645 removed from the course notes), lists the same "Verified definitions and mental models for <topic>" capability lines for every topic, and writes a pre-passed quiz item "What is the current growth portfolio depth level for <topic>?". That is a fact about the app that goes stale, like the pass-rate item CARD-647 removed.

## Goal
The portfolio note keeps its real numbers in front matter or body without the template lines, and writes no quiz item about its own level.

## Plan and decisions
- Backlog card (found while checking the remaining course writers for CARD-642); Jacob approved the build on 2026-10-06.
- The note's metadata (kind education_growth_portfolio, course topic, mastery level/label, academic rank, course step, generated time) moves to front matter, matching the course notes after CARD-645.
- The body holds only real data: level and progress, passed/total/to-review counts, the learner's actual passed and to-review quiz prompts (up to 12 each) and the ladder's next milestone.
- No quiz item is written; the depth stays recorded as the course_growth_portfolio learner fact.

## Change
- `depth.build_portfolio_note_content`: the `> **Topic:** / **Pedagogy Phase:** / **Generated:**` block and the fixed capability lines ("Verified definitions and mental models for X", "Grounded with dual coding ...", "Ledger items tracked under single-brain ...", "Continue through active course pipeline ...") removed; body is Where you are / Your quiz items (Passed, To review) / Next milestone from the ledger.
- `create_growth_portfolio_note`: reads the topic's quiz items for the note, writes the metadata as front matter and no longer upserts the pre-passed "What is the current growth portfolio depth level for X?" item.
- CARD-327 test updated to the new body and front matter.

## What dies
The template portfolio lines, the body metadata block and the self-referential quiz item. Items already in a learner's ledger are left alone.

## Proof
- Checks (failing first): front matter carries kind, topic, level and rank; no template lines or body metadata; the body lists the learner's real passed and to-review prompts and counts; creating the note adds no quiz item and still records the learner fact.
- Live: the portfolio route is not part of the course run; covered by unit and route tests.

## Results
| Check | Result | Notes |
|---|---|---|
| full pytest | pass | __PYTEST__ |
| preflight --fast --base qa | GREEN | __FAST__ |

## Release note
The growth portfolio note now shows your real level and the quiz items you have passed or need to review, keeps its details in the note's properties, and no longer adds a quiz question about its own level.
