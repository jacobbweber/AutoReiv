---
id: CARD-583
title: "Quiz extraction finds 0 items in a quiz written from the shipped education-quiz template"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: fix/card-583-quiz-extract-template-items
related:
  - CARD-242
labels:
  - type:bug
  - area:education
  - P2
needs_decision: none
milestone: M24
---

# [CARD-583] Quiz extraction finds 0 items in a quiz written from the shipped education-quiz template

> **Status**: Done (merged into qa 2026-09-29)
> **Labels**: `type:bug`, `area:education`, `P2`

## Why

Found in the 2026-09-29 battery test (throwaway :8770, Tutor quiz-turn skill on Spark, "Quiz me on the Kubernetes basics
note"). `education_quiz_extract` returned 0 items for the plain note, so the Tutor added a `## Quiz` section in the shipped
`education-quiz` template format (`### Item N` / `- **Prompt:** ...` / `- **Expected Binary Answer:** ...`) and extracted
again: still 0. `extract_quiz_items_from_note` only reads `- Q: ... / A: ...` bullets, so a quiz written from the product's
own template never yields items. The Tutor worked around it by upserting five mastery items by hand.

## Change

- `src/application/education/quiz_engine.py`: also read `Prompt` / `Expected (Binary) Answer` bullet pairs (bold
  optional); unfilled template placeholders like `[Exact question prompt]` are skipped. Q/A bullets unchanged.
- Tests `tests/unit/education/test_card583_quiz_template_items.py` (template-style and plain cases fail on the old code).

## Acceptance

- [x] A note with template-style quiz items extracts one item per Prompt / Expected Binary Answer pair.
- [x] The raw template (placeholders only) extracts nothing; Q/A notes still work.

## Not in this card (product question)

`education_quiz_extract` does not write questions for a note without a quiz section; the Tutor had to author them. Whether
extraction should generate questions from any note is Jacob's call (see battery report).

## Log

- 2026-09-29: fixed on the branch with tests.
- 2026-09-29: preflight --fast --base qa GREEN. Jacob: merge to qa (battery brief allows merging small fixes). Done; merged into qa.
