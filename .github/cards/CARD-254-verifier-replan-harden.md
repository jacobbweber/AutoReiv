# [CARD-254] Verifier / Replan Harden (232 class)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Binary external verify; fail	o replan cap then HITL park (232 class). Live: Forced fail 	o replan \le3 	o park; no infinite loop. Research: Copy Reflexion + binary external + N=3	o HITL. Adapt: force the fail path. Skip: LLM self-critique as verify. Handoff 
eq replan.
> **Labels**: type:architecture, type:feature, P1, ControlPlane, Verifier, Replan, AntiTheatre, HITL
> **Branch**: `feat/verifier-replan-harden-254` (off `feat/long-run-context-253` @ 00aa2ae)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Standing verify is **binary external only** (named checker pass/fail) - **never** LLM self-critique / same-model judge as standing pass (Shinn Reflexion 2023; Panickssery 2024).
2. On fail: **232-class** bounded replan (N=3) then **HITL park** - never silent advance, never infinite loop.
3. **Forced-fail** smoke path proves fail 	o replan \le3 	o park without relying on an LLM to invent the fail.
4. **Handoff 
eq replan**: A2A / supervisor child handoff must not bump `replan_count` or emit replan spans.
5. Mark CARD-253 Done. Do **not** start CARD-255.

### Beat 2: What AutoReiv Does Now
1. CARD-216 external verifier policy + CARD-232 bounded auto-replan exist and unit/live-proof the gate in isolation.
2. Chat standing `_stream_turn_bound` still calls `fail_phase` on named-checker fail - **bypasses** 232 replan	o park (dead-end / theatre vs Done bar).
3. Same-model critic flag only blocks when checker name is empty; spoofed name + critic could still path oddly.
4. No first-class **forced fail** helper for marathon smoke; handoff vs replan distinction not locked in 254-class tests.

### Beat 3: What Will Change
1. Harden `resolve_verify_outcome`: LLM self-critique / `used_same_model_critic` **never** yields standing `verified`.
2. Add `apply_forced_fail_verify_gate` (binary external forced fail 	o 232 replan/park) for smoke + TDD.
3. Wire Chat standing verify-fail through `apply_phase_complete_verify_gate` (replan or park) - not `fail_phase` dead-end.
4. Lock handoff 
eq replan (child create does not bump `replan_count` / replan journey).
5. TDD red	o green; live smoke `notes/marathon-card254-live-smoke.json`; CHANGELOG + scorecard; push feat only.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-VRH-001]**: Binary external verify only - LLM self-critique / same-model critic never standing `verified`.
- [x] **[REQ-VRH-002]**: Forced fail 	o replan \le3 	o HITL park (232 class); no infinite loop / no silent advance.
- [x] **[REQ-VRH-003]**: Handoff 
eq replan - standing child handoff does not increment `replan_count` or emit `standing.replan`.
- [x] **[REQ-VRH-004]**: Chat standing named-checker fail uses `apply_phase_complete_verify_gate` (replan/park) - not `fail_phase` dead-end.
- [x] **[REQ-VRH-005]**: Automated tests red	o green; live smoke `notes/marathon-card254-live-smoke.json`; CHANGELOG + scorecard; push `feat/*` only - never qa/main; do not start 255.

## 3. Constraints

- Branch `feat/verifier-replan-harden-254` off `feat/long-run-context-253` @ 00aa2ae. Never qa/main. Do **not** merge to grok.
- Copy Reflexion + binary external + N=3	o HITL; adapt by **forcing** the fail path. Skip LLM self-critique as verify.
- Do not start CARD-255.

## 4. Out of scope

- CARD-255+
- Merging to grok / qa / main
- Replacing CARD-232 constants or inventing a second replan orchestrator
- Making builtin critic a standing success path

## 5. Proof

- Unit: forced fail 	o 3 replans 	o park; same-model critic never verified; handoff leaves replan_count untouched; Chat fail path uses standing gate.
- Live: forced fail smoke 	o `notes/marathon-card254-live-smoke.json`.

## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- Hardened `resolve_verify_outcome`: LLM self-critique / `used_same_model_critic` never standing `verified` (even with spoofed checker name).
- Added `apply_forced_fail_verify_gate` (binary external forced fail -> CARD-232 replan/park; no LLM).
- `refuse_infinite_replan` hard stop at `MAX_REPLAN_ATTEMPTS=3`.
- Chat `_stream_turn_bound` verify-fail now uses `apply_phase_complete_verify_gate` (replan/park) - not `fail_phase` dead-end.
- `handoff_must_not_replan` locks A2A child create != replan (`replan_count` untouched).
- Tests: `tests/unit/orchestration/test_verifier_replan_harden_254.py` (6) + 216/232 suites green.
- Live smoke PASS: `notes/marathon-card254-live-smoke.json` (forced fail -> replan x3 -> park).
- Status: **Done**. Do not start CARD-255. Push `feat/*` only.
