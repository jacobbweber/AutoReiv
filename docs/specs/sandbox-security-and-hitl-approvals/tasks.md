# Implementation Tasks: Sandbox Security Guardrails & HITL Approvals

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-SAFE-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Dangerous Command Filter & Ephemeral Sandbox Worker
- [x] **Task 1.1** `[REQ-SAFE-001]`, `[REQ-SAFE-002]`: [RED] Write unit tests in `tests/unit/skills/test_sandbox_security.py` verifying dangerous command regex matching and isolated temp-dir subprocess execution.
- [x] **Task 1.2** `[REQ-SAFE-001]`, `[REQ-SAFE-002]`: [GREEN] Implement `DangerousCommandFilter` in `src/application/skills/command_filter.py` and `SandboxedSubprocessWorker` in `src/application/skills/sandbox_worker.py`.

### Slice 2: High-Risk Tool Tagging & Pending Approvals SQLite Store
- [x] **Task 2.1** `[REQ-SAFE-003]`, `[REQ-SAFE-004]`: [RED] Write unit tests in `tests/unit/kernel/test_hitl_approvals.py` verifying `is_high_risk` tool flags and `pending_approvals` CRUD operations.
- [x] **Task 2.2** `[REQ-SAFE-003]`, `[REQ-SAFE-004]`: [GREEN] Add `is_high_risk` property to `ToolDefinition`, add `pending_approvals` table in `src/infrastructure/memory/sqlite_store.py`, and implement `HITLApprovalEngine`.

### Slice 3: REST Approval Endpoints & Real-Time Stream Cancellation
- [x] **Task 3.1** `[REQ-SAFE-005]`, `[REQ-SAFE-006]`: [RED] Write integration tests in `tests/unit/web/test_hitl_web_api.py` verifying `GET /api/approvals/pending`, `POST /api/approvals/{id}/decision`, and `POST /api/chat/stream/{session_id}/abort`.
- [x] **Task 3.2** `[REQ-SAFE-005]`, `[REQ-SAFE-006]`: [GREEN] Implement approval REST routes and stream cancellation registry in `src/web/app.py`.

### Slice 4: Verification, Traceability, & PR Gate
- [x] **Task 4.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 4.3**: Conclude Milestone 10 and merge into `qa`.
