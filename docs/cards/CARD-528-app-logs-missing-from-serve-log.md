---
id: CARD-528
title: "App log lines from src.* loggers (INFO and WARNING) do not reach the serve log, so startup migrations cannot be checked from the log"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-520
  - CARD-256
labels:
  - type:bug
  - area:observability
  - area:ops
  - P3
---

# [CARD-528] Startup and app log lines are missing from the serve log

> **Status**: Ready (found in the CARD-520 build, 2026-09-26 ~1:45 PM ET, branch `feat/card-520-tool-escalation`). P3: nothing breaks, but operators cannot see what startup changed.
> **Related**: CARD-520 (startup migration logs its counts), CARD-256 (`scripts/restart_serve.py` writes `.autoreiv-restart-serve.log`)
> **Labels**: `type:bug`, `area:observability`, `area:ops`, `P3`

## Evidence

- `migrate_tool_escalation_names` logs its counts through `logging.getLogger(__name__)`. On a scratch server (`scratch\c505_run.ps1`, port 8767) it rewrote 3 seeded rows, yet neither its stdout/stderr files nor `.autoreiv-restart-serve.log` on serve contain the line; a temporary switch to `logger.warning` did not show either. Only uvicorn's own lines appear. The rows were verified from the database instead (`scratch\c520_mig_check.py`).
- So "the log shows the counts" (CARD-520 runbook step 2) cannot be checked, and the same is true for other startup work (`reset_stranded_training_gaps`, seeders).

## Change

Configure a root handler at app start (level INFO for `src.*`) that writes to stderr, so the serve and scratch logs carry app lines; keep uvicorn's format. Check that Live System Logs still gets its records.

## Done when

After a restart the serve log shows the CARD-520 migration line ("nothing to change" or the counts); a unit test asserts `src.*` INFO records reach a stderr handler.
