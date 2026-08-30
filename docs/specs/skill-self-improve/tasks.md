# Implementation Tasks: Skill Self-Improve

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)
> **Traceability Key**: All tasks must reference their corresponding `[REQ-xxx]` tags.
> **Cards**: CARD-110 through CARD-112. One card per vertical slice. No feature code in the spec-open commit.

---

## Vertical Slice Breakdown

### Slice D1 -- CARD-110 ACE-style online playbook notes + snapshot/rollback (HITL if writing SKILL.md)

- [ ] **Task 1.1** `[REQ-IMPROVE-001]` `[REQ-IMPROVE-002]`: [RED] Failing tests that a failed turn (telemetry `span_type=turn` `success=false` and/or `react_state=FAILED`) produces at most one tiny delta note. Generator is existing `AgentKernel`. No second ReAct loop. No LangGraph.
- [ ] **Task 1.2** `[REQ-IMPROVE-001]` `[REQ-IMPROVE-002]`: [GREEN] In-process Reflector post-turn hook. Curator merges incremental items only. Successful turns do not rewrite `SKILL.md`.
- [ ] **Task 1.3** `[REQ-IMPROVE-003]`: [RED] Online ACE leaves `src/` and Python `BuiltinSkill` modules unchanged. A Python-shaped delta stays `propose_tool` draft `requires human/code card`.
- [ ] **Task 1.4** `[REQ-IMPROVE-003]`: [GREEN] No live tool codegen. JSON stubs stay stubs.
- [ ] **Task 1.5** `[REQ-IMPROVE-004]`: [RED] Snapshot copies `SKILL.md` + notes sidecar under `$DATA_DIR/skills/<id>/snapshots/<utc-iso>/` before apply. Rollback restores. Snapshot I/O failure skips apply.
- [ ] **Task 1.6** `[REQ-IMPROVE-004]`: [GREEN] Snapshots are data-dir files, not git commits. Other packs untouched.
- [ ] **Task 1.7** `[REQ-IMPROVE-005]`: [RED] Intended `SKILL.md` patch goes through `propose_skill` (`kind=skill` `status=draft` + HITL park). Live `SKILL.md` unchanged until Approve + CARD-107 `commit_skill_pack`. CARD-106 gate holds.
- [ ] **Task 1.8** `[REQ-IMPROVE-005]`: [GREEN] Reuse AgentBuilderSkill / proposals table. No second builder. Approve still does not write disk.
- [ ] **Task 1.9** `[REQ-IMPROVE-006]`: [RED] Optional append-only sidecar (`PLAYBOOK_NOTES.md` or `notes.jsonl`) does not rewrite existing lines and does not modify `SKILL.md`. Promotion into `SKILL.md` is still `propose_skill`.
- [ ] **Task 1.10** `[REQ-IMPROVE-006]` `[REQ-IMPROVE-016]`: [GREEN] Sidecar under `$DATA_DIR/skills/<id>/`. Online path does not enqueue the nightly routine.

### Slice D2 -- CARD-111 nightly skill eval routine (SkillOpt-Sleep shape, validation gate)

- [ ] **Task 2.1** `[REQ-IMPROVE-007]`: [RED] Seed `skill-eval-sleep` (or equivalent id) into existing `routines` table via `BUILTIN_ROUTINES` / `seed_default_routines`. Same `RoutineExecutor` + `routine_runs`. No second scheduler. No `skillopt-sleep` CLI.
- [ ] **Task 2.2** `[REQ-IMPROVE-007]`: [GREEN] Target `agent-builder` (or documented builtin with `propose_skill`). Not Coding / Review / Conductor.
- [ ] **Task 2.3** `[REQ-IMPROVE-008]`: [RED] Seed `enabled=false`. When enabled, `next_run_at` is weekday 21:00 `America/New_York`, not 02:00 local, not 21:00 UTC. Docs say paused-by-default and why 2am is wrong.
- [ ] **Task 2.4** `[REQ-IMPROVE-008]`: [GREEN] Timezone-aware `next_run_at` (extend `ScheduleMatcher` / routine metadata). Do not ship naive cron-as-UTC.
- [ ] **Task 2.5** `[REQ-IMPROVE-009]`: [RED] Harvest read-only from live `$DATA_DIR` SQLite: failed `telemetry_spans` turns and FAILED jobs/phases in lookback 24â€“72h (default 72h). Cap max sessions/tasks. Do not harvest checkout `./data` when LocalAppData is live. Do not wipe DBs.
- [ ] **Task 2.6** `[REQ-IMPROVE-009]`: [GREEN] Reuse telemetry repository. Empty harvest is success no-op.
- [ ] **Task 2.7** `[REQ-IMPROVE-010]`: [RED] Replay optional and default off. When on, honors `max_concurrent_generations` default 1. No LangGraph.
- [ ] **Task 2.8** `[REQ-IMPROVE-011]`: [RED] Checker gate before stage. Pass â†’ `propose_skill` draft only (`auto_commit` false). Fail or missing checker (honest skip, not `verification_passed`) â†’ no proposal, no `SKILL.md` write. Record in `routine_runs`.
- [ ] **Task 2.9** `[REQ-IMPROVE-011]` `[REQ-IMPROVE-012]`: [GREEN] In-process gate (CARD-099 / VerificationSkill). No required `skillopt` pip. Thin adapter if present must fail closed when missing. No weight training.

### Slice D3 -- CARD-112 skill curator stale/archive (Hermes)

- [ ] **Task 3.1** `[REQ-IMPROVE-013]`: [RED] Unused user packs past stale window (default 30 days, last-used known) are moved to `$DATA_DIR/skills/_archive/<id>/` (or skills-archive). Not deleted. Live list omits them. Unknown last-used fails closed (no archive).
- [ ] **Task 3.2** `[REQ-IMPROVE-013]`: [GREEN] `UserSkillCatalog` skips `_archive` and `snapshots` when listing live packs. Curator may ride the nightly routine or a sibling routine in the same table.
- [ ] **Task 3.3** `[REQ-IMPROVE-014]`: [RED] `okta-admin` and `BUNDLED_PACK_IDS` are never auto-archived or deleted. Repo `src/infrastructure/skills/seeds/` is never deleted. Explicit user confirm required even to archive a bundled pack.
- [ ] **Task 3.4** `[REQ-IMPROVE-014]`: [GREEN] CARD-108 copy-if-missing seed still does not overwrite dest.
- [ ] **Task 3.5** `[REQ-IMPROVE-015]`: [RED] Unarchive moves back to `$DATA_DIR/skills/<id>/`. Dest-exists fails closed. Skills Studio can open the restored pack. No new proposal required.
- [ ] **Task 3.6** `[REQ-IMPROVE-015]` `[REQ-IMPROVE-016]`: [GREEN] Curator does not rewrite packs during an interactive chat turn.

### Slice D4 -- Verification, traceability, QA handoff

- [ ] **Task 4.1**: pytest + ruff on touched Python (implementation cards, not this spec-open).
- [ ] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight` when feature cards land.
- [ ] **Task 4.3**: Human QA on Jarvis: CARD-109 data dir still LocalAppData; enable `skill-eval-sleep` only when ready (default paused); failed turn can park `propose_skill` without rewriting `SKILL.md` or `src/`; rollback restores snapshot; okta-admin remains live; stale user pack archives; unarchive works; do not push; do not wipe DBs.

---

## Explicitly not in these tasks

Training weights, LangGraph, live tool codegen, required `skillopt` pip / microsoft/SkillOpt vendor, `--auto-adopt`, 02:00 local default, deleting packs, replacing Agent Builder or Conductor, Slice A/B contract changes beyond archive listing, wiping or merging CARD-109 databases, CARD-014 DAG.
