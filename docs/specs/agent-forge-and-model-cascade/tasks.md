# Implementation Tasks: Agent Forge Studio & Purpose Routing Cascade

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-FORGE-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Purpose-Based Model Resolution Cascade (`[REQ-FORGE-001]`, `[REQ-FORGE-002]`)
- [x] **Task 1.1**: [RED] Write unit tests in `tests/unit/kernel/test_purpose_model_cascade.py`.
- [x] **Task 1.2**: [GREEN] Update `AgentProfile` in `src/domain/kernel/models.py`, `BUILTIN_PROFILES` in `src/domain/agents/profiles.py`, and implement cascade resolution in `AgentKernel` (`src/application/kernel/agent_kernel.py`).

### Slice 2: SQLite Custom Agent CRUD & Registry (`[REQ-FORGE-003]`, `[REQ-FORGE-004]`)
- [x] **Task 2.1**: [RED] Write tests in `tests/unit/agents/test_custom_agent_crud.py` for SQLite table creation, CRUD operations, and built-in protection.
- [x] **Task 2.2**: [GREEN] Implement `custom_agents` table and methods in `src/infrastructure/memory/sqlite_store.py` and `BuiltinAgentRegistry` in `src/infrastructure/agents/registry.py`.

### Slice 3: System Agent Meta-Builder Skill (`[REQ-FORGE-005]`)
- [x] **Task 3.1**: [RED] Write tests in `tests/unit/skills/test_agent_builder_skill.py`.
- [x] **Task 3.2**: [GREEN] Implement `src/application/skills/agent_builder_skill.py` and register it on `system-agent`.

### Slice 4: REST Agent Management Endpoints & "Agent Forge" UI (`[REQ-FORGE-006]`)
- [x] **Task 4.1**: [RED] Write integration tests in `tests/unit/web/test_agent_forge_api.py`.
- [x] **Task 4.2**: [GREEN] Add REST endpoints (`POST /api/agents`, `PUT /api/agents/{id}`, `DELETE /api/agents/{id}`) in `src/web/app.py`, and build the Agent Studio Character Sheet + System Co-Pilot in `src/web/templates/index.html` & `src/web/static/app.js`.

### Slice 5: Verification, DoD Pre-Flight, & Goal Completion
- [x] **Task 5.1**: Run full test suite (`pytest`) and linters (`ruff check .`).
- [x] **Task 5.2**: Validate RTM integrity (`verify_rtm.py --pre-flight` with 96 requirements).
- [x] **Task 5.3**: Live test creating, editing, and using custom agents on remote hardware.
- [x] **Task 5.4**: Conclude Milestone 16 and merge into `qa`.
