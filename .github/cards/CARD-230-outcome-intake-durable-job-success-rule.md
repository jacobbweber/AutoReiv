# [CARD-230] Outcome Intake → Durable Job + success_rule

> **Status**: Ready
> **Created**: 2026-09-11
> **Spec Reference**: Standing Job/Phase Chat path (215–229) + catalog resolve (217/220) + external verifier (216)
> **Labels**: type:architecture, type:feature, AutoReiv.Orchestration, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Vague Chat ask becomes a durable Job automatically** — no Jacob toggle for "goal mode" / plan-and-execute.
2. Every standing Job carries an explicit **`success_rule`** (testable outcome, not vibes) so the verifier has a stop condition.
3. **Catalog resolve runs on intake** (matched IDs drive capability); agent picker is preference, not authority.
4. **Proof**: Chat multi-step / outcome-shaped ask → Job row with `success_rule` + matched catalog IDs before phase 1 runs.
5. **Not this card**: research-before-plan (231), bounded replan (232), mid-job scaffold (233), supervisor pick (234), new Studios / UI polish.

### Beat 2: What AutoReiv Does Now
1. Standing Job/Phase path (215+) exists for multi-step Chat and Routines; catalog resolve is wired (220).
2. Jobs may lack a durable, testable `success_rule` at intake — verifier stop condition is weak / vibes-shaped.
3. Agent selection can still feel like authority over which capabilities run, instead of catalog match driving the working set.
4. Vague high-level outcomes still need clearer automatic promotion into a Job with success criteria.

### Beat 3: What Will Change
1. Add **outcome intake** on Chat (and standing multi-step entry): vague / outcome-shaped ask → create durable Job with `success_rule` + auto catalog resolve.
2. Persist `success_rule` on the Job (and checkpoint path) so 216 verifier and later 232 replan have a real stop condition.
3. Treat agent picker as preference only — matched catalog IDs remain authority for capability subset.
4. TDD red→green: intake creates Job with non-empty testable `success_rule` + matched IDs before phase 1; scorecard + CHANGELOG; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

> Architect: sharpen / lock this bar before Builder implements.

- [ ] **[REQ-INTAKE-001]**: Vague / outcome-shaped Chat ask creates a durable Job automatically (no goal_mode toggle).
- [ ] **[REQ-INTAKE-002]**: Job persists an explicit `success_rule` (testable outcome — not free-text vibes only).
- [ ] **[REQ-INTAKE-003]**: Catalog resolve runs at intake; matched IDs are authority; agent picker is preference only.
- [ ] **[REQ-INTAKE-004]**: Proof — before phase 1: Job row has `success_rule` + matched catalog IDs.
- [ ] **[REQ-INTAKE-005]**: Extends standing Job/Phase path (215–229); no parallel orchestrator / no new Studio.
- [ ] **[REQ-INTAKE-006]**: Automated tests red→green; ruff clean; CHANGELOG + scorecard; push `feat/*` only — never qa/main. Live proof Jarvis→Nimo qwen when holds.

---

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime` (or next `feat/*` off `grok`). Never merge/push qa/main.
- Anti-theatre: real `success_rule` + durable Job + catalog match — not UI "goal" theatre.
- Out of scope: 231–234, UI polish, new Studios.

## 4. Modules Likely Touched

- `src/application/orchestration/` (outcome intake / Job create)
- `src/web/routers/chat.py` (standing multi-step entry)
- Job/Phase domain models + persistence (success_rule field)
- `tests/unit/orchestration/test_outcome_intake.py` (new)
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- Hold implement until Architect locks the Done bar above.
- TDD: red "intake Job has success_rule + matched IDs before phase 1" first, then green.
- Extend standing path — do not invent a second goal orchestrator.

