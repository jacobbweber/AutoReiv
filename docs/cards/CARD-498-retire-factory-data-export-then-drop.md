---
id: CARD-498
title: "Retire the Agent Training Factory (4/4): export Factory data on startup, then drop the tables"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-495
  - CARD-496
  - CARD-497
labels:
  - type:migration
  - area:factory
  - area:data
  - P2
---

# [CARD-498] Retire the Agent Training Factory (4/4): export Factory data on startup, then drop the tables

> **Status**: Ready (after CARD-497 and CARD-512, per ADR-0060 4.5). Card decisions D1-D2 below are still to confirm at `build`
> **Created**: 2026-09-25
> **Series**: CARD-495 → CARD-496 → CARD-497 → **CARD-498**
> **Labels**: `type:migration`, `area:factory`, `area:data`, `P2`
> **Note (CARD-520, 2026-09-26)**: also remove the one-release readers of the old remedy name: `LEGACY_TOOL_ESCALATION` and `normalize_remedy_kind` in `domain/observability/models.py`, the fallbacks in `modules/studios/tool_escalation.js` (`data-factory-escalation`, old key), and the distill fallback in `distillation_service.py`. Keep or delete `tool_escalation_migration.py` with them.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** Nobody loses history. If an install has old training jobs, they're saved to a backup file before the tables go away.

**Beat 2: What AutoReiv does now.**
- `schema.py` L381-429 creates `factory_jobs`, `factory_graphs`, `factory_packets` and `factory_eval_runs`, and `prompt_registry.py` L170 creates `factory_phase_instructions`.
- Jacob's live DB (read-only check, 2026-09-25) has **0 rows** in all of them. Other installs may have rows.

**Beat 3: What will change.**
- **Step 1, in the release with CARD-497:** stop creating these tables. On startup, if any exists with rows and `backups/factory-retire-*.json` does not exist yet:
  - export every row as JSON to `backups/factory-retire-<YYYYMMDD-HHMMSS>.json`;
  - log one line with the counts;
  - never block startup on an export failure (log a warning and skip the drop).
- **Step 2, the next release:** `DROP TABLE IF EXISTS` each one, only when the export file exists or the table is empty. Remove the CARD-497 308 redirects.
- The backup scheduler keeps including the export file.

**Beat 4: What dies.** The `factory_*` tables.

## 2. Acceptance criteria (EARS)

- **[REQ-498-001]** WHEN the app starts and a `factory_*` table has rows and no export exists, THE SYSTEM SHALL write `backups/factory-retire-<timestamp>.json` with every row, and log the counts.
- **[REQ-498-002]** IF the export fails, THEN THE SYSTEM SHALL log a warning, keep the tables and continue starting.
- **[REQ-498-003]** WHEN step 2 runs, THE SYSTEM SHALL drop a `factory_*` table only if it is empty or its rows are in an export file.
- **[REQ-498-004]** New installs SHALL NOT create `factory_*` tables.

## 3. Decisions

| # | Decision | Recommendation |
|---|----------|----------------|
| D1 | Export format | **JSON per table** (readable; tiny volumes) |
| D2 | Import back | **No importer** (no UI would read it) |

## 4. Failing-tests-first plan

pytest against a temp data dir:
- with rows: export written, counts logged, tables kept (step 1);
- export failure: startup continues;
- step 2: drop only after export;
- a fresh DB has no `factory_*` tables.

Never run against live AppData.

## 5. Runbook

1. Copy a DB with seeded factory rows into a scratch data dir and start the scratch server.
2. `backups/factory-retire-*.json` appears with the rows.
3. Restart: no second export.
4. On Jarvis, startup logs "0 rows, nothing to export".

## Audit revisions (CARD-495 audit, 2026-09-25)

- Also export, then drop, `factory_phase_instructions` (created in `prompt_registry.py` L170).
- Delete the `factory_jobs` column migrations in `connection.py` L125-130+ in the drop release. Keep fresh installs and upgrades working (migration tests for both).
- If CARD-512 retires the scaffold spine, export and drop `scaffold_spine` (`schema.py` L474) the same way.

## Note from the CARD-497 refinement (2026-09-26)

- CARD-497 (its D7) deletes `FactoryPacketRepository`, its `SQLiteStateStore` mixin and `domain/orchestration/factory_packets.py`, but keeps the tables, their CREATE SQL and column migrations. The export here should therefore read the tables with **plain SQL** (`SELECT *` to JSON per table), not through the repository.
- `factory_phase_instructions` exists only where `prompt_registry.py` ran; that file is deleted in CARD-497. Export and drop it **if present**, and test both cases.
- CARD-497 (D1) adds 308 redirects from the five old Skill Studio paths under `/api/agent_training_factory/`; remove them here.
- Jacob's DB (read-only check, 2026-09-26): 0 rows in `factory_jobs`, `factory_graphs`, `factory_packets`, `factory_eval_runs` and `scaffold_spine`; no `factory_phase_instructions` table.
