# Implementation Tasks: Multi-Agent Handoff Protocol & Supervisor Orchestration

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-A2A-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Standard A2A Handoff Envelope & Orchestrator Dispatch
- [x] **Task 1.1** `[REQ-A2A-001]`, `[REQ-A2A-002]`, `[REQ-A2A-004]`: [RED] Write unit tests in `tests/unit/orchestration/test_handoff_envelope.py` verifying 5-key envelope validation, context hydration, and specialist agent dispatch.
- [x] **Task 1.2** `[REQ-A2A-001]`, `[REQ-A2A-002]`, `[REQ-A2A-004]`: [GREEN] Implement `HandoffEnvelope` in `src/domain/orchestration/models.py` and `SupervisorOrchestrator` in `src/application/kernel/supervisor_orchestrator.py`.

### Slice 2: Delegate Subtask Skill & Inter-Agent Telemetry
- [x] **Task 2.1** `[REQ-A2A-003]`, `[REQ-A2A-005]`: [RED] Write unit tests in `tests/unit/skills/test_delegate_skill.py` verifying tool invocation and handoff span generation.
- [x] **Task 2.2** `[REQ-A2A-003]`, `[REQ-A2A-005]`: [GREEN] Implement `DelegateSubtaskSkill` in `src/application/skills/delegate_skill.py` and record `handoff` spans in `TelemetryCollector`.

### Slice 3: REST Delegation API
- [x] **Task 3.1** `[REQ-A2A-006]`: [RED] Write integration tests in `tests/unit/web/test_agent_delegation_api.py` verifying `POST /api/agents/delegate`.
- [x] **Task 3.2** `[REQ-A2A-006]`: [GREEN] Implement `POST /api/agents/delegate` endpoint in `src/web/app.py`.

### Slice 4: Verification, Traceability, & PR Gate
- [x] **Task 4.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 4.3**: Conclude Milestone 11 and merge into `qa`.
