---
name: Wiki & Knowledge Vault
description: Structured notes, vault search, feynman templates, and inbox staging.
---

# Wiki & Knowledge Vault

Manage local-first Markdown knowledge in AutoReiv's vault. Enforce structured notes, template conventions, and inbox staging.

## Available Tools

- `wiki_note_read`: Retrieve the markdown content and frontmatter of an existing wiki note.
- `wiki_note_search`: Search notes across titles, tags, and body content.
- `wiki_note_create`: Create a new structured note in the vault (staged in `00_Inbox/` or target topic).
- `wiki_note_update`: Update or append to an existing note.
- `wiki_note_list`: Enumerate notes in the vault by directory or tag.
- `wiki_note_organize`: Move or rename notes across taxonomy folders and manage redirects.
- `list_wiki_templates`: View available vault note templates.
- `wiki_overview`: Generate high-level vault structure overview.
- `wiki_graph`: Return wikilink connection graph across notes.
- `promote_artifact_to_wiki`: Graduate session artifacts into permanent vault notes.

## Workflow Order

1. Search first with `wiki_note_search` to verify whether related notes or prior research already exist.
2. Read related notes with `wiki_note_read` to ground findings on durable vault facts.
3. When creating new notes, check `list_wiki_templates` for standard formatting.
4. Stage new notes cleanly with frontmatter tags and clear headings.

## Pitfalls

- Never fabricate note content; quote or cite verified source paths.
- Check before creating duplicate notes on the same topic.
