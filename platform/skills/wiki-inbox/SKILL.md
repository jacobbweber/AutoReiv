---
name: Wiki Inbox Staging
description: Stage new notes into 00_Inbox/ via the One-Door Policy, or move and delete wiki notes with automatic empty-folder pruning.
tools:
- wiki_note_create
- wiki_note_move
- wiki_note_delete
- promote_artifact_to_wiki
version: 1.1.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: All newly authored notes land strictly in 00_Inbox/ with structured frontmatter; moves and deletions use wiki_note_move and wiki_note_delete.
---

# Wiki Inbox Staging (wiki-inbox)

Stage new knowledge, system health checks, research findings, and session deliverables into the AutoReiv Wiki vault, and relocate or delete notes when requested by the operator.

## Core Invariants
1. **The One-Door Policy**:
   - All newly created notes MUST land in `00_Inbox/` via `wiki_note_create`.
   - Never hijack personal weekly worklogs (`01_Notes/weekly/`).
   - To move a staged note into a specific `01_Notes/<domain>/<topic>/<slug>.md` path or rename/relocate an existing note, call `wiki_note_move(source_path=..., destination_path=...)` (which automatically prunes empty source topic/domain folders).
   - To permanently delete a note or stub, call `wiki_note_delete(relative_path=..., reason=...)` (which requires operator HITL approval and automatically prunes empty parent topic/domain folders). Never use `wiki_note_update` to fake moving or deleting a note.
2. **Templates vs Notes**:
   - Reusable templates are created with `wiki_template_create` and land strictly in `02_Resources/_Templates/<slug>.md`.
   - NEVER call `wiki_note_create` to author a template.
   - To create a note from an existing template, call `wiki_note_create(template="<slug>", ...)`.

## Available Tools
- `wiki_note_create`: Stage a structured note in `00_Inbox/` with title, domain, topic, tags, and summary.
- `wiki_note_move`: Move or rename an existing note in `00_Inbox/` or `01_Notes/`, update its `domain`/`topic` frontmatter, and prune empty source folders.
- `wiki_note_delete`: Permanently delete a note from `00_Inbox/` or `01_Notes/` (HITL-gated) and prune any now-empty parent topic/domain folders.
- `promote_artifact_to_wiki`: Graduate a session artifact directly into an inbox note.

## Workflow Order
1. Check if related research exists first.
2. Formulate clean markdown content without conversational preambles ("Here is what you requested").
3. Call `wiki_note_create(title=..., content=..., domain=..., topic=..., tags=[...], summary=...)`.
4. If the operator asked for the note at a specific path in `01_Notes/...` or asked to move/delete a note, call `wiki_note_move` or `wiki_note_delete` using the exact `path` returned by `wiki_note_create` / `wiki_note_search`.

## Done-when
- Note is safely persisted in `00_Inbox/<slug>.md` (or moved/deleted via `wiki_note_move` / `wiki_note_delete` with empty folders pruned).
