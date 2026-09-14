# [CARD-310] Routines structured schedule + full agent pickers

> **Status**: In Review
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Depends on**: CARD-309
> **Labels**: `type:feature`

## 1. Why / Intent
Jacob wants calendar-feel click UI (months, weekdays, days-of-month, time) plus biweekly with anchor date — one durable JSON schedule rule, not a scraped upcoming-dates table. Both Routines agent dropdowns must list every agent via `GET /api/agents` (same as Agent Studio), not routine-derived IDs or a 3-agent fallback.

## 2. Three Beats
- **Jacob means**: calendar-feel click UI + biweekly; see all agents.
- **Now**: cron string + presets (CARD-309); filter agents from routine list only; create select may fall back to 3 agents.
- **Change**: structured rule + matcher; full agent lists.

## 3. What to Build
- `ScheduleType.STRUCTURED` + durable `schedule_rule` (stored in `metadata["schedule_rule"]`, exposed via API).
- Rule shape: `{ months, weekdays, days_of_month, hour, minute, every_n_weeks, anchor_date }` — null/empty = any.
- When cron-representable (`every_n_weeks` ≤ 1 and no exotic combo), also set `cron_expression`; else null / UI "custom structured (not pure cron)".
- Extend `ScheduleMatcher` for structured next-fire / is_due (pure, unit-tested biweekly).
- API create/update accept `schedule_rule`; list returns it + `next_run_at` + cron when present; thin `POST /api/routines/preview-schedule`.
- UI: clickable months/weekdays/DOM/time/every-N-weeks+anchor; keep Advanced cron optional; live next-fire + cron preview.
- Filter + create agent dropdowns always from `/api/agents`.

## 4. Acceptance Criteria (Definition of Done)
- [x] Click months/weekdays/DOM/time/every-N-weeks → saved `schedule_rule` durable
- [x] Biweekly-style rule → `next_run_at` computed from rule (not scraped table)
- [x] Pause/disable blocks next fire (`enabled=false`)
- [x] Both agent dropdowns show ALL agents from `/api/agents`
- [x] Cron preview when representable
- [x] Pytest matcher structured/biweekly green
- [x] Vitest agent population + schedule UI chrome ids green
- [x] `node --check` routines.js; cache-bust bump; CHANGELOG [Unreleased]
- [x] HTTP smoke after `restart_serve.py`

## 5. Constraints
- One card. No FF to qa/main. No reset qa.
- Scratch helpers under `scratch/` only.
- Live data stays under `AUTOREIV_DATA_DIR`.
- Conventional commits. Leave dirty `uv.lock` uncommitted if it changes.
