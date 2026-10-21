# Weekly Worklog & Rollover Protocol (`weekly-rollover.md`)

Use this reference when initializing a new ISO week note (`01_Notes/weekly/YYYY-Www.md`), updating daily task checklists, or rolling unfinished tasks forward.

## ISO Week Naming & Structure
- Every weekly note lives at `01_Notes/weekly/YYYY-Www.md` (for example `01_Notes/weekly/2026-W43.md`).
- When initializing a missing week, call `wiki_template_read("weekly_notes")` first and pass `template="weekly_notes"`, `domain="weekly"`, `topic="worklog"` to `wiki_note_create`.

## Checklist & Carry-Over Rules
1. **Open vs. Completed Tasks**:
   - Open task: `- [ ] <description>`
   - Completed task: `- [x] <description>`
2. **Weekly Rollover (`### Carry-Over`)**:
   - Read the prior week's note (`01_Notes/weekly/YYYY-W(ww-1).md`).
   - Collect all remaining `- [ ]` lines (do not copy `- [x]` items).
   - Place them under `### 🔄 Carry-Over` at the top of the current week's note via `wiki_note_update`.
3. **Separation of Concerns**:
   - Never log system health dumps or architecture essays into `01_Notes/weekly/`; those belong in `00_Inbox/` via `wiki-inbox`.
