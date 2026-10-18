---
id: CARD-713
title: "Extract chat orchestration out of src/web/routers/chat.py and move application bootstrap out of src/infrastructure/agents/registry.py"
type: feature
status: Ready
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-713-chat-router-and-bootstrap-layering]
  checks: [tests/unit/architecture/test_card713_router_and_bootstrap_layering.py]
branch: feat/card-713-chat-router-and-bootstrap-layering
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-713 Extract chat orchestration out of src/web/routers/chat.py and move application bootstrap out of src/infrastructure/agents/registry.py

## Intent
1. `src/web/routers/chat.py` is 2,706 lines because 1,460 lines of multi-phase job execution (`execute_goal_job_phases`), LLM turn streaming (`_stream_turn_bound`), verification gating (`_apply_verify_gate`), background memory extraction, and a 627-line `chat_stream` worker closure live directly inside the FastAPI router.
2. `src/infrastructure/agents/registry.py` (`BuiltinAgentRegistry.bootstrap`) imports 38 modules from `src.application.*` inside `src/infrastructure/`, and `src/web/app.py` (680 lines) constructs duplicate `JobPhaseOrchestrator` and `UserSkillCatalog` instances and calls `app = create_app()` at module import time.
3. `src/application/system/busy.py` imports upward from `src/web/routers/chat.py` to inspect `_active_stream_tasks`.

## Goal
1. `src/web/routers/chat.py` is a thin HTTP/SSE router (<800 lines) that delegates turn streaming, standing job phase execution, verification gating, and attachment storage to `src/application/chat/`.
2. Application service & tool wiring (`bootstrap_ecosystem`) lives in `src/application/`, eliminating the 38 upward `src.infrastructure` -> `src.application` imports in `registry.py` and the duplicate `JobPhaseOrchestrator` / `UserSkillCatalog` instantiations in `create_app()`.
3. Active stream tracking lives in `src/application/chat/` so `src/application/system/busy.py` no longer imports from `src/web/`.

## Change
- Extract `_stream_turn_bound`, `execute_goal_job_phases`, `execute_goal_plan_steps`, `_apply_verify_gate`, `_background_extract_turn_memory`, and the `chat_stream` worker orchestration from `src/web/routers/chat.py` into `src/application/chat/` modules (`turn_streamer.py`, `job_runner.py`, `stream_worker.py`, `attachments.py`), bringing `src/web/routers/chat.py` and all new modules under 800 lines.
- Move tool/service registration out of `BuiltinAgentRegistry.bootstrap()` (`src/infrastructure/agents/registry.py`) into an application-layer bootstrap module and clean up `src/web/app.py` so each core service (`JobPhaseOrchestrator`, `UserSkillCatalog`) is instantiated once.
- Move active stream tracking to `src/application/chat/` and remove the `from src.web.routers import chat` import in `src/application/system/busy.py`.

## What dies
- 1,460 lines of inline orchestration in `src/web/routers/chat.py`.
- Upward `src.application.*` imports in `src/infrastructure/agents/registry.py` and upward `src.web.*` import in `src/application/system/busy.py`.
- Duplicate `JobPhaseOrchestrator` and `UserSkillCatalog` instantiations and redundant `except NameError:` blocks in `src/web/app.py`.

## Proof
- Journey `card-713-chat-router-and-bootstrap-layering`:
  1. Run a Chat turn and a multi-step goal job in `#view-chat` on desktop and phone, verifying SSE streaming, tool execution, and session persistence.
- Checks:
  - `tests/unit/architecture/test_card713_router_and_bootstrap_layering.py`

## Plan and decisions
- Phase 3 router & bootstrap layering cleanup.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-713\...`

## Release note
- Extracted chat turn and multi-phase job orchestration from `src/web/routers/chat.py` into `src/application/chat/`, moved ecosystem tool bootstrap out of `src/infrastructure/agents/registry.py`, and removed upward web imports from `src/application/` [CARD-713].
