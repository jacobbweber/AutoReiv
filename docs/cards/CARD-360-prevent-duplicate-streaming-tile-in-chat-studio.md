# [CARD-360] Prevent duplicate streaming tile in Chat Studio

> **Status**: Done  
> **Created**: 2026-09-18  
> **Spec Reference**: none  
> **Labels**: `type:bug`, `P1`, `AutoReiv.Chat`, `AntiTheatre`  
> **Branch**: `feat/prevent-duplicate-streaming-tile-360`  

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. When Jacob prompts an agent in Chat Studio, he observes two stacked dark tiles displaying `DEVELOPER` and `STREAMING...` pulsing simultaneously.
2. He wants to ensure AutoReiv is not running duplicate tasks or dual requests.
3. He wants this visual defect eliminated so only the single active turn streaming bubble appears, while ensuring multi-phase job tracking still functions when phases or steps actually exist.

### Beat 2: What AutoReiv Does Now
1. In `src/web/static/modules/studios/chat.js`, `executeChatTurn()` mounts the primary `streamBubble` to receive streaming tokens, tool pills, and reasoning traces.
2. At the start of turn reasoning, `AgentKernel` emits a `react_state` event (`THINKING`).
3. `updateJobChromeFromEvent` handles this event and immediately calls `paintInlineJobChrome()`, which calls `ensureInlineJobChromeBubble()` and appends a second bubble (`[data-job-chrome="inline"]`) into `messagesContainer`.
4. Because the turn has 0 phases and 0 plan steps, this second bubble renders only its header (`DEVELOPER` and `STREAMING...`) with empty/hidden phase and step containers, visually duplicating the stream tile.

### Beat 3: What Will Change
1. In `src/web/static/modules/studios/chat.js`, `paintInlineJobChrome()` will check whether `inlineJobChromeModel` has active phases (`phaseOrder.length > 0`) or plan steps (`steps.length > 0`) before mounting or rendering `[data-job-chrome="inline"]`, matching the guard already present in `remountInlineJobChrome()`.
2. Standard turns and initial `react_state` transitions will not spawn an empty duplicate bubble.
3. Multi-phase standing jobs and formulated plans will continue to mount the inline job chrome seamlessly as soon as phases or steps are registered.
4. Unit tests in `tests/unit/frontend/` will verify that `paintInlineJobChrome` does not mount an empty element on `react_state` events alone, and mounts correctly when phases or steps are populated.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-CHAT-CHROME-001]**: `paintInlineJobChrome()` SHALL NOT mount or render an inline job chrome bubble into `messagesContainer` when `phaseOrder` and `steps` are both empty.
- [x] **[REQ-CHAT-CHROME-002]**: `WHEN` a phase event (`phase_start`, `phase_complete`, `job_created` with phases) or plan event (`plan_formulated`, `step_start`) populates `phaseOrder` or `steps`, `paintInlineJobChrome()` SHALL mount and render the inline job chrome bubble.
- [x] **[REQ-CHAT-CHROME-003]**: `WHILE` an agent is reasoning during a single-turn chat prompt, Chat Studio SHALL display exactly one streaming bubble (`streamBubble`) without a duplicate empty chrome tile.
- [x] **[REQ-CHAT-CHROME-004]**: Automated frontend tests in `tests/unit/frontend/` pass cleanly without regressions to CARD-240 or CARD-295.
- [x] Zero lint errors via `ruff check .` and frontend vitest suite passing (552/552 tests green).

---

## 3. Constraints & Honor Flags
- Cut isolated branch `feat/prevent-duplicate-streaming-tile-360` from `qa`.
- Do not remove or alter `streamBubble` tool badges or markdown token streaming.
- Do not break Education Studio origin forwarder or standing job graph rendering.
- Follow strict Red-Green-Refactor TDD.

---

## 4. Verification Proof
- `tests/unit/frontend/chat_inline_chrome_guard_360.test.js`: 9/9 tests passing.
- `npm run test:unit:frontend`: 92 test files, 552 tests passing.
- Full unified preflight gate passed (Ruff, Pytest, Honesty smoke pack, ESLint, Vitest, Playwright smoke suite, RTM sync).
- Bumped frontend cache-buster in `src/web/templates/index.html` to `app.js?v=2.0.75`.

