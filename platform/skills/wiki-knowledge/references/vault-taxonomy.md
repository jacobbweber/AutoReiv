# Wiki Vault Taxonomy (`vault-taxonomy.md`)

AutoReiv's Markdown Wiki vault (`$DATA_DIR/wiki/`) enforces a strict four-folder architecture so staged drafts, graduated notes, reusable templates, and historical snapshots never collide.

## Folder Layout
1. `00_Inbox/` — **One-Door Staging**:
   - All newly created notes (`wiki_note_create`) land in `00_Inbox/<slug>.md` with `status: inbox`.
   - Never bypass `00_Inbox/` when capturing new notes, research, or study artifacts.
2. `01_Notes/<domain>/<topic>/<slug>.md` — **Graduated Two-Depth Warehouse**:
   - Curated, verified notes live under a degree/domain folder and a subject/topic folder (`wiki_note_organize`).
   - Weekly operational checklists live under `01_Notes/weekly/YYYY-Www.md` (`wiki_tasks`).
3. `02_Resources/_Templates/<Folder>/<slug>.md` — **Agent-Scoped Templates**:
   - Each agent reads and writes only its own configured `template_folder` (e.g., `02_Resources/_Templates/General` for AutoReiv, `02_Resources/_Templates/Education` for Tutor) via `wiki_template_*`.
   - Templates are never stored inside `00_Inbox/` or `01_Notes/`.
4. `03_Archive/<slug>_<timestamp>.md` — **Zero-Data-Loss History**:
   - Superseded or merged notes are snapshotted to `03_Archive/` (`wiki_note_archive` or `wiki_note_update(..., backup_to_archive=True)`) before major rewrites.
