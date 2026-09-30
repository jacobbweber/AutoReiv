---
id: CARD-582
title: "wiki_note_organize files notes into the legacy notes/ tree instead of 01_Notes/"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: fix/card-582-organize-into-01-notes
related:
  - CARD-173
  - CARD-406
labels:
  - type:bug
  - area:wiki
  - P2
needs_decision: none
milestone: M24
---

# [CARD-582] wiki_note_organize files notes into the legacy notes/ tree instead of 01_Notes/

> **Status**: Done (merged into qa 2026-09-29)
> **Labels**: `type:bug`, `area:wiki`, `P2`

## Why

Found in the 2026-09-29 battery test (throwaway :8770, AutoReiv wiki_tasks skill on Spark, "create this week's weekly
note in 01_Notes"). The note was staged in `00_Inbox/`, then `wiki_note_organize` moved it to
`notes/weekly/worklog/w40_2026_w40.md`: a new top-level `notes/` folder in a vault that has `01_Notes/`.
`WikiStore.organize_note` hard-coded `notes/`, while graduation already uses `01_Notes` when it exists and vault
curation (CARD-173/406) migrates the legacy `notes/` tree away. The reply then reported the legacy path as the note's home.

## Change

- `src/domain/wiki/store.py` `organize_note`: target `01_Notes/<domain>/<topic>/` when `01_Notes/` exists, else `notes/`
  (legacy vault), the same rule as graduation.
- Tests `tests/unit/skills/test_card582_organize_into_01_notes.py` (the scaffolded-vault case fails on the old code);
  `test_librarian_tools.py` now expects `01_Notes/` for its scaffolded vault.

## Acceptance

- [x] Organizing an inbox note in a scaffolded vault lands in `01_Notes/...` and creates no `notes/` folder.
- [x] A legacy vault without `01_Notes/` still uses `notes/`.

## Log

- 2026-09-29: fixed on the branch with tests.
- 2026-09-29: preflight --fast --base qa GREEN. Jacob: merge to qa (battery brief allows merging small fixes). Done; merged into qa.
- 2026-09-29: battery triage: live on the throwaway after the merge: AutoReiv's weekly note went 00_Inbox/week_40_2026_w40.md -> 01_Notes/weekly/worklog/week_40_2026_w40.md; no notes/ folder
