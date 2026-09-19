# [CARD-361] Dual-Engine Front Door (AutoReiv Core & Direct Mode)

> **Status**: In Review
> **Created**: 2026-09-19
> **Spec Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) & [docs/specs/dual-engine-front-door/](file:///d:/Projects/Active/AutoReiv/docs/specs/dual-engine-front-door/)
> **Labels**: `type:feature`, `domain:chat`, `domain:orchestration`, `architecture:autonomic-os`

---

## 1. Why / Intent

As mandated by **ADR-0054** (*Autonomic Operating System, Demand-Paged Capabilities & Mechanical Governance*), AutoReiv is eliminating the anti-pattern of persona dropdowns and conversational roundtables (retiring CARD-340). Foundation model intelligence resides in parametric weights; personas do not expand cognitive capacity. Chat Studio's front door is streamlined into two explicit, intentional operational engines:

1. **AutoReiv Core**: The primary state-machine orchestrator (`JobPhaseOrchestrator`), executing structured, phased workflows with demand-paged tools, grounded context, and mechanical verification.
2. **Direct Mode**: A raw, unconstrained conversational LLM stream with zero tool schemas, zero orchestrator overhead, and instant sub-second Time to First Token.

---

## 2. What to Build

1. **Dual-Engine Front Door UI (`index.html`, `chat.js`)**:
   - Retire the multi-persona dropdown from Chat Studio.
   - Introduce a clear, high-contrast segmented engine toggle in the Chat Studio header:
     - **⚡ AutoReiv Core** (`autoreiv`): Phased state machine, demand-paged capabilities, mechanical verification.
     - **💬 Direct Mode** (`direct`): Zero tool schemas, instant conversational LLM stream.
   - Synchronize with the underlying `#agentSelect` element to preserve compatibility with existing automated test harnesses.
   - Filter `agentsVisibleInChat` strictly to the two front-door engines (`autoreiv` and `direct`).
   - Suppress the Job/Phase status strip and inline job chrome when Direct Mode is active.

2. **Direct Mode Fast Path in Chat Router (`src/web/routers/chat.py`)**:
   - In `POST /api/chat/stream`: When `agent_id == 'direct'`, bypass `JobPhaseOrchestrator.create_job_from_catalog_resolve`.
   - Prevent minting of redundant `Job` and `Phase` database records for direct conversational questions.
   - Stream directly via `AgentKernel.stream_turn` with `tools=None` (zero tool schemas sent to the provider).
   - Save user and assistant messages directly to the session store.
   - Emit SSE `token` events and a clean `turn_done` event without phase lifecycle noise.

3. **Session Scoping & Engine Switching**:
   - Filter and load sessions for the active engine (`agent_id=autoreiv` vs `agent_id=direct`).
   - Create new sessions labeled appropriately (`AutoReiv Chat` vs `Direct Chat`).

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **[REQ-CHAT-DUAL-001]**: Chat Studio displays a dual-engine front door in the top bar with **AutoReiv Core** and **Direct Mode**, retiring persona dropdown lists.
- [x] **[REQ-CHAT-DUAL-002]**: Direct Mode (`agent_id='direct'`) in `POST /api/chat/stream` bypasses job minting and catalog resolution, streaming tokens directly with zero tool schemas.
- [x] **[REQ-CHAT-DUAL-003]**: AutoReiv Core (`agent_id='autoreiv'`) executes through `JobPhaseOrchestrator` with full phase lifecycle and verification.
- [x] **[REQ-CHAT-DUAL-004]**: Switching engines cleanly switches active sessions without cross-channel message pollution.
- [x] **[REQ-CHAT-DUAL-005]**: While Direct Mode is active, Job/Phase status strip and chrome are suppressed.
- [x] Automated unit and frontend tests pass via `pytest` and `npm run test:unit:frontend`.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Invariants

- Grounded in **ADR-0054**.
- Single isolated `feat/card-361-dual-engine-front-door` branch cut from `qa`.
- Preserve backward compatibility for tests asserting on `#agentSelect`.
- Follow three beats before code; wait for Jacob's **build**.
