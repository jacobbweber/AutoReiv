# [CARD-231] Standing Research-Before-Plan (Capability Gap Only)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect feed after CARD-230; standing Job/Phase (215-230) + catalog C (217/220) + memory.db (226) + journey (227)
> **Labels**: type:architecture, type:feature, AutoReiv.Orchestration, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. After intake catalog resolve, if the match is **thin/gap**, the Job inserts a **research** phase **before** plan formulate — standing runtime, no Jacob toggle.
2. If the match is **sufficient**, skip research — go straight to formulate/execute (no latency tax on every job).
3. Research writes facts into `memory.db` and may propose catalog gaps — it does **not** write trusted skills/tools (218/233).
4. Checkpoint persists `research_inserted: true|false` + reason; Observability `job_id` journey shows the research span.
5. **Not this card**: bounded replan (232), mid-job scaffold (233), supervisor pick (234), new Studios.

### Beat 2: What AutoReiv Does Now
1. CARD-230 outcome intake creates a durable Job with testable `success_rule` + matched catalog IDs before phase 1.
2. `create_job_from_catalog_resolve` always formulates Research/Handoff/Execute — research is not gated on thin/gap.
3. Thin catalog matches still pay a full research latency tax (or skip gap analysis entirely).
4. Checkpoints lack `research_inserted` / reason; journey has no dedicated research span.

### Beat 3: What Will Change
1. Deterministic thin/gap vs sufficient heuristic after catalog resolve (documented below).
2. Thin → insert Research phase before Formulate/Execute; sufficient → Formulate/Execute only.
3. Research phase persists facts to `<agent>_memory.db` + catalog-gap proposals only (never trusted skill/tool writes).
4. Checkpoint + standing journey surface `research_inserted` + reason + research span.
5. TDD red→green + live Jarvis→qwen smoke; CHANGELOG + scorecard; push `feat/*` only.

---

## 2. Thin / Gap vs Sufficient Heuristic (locked)

Deterministic, unit-testable (`assess_catalog_match`):

| Condition | Classification | `research_inserted` | Reason code |
|-----------|----------------|---------------------|-------------|
| `len(matched_ids) == 0` | thin/gap | `true` | `empty_matched_ids` |
| `len(matched_ids) < SUFFICIENT_MATCH_MIN` (2) | thin/gap | `true` | `below_threshold:N<2` |
| success_rule implies critical family (health/verify/wiki/execute) with no overlapping keywords on matched entries | thin/gap | `true` | `missing_critical_roles:<families>` |
| otherwise (`count >= 2` and critical families covered or none implied) | sufficient | `false` | `sufficient_match` |

Standing runtime only — no Jacob toggle.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **[REQ-RESEARCH-001]**: After intake catalog resolve, if match is **thin/gap** (below threshold or empty critical roles for the `success_rule`), Job inserts a **research** phase **before** plan formulate — standing runtime, no Jacob toggle.
- [x] **[REQ-RESEARCH-002]**: If match is **sufficient**, skip research — go straight to formulate/execute (no latency tax every job).
- [x] **[REQ-RESEARCH-003]**: Research phase writes facts into `memory.db` + may propose catalog gaps; does **not** write trusted skills/tools (218/233).
- [x] **[REQ-RESEARCH-004]**: Checkpoint persists `research_inserted: true|false` + reason; Observability `job_id` journey shows the research span.
- [x] **[REQ-RESEARCH-005]**: Extends 215–230 only; red→green + live smoke; feat-only.

## 4. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: real thin/gap gate + memory.db facts + journey span — not a UI toggle.
- Out of scope: 232–234. Do not write trusted skills/tools from research.

## 5. Modules Likely Touched

- `src/application/orchestration/research_before_plan.py` (new)
- `src/application/orchestration/job_phase_orchestrator.py`
- `src/domain/orchestration/models.py` (checkpoint fields)
- `src/infrastructure/memory/` (schema + checkpoint persist + journey)
- `src/application/observability/standing_journey.py`
- `tests/unit/orchestration/test_research_before_plan.py` (new)
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 6. Marathon Build Lock

- Architect Done bar locked — Builder implements now.
- TDD: red tests for 001–004 first, then green.
- Extend standing path — do not invent a second orchestrator.

## 7. Marathon Build Notes (Jarvis 2026-09-11 ET)

- Heuristic in `research_before_plan.assess_catalog_match`: empty IDs / count < 2 / missing critical roles.
- Thin → Research → Formulate → Execute; sufficient → Formulate → Execute.
- Research writes `<agent>_memory.db` + catalog gap proposals; trusted writers never called.
- Checkpoint columns `research_inserted` + `research_reason`; journey `standing.research` span.
- Tests: `tests/unit/orchestration/test_research_before_plan.py` (9) green; related suites green; ruff clean.
- Live smoke PASS: `notes/marathon-card231-live-smoke.json`.
- Status: **Done**; push `feat/*` only.

