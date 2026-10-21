---
name: Wiki Vault Curation & Archiving
description: Deep vault maintenance, inbox graduation, template management, deduplication, and archival versioning.
tools:
- wiki_note_organize
- wiki_note_update
- wiki_note_archive
- wiki_template_list
- wiki_template_read
- wiki_template_create
- wiki_template_update
- wiki_overview
version: 1.1.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Curation preserves superseded notes in 03_Archive/ and enforces Degree/Class taxonomy.
---

# Wiki Vault Curation & Archiving (wiki-curation)

Manage the lifecycle of knowledge notes and structured note templates: graduate staged items from `00_Inbox/` to `01_Notes/`, author or update templates in the agent's template folder, merge duplicate topics, and preserve historical versions in `03_Archive/`.

## Progressive References (`skill_view`)
- `skill_view(skill_id="wiki-curation", reference="templates-guide.md")`: Authoring, updating, and organizing structured note templates (`wiki_template_list`, `wiki_template_read`, `wiki_template_create`, `wiki_template_update`) in `02_Resources/_Templates/`.

## Core Invariants
1. **Zero Data Loss**:
   - Before rewriting or merging into an existing graduated note in `01_Notes/`, call `wiki_note_archive(relative_path, reason=...)` to snapshot the previous state in `03_Archive/<slug>_<timestamp>.md`.
2. **Two-Depth Warehouse**:
   - Notes in `01_Notes/` are filed strictly under `01_Notes/<domain>/<topic>/<slug>.md`.
3. **Templates Stay in `_Templates/`**:
   - Use `wiki_template_create` and `wiki_template_update` for templates; never call `wiki_note_create` to create a template.

## Available Tools
- `wiki_note_organize`: Move a note from `00_Inbox/` into a specific degree domain and subject topic.
- `wiki_note_update`: Edit or append to an existing note, optionally setting `backup_to_archive=True`.
- `wiki_note_archive`: Move a superseded, deprecated, or historical note into `03_Archive/`.
- `wiki_template_list`: Discover structured note templates.
- `wiki_template_read`: Read a template skeleton by slug.
- `wiki_template_create`: Create a new structured note template in this agent's template folder.
- `wiki_template_update`: Modify an existing template's title, description, content, or tags.
- `wiki_overview`: Inspect recent vault activity and note distribution.

## Workflow Order
1. List inbox notes to triage (or call `wiki_template_list` when managing templates; see `references/templates-guide.md`).
2. For each note, check for high semantic overlap in `01_Notes/`.
3. If merging into an existing note, archive the existing snapshot first, then append new sections and merge frontmatter tags.
4. If novel, organize into `01_Notes/<domain>/<topic>/`.

## Done-when
- Inbox notes are graduated, superseded files are preserved in `03_Archive/`, or requested note templates are created/updated in `_Templates/`.
