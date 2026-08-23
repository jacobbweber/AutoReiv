# Implementation Tasks: Built-in Agents & Scoped Skills

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-AGENTS-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Built-in Agent Profiles & Factory
- [x] **Task 1.1** `[REQ-AGENTS-001]`: [RED] Write failing unit tests in `tests/unit/agents/test_builtin_profiles.py` verifying definitions of all 4 agents and tool permissions.
- [x] **Task 1.2** `[REQ-AGENTS-001]`: [GREEN] Implement `src/domain/agents/profiles.py` with standard profiles and validation.

### Slice 2: Task Tracker Skill
- [x] **Task 2.1** `[REQ-AGENTS-002]`: [RED] Write failing unit tests in `tests/unit/skills/test_task_tracker_skill.py` for task CRUD and persistence in SQLite.
- [x] **Task 2.2** `[REQ-AGENTS-002]`: [GREEN] Implement task models in `src/domain/skills/task_models.py` and `TaskTrackerSkill` in `src/application/skills/task_tracker_skill.py`.

### Slice 3: Linux Sysadmin Skills (System Info & Safe CLI)
- [x] **Task 3.1** `[REQ-AGENTS-003]`, `[REQ-AGENTS-004]`: [RED] Write failing unit tests in `tests/unit/skills/test_sysadmin_skill.py` for host metrics collection and timeout command execution.
- [x] **Task 3.2** `[REQ-AGENTS-003]`, `[REQ-AGENTS-004]`: [GREEN] Implement `SysadminSkill` in `src/application/skills/sysadmin_skill.py`.

### Slice 4: Librarian Skills (YAML Frontmatter & PARA-Wiki)
- [x] **Task 4.1** `[REQ-AGENTS-005]`: [RED] Write failing unit tests in `tests/unit/skills/test_librarian_skill.py` for frontmatter parsing, note creation, and path traversal protection.
- [x] **Task 4.2** `[REQ-AGENTS-005]`: [GREEN] Implement `LibrarianSkill` in `src/application/skills/librarian_skill.py`.

### Slice 5: System Agent Skills & Full Agent Registry
- [x] **Task 5.1** `[REQ-AGENTS-006]`: [RED] Write failing unit tests in `tests/unit/skills/test_system_agent_skill.py` for health checks and telemetry querying.
- [x] **Task 5.2** `[REQ-AGENTS-006]`: [GREEN] Implement `SystemAgentSkill` in `src/application/skills/system_agent_skill.py` and `BuiltinAgentRegistry` in `src/infrastructure/agents/registry.py`.

### Slice 6: Verification, Traceability, & QA Gate
- [x] **Task 6.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 6.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 6.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
