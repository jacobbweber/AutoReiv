# Vertical Slice Tasks: Dual Engine Front Door (AutoReiv Core & Direct Mode)

> **Spec Reference**: [docs/specs/dual-engine-front-door/requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/dual-engine-front-door/requirements.md)  
> **Card Reference**: [CARD-361](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-361-dual-engine-front-door-autoreiv-core-and-direct-mode.md)

---

## Slice 1: Backend Fast-Path for Direct Mode (`[REQ-CHAT-DUAL-002]`, `[REQ-CHAT-DUAL-003]`)

- [ ] **Task 1.1** `[REQ-CHAT-DUAL-002]`: [RED] Write unit test in `tests/unit/web/test_chat_direct_mode.py` verifying that when `agent_id == 'direct'`, `chat_stream` bypasses `JobPhaseOrchestrator.create_job_from_catalog_resolve`, mints no job/phase DB records, invokes `AgentKernel` with zero tools, and yields token + turn_done events without phase lifecycle events.
- [ ] **Task 1.2** `[REQ-CHAT-DUAL-002]`: [GREEN] Implement Direct Mode fast-path in `src/web/routers/chat.py` inside `chat_stream()`, routing `agent_id == 'direct'` to direct kernel streaming without job creation.
- [ ] **Task 1.3** `[REQ-CHAT-DUAL-003]`: [GREEN] Verify AutoReiv Core (`agent_id == 'autoreiv'`) retains standing `JobPhaseOrchestrator` execution and phase events without regression.
- [ ] **Task 1.4**: [REFACTOR] Clean up helper functions and ensure proper exception handling and session message persistence for Direct Mode.

---

## Slice 2: Frontend Dual-Engine Front Door & Visibility (`[REQ-CHAT-DUAL-001]`, `[REQ-CHAT-DUAL-004]`, `[REQ-CHAT-DUAL-005]`)

- [ ] **Task 2.1** `[REQ-CHAT-DUAL-001]`: [RED] Write frontend unit test in `tests/unit/frontend/chat_dual_engine_front_door_361.test.js` asserting that `isAgentVisibleInChat` and `agentsVisibleInChat` filter exclusively to `autoreiv` and `direct`, and verifying dual-engine toggle elements.
- [ ] **Task 2.2** `[REQ-CHAT-DUAL-001]`: [GREEN] Update `isAgentVisibleInChat` in `src/web/static/modules/studios/chat.js` and `chat/stream.js` to restrict Chat Studio to `autoreiv` and `direct`.
- [ ] **Task 2.3** `[REQ-CHAT-DUAL-001]`: [GREEN] Add segmented dual-engine front door control in `src/web/templates/index.html` header, keeping `#agentSelect` synchronized for backward compatibility.
- [ ] **Task 2.4** `[REQ-CHAT-DUAL-004]`, `[REQ-CHAT-DUAL-005]`: [GREEN] Implement engine switching logic, active button state styling, and suppression of `#jobPhaseStatusStrip` in `src/web/static/modules/studios/chat.js` when Direct Mode is active.
- [ ] **Task 2.5**: [REFACTOR] Update existing test expectations in `tests/unit/frontend/agent_packs.test.js` to reflect the retired persona dropdowns and ADR-0054 dual-engine front door.

---

## Slice 3: Verification & Preflight Gates

- [ ] **Task 3.1**: Run `pytest` across all web and orchestration test suites.
- [ ] **Task 3.2**: Run `npm run test:unit:frontend`.
- [ ] **Task 3.3**: Run `ruff check .` and `npm run lint:frontend`.
- [ ] **Task 3.4**: Update `CHANGELOG.md` under `[Unreleased]` with CARD-361 entry.
