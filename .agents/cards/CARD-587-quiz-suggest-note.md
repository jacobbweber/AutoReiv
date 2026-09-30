---
id: CARD-587
title: "Tutor quiz: extraction suggests questions into a separate quiz note (never edits the source); plain notes work"
status: In Review
created: 2026-09-29
branch: card/587-quiz-suggest-note
related:
  - CARD-583
  - CARD-438
labels:
  - type:feature
  - area:education
  - P2
needs_decision: none
milestone: M24
---

# [CARD-587] Tutor quiz: extraction suggests questions into a separate quiz note (never edits the source); plain notes work

> **Status**: In Review
> **Labels**: `type:feature`, `area:education`, `P2`

## Why

2026-09-29 battery (tu-02 "Quiz me on the Kubernetes basics note"): `education_quiz_extract` returned 0 items for a
plain note, so the Tutor wrote a Quiz section into Jacob's own note (through approval) and upserted items by hand.
Jacob (2026-09-29): quiz_extract suggests questions and saves them in a separate quiz note; never edit the source note;
fix the plain-note case.

## Change

- `quiz_engine.py`: `suggest_quiz_items_from_note()` turns definition lines (`- **Term**: meaning`, `- Term: meaning`,
  `- **Term** - meaning`) into "Which term matches this description: <meaning>?" -> `<term>` (the grader is an exact
  match, so answers stay short); `quiz_note_path_for()` (`<note>-quiz.md` next to the source); `render_quiz_note()` in
  the shipped education-quiz format with a link back to the source.
- `education_quiz_extract`: new `questions=[{prompt, answer}]` and `quiz_path`. A note with its own quiz items works as
  before. Otherwise the agent's questions, or the suggestions, are merged into the separate quiz note, extracted from
  there and saved to mastery. A prose note without definitions returns `needs_questions` with a hint (write 3-7
  short-answer questions and call again); nothing is written. `quiz_path` cannot be the source note; the result always
  says `source_edited: false`.
- `quiz-turn` skill 1.2.0: step 1 says the same and forbids editing the source note.

## Acceptance

- [x] Plain note with definitions -> `<note>-quiz.md` created, items saved, source bytes unchanged.
- [x] Prose note -> `needs_questions`, nothing written; agent questions are saved, merged without duplicates, gradeable.
- [x] Notes with their own quiz section unchanged.
- [ ] Live on the throwaway :8770 with the Tutor (see Log).

## Log

- 2026-09-29: built on the branch with tests (`tests/unit/education/test_card587_quiz_suggest_note.py`).
