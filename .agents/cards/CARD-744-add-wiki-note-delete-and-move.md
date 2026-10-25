---
id: CARD-744
title: "Add HITL-gated wiki_note_delete and wiki_note_move to wiki-curation and prune empty topic folders"
type: feature
status: Ready
priority: P2
milestone: M34
needs_decision: none
proof:
  journeys: [card-744-add-wiki-note-delete-and-move]
  checks: [tests/integration/test_card744_wiki_note_delete_and_move.py]
branch: feat/card-744-add-wiki-note-delete-and-move
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-24
---

# CARD-744 Add HITL-gated wiki_note_delete and wiki_note_move to wiki-curation and prune empty topic folders

## Intent
When curating or reorganizing notes in the Wiki vault, `AutoReiv` previously only had `wiki_note_create` and `wiki_note_update`, leaving empty stub files and orphaned topic folders behind when migrating notes across domains and forcing the operator to ask `AutoReiv` to author custom deletion scripts. Built-in, HITL-gated `wiki_note_delete` and `wiki_note_move` tools in `wiki-curation` let `AutoReiv` cleanly move or remove notes and automatically prune empty parent topic folders.

## Goal
The operator can ask `AutoReiv` in Chat to move or delete a wiki note in `00_Inbox/` or `01_Notes/`, approve the HITL confirmation card, and have the note moved or deleted on disk and in the wiki index with any now-empty parent topic/domain directory under `01_Notes/` or `00_Inbox/` automatically removed.

## Change
- `src/infrastructure/wiki/store.py`, `src/application/wiki/curation_service.py`: add `delete_note(relative_path)` and `move_note(source_path, destination_path, update_frontmatter=None)` with path-traversal jailing under the vault root and automatic pruning of empty parent directories up to (but never including) top-level vault roots (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`). Also prune empty parent directories in `promote_note`.
- `src/application/skills/wiki_tools.py`, `src/application/agent_skills/schema.py`, `src/application/kernel/tool_access.py`: register `wiki_note_delete` (`requires_hitl=True`, `risk="destructive"`) and `wiki_note_move` (`requires_hitl=True`, `risk="write"`).
- `platform/skills/wiki-curation/SKILL.md`, `platform/skills/wiki-curation/references/curation-rubric.md`: add `wiki_note_delete` and `wiki_note_move` to `tools:` and document when to move vs archive vs permanently delete a note.

## What dies
- Nothing.

## Proof
- Journey `card-744-add-wiki-note-delete-and-move`:
  1. Creates a note in a nested topic folder (`01_Notes/general/temp_topic/stub_note.md`), moves or deletes it through `AutoReiv` with HITL approval, and verifies both the markdown file and the empty `01_Notes/general/temp_topic/` folder are removed from disk and the Wiki UI tree on desktop and phone.
- Checks: `tests/integration/test_card744_wiki_note_delete_and_move.py`.

## Plan and decisions
- Approved by Jacob (`Option A`): Add HITL-gated `wiki_note_delete` and `wiki_note_move` to `wiki-curation` with automatic pruning of empty parent topic folders (never top-level PARA folders).

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- **Added**: Added HITL-gated `wiki_note_delete` and `wiki_note_move` tools to `wiki-curation` with automatic pruning of empty parent topic folders (`CARD-744`).

