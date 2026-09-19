# Implementation Tasks: Plan-and-Execute Graph Engine & Goal Mode

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-PLAN-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Domain Models & Planning Skill Tools
- [ ] **Task 1.1** `[REQ-PLAN-001]`, `[REQ-PLAN-003]`: [RED] Write unit tests in `tests/unit/planning/test_plan_models.py` and `tests/unit/skills/test_planning_skill.py`.
- [ ] **Task 1.2** `[REQ-PLAN-001]`, `[REQ-PLAN-003]`: [GREEN] Implement `src/domain/planning/models.py` and `src/application/skills/planning_skill.py`.

### Slice 2: Plan-and-Execute Engine & Step Orchestration
- [ ] **Task 2.1** `[REQ-PLAN-001]`, `[REQ-PLAN-002]`: [RED] Write unit tests in `tests/unit/kernel/test_plan_engine.py` verifying formulation, step-by-step dispatch, and goal completion synthesis.
- [ ] **Task 2.2** `[REQ-PLAN-001]`, `[REQ-PLAN-002]`: [GREEN] Implement `src/application/kernel/plan_engine.py`.

### Slice 3: REST Goal API & Web UI Visual Step Tracker
- [ ] **Task 3.1** `[REQ-PLAN-004]`, `[REQ-PLAN-005]`, `[REQ-PLAN-006]`: [RED] Write integration tests in `tests/unit/web/test_goal_chat_api.py`.
- [ ] **Task 3.2** `[REQ-PLAN-004]`, `[REQ-PLAN-005]`, `[REQ-PLAN-006]`: [GREEN] Implement `POST /api/chat/goal` in `src/web/app.py`, companion UI checkbox, and visual step checklist in `src/web/templates/index.html` & `src/web/static/app.js`.

### Slice 4: Verification, Traceability, & PR Gate
- [ ] **Task 4.1**: Run full test suite and linters (`pytest`, `ruff check .`).
- [ ] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [ ] **Task 4.3**: Conclude Milestone 14 and merge into `qa`.
