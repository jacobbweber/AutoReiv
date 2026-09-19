# Implementation Tasks: Self-Verification Loops & SRE Health Auditing

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-VERIFY-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Deterministic Verification Skill & Programmatic Assertions
- [ ] **Task 1.1** `[REQ-VERIFY-001]`: [RED] Write unit tests in `tests/unit/skills/test_verification_skill.py` verifying programmatic metric assertions, schema validation, and discrepancy diagnostics.
- [ ] **Task 1.2** `[REQ-VERIFY-001]`: [GREEN] Implement `VerificationSkill` in `src/application/skills/verification_skill.py`.

### Slice 2: Reflexion Loop State Machine & Kernel Verified Turn
- [ ] **Task 2.1** `[REQ-VERIFY-002]`, `[REQ-VERIFY-003]`: [RED] Write unit tests in `tests/unit/kernel/test_reflexion_engine.py` verifying critique note generation, refinement iterations, and max budget termination.
- [ ] **Task 2.2** `[REQ-VERIFY-002]`, `[REQ-VERIFY-003]`: [GREEN] Implement `ReflexionLoopEngine` in `src/application/kernel/reflexion_engine.py` and bind `run_verified_turn` to `AgentKernel`.

### Slice 3: Auditor Critic Profile & REST Endpoints
- [ ] **Task 3.1** `[REQ-VERIFY-004]`, `[REQ-VERIFY-005]`, `[REQ-VERIFY-006]`: [RED] Write unit & integration tests in `tests/unit/web/test_verified_chat_api.py` verifying `POST /api/chat/verified` and `POST /api/agents/audit`.
- [ ] **Task 3.2** `[REQ-VERIFY-004]`, `[REQ-VERIFY-005]`, `[REQ-VERIFY-006]`: [GREEN] Add `AUDITOR_CRITIC_PROFILE` in `src/domain/agents/profiles.py` and implement REST endpoints in `src/web/app.py`.

### Slice 4: Verification, Traceability, & PR Gate
- [ ] **Task 4.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [ ] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [ ] **Task 4.3**: Conclude Milestone 13 and merge into `qa`.
