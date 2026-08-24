# Implementation Tasks: Lean JIT Agent Discovery and Isolated Subagent Handoff Engine

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks reference their corresponding `[REQ-ORCH-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: JIT Agent Directory Service (`[REQ-ORCH-001]`)
- [x] **Task 1.1**: [RED] Write unit tests for `AgentDirectoryService` in `tests/unit/orchestration/test_agent_directory_service.py`.
- [x] **Task 1.2**: [GREEN] Implement `AgentDirectoryService` in `src/application/orchestration/directory_service.py` with fast keyword and capability matching across built-in and SQLite custom agents.

### Slice 2: Orchestration Skill & Isolated Handoff Engine (`[REQ-ORCH-002]`, `[REQ-ORCH-003]`)
- [x] **Task 2.1**: [RED] Write unit tests for `HandoffIsolationEngine` and `OrchestrationSkill` (`lookup_agents`, `handoff_to_agent`, anti-recursion, depth limiting) in `tests/unit/skills/test_orchestration_skill.py`.
- [x] **Task 2.2**: [GREEN] Implement `HandoffIsolationEngine` in `src/application/orchestration/handoff_engine.py` and `OrchestrationSkill` in `src/application/skills/orchestration_skill.py`.
- [x] **Task 2.3**: Update `src/application/skills/manifest.py` to register `OrchestrationSkill` in the hierarchical skill catalog.

### Slice 3: Control Plane Streaming Telemetry & Chat UI (`[REQ-ORCH-004]`)
- [x] **Task 3.1**: Update `src/web/app.py` to wire `HandoffIsolationEngine` and `AgentDirectoryService` to `AgentKernel`.
- [x] **Task 3.2**: Update `src/web/static/app.js` and `src/web/templates/index.html` to render visual subagent delegation badges in Chat Studio.

### Slice 4: Verification, Pre-Flight Gates & Session Wrap-Up
- [ ] **Task 4.1**: Run full test suite (`pytest`) and linting (`ruff check .`).
- [ ] **Task 4.2**: Verify RTM integrity (`verify_rtm.py --pre-flight` with all 114 requirements passing).
- [ ] **Task 4.3**: Live test JIT agent lookup and subagent handoff in browser chat.
