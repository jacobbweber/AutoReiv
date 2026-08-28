# Tasks: Visual Goal Mode & Reflexion Streaming

## Vertical Slices

### Slice 1: Backend SSE Streaming for Goal Mode & Reflexion (`[REQ-CHAT-010]`, `[REQ-CHAT-011]`, `[REQ-CHAT-012]`, `[REQ-CHAT-014]`)
- [x] Task 1.1: Add unit/integration tests in `tests/integration/test_chat_stream_modes.py` asserting SSE emissions for `goal_mode=True` (`plan_formulated`, `step_start`, `step_complete`) and `self_verify=True` (`reflexion_attempt`, `reflexion_verified`).
- [x] Task 1.2: Update `ChatStreamRequest` model in `src/web/routers/chat.py` with `goal_mode: bool = False` and `self_verify: bool = False`.
- [x] Task 1.3: Update `chat_stream` generator in `src/web/routers/chat.py` to route through `PlanAndExecuteEngine` and `ReflexionLoopEngine` with event yielding.

### Slice 2: Frontend Interactive Milestone Tracker & Reflexion Badges (`[REQ-CHAT-013]`)
- [x] Task 2.1: Update `executeChatTurn` in `src/web/static/modules/studios/chat.js` to send `goal_mode` and `self_verify` flags in the POST payload.
- [x] Task 2.2: Add DOM template structure and event handlers for `plan_formulated`, `step_start`, `step_complete`, `reflexion_attempt`, and `reflexion_critique` in `chat.js`.
- [x] Task 2.3: Add Vitest frontend tests for plan milestone rendering in `tests/unit/frontend/chat_modes.test.js`.

### Slice 3: Verification & Definition of Done Gate
- [x] Task 3.1: Run full pre-flight verification (`python .agents/skills/rtm-sync/scripts/preflight.py`).
- [x] Task 3.2: Update RTM in `docs/rtm.json` and sync with `verify_rtm.py`.
- [ ] Task 3.3: Provide human verification runbook with real live test scenario.
