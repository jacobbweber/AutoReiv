# [CARD-216] Standing External Verifier Policy

> **Status**: In Progress
> **Created**: 2026-09-10
> **Spec Reference**: Design room lock after CARD-215; Shinn Reflexion (2023); Panickssery et al. same-model judges (2024)
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Binary external check only**: Reflexion / retry is allowed only when a **named checker** returns a real binary pass/fail (pytest, schema assert, health probe, or tool checker). Same-model "looks good" critique is not a success path.
2. **Honest skip**: If no checker is configured, verify is skipped honestly (`skipped_no_checker`) — never a fake pass, never silent same-model judge theatre.
3. **Standing gate**: This policy is wired into `JobPhaseOrchestrator` phase-complete and `run_verified_turn`, not a Chat toggle.
4. **Operator truth**: Chat + Observability show `verified` / `skipped_no_checker` / `failed` so Jacob can see what actually happened.
5. **Not this card**: Capability catalog (slice C), self-write of checkers.

### Beat 2: What AutoReiv Does Now
1. CARD-215 standing Job-Graph retires `goal_mode` and skips Chat `self_verify` without a checker (`status: skipped`).
2. `ReflexionLoopEngine` still accepts `use_builtin_critic=True` (same-model judge) as an alternate check path — standing policy must not treat that as pass authority.
3. `JobPhaseOrchestrator.complete_phase` does not encode verify outcome statuses; Chat `_apply_verify_gate` is the main gate today.
4. Chat badge already distinguishes passed / skipped / failed; Observability journey does not yet surface a durable `verify_status` enum of `verified | skipped_no_checker | failed`.

### Beat 3: What Will Change
1. Introduce a standing external-verifier policy module (status enum + helpers) citing Shinn Reflexion 2023 and Panickssery 2024 same-model judge risk.
2. Phase-complete path records / emits `verified` | `skipped_no_checker` | `failed`; missing checker never advances as verified.
3. `run_verified_turn` / Reflexion retry only when a named binary checker is present; missing checker → `skipped_no_checker`.
4. Chat + Observability display those three statuses.
5. Proof: red tests then green. Out of scope: catalog C, self-write.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-VERIFY-EXT-001]**: Named checker with binary pass/fail may run Reflexion/retry; result is `verified` or `failed`.
- [x] **[REQ-VERIFY-EXT-002]**: Missing checker → `skipped_no_checker` (honest skip); never `verification_passed=true` and never same-model-only success.
- [x] **[REQ-VERIFY-EXT-003]**: Policy is enforced at JobPhaseOrchestrator phase-complete gate and `AgentKernel.run_verified_turn`.
- [x] **[REQ-VERIFY-EXT-004]**: Chat + Observability show `verified` / `skipped_no_checker` / `failed`.
- [x] **[REQ-VERIFY-EXT-005]**: Automated tests: red then green; ruff clean; work on `feat/*` off `grok` — never merge `qa`/`main`.
- [x] **[REQ-VERIFY-EXT-006]**: CHANGELOG `[Unreleased]` notes the standing external-verifier policy; card cites Shinn 2023 + Panickssery 2024.

---

## 3. Constraints & Honor Flags

- Status: **In Progress** (build started on Jarvis marathon).
- Branch: continue `feat/standing-job-graph-runtime` or cut `feat/standing-external-verifier-policy` from `grok` / current feat. Never push `qa`/`main`.
- Out of scope: capability catalog C, self-write of verifiers, new Chat mode toggles.
- Anti-theatre: durable verify_status on phase/job facts or SSE + Studio display; failure mode explicit.

---

## 4. Modules Likely Touched

- `src/application/orchestration/` — policy + phase-complete gate
- `src/application/kernel/reflexion_engine.py` + `agent_kernel.run_verified_turn`
- `src/web/routers/chat.py` — SSE status strings
- Chat / Observability SPA modules
- `tests/unit/` + `tests/integration/` red→green

---

## 5. Citations

- Shinn, Noah et al. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning*.
- Panickssery, Arjun et al. (2024). *LLM Evaluators Recognize and Favor Their Own Generations* (same-model judge bias).


