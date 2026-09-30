---
id: CARD-589
title: "wiki_note_list category filter matches the numbered vault folders (it listed nothing for 'notes')"
status: In Review
created: 2026-09-30
branch: card/589-wiki-list-category
related:
  - CARD-582
labels:
  - type:bug
  - area:wiki
  - P2
needs_decision: none
milestone: M24
---

# [CARD-589] wiki_note_list category filter matches the numbered vault folders (it listed nothing for 'notes')

> **Status**: In Review
> **Labels**: `type:bug`, `area:wiki`, `P2`

## Why

2026-09-30 battery (ar-07 "List my wiki notes ..."): AutoReiv called `wiki_note_list(category="notes")` and got `[]`
although `01_Notes/kubernetes-basics.md` exists; it fell back to search. The tool's category enum is
`notes | inbox | resources`, but `WikiStore.list_notes` compared it as a path prefix, and the scaffolded vault numbers
its folders (`00_Inbox/`, `01_Notes/`, `02_Resources/`), so every category listed nothing. Same family as CARD-582.

## Change

- `store.py`: `_category_prefixes()` maps `inbox` / `notes` / `resources` / `archive` to the numbered folder and the
  legacy folder (`01_Notes/` or `notes/` ...); a folder name (`01_Notes`, `Notes/`) works too; anything else stays a
  plain prefix. Used by the tool and `GET /api/wiki/notes?category=`.
- Tests: `tests/unit/wiki/test_card589_list_category_folders.py`.

## Acceptance

- [x] `category=notes|inbox|resources` lists the numbered folders; folder names and legacy folders still match.
- [x] Live: `wiki_note_list(category="notes")` lists 01_Notes in the throwaway (see Log).

## Log

- 2026-09-30: built on the branch with tests.
- 2026-09-30 (live, throwaway :8770 on qa + 589/590/591, nemotron): ar-07 `wiki_note_list(category="notes")` returned the 01_Notes notes (was `[]` on qa).
