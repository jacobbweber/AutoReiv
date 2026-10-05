---
id: CARD-636
title: "Five shipped routines on New York local times; deleted ones stay deleted"
type: feature
status: In Progress
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: [card-636-cut-routines-local-times]
  checks: [tests/unit/routines/test_card636_routine_cut.py, tests/unit/routines/test_routine_scheduler.py, tests/unit/routines/test_skill_eval_sleep.py, tests/unit/skills/test_skill_curator.py, tests/unit/web/test_routine_management_api.py]
branch: feat/card-636-cut-routines-local-times
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-05
related:
  - CARD-635
  - CARD-637
---

# CARD-636 Five shipped routines on New York local times; deleted ones stay deleted

## Intent
Jacob approved the routines cut ("go with your picks"): keep the five routines that do real work, run them overnight on his clock (America/New_York), one model routine at a time, and stop shipped routines from coming back after he deletes them.

## Goal
A fresh or upgraded install has exactly five shipped routines, all enabled, each scheduled for its New York slot across DST, none firing at boot, with the Studio and API showing the schedule the scheduler actually uses.

## Change
- `src/domain/routines/manifests.py`: five routines on local slots (`timezone: America/New_York`, hour, minute, optional `weekdays` in cron convention); cron strings mirror the slot.
  - Nightly SRE Health Pulse (`hourly-sre-pulse`, id kept) daily 02:00.
  - Education retrieval retention daily 02:30 (no model).
  - Wiki curation daily 03:00; its prompt now also does the old nightly hygiene (titles, tags, library index).
  - Weekly note rollover Mondays 04:00 (was 00:00 UTC = 8 PM ET Sunday).
  - Telemetry friction auditor daily 04:30, now enabled, and it also runs the skill-eval job (replay, commit and archive off).
  - `REMOVED_BUILTIN_ROUTINE_IDS`: daily-sysinfo, morning-briefing, nightly-hygiene, skill-eval-sleep, skill-curator.
- `src/application/routines/seed.py` (new): the one shared seed `seed_builtin_routines(store)` used by the web app and the CLI.
  - Guarded one-time migration `migrate_card636` (setting `routines_card636_migrated`): deletes the five removed rows and their `routine_runs`, rewrites the kept rows to the new schedule (keeps approval_mode, run_as_job and job links), and recomputes their next run from now.
  - Deleting a shipped routine records it in setting `deleted_builtin_routines`; the seed never recreates it.
- `matcher.py`: `weekdays` day lists; `describe_schedule` and `next_run_eta`; `sync_local_slot_to_cron` so a Studio cron edit moves the local slot (a cron the slot cannot express drops it, so the cron is used).
- `routers/routines.py`: DELETE remembers shipped ids; list shows `describe_schedule` / `next_run_eta` (it used to humanize the unused UTC cron); PUT syncs the slot on a cron edit.
- `executor.py`: auditor branch also runs `run_skill_eval_job(replay=False)` and appends "Skill eval: ..." to the run output.
- `humanizer.py`: `format_eta`. `routines.js`: builtin fallback ids are the five.

## What dies
- Routines: Daily System Info, Morning Briefing, Nightly Hygiene (merged into wiki curation), Skill eval sleep (merged into the auditor), Skill curator (paused, never used).
- `RoutineScheduler.seed_default_routines`, the two copy-pasted seed loops in `app.py` and `cli/main.py`, and the `day1_routines_seeded` setting.
- Executor branches for skill-curator and skill-eval-sleep; `skill_curator.run_curator_job` and its `job_output_text` (no callers left). `curate_user_skills`, `maybe_curate_from_routine` and the Skills Studio archive tools stay.

## Proof
- Journey `card-636-cut-routines-local-times`: (1) fresh env lists exactly the five, each next run on its New York hour/minute (rollover on a Monday), all enabled, none ran after 25 s; (2) Routines Studio shows "Daily at 02:00 ET" etc. and no UTC or removed routine (screenshot); (3) deleting wiki-curation removes it from the API and the Studio.
- Checks: `test_card636_routine_cut.py` (failing first): five builtins and removed ids gone; next runs from Mon 2026-10-05 6:30 PM ET and across DST end (02:00 ET = 07:00Z after Nov 1); migration deletes removed rows and their run history and rewrites kept rows, once; a deleted builtin is not reseeded (API delete across a restart; custom deletes are not recorded); API human_schedule/next_run_eta; auditor runs skill eval; one shared seed; removed handlers gone; Studio cron edit moves the slot (negative: an unmappable cron drops it).

## Plan and decisions
- Ids kept for the renamed SRE pulse so run history and job links survive.
- Model routines (SRE pulse, wiki curation, weekly rollover, auditor) are at least 30 minutes apart; education retention needs no model.
- The migration is guarded by a setting so it runs once; later edits by Jacob are not overwritten.

## Findings
- (fixed here) `/api/routines` humanized the UTC cron even for local-clock routines, and a Studio cron edit on a local-clock routine was silently ignored.
- The live serve runs with `--reload` from the main checkout, so uncommitted branch edits there hot-load into Jacob's running app. CARD-636 was built in a separate worktree for that reason.
- `tests/unit/orchestration/test_fleet_coordinator.py::test_fleet_coordinator_delegates_to_specialist` depends on the untracked `notes/homelab` tree, so it fails in any clean worktree or CI checkout.

## Results

## Release note
Shipped routines are cut to five that run overnight on New York time (SRE pulse 2:00, education retention 2:30, wiki curation 3:00, weekly note rollover Mondays 4:00, telemetry and skill audit 4:30). Daily System Info, Morning Briefing, Nightly Hygiene and the two paused skill routines are removed with their run history, and a shipped routine you delete stays deleted.
