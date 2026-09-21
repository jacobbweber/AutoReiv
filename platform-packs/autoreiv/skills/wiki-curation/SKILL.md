---
name: Wiki Vault Curation & Archiving
description: Deep vault maintenance, inbox graduation, template conformance, deduplication, and archival versioning.
version: 1.0.0
tier: platform
requires_tools:
  - wiki_note_organize
  - wiki_note_update
  - wiki_note_archive
  - wiki_template_list
  - wiki_template_read
  - wiki_overview
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Curation preserves superseded notes in 03_Archive/ and enforces Degree/Class taxonomy.
---

# Wiki Vault Curation & Archiving (wiki-curation)

Manage the lifecycle of knowledge notes: graduate staged items from `00_Inbox/` to `01_Notes/`, check template conformance, merge duplicate topics, and preserve historical versions in `03_Archive/`.

## Core Invariants
1. **Zero Data Loss**:
   - Before rewriting or merging into an existing graduated note in `01_Notes/`, call `wiki_note_archive(relative_path, reason=...)` to snapshot the previous state in `03_Archive/<slug>_<timestamp>.md`.
2. **Two-Depth Warehouse**:
   - Notes in `01_Notes/` are filed strictly under `01_Notes/<domain>/<topic>/<slug>.md`.

## Available Tools
- `wiki_note_organize`: Move a note from `00_Inbox/` into a specific degree domain and subject topic.
- `wiki_note_update`: Edit or append to an existing note, optionally setting `backup_to_archive=True`.
- `wiki_note_archive`: Move a superseded, deprecated, or historical note into `03_Archive/`.
- `wiki_template_list`: Discover structured note templates.
- `wiki_template_read`: Read a template skeleton by slug.
- `wiki_overview`: Inspect recent vault activity and note distribution.

## Workflow Order
1. List inbox notes to triage.
2. For each note, check for high semantic overlap in `01_Notes/`.
3. If merging into an existing note, archive the existing snapshot first, then append new sections and merge frontmatter tags.
4. If novel, organize into `01_Notes/<domain>/<topic>/`.

## Done-when
- Inbox notes are graduated, superseded files are preserved in `03_Archive/`, and tags are reconciled.
