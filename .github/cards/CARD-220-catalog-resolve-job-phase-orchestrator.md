# [CARD-220] Catalog Resolve into JobPhaseOrchestrator (Standing C Runtime)

> **Status**: In Review
> **Created**: 2026-09-10
> **Spec Reference**: Design room after CARD-219; wires Capability Catalog C (CARD-217) into standing Job-Graph (CARD-215) + crash-resume checkpoints (CARD-219) + external verifier (CARD-216)
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **C is standing runtime, not a panel toy**: `JobPhaseOrchestrator` consults capability catalog resolve on multi-step work - `intent → matched subset → Research / Handoff / Execute` - not Observability-only match demos.
2. **No cold re-resolve drift**: Persist **matched capability IDs** on the Job/Phase checkpoint (extend CARD-219). Resume reuses the same subset; do not re-resolve and silently change the plan.
3. **Honest advance rules**: Only `verified` advances Execute (and any phase that carries a checker). `failed` ⇒ park + needs_replan (never silent advance). `skipped_no_checker` never counts as a verified advance (Research/Handoff may continue on honest skip; Execute does not advance on skip).
4. **Extend, do not invent**: Reuse CapabilityCatalogResolver + crash_resume checkpoint + JobPhaseOrchestrator. No second catalog, no second graph engine.
5. **Not this card**: UI polish, new Studios, ATF/Lab rewrite, Homelab domain outcomes.

### Beat 2: What AutoReiv Does Now
1. CARD-217 match-only resolve + Observability panel exist; Chat/JobPhase path does not consult the catalog when formulating phases.
2. CARD-219 checkpoints persist `job_id`, phase index, verifier status, HITL park - but not matched capability IDs.
3. CARD-216 phase-complete gate completes/advances on `skipped_no_checker` and `fail_phase`s on checker failure - standing C runtime needs stricter Execute advance + park/replan on fail.
4. Standing Job-Graph routes multi-step to Job/Phase without catalog-shaped Research/Handoff/Execute lanes.

### Beat 3: What Will Change
1. `JobPhaseOrchestrator.create_job_from_catalog_resolve(intent)` → resolve subset → durable Research / Handoff / Execute phases + matched IDs on checkpoint.
2. Extend `job_phase_checkpoints` + `JobPhaseCheckpoint` with `matched_capability_ids`; resume_after_crash returns those IDs (no cold re-resolve).
3. Standing advance gate: verified advances Execute; failed ⇒ park + needs_replan; skipped_no_checker never labeled/used as verified advance.
4. Proof: red tests then green; CHANGELOG; feat branch only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-CATJOB-001]**: `JobPhaseOrchestrator` consults capability catalog resolve: intent → matched subset → Research / Handoff / Execute phase plan (standing runtime, not Observability-only).
- [x] **[REQ-CATJOB-002]**: Matched capability IDs persist on Job/Phase checkpoint (extend CARD-219). `resume_after_crash` reuses the same subset - no cold re-resolve drift.
- [x] **[REQ-CATJOB-003]**: Advance rules: only `verified` advances Execute (checker phases); `failed` ⇒ park + `needs_replan` (never silent advance); `skipped_no_checker` never counts as verified advance (Research/Handoff may continue on honest skip; Execute does not advance on skip).
- [x] **[REQ-CATJOB-004]**: Extends existing CapabilityCatalogResolver + crash_resume checkpoint + JobPhaseOrchestrator - no second catalog/graph engine. Out of scope: UI polish, new Studios.
- [x] **[REQ-CATJOB-005]**: Automated tests red→green; ruff clean; CHANGELOG `[Unreleased]`; push `feat/*` only - never merge/push qa/main.

---

## 3. Constraints & Honor Flags

- Status: **In Review** (catalog resolve standing runtime green on feat).
- Branch: `feat/standing-job-graph-runtime`. Never push qa/main.
- Out of scope: UI polish, new Studios, ATF/Lab rewrite, Homelab domain outcomes.
- Anti-theatre: durable matched IDs on checkpoint + standing orchestrator resolve path; failure = empty subset / park+replan / no silent Execute advance on skip.

---

## 4. Modules Likely Touched

- `src/application/orchestration/job_phase_orchestrator.py` - catalog formulate + matched IDs on commit/resume
- `src/application/orchestration/external_verifier_policy.py` - advance rules
- `src/application/orchestration/crash_resume.py` - expose matched IDs
- `src/domain/orchestration/models.py` - JobPhaseCheckpoint.matched_capability_ids
- `src/infrastructure/memory/schema.py` + `repositories/jobs.py` + `connection.py` - column migrate
- `tests/unit/orchestration/test_catalog_resolve_job_runtime.py`

---

## 5. Marathon Notes

- Build lock: resolve → R/H/E + checkpoint matched IDs + verified-only Execute advance.
- TDD: red catalog-into-orchestrator + resume ID reuse + advance rules first, then green.


## 6. Marathon Build Notes (Jarvis)

- Unit: `tests/unit/orchestration/test_catalog_resolve_job_runtime.py` 4 passed (red→green).
- Related: crash-resume + verifier + job-phase + catalog + schema 39 passed; ruff clean.
- Branch: `feat/standing-job-graph-runtime` only (never qa/main).
