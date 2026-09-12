# [CARD-271] Foundation audit - ReAct vs Job spine truth

> **Status**: Ready
> **Created**: 2026-09-12
> **Spec Reference**: Foundation audit after CARD-270. Architect: ReAct + Job spine audit (skip DAG canvas unless same Job/HITL). Prove short Ask stays plain ReAct; outcome Ask creates durable Job with Observe journey. Stack on eat/training-factory-truth-270 @ db2b33e. Hold FF until Jacob merge phrase.
> **Labels**: 	ype:chore, P0, FoundationAudit, StandingJob, ReAct, AntiTheatre
> **Branch**: eat/react-job-spine-truth-271 (off 270 tip; push feat only)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Short chat stays **ReAct** (no fake Job strip / no invent journey).
2. Outcome-shaped asks create a real **Job** with phases; Observe can open that job_id and show standing journey (intake / advance / verify — not empty theatre).
3. Skip DAG/Flows canvas work unless it shares the same Job/HITL spine.
4. **Not this card**: 272 install/Compose, UI marathon, Lumina.

### Beat 2: What AutoReiv Does Now
1. 
oute_standing_chat + is_outcome_shaped decide MULTI_STEP_JOB_GRAPH vs SHORT_REACT (CARD-215/230).
2. Chat stream uses that route for create_job_from_catalog_resolve vs kernel ReAct.
3. Wave-2 operator note: some capable asks did not prove Job/job_id in Observe — audit gap.
4. DAG canvas is out of scope unless same Job/HITL.

### Beat 3: What Will Change
1. Audit + harden routing honesty: short Ask never mints a Job; forced outcome Ask always mints job_id with Observe journey events.
2. TDD for 
oute_standing_chat / intake edge cases if theatre found.
3. Live smoke 
otes/marathon-card271-live-smoke.json: (A) chitchat → no job; (B) outcome → job_id + standing-journey 200 with events.
4. CHANGELOG; push feat; hold FF.

## 2. Acceptance Criteria

- [ ] **[REQ-FAUD-271-001]**: Short chitchat routes SHORT_REACT; live Ask creates no durable Job (or empty journey jobs).
- [ ] **[REQ-FAUD-271-002]**: Outcome-shaped Ask routes MULTI_STEP_JOB_GRAPH; live Ask yields job_id + Observe standing-journey usable.
- [ ] **[REQ-FAUD-271-003]**: No DAG canvas scope expansion; HITL/same-job paths unchanged.
- [ ] **[REQ-FAUD-271-004]**: Tests + live artifact + CHANGELOG; push feat only; hold FF. No qa/main.

## 3. Constraints

- Quality > speed. Extend standing_job_graph / outcome_intake / chat stream — do not invent a second orchestrator.
- Out of scope: 272, Flows DAG redesign, horizon D.

## 4. Modules Likely Touched

- src/application/orchestration/standing_job_graph.py
- src/application/orchestration/outcome_intake.py
- src/web/routers/chat.py (only if routing honesty broken)
- 	ests/unit/orchestration/test_card271_*.py
- 
otes/scripts/react_job_spine_truth_271.py
- CHANGELOG.md

## 5. Design-room one-liner

ReAct vs Job spine truth: short stays ReAct; outcomes mint real Jobs Observe can open — no DAG theatre this card.

## 6. Build lock

CoS keep-rolling / Architect 271 bar: Builder may implement immediately on this Ready card.
