---
name: Weekly Work Logs & Task Journaling
description: Maintain Obsidian-compatible Weekly Work Logs, daily reminders, and automated task carry-over using standard Wiki tools.
version: 1.0.0
tier: platform
requires_tools:
  - wiki_note_read
  - wiki_note_create
  - wiki_note_update
  - wiki_template_read
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Weekly worklogs and daily tasks are maintained in 01_Notes/weekly/ using canonical wiki tools.
---

# Weekly Work Logs & Task Journaling (wiki_tasks)

Manage weekly work logs, daily standup items, task checklists (`- [ ]`), and weekly carry-over. Ground all task tracking in the user's weekly notes located at `01_Notes/weekly/YYYY-Www.md` (e.g. `01_Notes/weekly/2026-W39.md`).

## Core Invariants
1. **Never Confuse Tasks with General Notes**:
   - Weekly worklogs are exclusively for daily task tracking, to-do checklists (`- [ ]`), and project goals.
   - General documentation, system health reports, research, and meeting minutes MUST be created via `wiki_note_create` staged into `00_Inbox/`. Never append system health reports into personal weekly work journals.
2. **Deterministic File Location**:
   - Weekly notes live strictly at `01_Notes/weekly/YYYY-Www.md` where `YYYY-Www` is the current ISO week (e.g. `2026-W39`).

## Workflow Order
1. **Inspect / Read Current Week**:
   - Call `wiki_note_read("01_Notes/weekly/YYYY-Www.md")`.
2. **Initialize if Missing**:
   - If `wiki_note_read` indicates the note does not exist, call `wiki_template_read("weekly_notes")` to inspect the canonical structure.
   - Stage the weekly note via `wiki_note_create(title="WEEK WW (YYYY-Www)", content=template_content, template="weekly_notes", domain="weekly", topic="worklog")`.
3. **Log Daily Tasks & Reminders**:
   - Read the existing content with `wiki_note_read`.
   - Append or update the task under the appropriate day heading (e.g. `### Monday 21`) using `wiki_note_update`.
   - Use standard Markdown checkboxes: `- [ ] <task description>`.
4. **Complete Tasks**:
   - Change `- [ ] <task>` to `- [x] <task>` via `wiki_note_update`.
5. **Carry-Over Unfinished Tasks**:
   - When rolling into a new week, read the previous week's note (`YYYY-W(ww-1).md`), find any remaining `- [ ]` tasks, and copy them into `### 🔄 Carry-Over` in the new week's note.

## Done-when
- Weekly worklog exists at `01_Notes/weekly/YYYY-Www.md` and contains the updated task checklist or carry-over state.
