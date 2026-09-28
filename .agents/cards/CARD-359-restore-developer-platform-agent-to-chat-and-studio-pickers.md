# [CARD-359] Restore Developer Platform Agent to Chat and Studio Pickers

> **Status**: Done  
> **Created**: 2026-09-18  
> **Spec Reference**: `docs/specs/agent-packs.md`, `docs/cards/CARD-341-full-platform-agent-decoupling-and-disk-cleanup.md`  
> **Labels**: `type:bug`, `type:enhancement`, `AutoReiv.Web`, `AutoReiv.Chat`, `AutoReiv.Forge`, `domain:agents`  

---

## 1. Three Beats

### Beat 1: What Jacob means
Jacob noticed that the `Developer` platform agent is missing from Chat Studio's agent dropdown and other studio selectors. He wants `Developer` restored so it is visible and selectable across Chat Studio and other agent picker interfaces, allowing operators to chat directly with Developer for SDLC, code review, and engineering tasks.

### Beat 2: What AutoReiv does now
The Developer agent is completely intact in the backend:
- Its manifest exists at `platform-packs/developer/pack.json` with `show_in_chat: true`, system prompt, skills (`plan`, `build`, `test`), and tools.
- Its live storage is seeded in `%LOCALAPPDATA%\AutoReiv\packs\developer\`.
- In `src/application/agent_packs/schema.py`, it is registered in `PLATFORM_PACK_IDS` and `CHAT_SHOWN_BY_ID`.
- In `src/infrastructure/skills/platform_packs.py`, it is registered in `PLATFORM_PACK_IDS`.
- The backend API endpoint `GET /api/agents` serves `developer` with `is_platform_pack: true` and `show_in_chat: true`.

However, during the CARD-339/341 platform cleanup (when legacy agents `assistant` and `wiki` were retired), `'developer'` was accidentally added to hardcoded client-side exclusion filters:
1. `isAgentVisibleInChat` in `src/web/static/modules/studios/chat.js` (line 62).
2. `isAgentVisibleInChat` in `src/web/static/modules/studios/chat/stream.js` (line 134).
3. `isStudioAgentVisible` in `src/web/static/modules/studios/forge.js` (line 313).

Because of these three hardcoded exclusions, the frontend discards `developer` when populating:
- Chat Studio active agent selector (`#agentSelect`).
- Agent Forge agent selector (`#forgeAgentSelect`).

### Beat 3: What will change
1. **Chat Studio Visibility**:
   - In `src/web/static/modules/studios/chat.js` and `src/web/static/modules/studios/chat/stream.js`, remove `agent.id === 'developer'` from `isAgentVisibleInChat`.
   - Developer will now be visible in `#agentSelect` and `#trainAgentTargetSelect`.
2. **Agent Forge Visibility**:
   - In `src/web/static/modules/studios/forge.js`, remove `'developer'` from the retired agent exclusion list in `isStudioAgentVisible`.
   - Developer will now be visible in `#forgeAgentSelect`.
3. **Frontend Test Alignment**:
   - Update `tests/unit/frontend/agent_packs.test.js` to assert `isAgentVisibleInChat(developer) === true` and include `developer` in expected visible agents.
   - Update `tests/unit/frontend/forge_agent_select.test.js` to assert `isStudioAgentVisible({ id: 'developer' }) === true`.
4. **Cache Buster**:
   - Bump frontend script version to `app.js?v=2.0.73` in `src/web/templates/index.html`.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] `Developer` is visible in Chat Studio's agent dropdown (`#agentSelect`).
- [x] Selecting `Developer` in Chat Studio updates the active header and allows starting a new session with Developer.
- [x] `Developer` is visible in Agent Forge's agent selector (`#forgeAgentSelect`).
- [x] Existing retired agents (`assistant`, `wiki`, `conductor`, `coding`, `review`, `agent-builder`) remain hidden.
- [x] Vitest unit tests in `tests/unit/frontend/agent_packs.test.js` and `tests/unit/frontend/forge_agent_select.test.js` pass.
- [x] All preflight gates pass (`python .agents/skills/rtm-sync/scripts/preflight.py`).
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 3. Constraints & Honor Flags
- No backend schema or API changes required (backend already correctly considers `developer` visible and seeded).
- No code without Jacob's explicit `build` instruction.
