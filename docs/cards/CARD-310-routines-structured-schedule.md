# [CARD-310] Routines structured schedule + full agent pickers

> **Status**: In Review
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-14

## Intent
Visual click-to-build schedule (months / weekdays / DOM / time / every-N-weeks + anchor) persisted as one `metadata.schedule_rule` JSON. Matcher computes next fire. No scraped upcoming-dates table. Filter + create agent dropdowns = full `/api/agents` roster.

## Acceptance
- [x] Structured schedule UI boxes
- [x] Durable schedule_rule on save
- [x] next_run from rule including biweekly
- [x] Cron preview only when representable
- [x] Both agent dropdowns from full /api/agents
- [x] enabled=false blocks due
