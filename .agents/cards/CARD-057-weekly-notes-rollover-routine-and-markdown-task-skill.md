# [CARD-057] Weekly Notes Rollover Routine and Markdown Task Skill

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/weekly-notes-rollover-and-task-skill/
> **Labels**: `type:feature`, `milestone:21`

---

## 1. Why / Intent
Enable the `assistant` agent to maintain a Markdown-first Obsidian-compatible Weekly Work Log and To-Do system in `data/wiki/01_Notes/weekly/` (with `[[My Dashboard]]` links, daily work logs with `✅ YYYY-MM-DD` timestamps, focusing/ad-hoc/carry-over/done sections). Provide both conversational skill tools for on-demand task logging in Chat Studio and an automated weekly background routine running every Monday at midnight to generate the new week note and roll over all unacknowledged/incomplete tasks.

---

## 2. What to Build
1. **Wiki Template Seeding (`data/wiki/03_Resources/templates/weekly_notes.md`)**:
   - Standard weekly notes markdown template with `{{day:dddd D}}` date placeholders, `[[My Dashboard]]` link, and sections for Projects, Summary (Focusing, Ad-Hoc, Carry-Over, Done), and Daily Work Logs (Monday–Sunday).
2. **Weekly Notes & To-Dos Skill (`src/application/skills/weekly_notes_skill.py`)**:
   - `get_or_create_weekly_note(week_str)`: Calculates week bounds (Mon-Sun), interpolates dates, and auto-imports carry-over tasks.
   - `log_daily_work_item(day, item_text, is_completed, section)`: Appends daily log items with optional `✅ YYYY-MM-DD` timestamp.
   - `complete_weekly_task(task_text, day)`: Marks matching tasks as complete (`- [x]` and `✅ YYYY-MM-DD`).
   - `rollover_weekly_tasks(from_week, to_week)`: Scans un-checked items from previous week into the new week's `Carry-Over` block.
   - `get_weekly_summary(week_str)`: Returns structured summary of active, carried-over, and completed tasks for the week.
3. **Autonomous Routine Manifest (`src/domain/routines/manifests.py`)**:
   - Add built-in routine `weekly_note_rollover` (`0 0 * * 1` Monday midnight) bound to `assistant`.
4. **Skill Pack Realignment (`src/application/skills/manifest.py` & `src/domain/agents/profiles.py`)**:
   - Rebrand `tasks` pack to `Weekly Notes & To-Dos` under Tier 1 (Productivity).
   - Authorize weekly note tools in `ASSISTANT_PROFILE` and `AUTOREIV_PROFILE`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-WNOTE-001]`: Weekly note template seeded in `data/wiki/03_Resources/templates/weekly_notes.md` with date interpolation engine.
- [x] `[REQ-WNOTE-002]`: `WeeklyNotesSkill` provides conversational tools (`get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`, `get_weekly_summary`).
- [x] `[REQ-WNOTE-003]`: Automated task carry-over engine extracts incomplete/unmarked tasks from Week $N-1$ into Week $N$'s `Carry-Over` section.
- [x] `[REQ-WNOTE-004]`: Built-in autonomous routine `weekly_note_rollover` registered in `BUILTIN_ROUTINES` (`0 0 * * 1`).
- [x] `[REQ-WNOTE-005]`: Comprehensive Verification Gate: Pytest unit & integration tests, Vitest, and Playwright smoke tests pass 100% green.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
