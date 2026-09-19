# Implementation Tasks: Retire Autonomous Training Checkbox & JIT Synthesis

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks reference corresponding `[REQ-PRUNE-AUTO-xxx]` tags.  

---

## Vertical Slice Breakdown

### Slice 1: Agent Studio UI Pruning & Test Alignment
- [x] **Task 1.1** `[REQ-PRUNE-AUTO-001, REQ-PRUNE-AUTO-004]`: [RED] Update `tests/unit/frontend/auto_train_backlog.test.js` to assert that `#forgeAutoTrainCheckbox` and `#forgeMaxTrainRetriesInput` are NOT present in `index.html` and NOT bound in `forge.js`, while preserving `#agentTrainingBacklogCard` and `#agentBacklogList`.
- [x] **Task 1.2** `[REQ-PRUNE-AUTO-001]`: [GREEN] Remove lines 2622–2636 from `src/web/templates/index.html`.
- [x] **Task 1.3** `[REQ-PRUNE-AUTO-001]`: [GREEN] Clean up `forgeAutoTrainCheckbox` and `forgeMaxTrainRetriesInput` references from `src/web/static/modules/studios/forge.js`.
- [x] **Task 1.4**: Run `npm run test:unit:frontend` to verify frontend tests pass.

### Slice 2: Kernel JIT Synthesis Retirement & Factory Backlog Routing
- [x] **Task 2.1** `[REQ-PRUNE-AUTO-002, REQ-PRUNE-AUTO-004]`: [RED] Update kernel tests in `tests/unit/kernel/test_in_flight_synthesis.py` or write test verifying that detected gaps unconditionally route to `capability_gap_repo.create_gap` without invoking `jit_synthesizer`.
- [x] **Task 2.2** `[REQ-PRUNE-AUTO-002]`: [GREEN] Update `src/application/kernel/agent_kernel.py` in `run_turn` and `run_stream` to unconditionally record detected gaps to `capability_gap_repo.create_gap`.
- [x] **Task 2.3** `[REQ-PRUNE-AUTO-003]`: Verify `AgentProfile` and `AgentCustomization` models preserve backward-compatible default values.
- [x] **Task 2.4**: Run pytest on kernel test suite.

### Slice 3: Verification, RTM & Pre-flight
- [x] **Task 3.1**: Register requirements `[REQ-PRUNE-AUTO-001..004]` in `docs/rtm.json`.
- [x] **Task 3.2**: Run `uv run python .agents/skills/rtm-sync/scripts/preflight.py`.
- [x] **Task 3.3**: Update `CHANGELOG.md` under `[Unreleased]`.
