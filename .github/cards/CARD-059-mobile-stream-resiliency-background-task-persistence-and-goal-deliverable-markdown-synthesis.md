# [CARD-059] Mobile Stream Resiliency Background Task Persistence and Goal Deliverable Markdown Synthesis

> **Status**: In Progress
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/CARD-059-mobile-stream-resiliency-and-synthesis.md`
> **Labels**: `type:feature`, `area:web`, `area:kernel`, `area:planning`

---

## 1. Why / Intent
On mobile devices (e.g. Android/iOS Chrome over LAN), when a user's screen locks, screensaver activates, or they switch to another app during a long-running multi-step Goal Mode or Reflexion execution:
1. The mobile browser terminates/suspends the active EventSource/fetch TCP stream.
2. Previously, client disconnection cancelled the FastAPI generator coroutine before synthesis completed, preventing the assistant reply from being saved to SQLite.
3. Upon returning to the browser, the frontend reloaded an incomplete session where the assistant bubble disappeared entirely.
4. Additionally, when the final goal synthesis prompt ran on local LLMs (like `qwen3.8:latest`), the model occasionally produced raw JSON output (`{ "goal": ..., "action_plan": ... }`) rather than formatted human-readable Markdown.

This card decouples long-running LLM execution from client stream lifetime via background task shielding, implements mobile tab reconnection sync in Chat Studio, enforces strict Markdown deliverable formatting in the planning synthesis prompt, and adds fallback JSON-to-Markdown rendering for structured agent outputs.

---

## 2. What to Build
- **Backend Stream Generator Shielding (`src/web/routers/chat.py`)**:
  - Run Goal Mode / Reflexion / long execution in an asynchronous task protected from client disconnection (`asyncio.shield` / background worker) so execution always completes and saves to SQLite even if the client disconnects mid-stream.
  - Enhance `synth_prompt` with strict executive Markdown formatting directives and negative constraints against raw JSON dicts.
  - Implement JSON-to-Markdown formatter fallback for structured deliverables.
- **Frontend Tab Focus & Visibility Reconnection Sync (`src/web/static/modules/studios/chat.js`)**:
  - Add `document.addEventListener('visibilitychange')` and window `focus` handler to detect when the user returns to the app.
  - If a background turn was in flight or stream was interrupted, re-fetch `/api/chat/sessions/{id}/messages` and restore the completed chat state without blanking the thread.
- **Automated Test Coverage**:
  - Unit tests for background execution shielding, JSON fallback formatting, and mobile visibility sync.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-MOB-STREAM-001]`: Client disconnection / stream abort does not cancel backend turn execution or SQLite persistence.
- [ ] `[REQ-MOB-STREAM-002]`: Chat Studio automatically synchronizes and restores messages on mobile visibility change / window focus.
- [ ] `[REQ-MOB-STREAM-003]`: Goal Mode deliverable synthesis prompt strictly produces structured Markdown with headings, bullet points, checklists, and summary tables.
- [ ] `[REQ-MOB-STREAM-004]`: JSON deliverables are gracefully formatted into clean Markdown sections.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .` and `npm run lint:frontend`.
- [ ] Vitest and Playwright smoke tests pass cleanly.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
