---
id: CARD-641
title: "Course steps without their own writer record progress only"
type: bug
status: Done
completed: 2026-10-05
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: [card-641-course-steps-record-progress-only]
  checks: [tests/unit/education/test_card641_progress_only_steps.py]
branch: feat/card-641-progress-only-steps
log: {minutes: 35, qa_runs: 1, findings: 2}
created: 2026-10-05
related:
  - CARD-320
  - CARD-639
  - CARD-640
---

# CARD-641 Course steps without their own writer record progress only

## Intent
Course steps that have no writer of their own (retrieval, retention, custom, and any other step name) fall through to a generic writer. It saves a "Course Retrieval: topic" style note built from a knowledge-type template, a quiz item "What Learning OS step did you just complete for topic?" whose answer is the step name, and a memory fact. That is filler in the wiki and in the mastery ledger.

## Goal
Steps without a real writer record progress only: the course moves on, and no wiki note, no quiz or mastery-ledger item and no memory fact are written.

## Change
- `course.py`: replace the generic fallthrough with a progress-only result (`skip_reason: no_writer`, no wiki path, no item ids, no tools used). Steps with their own writers (priming, dual coding, elaboration, construction, application, analysis, environment) are unchanged by this card.

## What dies
The generic "Course X: topic" notes, the "What Learning OS step did you just complete" quiz items and the matching `course_step_X` memory facts for steps without a writer.

## Proof
- Journey `card-641-course-steps-record-progress-only` on a throwaway server with the Spark model: run a course through retrieval and retention; both advance, and no "Course Retrieval" or "Course Retention" note and no "What Learning OS step" quiz item exist.
- Checks (failing first): completing retrieval, retention and custom advances the course and writes no note, no mastery item and no memory fact; the course finishes after retention.

## Plan and decisions
- Built after CARD-640.

## Findings
- The full course run shows template quiz items from steps that do have writers: priming ("Where should Priming write durable knowledge for X?" and a one-sentence definition answered with "X is a durable concept learned via Priming schema..."), analysis ("What is the analysis pass rate and weak item status for X?"), environment (CARD-642) and the two labs ("Perform construction lab for X with verified invariants.", CARD-643). Priming and analysis are filed as backlog CARD-646 and CARD-647.
- The knowledge-type note builder is no longer used by the course pipeline; it is still used by the knowledge artifact preview route, so it stays.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-641-course-steps-record-progress-only | desktop | pass | live_qa :8770 with Spark nemotron-3.5-lightning; whole course on "Raft log replication" (9 steps) after adding a Raft note: retrieval and retention wrote nothing (skip_reason no_writer); dual coding written from the note (quiz "What condition must a follower's log satisfy to accept an AppendEntries message?"); course completed; Wiki lists 6 course notes, none "Course Retrieval" or "Course Retention"; no "What Learning OS step" quiz item among 8 |
| card-641-course-steps-record-progress-only | phone | pass | same |
| tests/unit/education + skills | - | pass | 620 passed (6 new checks, failing first; CARD-322 test updated for retrieval) |
| preflight --fast --base qa | - | GREEN | ruff, eslint, guard 188, vitest 1091 |

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\course-filler\card-641\`
- `card-641-course-steps-record-progress-only-desktop-03-the-wiki-inbox-lists-only-the-course-notes-from-.png`
- `card-641-course-steps-record-progress-only-phone-03-the-wiki-inbox-lists-only-the-course-notes-from-.png`

## Release note
Course steps that have nothing real to write (retrieval, retention, custom) now just record your progress instead of saving a generic note and a "what step did you just complete" quiz item.
