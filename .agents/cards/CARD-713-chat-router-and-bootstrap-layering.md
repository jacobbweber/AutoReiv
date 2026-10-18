---
id: CARD-713
title: "Extract chat orchestration out of src/web/routers/chat.py and move application bootstrap out of src/infrastructure/agents/registry.py"
type: feature
status: Done
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-713-chat-router-and-bootstrap-layering]
  checks: [tests/unit/architecture/test_card713_router_and_bootstrap_layering.py]
branch: feat/card-713-chat-router-and-bootstrap-layering
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-17
---

# CARD-713 Extract chat orchestration out of src/web/routers/chat.py and move application bootstrap out of src/infrastructure/agents/registry.py

## Intent
1. `src/web/routers/chat.py` was 2,706 lines because multi-phase job execution (`execute_goal_job_phases`), LLM turn streaming (`_stream_turn_bound`), verification gating (`_apply_verify_gate`), background memory extraction, attachment persistence, and active stream task tracking lived directly inside the FastAPI router.
2. `src/infrastructure/agents/registry.py` (`BuiltinAgentRegistry.bootstrap`) imported 37 modules from `src.application.*` inside `src/infrastructure/`, and `src/web/app.py` had duplicate `UserSkillCatalog` wiring, `except NameError:` blocks, and eager `app = create_app()` at import time.
3. `src/application/system/busy.py` imported upward from `src/web/routers/chat.py` to inspect `_active_stream_tasks`.

## Goal
1. `src/web/routers/chat.py` is a thin HTTP/SSE router (<800 lines) that delegates turn streaming, standing job phase execution, plan review resumption, verification gating, active stream tracking, and attachment storage to `src/application/chat/`.
2. Application service & tool wiring (`bootstrap_ecosystem`) lives in `src/application/bootstrap/ecosystem.py`, eliminating the 37 upward `src.infrastructure` -> `src.application` skill imports in `registry.py` and cleaning up `src/web/app.py`.
3. Active stream tracking lives in `src/application/chat/stream_registry.py` so `src/application/system/busy.py` no longer imports from `src/web/`.

## Change
- Extracted `src/application/chat/stream_registry.py` (94 lines), `src/application/chat/attachments.py` (213 lines), `src/application/chat/turn_streamer.py` (761 lines), `src/application/chat/job_runner.py` (650 lines), and `src/application/chat/job_resume.py` (593 lines) from `src/web/routers/chat.py`, reducing `src/web/routers/chat.py` from 2,706 lines to 784 lines.
- Created `src/application/bootstrap/ecosystem.py` (267 lines) with `bootstrap_ecosystem(...)` and updated `BuiltinAgentRegistry.bootstrap()` in `src/infrastructure/agents/registry.py` (206 lines) to delegate to it, removing all 37 `src.application.*` skill/service imports from `src/infrastructure/agents/registry.py`.
- Updated `src/application/system/busy.py` to call `has_active_chat_streams()` from `src/application/chat/stream_registry.py` instead of importing `src.web.routers.chat`.
- Cleaned up `src/web/app.py` (671 lines) to wire `job_orchestrator` into `registry.orchestration_tools`, eliminate duplicate `UserSkillCatalog` and `except NameError:` blocks, and expose the module-level `app` lazily via PEP 562 `__getattr__`.

## What dies
- ~1,920 lines of inline orchestration in `src/web/routers/chat.py`.
- 37 upward `src.application.*` skill/tool imports in `src/infrastructure/agents/registry.py` and upward `src.web.*` import in `src/application/system/busy.py`.
- Duplicate `UserSkillCatalog` wiring, `except NameError:` blocks, and eager module-import `app = create_app()` in `src/web/app.py`.

## Proof
- Journey `card-713-chat-router-and-bootstrap-layering`:
  1. Verifies `<800`-line bounds across `src/web/routers/chat.py`, `src/application/chat/*.py`, and `src/application/bootstrap/ecosystem.py`, layering guards, and attachment upload/download round-trip.
  2. Runs a streaming tool-calling turn in `#view-chat` on desktop and phone, verifying SSE streaming, session status tracking, tool execution, and responsive layout.
- Checks:
  - `tests/unit/architecture/test_card713_router_and_bootstrap_layering.py`

## Plan and decisions
- Phase 3 router & bootstrap layering cleanup.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-713-chat-router-and-bootstrap-layering` | desktop | PASS | Verified <800-line chat/bootstrap modules, attachment round-trip, and streaming tool-calling turn |
| `card-713-chat-router-and-bootstrap-layering` | phone | PASS | Verified <800-line chat/bootstrap modules, attachment round-trip, and streaming tool-calling turn with 0px overflow |

Screenshots:
- `/tmp/autoreiv-qa/card-713/card-713-chat-router-and-bootstrap-layering-desktop-01-verify-chat-router-decomposition-bootstrap-layer.png`
- `/tmp/autoreiv-qa/card-713/card-713-chat-router-and-bootstrap-layering-desktop-03-verify-persisted-messages-session-status-endpoin.png`
- `/tmp/autoreiv-qa/card-713/card-713-chat-router-and-bootstrap-layering-phone-03-verify-persisted-messages-session-status-endpoin.png`

## Release note
- Extracted chat turn and multi-phase job orchestration from `src/web/routers/chat.py` into `src/application/chat/`, moved ecosystem tool bootstrap out of `src/infrastructure/agents/registry.py`, and removed upward web imports from `src/application/` [CARD-713].
