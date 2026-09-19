# Implementation Tasks: Multi-OS Packaging & Bare-Metal / Docker Deployment

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-DEPLOY-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: CLI Entry Point & Dispatcher
- [x] **Task 1.1** `[REQ-DEPLOY-001]`, `[REQ-DEPLOY-002]`: [RED] Write failing unit tests in `tests/unit/cli/test_cli_commands.py` verifying `serve`, `status`, `chat`, and `routine` CLI parsing and execution.
- [x] **Task 1.2** `[REQ-DEPLOY-001]`, `[REQ-DEPLOY-002]`: [GREEN] Implement CLI command dispatcher in `src/cli/main.py`.

### Slice 2: Background Routine Engine Server Lifespan
- [x] **Task 2.1** `[REQ-DEPLOY-006]`: [RED] Write failing integration tests in `tests/unit/cli/test_server_lifespan.py` verifying the background `RoutineScheduler` launches on FastAPI app startup and shuts down gracefully.
- [x] **Task 2.2** `[REQ-DEPLOY-006]`: [GREEN] Integrate `lifespan` handler into `src/web/app.py`.

### Slice 3: Multi-OS Manifests & Containerization
- [x] **Task 3.1** `[REQ-DEPLOY-003]`: Create Ubuntu `systemd` service unit (`deploy/systemd/autoreiv.service`) and installer script (`deploy/systemd/install_systemd.sh`).
- [x] **Task 3.2** `[REQ-DEPLOY-004]`: Create Windows runner scripts (`deploy/windows/run_autoreiv.ps1`, `run_autoreiv.bat`, `install_windows_service.ps1`).
- [x] **Task 3.3** `[REQ-DEPLOY-005]`: Create production `Dockerfile`, `docker-compose.yml`, and `.env.example` with host volume mounts.

### Slice 4: Verification, Traceability, & QA Gate
- [x] **Task 4.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 4.3**: Prepare step-by-step verification instructions for Human QA tester targeting the `qa` branch.
