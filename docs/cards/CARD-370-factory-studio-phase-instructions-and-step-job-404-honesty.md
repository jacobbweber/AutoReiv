# [CARD-370] Factory Studio Phase Instructions and Step Job 404 Honesty

> **Status**: In Review  
> **Created**: 2026-09-19  
> **Spec Reference**: none  
> **Labels**: `type:bugfix`, `backend`, `factory-studio`, `api-honesty`

---

## 1. Why / Intent
Fix two critical API reliability and contract honesty issues in Factory Studio (`agent_training_factory.py`) discovered during live stress testing: an unhandled HTTP 500 error when updating or resetting phase instructions due to an application state attribute mismatch, and an inconsistent HTTP 200 return for stepping non-existent jobs.

---

## 2. Three Beats

### Beat 1: What Jacob Means
When an operator customizes or resets phase instructions in Factory Studio, the server must properly resolve the database path and persist/reset the prompt without crashing with an HTTP 500 error. When an operator or automated client attempts to step a job that does not exist, the API must honestly return HTTP 404 Not Found rather than falsely returning HTTP 200 OK with a null job.

### Beat 2: What AutoReiv Does Now
- In `src/web/routers/agent_training_factory.py` lines 722, 730, and 743, `list_phase_instructions`, `update_phase_instruction`, and `delete_phase_instruction` look for `getattr(request.app.state, "data_paths", None)`. However, `src/web/app.py` line 342 sets `app.state.data_dir_paths = data_paths`. Because `data_paths` is not defined on `app.state`, `paths` is always `None`, raising `HTTPException(status_code=500, detail="Database path not initialized.")`.
- In `src/web/routers/agent_training_factory.py` lines 329–341, `step_factory_job` calls `runner.step_job(job_id)` and returns `{"success": True, "stepped": False, "job": None}` with HTTP 200 when `job_id` does not exist. In contrast, `promote` and `delete` check `if not job:` and raise HTTP 404.

### Beat 3: What Will Change
- In `src/web/routers/agent_training_factory.py`, update lines 722, 730, and 743 to inspect `getattr(request.app.state, "data_dir_paths", None)` with a fallback to `getattr(request.app.state.store, "db_path", None)`.
- In `src/web/routers/agent_training_factory.py`, update `step_factory_job` to look up `job = repo.get_job(job_id)` and raise `HTTPException(status_code=404, detail=f"Job '{job_id}' not found")` if `job is None`.
- Add comprehensive unit tests in `tests/unit/web/test_agent_training_factory_router.py` verifying successful phase instruction customization, reset, and 404 rejection on non-existent job stepping.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `GET /api/agent_training_factory/phases/instructions` succeeds and returns configured phase instructions.
- [x] `PUT /api/agent_training_factory/phases/{phase_id}/instructions` successfully saves custom instructions without HTTP 500 error.
- [x] `DELETE /api/agent_training_factory/phases/{phase_id}/instructions` successfully resets phase instructions to default without HTTP 500 error.
- [x] `POST /api/agent_training_factory/jobs/{job_id}/step` returns HTTP 404 with detail `"Job '<job_id>' not found"` when `job_id` does not exist.
- [x] Automated regression tests pass via `pytest tests/unit/web/test_agent_training_factory_router.py`.
- [x] Zero lint errors via `ruff check src tests`.
- [x] All 7 preflight gates pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to active studio functionality.
- Single isolated `feat/card-370-factory-router-fixes` branch cut from `qa` upon Jacob's `build` approval.
