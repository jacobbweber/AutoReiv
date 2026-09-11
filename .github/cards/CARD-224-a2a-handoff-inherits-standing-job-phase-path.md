# [CARD-224] A2A Handoff Inherits Standing Job/Phase Path

> **Status**: In Progress
> **Created**: 2026-09-11
> **Spec Reference**: Design room after CARD-222/223; Architect CARD-224 — A2A handoff inherits standing path
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Orchestration`, `AutoReiv.A2A`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Handoff is not a second orchestrator**: When Chat/Routine standing work delegates via A2A, the child must enter the same Job/Phase runtime (catalog matched IDs → CARD-221 policy → verifier → checkpoint).
2. **Prefer linked `child_job_id`**: Parent standing `job_id` spawns a durable linked child job; crash-resume and Observability can follow the link.
3. **No tool widen**: If parent matched subset / durable policy would `BLOCK` a tool, the child after handoff still `BLOCK`s it (capability subset cannot grow).
4. **Not this card**: Memory brain honesty (CARD-116 product ACs), ADF Lab labeling UI, new Studios.

### Beat 2: What AutoReiv Does Now
1. Standing Chat/Routine multi-step uses `create_job_from_catalog_resolve` (CARD-215..222).
2. `HandoffIsolationEngine` still runs isolated `stream_turn` child sessions without creating a standing child Job/Phase or inheriting matched IDs.
3. ToolPolicyGate can enforce matched capability subset, but A2A children were not bound to the parent subset via a linked job.

### Beat 3: What Will Change
1. Helper `standing_a2a_handoff.create_standing_child_job` reuses parent matched IDs (no cold re-resolve) and records parent→child link.
2. `HandoffIsolationEngine` + app wiring: when `context_payload.parent_job_id` (or `job_id`) present, create linked `child_job_id` and stamp `HandoffResult`.
3. Child matched IDs ⊆ parent matched IDs; policy capability_subset BLOCK cannot widen.
4. TDD red→green; CHANGELOG; push `feat/*` only — never merge/push qa/main.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-A2ASTAND-001]**: Helper creates linked standing child catalog R/H/E job inheriting parent matched capability IDs (no cold re-resolve).
- [x] **[REQ-A2ASTAND-002]**: Child matched IDs do not widen beyond parent; capability_subset BLOCK remains BLOCK after handoff.
- [x] **[REQ-A2ASTAND-003]**: `HandoffResult` exposes optional `parent_job_id` / `child_job_id`; engine stamps them when standing link created.
- [ ] **[REQ-A2ASTAND-004]**: Live smoke: parent standing job → A2A handoff → linked child_job_id + policy gate decision on child session (Jarvis).
- [x] **[REQ-A2ASTAND-005]**: Automated tests green; ruff clean; CHANGELOG `[Unreleased]`; push `feat/*` only.

---

## 3. Constraints & Honor Flags

- Status: **In Progress** (thin TDD slice + engine wire landed; live A2A smoke deferred).
- Branch: `feat/standing-job-graph-runtime`. Never push qa/main.
- Out of scope: CARD-116 memory consolidate honesty, ADF Lab labeling, Docs Studio.

## 4. Modules Touched

- `src/application/orchestration/standing_a2a_handoff.py` (new)
- `src/application/orchestration/handoff_engine.py`
- `src/domain/orchestration/models.py` (`HandoffResult` link fields)
- `src/web/app.py` (wire `job_orchestrator` into handoff engine)
- `tests/unit/orchestration/test_standing_a2a_handoff.py`

## 5. Marathon Build Notes (Jarvis 2026-09-10 ET)

- Thin green: inherit matched IDs + no-widen + linked child_job_id maps.
- Engine best-effort creates child when `context_payload.parent_job_id|job_id` set.
- Live A2A end-to-end with qwen still optional next beat after CARD-222 smoke notes.
