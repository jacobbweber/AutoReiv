# [CARD-233] Mid-Job Self-Scaffold (Capability Gap → 218 Spine)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect feed after CARD-232; standing Job/Phase (215-232) + self-scaffold spine (218) + research gap proposals (231) + HITL park (232) + catalog re-resolve (220/230)
> **Labels**: type:architecture, type:feature, AutoReiv.Orchestration, AutoReiv.Kernel, AntiTheatre, AgentForge

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. When a **running** Job hits a **capability gap** (tool/skill missing for `success_rule` / phase), standing runtime opens a **candidate** skill/tool draft via the **218 spine** — never writes trusted from a live phase.
2. Honest path only: draft → sandbox → version → **HITL approve** → trusted → **catalog re-resolve** (update matched IDs on checkpoint). Reject unscoped trusted write.
3. Until HITL promotes, Job **parks** (or continues only with remaining matched capabilities) — no silent use of candidate as trusted.
4. Observability `job_id` journey shows `scaffold_candidate` + HITL + re-resolve spans; Forge candidate queue is the operator path.
5. **Not this card**: supervisor pick (234).

### Beat 2: What AutoReiv Does Now
1. CARD-218: `SelfScaffoldSpine` draft→sandbox→version→HITL→trusted + Forge candidate queue; unscoped trusted write rejected.
2. CARD-231: research may **propose** catalog gaps but does not open the spine or write trusted.
3. CARD-232: HITL park path + checkpoint fields + standing journey replan/park spans.
4. Catalog resolve + matched IDs on checkpoint (220/230) — no mid-job re-resolve after scaffold promote.

### Beat 3: What Will Change
1. Mid-job gap detector opens a **candidate** via 218 spine (never trusted from live phase).
2. Park (or continue-with-matched-only) until HITL promote; then re-resolve updates matched IDs on checkpoint.
3. Journey spans: `scaffold_candidate` + HITL + re-resolve; Forge queue remains operator path.
4. Reject unscoped trusted write mid-phase (reuse 218 gate).
5. TDD red→green + live smoke; CHANGELOG + scorecard; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-SCAFFOLD-001]**: When a running Job hits a capability gap (tool/skill missing for `success_rule` / phase), standing runtime opens a **candidate** skill/tool draft via the **218 spine** — never writes trusted from a live phase.
- [x] **[REQ-SCAFFOLD-002]**: Path: draft → sandbox → version → **HITL approve** → trusted → catalog re-resolve (update matched IDs on checkpoint). Reject unscoped trusted write.
- [x] **[REQ-SCAFFOLD-003]**: Until HITL promotes, Job **parks** (or continues only with remaining matched capabilities) — no silent use of candidate as trusted.
- [x] **[REQ-SCAFFOLD-004]**: Observability `job_id` journey shows `scaffold_candidate` + HITL + re-resolve spans; Forge candidate queue is the operator path.
- [x] **[REQ-SCAFFOLD-005]**: Extends 215–232 + 218; red→green (incl. "no trusted write mid-phase"); live smoke; feat-only.

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: real spine draft + park/HITL + re-resolve — not a UI toggle.
- Out of scope: CARD-234.
- Never write trusted from a live phase without HITL.

## 4. Modules Likely Touched

- `src/application/orchestration/mid_job_self_scaffold.py` (new)
- `src/application/capabilities/scaffold_spine.py` (reuse)
- `src/application/orchestration/job_phase_orchestrator.py` (thin hook)
- `src/application/observability/standing_journey.py` (spans)
- `tests/unit/orchestration/test_mid_job_self_scaffold.py` (new)
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- Architect Done bar locked — Builder implements now.
- TDD: red tests for 001-004 first (incl. no trusted write mid-phase), then green.
- Extend standing path + 218 spine only — do not invent a second scaffold product.

## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- `mid_job_self_scaffold.py`: detect gap (231 heuristic) → `spine.draft` candidate; park or continue-matched-only; HITL promote → catalog re-resolve updates matched IDs.
- Journey spans: `standing.scaffold_candidate` / `standing.scaffold_hitl` / `standing.catalog_reresolve`; Forge `list_candidates` is operator path.
- Thin orch hooks: `handle_mid_job_capability_gap` / `promote_mid_job_scaffold`.
- Tests: `tests/unit/orchestration/test_mid_job_self_scaffold.py` (9) green; related suites green.
- Live smoke: `notes/marathon-card233-live-smoke.json`.
- Status: **Done**; push `feat/*` only. Never write trusted from live phase without HITL.

