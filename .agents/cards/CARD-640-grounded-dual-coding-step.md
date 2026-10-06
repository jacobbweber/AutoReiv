---
id: CARD-640
title: "Dual coding course step is built from your wiki notes on the topic, or writes nothing"
type: bug
status: Done
completed: 2026-10-05
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: [card-640-dual-coding-grounded-or-skipped]
  checks: [tests/unit/education/test_card640_grounded_dual_coding.py]
branch: feat/card-640-grounded-dual-coding
log: {minutes: 60, qa_runs: 2, findings: 1}
created: 2026-10-05
related:
  - CARD-321
  - CARD-639
  - CARD-641
---

# CARD-640 Dual coding course step is built from your wiki notes on the topic, or writes nothing

## Intent
The dual coding course step writes the same template for every topic: a fixed paragraph ("Dual Coding for X pairs verbal concept definitions with visual relational models..."), a fixed four-box diagram (X, Key Concepts and Invariants, Concrete Implementation Flow, Verified Mastery and Application), and a quiz item asking "What are the two representations used in Dual Coding for X?" with the answer "verbal prose and visual diagrams". None of it says anything about the topic.

## Goal
The dual coding step produces content grounded in the topic and in Jacob's own material, or writes nothing. Simple and honest beats generated filler.

## Change
- New `src/application/education/dual_coding.py`:
  - Find source notes: search the wiki for the topic, skip notes the course pipeline wrote itself ("Course ..." and "Priming: ..." notes, notes tagged course or priming), and keep up to three notes that actually mention the topic.
  - Compose: one call to the configured model (the Spark model on Jarvis) with those notes as the only source, asking for a short explanation, a Mermaid flowchart, a step-through, and one question with its answer, all taken from the notes.
  - Check the reply: the diagram must be a flowchart with at least three labelled boxes whose labels use words from the notes, the explanation must not be empty, and the question and answer must be present with the answer using words from the notes.
- The course step writes the note (with links to the source notes) and the quiz item only when that check passes. With no matching notes, no model, a model error, or a reply that fails the check, the step writes nothing, says why (`skip_reason`: no_wiki_notes, model_unavailable, model_output_invalid), and the course still moves on.
- `/api/education/course/complete-step` composes the content when the course is on the dual coding step; `/api/education/course/dual-coding/preview` uses the same grounded path and returns the skip reason instead of a template.
- The fixed template function `build_dual_coding_preview` is removed.

## What dies
The fixed dual coding paragraph, the fixed four-box diagram and the "two representations" quiz item.

## Proof
- Journey `card-640-dual-coding-grounded-or-skipped` on a throwaway server with the Spark model: a course on a topic with no wiki notes skips dual coding and writes nothing; after adding a real note on a topic, dual coding writes a note whose diagram and quiz use words from that note and link to it.
- Checks (failing first): no matching notes means no note, no quiz item, no memory fact and the course advances; a fake model reply grounded in the note is written with source links; a generic reply (the old template) is refused; a model error is a skip; course-written notes are not used as sources.

## Plan and decisions
- Engineering call: ground in wiki notes plus one model call, and skip whenever grounding is not possible. No fallback template.

## Findings
- Course step notes put their metadata lines (tags, kind, step, topic, created) in the note body, so the Wiki shows them as one run-on paragraph, and the Wiki meta line calls a dual coding note `priming_schema`. True of every course step note, not just dual coding. Filed as backlog CARD-645.
- First live run: the phone Wiki step timed out on a click while the note was already open (the list re-renders). The journey now checks the opened note; second run green.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-640-dual-coding-grounded-or-skipped | desktop | pass | live_qa :8770 with Spark nemotron-3.5-lightning. "Bloom filter false positives" (no notes): skip_reason no_wiki_notes, nothing written, course moves to retrieval. After adding a Raft note: dual coding written in 3 s, explanation and flowchart (Leader, Followers, AppendEntries, accept if previous index matches) taken from the note, links `[[00_Inbox/raft_log_replication]]`; quiz "What condition must a follower's log satisfy to accept an AppendEntries message from the leader?"; note opens in the Wiki Studio |
| card-640-dual-coding-grounded-or-skipped | phone | pass | same |
| tests/unit/education + skills | - | pass | 615 passed (10 new checks, failing first; CARD-321 and CARD-322 tests now hand in grounded content) |
| preflight --fast --base qa | - | GREEN | ruff, eslint, guard 188, vitest 1091 |

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\course-filler\card-640\`
- `card-640-dual-coding-grounded-or-skipped-desktop-03-the-note-shows-in-the-wiki-studio.png`
- `card-640-dual-coding-grounded-or-skipped-phone-03-the-note-shows-in-the-wiki-studio.png`

## Release note
The dual coding course step now builds its explanation, diagram and quiz question from your own wiki notes on the topic; when you have no notes on it, or the model cannot produce a grounded answer, it writes nothing instead of a generic template.
