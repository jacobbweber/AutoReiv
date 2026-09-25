---
id: CARD-488
title: "Switching chats while your own reply is streaming keeps showing the old chat and blocks sending"
status: In Progress
created: 2026-09-25
branch: qa
related:
  - CARD-485
  - CARD-486
  - CARD-487
  - CARD-154
  - CARD-493
  - CARD-494
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P2
---

# [CARD-488] Switching chats while your own reply is streaming keeps showing the old chat and blocks sending

> **Status**: In Progress (build 2026-09-25 ET on `feat/card-488-switch-during-own-reply`; D1-D7 accepted as recommended)
> **Created**: 2026-09-25
> **Observed during**: the CARD-485 build (scratch server, Playwright `scratch/c485_ownstream.cjs`). Re-reproduced on qa `2bd55bd0` with a real slow reply (`scratch/c488_ui.cjs`).
> **Related**: CARD-485 (select path, busy state), CARD-486 (Stop), CARD-487 (live replay), CARD-154 (server work survives disconnect), follow-ups CARD-493 / CARD-494
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first on `feat/card-488-switch-during-own-reply` |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means
If I start a long reply in chat A and then open chat B (or press New chat, or pick another agent), B should show B's messages and let me type and send right away. A keeps working in the background. When I go back to A, it shows that it's still working, with a Stop that stops **A**, and then the finished answer. Stop should never hit the wrong chat.

### Beat 2: What AutoReiv does now (qa `2bd55bd0`)

**Repro.** Setup: scratch server `scripts/smoke_server.py --port 8767` with the slow fake model `scratch/c486_fake_gateway.py` (1 word per 0.5 s). B already had the message "hello from B". Steps: send "tell me a long story" in A, wait for 3 words, then pick B from the drawer. No real AppData was used.

| Check after picking B | Result |
|---|---|
| B highlighted in Recent Chats | yes (CARD-485) |
| View shows B's messages | **no**: still A's prompt and A's "Streaming..." bubble (1 stream bubble) |
| Send / Stop | **Send hidden, Stop shown** |
| Type "message typed in B" and press Enter | **nothing sent**; the text stays in the box |
| Press Stop while B is open | **the abort goes to B** (CARD-486 uses the open chat). The model kept writing A: `req3 chunk 12` 3 s later, never cancelled |
| A finishes while B is open | the view then flips to B's messages and Send returns; A's full reply is saved |
| Go back to A | A shows its full reply |

**Root cause.** One flag, `state.isStreaming`, means "this tab is streaming", and every view path treats it as "the open chat is streaming":
- `selectSession` (`chat.js` L602-609) sets `state.activeSessionId = B` and calls `afterSelect` (`chat/session_select.js` L254-259). Nothing detaches the running turn.
- `loadMessages(B)` (`chat.js` L611-635) passes `isStreaming: state.isStreaming` (L622). `renderMessages` (`chat/render.js` L723) returns early while streaming, so A's DOM (prompt + stream bubble) stays.
- The composer ignores submits while `state.isStreaming` (`chat/composer.js` L365; Enter goes through the same form submit, L306/L347). That is why Enter "does nothing" in B.
- `executeChatTurn` (`chat.js` L693-905) captures A's id only once, for the payload (L783). It keeps writing tokens into A's bubble (L803-807) and job events into the shared job strip (`updateJobChromeFromEvent`, L818). When A finishes, it pushes A's reply into `state.messages` (B's array now, L863) and then reloads `state.activeSessionId` (L869-870), which is why the view only recovers at the end. Its `finally` (L899-905) resets Send, Stop and `activeAbortController` unconditionally.
- Stop (`chat/stop.js` L60) aborts `state.activeSessionId` (B), while `activeAbortController` still belongs to A's fetch. Cancelling that fetch doesn't stop the server (CARD-154), so A keeps running.
- **Agent switch** has the same problem: `switchSelectedAgent` (`chat.js` L502-517) calls `loadSessions`, which returns early on `state.isStreaming` (`chat/chrome.js` L141). The previous agent's chat stays open under the new agent's header, and the next send uses the new agent with A's session id. New chat goes through `selectSession`, so it hits the same problem as a pick.
- The watcher (`session_select.js` L176) skips busy while `state.isStreaming`. When A is reopened with its turn still attached, it counts as "own stream". That's harmless today and correct after the fix.

Pre-split had the same early return (pre-split `loadMessages` L1659), so this is **not** a CARD-397 regression. CARD-485 made it visible by making picks actually switch.

### Beat 3: What will change
1. **Detach on switch.** A new small module, `chat/own_stream.js`, exports `createOwnStreamTracker()`. It holds the running turn: `{sessionId, controller, token}`.
   - `executeChatTurn` calls `begin(sessionId, controller)` and gets a turn token.
   - Every UI write in that turn checks `isCurrent(token)` first: tokens, events, the job strip, the push into `state.messages`, the final reload, and `finally`.
2. **`selectSession(B)` with B ≠ the streaming chat** (list pick, New chat, restore, agent switch) calls `detach()` before rendering. `detach()` does this:
   - cancels only the browser request (the server keeps going, CARD-154);
   - clears `state.isStreaming`;
   - removes the stream bubble;
   - restores Send and hides Stop.

   Then B renders normally and can send. Re-selecting the chat that is streaming (the same id) does not detach.
3. **Back to A:** the CARD-485 watcher sees `/status` running and shows busy with Stop. Stop takes the CARD-486 busy-elsewhere path and aborts **A**. When A finishes, the watcher reloads the full reply. Live words while returning are CARD-487.
4. **Stop target:** `createStopHandler` gets a `getStreamSessionId` dep. While a turn is attached, Stop aborts that turn's chat. Otherwise it aborts the open chat. After a detach there's no attached turn, so Stop in B is hidden unless B itself is busy.
5. **Agent switch:** `switchSelectedAgent` detaches the same way. `loadSessions` drops the `|| state.isStreaming` early return (`chrome.js` L141), so the new agent opens its own last chat.
6. `chat.js` stays ≤ 1,045 lines (1,009 now). Most of the logic lives in `own_stream.js`.

### Beat 4: What dies
- Chat A's reply spilling into chat B.
- A composer that silently ignores Enter.
- Stop hitting the wrong chat.
- An agent switch that leaves the old agent's chat open under the new agent's header.
- The single `isStreaming` flag standing for both "this tab is streaming" and "the chat on screen is streaming".

---

## 2. Decisions (recommendations in bold)

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | What happens to A's reply when switching away? | (a) keep it running on the server and detach only the browser; (b) abort it on the server | **(a)**: matches CARD-154 and REQ-488-003. Switching is not Stop, and the repro shows A still gets saved |
| D2 | Switching back to A while it's still running | (a) busy + Stop + finished reply (CARD-485 watcher); (b) keep the browser stream alive in the background and re-attach the live bubble | **(a) now**; live replay belongs to **CARD-487** (a server `/follow` stream covers switch-back, reload and phone in one design). (b) would add a hidden background renderer that CARD-487 replaces anyway |
| D3 | Stop target | (a) the attached turn's chat if any, else the open chat; (b) always the open chat (today) | **(a)**: Stop can never hit a different chat than the reply on screen |
| D4 | Busy state per chat | (a) only the open chat, from `/status` (CARD-485 watcher); (b) remember every chat's busy state in the browser | **(a)**: the server is the source of truth, and it already works across devices. Busy badges in Recent Chats are filed as **CARD-493** |
| D5 | New chat and agent switch during a reply | (a) same detach path as a pick; (b) leave as is | **(a)**: same bug, same fix, a few lines. Agent switch today leaves A open under the new agent |
| D6 | Tell Jacob that A is still running when he leaves it? | (a) no toast; (b) info toast "Chat A is still replying" | **(a)**: going back shows busy anyway, and CARD-493's list badge is the better signal |
| D7 | Sending in B while A still runs on the server | (a) allow; (b) block until A finishes | **(a) allow**. With the default of 1 generation slot, B's reply waits behind A (seen in the CARD-486 repro) and shows only "Streaming..." meanwhile. A "waiting for another reply" hint is filed as **CARD-494** |

---

## 3. Acceptance criteria (EARS)

- **[REQ-488-001]** WHEN the user selects a different chat (list pick, New chat, restore or agent switch) WHILE this tab is streaming a reply, THE SYSTEM SHALL cancel only this tab's stream request, clear the streaming state, and render the selected chat's own messages with Send visible and Stop hidden.
- **[REQ-488-002]** WHEN the user presses Send or Enter in the newly selected chat, THE SYSTEM SHALL send the message to that chat's session id.
- **[REQ-488-003]** THE SYSTEM SHALL NOT abort the server-side reply when the user only switches chats (no `/abort` request).
- **[REQ-488-004]** WHILE a turn has been detached, THE SYSTEM SHALL NOT write its tokens, events, job strip, messages, reload or button state into the view.
- **[REQ-488-005]** WHEN the user returns to the chat whose reply is still running, THE SYSTEM SHALL show the busy state with Stop (CARD-485), and then the finished reply.
- **[REQ-488-006]** WHEN the user presses Stop, THE SYSTEM SHALL abort the chat whose reply is attached to this tab if there is one, otherwise the open chat, and never any other chat.
- **[REQ-488-007]** WHEN the user switches agent WHILE this tab is streaming, THE SYSTEM SHALL open the new agent's chat (last used or newest) rather than keep the previous agent's chat.
- **[REQ-488-008]** WHEN the selected chat is the one already streaming, THE SYSTEM SHALL keep the stream attached.

---

## 4. Failing-tests-first plan (commit 2, confirmed red)

**Vitest:** `tests/unit/frontend/chat_switch_during_reply_488.test.js` (new)
1. `createOwnStreamTracker`:
   - `begin` returns a token and `isCurrent(token)` is true;
   - `detach()` aborts the controller once, clears `state.isStreaming`, and returns the detached session id;
   - after that `isCurrent(token)` is false (REQ-001/004).
2. `createSessionSelect().afterSelect('B')` while the tracker holds 'A':
   - calls `detachOwnStream` **before** `loadMessages('B')`;
   - `state.isStreaming` is false when `loadMessages` runs (REQ-001).
3. `afterSelect('A')` while the tracker holds 'A': no detach (REQ-008).
4. A stale turn: after `detach()`, the turn's finish step does not push to `state.messages`, reload, or touch Send/Stop (tested through the tracker guard helper `runIfCurrent`) (REQ-004).
5. Stop target: `createStopHandler` with `getStreamSessionId: () => 'A'` and `activeSessionId 'B'` POSTs `/api/chat/stream/A/abort`. With no attached turn it uses the open chat (REQ-006).
6. The watcher on return: A is running and nothing is attached (`isStreaming` false), so busy turns on (REQ-005; guards the existing behaviour after detach).
7. `loadSessions` (chrome.js) with `state.isStreaming` true and the active chat not in the new agent's list calls `selectSessionFn` (REQ-007).
8. Wiring guard: `chat.js` imports `createOwnStreamTracker` and passes `detachOwnStream` to `createSessionSelect`. The `|| state.isStreaming` early return is gone from `chrome.js`. `chat.js` ≤ 1,045 lines.

**Playwright smoke** (`tests/e2e/smoke.spec.js`, desktop 1280×800 and phone 390×844)
- **TC-30: switching chats during your own reply shows the other chat and sends there.**
  1. Seed chats A and B. Route B's `/messages` to include "hello from B".
  2. Route `/api/chat/stream` so A hangs and B answers fast.
  3. Send in A, then pick B. Expect: B's text shows, no `[data-stream-bubble]`, Send visible, Stop hidden, and 0 `/abort` requests.
  4. Press Enter with text in B. Expect exactly 1 stream POST with `session_id` = B, and the box clears.
- **TC-31: back to the running chat, Stop stops that chat.**
  1. After TC-30's steps, route `/status` so A is running until `/abort` is hit.
  2. Pick A. Expect busy (Stop visible).
  3. Press Stop. Expect 1 `/abort` whose URL contains A's id and not B's; Send comes back.
- **TC-32: switching agent during your own reply opens that agent's chat.**
  1. Send in A with the stream hanging.
  2. Switch the engine to another agent. Expect its chat to open (highlighted, its messages), Send visible, and 0 `/abort` requests.

**pytest:** none; the backend is untouched. CARD-486's `/status` and `/abort` contracts already cover the server side.

**Gates:**
- full Vitest (known CARD-456 failures only);
- `pytest tests/unit` (known CARD-454 failure only) and `pytest tests/integration`;
- full smoke;
- ESLint baseline;
- ruff baseline;
- line caps.

## 5. Build order
1. Card In Progress.
2. Failing tests.
3. Fix:
   - `chat/own_stream.js`
   - `executeChatTurn` token guards
   - `selectSession` / `switchSelectedAgent` detach
   - `session_select.js` `detachOwnStream` dep
   - `stop.js` `getStreamSessionId`
   - `chrome.js` L141
4. CHANGELOG `### Fixed`.
5. Scavenger Pass: remove the now-dead `isStreaming` early return in `loadSessions`.
6. Scratch repro rerun (`scratch/c488_ui.cjs`).
7. In Review.
8. Restart serve.

## 6. Runbook (Jacob, after `merge to qa`)
Desktop http://127.0.0.1:8000 and phone http://192.168.1.99:8000.
1. **Switch during a reply:**
   1. In chat A, ask "write a 1,500-word story".
   2. After a few lines, open the chat list and pick chat B.
   3. Expect: B's own messages, Send visible, and no story text in B.
2. **Send in B:** type "hi" in B and press Enter. It sends in B. If A is still writing, B may wait until A is done (CARD-494).
3. **Back to A:** pick A. Expect Stop visible while it's still writing, then the full story appears when it finishes.
4. **Stop hits the right chat:** repeat step 1, go back to A, and press Stop. A stops ("Stopped"), and B is untouched.
5. **New chat during a reply:** start a long reply, then press New chat. The empty new chat opens and you can type.
6. **Agent switch during a reply:** start a long reply, then pick another agent in the engine selector. That agent's chat opens and you can type there.
7. **Phone:** repeat steps 1-3 on the phone.

---

## Note (2026-09-25 ET, CARD-486 build)

CARD-486 Stop (`chat/stop.js`) cancels this tab's request and POSTs `/abort` for `state.activeSessionId`. If Jacob switches chats while his own reply streams (this card's bug) and then presses Stop, the browser request is cancelled but the server abort goes to the **newly opened** chat. The original reply keeps running on the server. When this card is built, track the streaming chat's id in `executeChatTurn` and have Stop abort that id (pass a `getStreamSessionId` dep to `createStopHandler`), with a Vitest case for it. **Confirmed on qa `2bd55bd0` (repro above) and covered by D3 / REQ-488-006.**
