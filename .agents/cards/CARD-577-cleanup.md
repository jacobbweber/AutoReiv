---
id: CARD-577
title: "Cleanup: finish Factory retirement (ADR-0060), one agent-save path, stale wording, obsolete cards"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: chore/card-577-cleanup
related:
  - CARD-498
  - CARD-512
  - CARD-514
  - CARD-515
  - CARD-506
  - CARD-462
  - CARD-529
labels:
  - type:chore
  - area:cleanup
  - P2
needs_decision: none
milestone: M22
---

# [CARD-577] Cleanup: finish Factory retirement, one agent-save path, stale wording, obsolete cards

> **Status**: Done
> **Labels**: `type:chore`, `area:cleanup`, `P2`

## Why

Item 3 of the 2026-09-29 triage: a cleanup pass with no product decision. Jacob is dev-only, so a clean removal is fine after a DB backup.

## Change

- **CARD-498 (export then drop):** `schema.py` no longer creates the Factory or scaffold-spine tables. On startup `connection.py` drops `factory_jobs`, `factory_graphs`, `factory_packets`, `factory_eval_runs` and `scaffold_spine`; any rows are first exported to `<data>/backups/factory-retire-<ts>.json`, and a failed export skips the drop. Jacob's DB was backed up to `backups/autoreiv-pre-card577-20260929-125805.db`; all five tables had 0 rows.
- **CARD-512 (scaffold spine):** removed `SelfScaffoldSpine`, its repository and domain model, the `/api/capabilities/scaffold/*` and capability-gap smoke routes, mid-job self-scaffold (`handle_mid_job_capability_gap`, `promote_mid_job_scaffold`, `forge_approve_and_resume`) and the self-scaffold queue e2e module. The supervisor's "scaffold" action now parks the phase; research suggests `ask_toolsmith`. The 308 redirects from `/api/agent_training_factory/*` are gone (404).
- **CARD-514:** superseded by CARD-569 (New Agent opens the Quick Scaffold modal). Only the dead `#forgeQuickScaffoldBtn` hook was removed.
- **CARD-515:** Skill Studio's dead assigned-skills render (`renderAssignedSkills`, `factoryAssignedSkillChrome`) removed; Factory-named ids are now `#studioOpenSkillStudioBtn` / `forge-open-skill-studio` and `data-section="capability-gaps"`.
- **CARD-506:** the last duplicate save route `POST /api/settings/agents/{id}` removed; Agent Studio saves only through `PUT /api/agents/{id}` (model, provider and context window included).
- **Wording:** steering `product.md` / `structure.md` list all 11 studios; the Skill Studio authoring template id is now `skill_studio_toolsmith_authoring` (open jobs under the old id are not resumed; dev-only).
- **Tests:** the routine HITL park test is re-pointed from `cli_exec` to `write_project_file` and unskipped; new `test_card577_retired_tables.py`, `test_card506_one_agent_save_path.py`; Factory redirect tests replaced by 404 checks; card_497 test_17 replaced by a pointer.
- **Cards:** closed as obsolete: CARD-510, 535, 557, 518, 457, 458, 459, 468, 521, 499; CARD-514 superseded. In Review with this card: CARD-498, 512, 515, 506. Shrunk: CARD-529 (item 3 only), CARD-462 (job and handoff budgets). Findings updated.

## Results (2026-09-29)

- ruff clean; full not-slow pytest 2014 passed, 12 skipped; vitest 957 passed; eslint only the old `callbacks` warning in `forge/scaffold.js`.
- Fast preflight `--base qa`: GREEN (62 s; guard 188, changed 52, mapped 502 passed).
- Live smoke on a throwaway :8770 from the committed branch: `/api/capabilities/scaffold/candidates` 404, `/api/capabilities/registry` 200, `/api/agent_training_factory/skills` 404, `POST /api/settings/agents/developer` 404. In Agent Studio, a Developer Save with model `qwen3-coder:latest` and context window 131072 returned 200, the values persisted, and they were still there after a reload. Skill Studio loaded 44 skills. A new authoring job has `template_id` `skill_studio_toolsmith_authoring` with agent `toolsmith`. No Factory UI remnants, no calls to retired routes, no page errors.
- Tool-mount probe (read-only, for Jacob's question): Developer's turn 1 mounts 15 of 26 tools. The 10 pinned project/card tools plus 5 baseline tools; skill_view is not mounted. Findings line updated.

## Log
- 2026-09-29: Jacob approved item 3 of the triage as CARD-577 (cleanup, no product decision). Built on `chore/card-577-cleanup`; not merged or pushed.
- 2026-09-29: Jacob: merge to qa. Done; merged into qa.
