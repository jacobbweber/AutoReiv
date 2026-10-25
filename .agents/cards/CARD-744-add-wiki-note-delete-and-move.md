---
id: CARD-744
title: "Add HITL-gated wiki_note_delete and wiki_note_move to wiki-curation and prune empty topic folders"
type: feature
status: Done
priority: P2
milestone: M34
needs_decision: none
proof:
  journeys: [card-744-add-wiki-note-delete-and-move]
  checks: [tests/integration/test_card744_wiki_note_delete_and_move.py]
branch: feat/card-744-add-wiki-note-delete-and-move
log: {minutes: 18, qa_runs: 2, findings: 1}
created: 2026-10-24
---

# CARD-744 Add HITL-gated wiki_note_delete and wiki_note_move to wiki-curation and prune empty topic folders

## Intent
When curating or reorganizing notes in the Wiki vault, `AutoReiv` previously only had `wiki_note_create` and `wiki_note_update`, leaving empty stub files and orphaned topic folders behind when migrating notes across domains and forcing the operator to ask `AutoReiv` to author custom deletion scripts. Built-in, HITL-gated `wiki_note_delete` and `wiki_note_move` tools in `wiki-curation` let `AutoReiv` cleanly move or remove notes and automatically prune empty parent topic folders.

## Goal
The operator can ask `AutoReiv` in Chat to move or delete a wiki note in `00_Inbox/` or `01_Notes/`, approve the HITL confirmation card, and have the note moved or deleted on disk and in the wiki index with any now-empty parent topic/domain directory under `01_Notes/` or `00_Inbox/` automatically removed.

## Change
- `src/domain/wiki/store.py`, `src/domain/wiki/note_ops.py`: extract note mutation/curation operations (`archive_note`, `organize_note`, `move_note`, `remove_note`, `delete_note`, `delete_folder`, `prune_empty_parents`) into `src/domain/wiki/note_ops.py` with path-traversal jailing under the vault root and automatic pruning of empty parent directories up to (but never including) top-level vault roots (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`).
- `src/application/skills/wiki_tools.py`, `src/application/skills/wiki_note_helpers.py`, `src/application/safety/tool_policy_gate.py`, `src/application/kernel/tool_access.py`: register `wiki_note_delete` (`risk="destructive"`, HITL confirmation required) and `wiki_note_move` (`risk="write"`, HITL confirmation required).
- `src/application/kernel/react_loop.py`, `src/application/kernel/reply_rules.py`: record deferred `Role.TOOL` messages (`record_deferred_sibling_tool_calls`) for remaining sibling tool calls when an earlier tool call in a multi-tool assistant batch parks for HITL approval so the model executes the remaining tool calls upon resume.
- `platform/skills/wiki-curation/SKILL.md`: add `wiki_note_delete` and `wiki_note_move` to `tools:` and document when to move vs archive vs permanently delete a note.

## What dies
- Nothing.

## Proof
- Journey `card-744-add-wiki-note-delete-and-move`:
  1. Creates notes in nested topic folders (`01_Notes/general/temp_move_topic/splunk_move_note.md` and `01_Notes/general/temp_delete_topic/splunk_stub_note.md`), moves one and deletes the other through `AutoReiv` with HITL approval, and verifies the moved note, deleted stub, and pruned empty topic/domain folders on disk and in the Wiki UI tree on desktop and phone.
- Checks: `tests/integration/test_card744_wiki_note_delete_and_move.py`.

## Plan and decisions
- Approved by Jacob (`Option A`): Add HITL-gated `wiki_note_delete` and `wiki_note_move` to `wiki-curation` with automatic pruning of empty parent topic folders (never top-level PARA folders).

## Findings
- Fixed in-area (`src/application/kernel/react_loop.py`, `src/application/kernel/reply_rules.py`): When the model emitted multiple tool calls in a single assistant message (e.g. `wiki_note_move` + `wiki_note_delete`) and the first tool call paused for HITL approval, the remaining sibling tool calls had no `Role.TOOL` result saved in history, causing the model to assume on resume that both had already executed. Fixed via `record_deferred_sibling_tool_calls`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-744-add-wiki-note-delete-and-move` | desktop | PASS | `/tmp/autoreiv-qa/card-744/card-744-add-wiki-note-delete-and-move-desktop-02-in-chat-autoreiv-mounts-wiki-curation-and-runs-w.png`, `/tmp/autoreiv-qa/card-744/card-744-add-wiki-note-delete-and-move-desktop-03-verify-wiki-studio-reflects-the-updated-vault-tr.png` |
| `card-744-add-wiki-note-delete-and-move` | phone | PASS | `/tmp/autoreiv-qa/card-744/card-744-add-wiki-note-delete-and-move-phone-02-in-chat-autoreiv-mounts-wiki-curation-and-runs-w.png`, `/tmp/autoreiv-qa/card-744/card-744-add-wiki-note-delete-and-move-phone-03-verify-wiki-studio-reflects-the-updated-vault-tr.png` |

## Release note
- **Added**: Added HITL-gated `wiki_note_delete` and `wiki_note_move` tools to `wiki-curation` with automatic pruning of empty parent topic folders (`CARD-744`).

