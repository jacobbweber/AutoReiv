# Wiki Curation, Templates & Tasks Guide (`curation-and-templates.md`)

Use this reference to pick the right Wiki skill and toolset for each vault operation:

| Job | Skill ID | Mounting | Core Tools |
|---|---|---|---|
| Search, read & graph lookup | `wiki-knowledge` | Pinned | `wiki_note_search`, `wiki_note_read`, `wiki_note_list`, `wiki_graph` |
| Capture new notes into `00_Inbox/` | `wiki-inbox` | Pinned | `wiki_note_create`, `wiki_note_append` |
| Daily tasks & weekly worklogs (`01_Notes/weekly/`) | `wiki_tasks` | Pinned | `wiki_note_read`, `wiki_note_create(template="weekly_notes")`, `wiki_note_update` |
| Create or update note templates | `wiki-templates` | Pinned | `wiki_template_list`, `wiki_template_read`, `wiki_template_create`, `wiki_template_update` |
| Graduate `00_Inbox/` notes, deduplicate & archive | `wiki-curation` | On demand (`skill_view(skill_id="wiki-curation")`) | `wiki_note_organize`, `wiki_note_update`, `wiki_note_archive`, `wiki_overview` |

## Curation Protocol
1. Call `skill_view(skill_id="wiki-curation")` to mount `wiki_note_organize`, `wiki_note_archive`, and `wiki_overview`.
2. Inspect `00_Inbox/` notes (`wiki_note_list(status="inbox")`) and check `01_Notes/` for semantic overlap (`wiki_note_search`).
3. If merging into an existing graduated note, call `wiki_note_archive(relative_path, reason=...)` first so no prior facts are lost.
4. If graduating a distinct topic, call `wiki_note_organize` to move it into `01_Notes/<domain>/<topic>/<slug>.md`.
