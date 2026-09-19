# [CARD-368] Retire Autonomous Training Checkbox and In-Flight JIT Synthesis

> **Status**: In Review
> **Created**: 2026-09-19
> **Spec Reference**: `docs/specs/retire-autonomous-training/`
> **Labels**: `type:cleanup`, `domain:agents`, `domain:kernel`, `domain:forge`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Remove the vestigial "Allow Autonomous Training" checkbox and "Max Auto-Train Retries" input from Agent Studio (Agent Forge).
2. Stop attempting unpredictable in-flight JIT tool code synthesis in Python during live chat turns.
3. Ensure any capability gaps detected during chat are logged directly and reliably to Factory Studio's Backlog queue for deliberate review and test-driven authoring.

### Beat 2: What AutoReiv Does Now
1. `src/web/templates/index.html` renders `#forgeAutoTrainCheckbox` and `#forgeMaxTrainRetriesInput`.
2. `src/web/static/modules/studios/forge.js` binds and persists `allow_autonomous_training` and `max_training_retries`.
3. In `src/application/kernel/agent_kernel.py`, if an agent has `allow_autonomous_training` enabled, it invokes `jit_synthesizer.synthesize_and_deploy`, attempting in-flight sandbox retries to compile raw Python code during active conversation turns.

### Beat 3: What Will Change
1. Remove `#forgeAutoTrainCheckbox` and `#forgeMaxTrainRetriesInput` from Agent Studio UI (`index.html` and `forge.js`).
2. Simplify the capability gap handler in `agent_kernel.py`: whenever a gap is detected, always log it directly to SQLite `capability_gaps` (`capability_gap_repo.create_gap`) for Factory Studio; eliminate the in-flight JIT synthesis branch during chat execution.
3. Keep backward-compatible model defaults (`allow_autonomous_training = False`, `max_training_retries = 2`) on `AgentProfile` and `AgentCustomization` so existing database schemas and rows remain completely stable.
4. Update frontend and backend unit tests to verify the pruned UI and the direct Factory backlog routing.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] `[REQ-PRUNE-AUTO-001]`: Remove `#forgeAutoTrainCheckbox` and `#forgeMaxTrainRetriesInput` from `src/web/templates/index.html` and clean up DOM references in `src/web/static/modules/studios/forge.js`.
- [x] `[REQ-PRUNE-AUTO-002]`: Update `src/application/kernel/agent_kernel.py` so all detected capability gaps log directly to `capability_gap_repo.create_gap` (Factory Studio backlog) with zero in-flight JIT synthesis execution during chat.
- [x] `[REQ-PRUNE-AUTO-003]`: Maintain backward-compatible schema and API defaults on `AgentProfile` and `AgentCustomization` with zero database migrations or breaking contract changes.
- [x] `[REQ-PRUNE-AUTO-004]`: Unit tests in `tests/unit/frontend/auto_train_backlog.test.js` and `tests/unit/kernel/` pass cleanly with zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 3. Constraints & Honor Flags

- Cut from `qa` into isolated branch `feat/card-368-retire-auto-train-checkbox`.
- TDD Red-Green-Refactor.
- Hold merge until Jacob says `merge to qa`.
