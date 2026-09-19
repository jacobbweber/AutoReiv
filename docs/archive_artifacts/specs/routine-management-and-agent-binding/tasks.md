# Implementation Tasks: Routine Management and Agent Binding

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-ROUT-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Schedule Humanizer & Next-Run Calculator (`[REQ-ROUT-001]`)
- [x] **Task 1.1**: [RED] Write unit tests for cron humanizer and next run calculation in `tests/unit/routines/test_schedule_humanizer.py`.
- [x] **Task 1.2**: [GREEN] Implement `src/application/routines/humanizer.py` with `cron_to_human()` and `compute_next_run_eta()`.

### Slice 2: Routine CRUD & Toggle REST Endpoints (`[REQ-ROUT-002]`, `[REQ-ROUT-003]`)
- [x] **Task 2.1**: [RED] Write integration tests in `tests/unit/web/test_routine_management_api.py`.
- [x] **Task 2.2**: [GREEN] Add `DELETE /api/routines/{id}`, `PUT /api/routines/{id}`, `POST /api/routines/{id}/toggle`, and `agent_id` filtering in `src/web/app.py` and `SQLiteStateStore`.

### Slice 3: Routines Studio Management UI & Modal Editor (`[REQ-ROUT-004]`)
- [x] **Task 3.1**: Build `[+ New Routine]` modal and edit controls in `src/web/templates/index.html`.
- [x] **Task 3.2**: Implement routine creation, editing, pausing, and deleting logic with humanized schedule display in `src/web/static/app.js`.

### Slice 4: Agent Forge "Assigned Routines" Character Sheet Integration (`[REQ-ROUT-005]`)
- [x] **Task 4.1**: Add `[⏰ Assigned Background Routines]` card to the Agent Forge character sheet in `src/web/templates/index.html`.
- [x] **Task 4.2**: Wire dynamic agent routine loading and rendering in `src/web/static/app.js`.

### Slice 5: Verification, DoD Pre-Flight & Session Wrap-Up
- [x] **Task 5.1**: Run full test suite (`pytest`) and linters (`ruff check .`).
- [x] **Task 5.2**: Validate RTM integrity (`verify_rtm.py --pre-flight` with all requirements passing).
- [x] **Task 5.3**: Live test routine creation, editing, pausing, running, and agent binding on running server.
