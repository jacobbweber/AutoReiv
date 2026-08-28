# Vertical Slice Tasks: Weekly Notes Rollover Routine & Markdown Task Skill

> **Card ID**: [`CARD-057`](file:///d:/Projects/Active/AutoReiv/.github/cards/CARD-057-weekly-notes-rollover-routine-and-markdown-task-skill.md)  
> **Spec**: `docs/specs/weekly-notes-rollover-and-task-skill/`  
> **Status**: Ready

---

## Vertical Slices

### Slice 1: Weekly Notes Skill & Task Carry-Over Engine
- [ ] Task 1.1: [REQ-WNOTE-001] Seed default weekly note template in `data/wiki/03_Resources/templates/weekly_notes.md` with date placeholders.
- [ ] Task 1.2: [REQ-WNOTE-002, REQ-WNOTE-003] Implement `WeeklyNotesSkill` in `src/application/skills/weekly_notes_skill.py`:
  - `get_or_create_weekly_note(week_str)`
  - `log_daily_work_item(day, item_text, is_completed, section)`
  - `complete_weekly_task(task_text, day)`
  - `rollover_weekly_tasks(from_week, to_week)`
  - `get_weekly_summary(week_str)`
- [ ] Task 1.3: [REQ-WNOTE-005] Write unit test suite `tests/unit/skills/test_weekly_notes_skill.py` (Red $\to$ Green).

### Slice 2: Autonomous Rollover Routine
- [ ] Task 2.1: [REQ-WNOTE-004] Register `weekly_note_rollover` in `src/domain/routines/manifests.py` (`0 0 * * 1` cron).
- [ ] Task 2.2: [REQ-WNOTE-004] Add `rollover_weekly_notes` handler in `src/application/routines/executor.py`.
- [ ] Task 2.3: [REQ-WNOTE-005] Write unit tests in `tests/unit/routines/test_weekly_rollover_routine.py`.

### Slice 3: Skill Pack & Agent Profile Realignment
- [ ] Task 3.1: [REQ-WNOTE-002] Update `BUILTIN_SKILL_PACKS` in `src/application/skills/manifest.py` to replace `tasks` with `Weekly Notes & To-Dos`.
- [ ] Task 3.2: [REQ-WNOTE-002] Update `ASSISTANT_PROFILE` and `AUTOREIV_PROFILE` in `src/domain/agents/profiles.py`.
- [ ] Task 3.3: [REQ-WNOTE-002] Wire `WeeklyNotesSkill` into `BuiltinAgentRegistry.bootstrap` in `src/infrastructure/agents/registry.py`.

### Slice 4: Comprehensive Verification & DoD Gate
- [ ] Task 4.1: [REQ-WNOTE-005] Run Pytest, Vitest, ESLint, and Playwright smoke tests.
- [ ] Task 4.2: [REQ-WNOTE-005] Synchronize `docs/rtm.json` with `[REQ-WNOTE-001]` to `[REQ-WNOTE-005]`.
- [ ] Task 4.3: [REQ-WNOTE-005] Run pre-flight verification script and commit to `qa`.
