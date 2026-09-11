# [CARD-230] Outcome Intake → Durable Job + success_rule

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Standing Job/Phase Chat path (215-229) + catalog resolve (217/220) + external verifier (216)
> **Labels**: type:architecture, type:feature, AutoReiv.Orchestration, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Vague Chat ask becomes a durable Job automatically** - no Jacob toggle for "goal mode" / plan-and-execute.
2. Every standing Job carries an explicit **`success_rule`** (testable outcome, not vibes) so the verifier has a stop condition.
3. **Catalog resolve runs on intake** (matched IDs drive capability); agent picker is preference, not authority.
4. **Proof**: Chat multi-step / outcome-shaped ask → Job row with `success_rule` + matched catalog IDs before phase 1 runs.
5. **Not this card**: research-before-plan (231), bounded replan (232), mid-job scaffold (233), supervisor pick (234), new Studios / UI polish.

### Beat 2: What AutoReiv Does Now
1. Standing Job/Phase path (215+) exists for multi-step Chat and Routines; catalog resolve is wired (220).
2. Jobs may lack a durable, testable `success_rule` at intake - verifier stop condition is weak / vibes-shaped.
3. Agent selection can still feel like authority over which capabilities run, instead of catalog match driving the working set.
4. Vague high-level outcomes still need clearer automatic promotion into a Job with success criteria.

### Beat 3: What Will Change
1. Add **outcome intake** on Chat (and standing multi-step entry): vague / outcome-shaped ask → create durable Job with `success_rule` + auto catalog resolve.
2. Persist `success_rule` on the Job (and checkpoint path) so 216 verifier and later 232 replan have a real stop condition.
3. Treat agent picker as preference only - matched catalog IDs remain authority for capability subset.
4. TDD red→green: intake creates Job with non-empty testable `success_rule` + matched IDs before phase 1; scorecard + CHANGELOG; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

> Architect-locked Done bar (2026-09-11). Builder: replace drafts with these exactly.

- [x] **[REQ-INTAKE-001]**: Outcome-shaped Chat ask (multi-step / goal / deliverable language — not short chitchat) creates a durable Job on the standing path with **no** goal_mode toggle. Short tool turns stay plain ReAct (215 rule).
- [x] **[REQ-INTAKE-002]**: Job persists `success_rule` as a **testable stop condition** (structured string the 216 verifier can fail against — e.g. "done when X exists / test Y passes / health Z returns 200"). Free-text vibes-only (`"looks good"`) is reject at intake.
- [x] **[REQ-INTAKE-003]**: Catalog resolve runs at intake; **matched IDs are capability authority**. Agent picker only biases which agent runs the Job — it must not widen matched subset or bypass resolve.
- [x] **[REQ-INTAKE-004]**: Before phase 1 execute: Job row has non-empty `success_rule` + `matched_capability_ids` on checkpoint. Missing either ⇒ do not start phases (fail closed).
- [x] **[REQ-INTAKE-005]**: Extends 215–229 only — no second orchestrator, no new Studio.
- [x] **[REQ-INTAKE-006]**: Red→green tests for 001–004; live Jarvis→qwen smoke; CHANGELOG + scorecard; feat-only.

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime` (or next `feat/*` off `grok`). Never merge/push qa/main.
- Anti-theatre: real `success_rule` + durable Job + catalog match - not UI "goal" theatre.
- Out of scope: 231-234, UI polish, new Studios.

## 4. Modules Likely Touched

- `src/application/orchestration/` (outcome intake / Job create)
- `src/web/routers/chat.py` (standing multi-step entry)
- Job/Phase domain models + persistence (success_rule field)
- `tests/unit/orchestration/test_outcome_intake.py` (new)
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- Architect Done bar locked — Builder implements now.
- TDD: red "intake Job has success_rule + matched IDs before phase 1" first, then green.
- Extend standing path - do not invent a second goal orchestrator.
