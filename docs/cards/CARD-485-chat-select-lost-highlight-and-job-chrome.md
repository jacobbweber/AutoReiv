---
id: CARD-485
title: "Picking a chat doesn't move the list highlight or restore its job strip and running-turn status (lost in the CARD-397 split)"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-397
  - CARD-476
  - CARD-473
  - CARD-466
  - CARD-471
  - CARD-486
  - CARD-487
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P3
---

# [CARD-485] Picking a chat doesn't move the list highlight or restore its job strip and running-turn status (lost in the CARD-397 split)

> **Status**: Ready (refined 2026-09-25 ET, planning only)
> **Created**: 2026-09-25
> **Observed during**: the CARD-476 build (scratch server, Playwright).
> **Related**: CARD-397 (split), CARD-476 (session guard/restore), CARD-473 (phone catch-up), CARD-466 (New chat into + Options), CARD-471 (Options drawer wiring), CARD-486 (Stop doesn't stop the server), CARD-487 (watch a running reply live)
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first on a `feature/CARD-485-*` branch off qa |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

When I pick a chat from the Recent Chats list:
- the list should show it as the open one;
- the drawer should get out of the way (it covers most of a phone screen);
- if that chat has a job, its job strip should come back;
- if a reply is still being worked on (started earlier, on another tab or on the phone), I should see it's busy, and the finished reply should appear when it's done.

This worked before the split.

### Beat 2: What AutoReiv does now (evidence at qa `2cc71d1a`)

**Before the split (`7b563003^`, `scratch/pre397_chat.js`):** `selectSession` (L1628-1650):
1. stopped any old status poll (L1629-1632);
2. `renderSessionList()`, which moved the highlight (L1636);
3. loaded messages and pending approvals (L1637-1638);
4. `hydrateJobChromeFromSession(sessionId)` (L1640 → L1569-1626). It fetched `/api/chat/sessions/{id}/journey`, rebuilt the job strip from `hydrateJobPhaseStateFromJourney`, and rebuilt the inline phase chips;
5. `checkSessionBackgroundStatus(sessionId)` (L1641 → L1667-1725). It fetched `/api/sessions/{id}/status`. When `is_running`, it showed Stop, hid Send and polled every 2 s. When the reply was done, it reloaded messages and approvals and restored Send;
6. refreshed the context badge if Options was open (L1643-1645);
7. collapsed the sessions drawer (CARD-296, L1647);
8. jumped to the latest message (L1648-1649).

**Now:**
- `src/web/static/modules/studios/chat.js` `selectSession` (L626-635) only sets the id, saves it, resets the job strip and inline chrome, loads messages and approvals, and refreshes the workbench count. None of steps 1, 2, 4, 5, 6, 7 or 8.
- `hydrateJobPhaseStateFromJourney` still exists (`chat.js` L208-240), but nothing calls it. The CARD-295 contract (`tests/unit/frontend/chat_hitl_journey_295.test.js` L104) only checks that the name appears in the file, so it stays green.
- `checkSessionBackgroundStatus` survives only as a controller method that returns `querySessionStatus()` (`chat.js` L1031-1033; `chat/stream.js` L76-86). It changes no UI, starts no poll, and nothing calls it.
- The list items bind clicks at `chat/chrome.js` L108. CARD-476 re-renders the list only after load and create (`chrome.js` `loadSessions`/`createNewSession`), not after a click.
- `setupChatScroll` returns `jumpMessagesToLatest` and `collapseChatSessionsDrawer` exists (`chat/scroll.js` L59-67, L95-101), but `selectSession` uses neither.

**Scratch repro (2026-09-25 ET, `scripts/smoke_server.py --port 8767`, `scratch/c485_repro.cjs`, no AppData):** three chats were seeded ("newest", "middle", "target"). Journey was intercepted to return a job waiting for approval, and status was intercepted to report `is_running: true` for "target". Then the sessions drawer was opened and "target" clicked.

| Check after clicking "target" | Desktop 1280x800 | Phone 390x844 | Pre-split |
|---|---|---|---|
| Messages loaded for target / saved as last chat | yes / yes | yes / yes | yes / (no key) |
| List highlight | stays on "newest" `[true,false,false]` | same | moves |
| Sessions drawer | stays open | stays open (covers ~85% of the screen) | collapses |
| `/journey` requests on select | 0 | 0 | 1 |
| Job strip / inline phase chips | hidden / 0 | hidden / 0 | shown |
| `/status` requests on select | 0 | 0 | 1, then a 2 s poll |
| Stop shown, Send hidden while running | no | no | yes |
| `/journey` or `/status` requests on page load | 0 / 0 | 0 / 0 | 1 / 1 (load selects a chat) |

**Found alongside (filed separately):**
- **CARD-486:** Stop no longer tells the server to stop. Pre-split the Stop handler POSTed `/api/chat/stream/{id}/abort` (L3538-3546), which checkpoints the job per CARD-259. Current `onCancelStream` (`chat.js` L942+) only aborts the browser fetch. Repro `scratch/c485_stop.cjs`: 0 abort requests after clicking Stop.
- **CARD-487:** watching a running reply's words live after switching chats or devices never existed (pre-split only polled). New scope.

### Beat 3: What will change

A new module `chat/session_select.js`, because `chat.js` is at 1,036 of 1,045 lines. `chat.js` gets only wiring, about 6 lines.
1. **Highlight.** After selecting, re-render the list with the new active id (reuse `renderSessionList` from `chrome.js`).
2. **Drawer and scroll.** Collapse `#chatSessionsDrawer` after a click in the list (not on the automatic select at load), and jump to the latest message.
3. **Job strip.** `hydrateJobChromeFromSession(sessionId)` fetches `/journey` and sets the strip via `hydrateJobPhaseStateFromJourney`. It also rebuilds the inline phase chips from the chosen job's phases, and ignores the result if the user switched chats meanwhile. `chat.js` passes setters for `jobPhaseState` and `inlineJobChromeModel` (closure variables).
4. **Busy state for a running reply.** `watchSessionStatus(sessionId)`:
   - When `/status` says `is_running`: show Stop, hide Send, mark busy, and poll every 2 s while that chat stays open.
   - When it's done: reload messages and approvals and restore Send.
   - Selecting another chat, or this tab starting its own stream, stops the poll.
   - Single in-flight check, as pre-split.

   CARD-473 (phone return) reuses this helper instead of writing its own.
5. **Context badge.** If the Options drawer is open, refresh the context badge for the new chat. CARD-471 owns the rest of the drawer.
6. Page load goes through the same `selectSession`, so a restored chat (CARD-476) also gets its job strip and busy state.

### Beat 4: What dies

- The stale highlight, and a sessions drawer you have to close yourself after picking a chat.
- The job strip that only appears for the job you are streaming right now.
- A chat that looks idle, with Send enabled, while its reply is still being made elsewhere.
- The hollow CARD-295 contract: it becomes a behaviour test.
- The dead `checkSessionBackgroundStatus` stub: it now does what its name says, and CARD-473 uses it.

## 2. Decisions (recommendations in bold)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | Collapse the sessions drawer after a pick? | (a) **collapse on a click in the list, on desktop and phone** (pre-split CARD-296); (b) phone only; (c) never | **(a)**: pre-split parity. The drawer is an overlay on both layouts, and it stays open on automatic selects (load, New chat from + Options per CARD-466). |
| D2 | What does "shows a still-running reply" mean? | (a) **busy state + 2 s poll, then show the finished reply** (pre-split); (b) stream the words live | **(a) here, (b) as CARD-487**: (b) needs backend event buffering and replay. |
| D3 | Poll interval and limits | **2 s while the chat is open and the page visible; stop on switch or finish** | Pre-split value. Pausing while hidden avoids phone battery drain; CARD-473 re-checks on return. |
| D4 | Refresh the context badge on select when Options is open? | **yes, one call** vs. leave it to CARD-471 | **Yes**: it's one call on the select path. CARD-471 keeps the drawer close/Compact/tools work. |
| D5 | Where does the code live? | **new `chat/session_select.js`** vs. inline in `chat.js` | **New module**: `chat.js` has 9 lines of headroom. |

## 3. Acceptance criteria (EARS)

- **[REQ-485-001]** WHEN the user selects a chat, THE SYSTEM SHALL mark that chat, and only that chat, as active in the Recent Chats list.
- **[REQ-485-002]** WHEN the user selects a chat by clicking it in the sessions drawer, THE SYSTEM SHALL close the drawer and show the latest message.
- **[REQ-485-003]** WHEN a chat is selected (click, restore on load, or New chat) AND its journey has a job, THE SYSTEM SHALL show the job strip and inline phase chips for that job (waiting-for-approval first, then running, then the rest).
- **[REQ-485-004]** WHEN a chat is selected AND its journey has no job, THE SYSTEM SHALL keep the job strip hidden.
- **[REQ-485-005]** WHEN a chat is selected AND the server reports it is running, THE SYSTEM SHALL show Stop, hide Send, and check again every 2 seconds while that chat stays open.
- **[REQ-485-006]** WHEN a polled chat stops running, THE SYSTEM SHALL reload its messages and pending approvals and restore Send.
- **[REQ-485-007]** WHEN the user selects a different chat WHILE a status poll or journey fetch is in flight, THE SYSTEM SHALL stop the old poll and ignore late results for the old chat.
- **[REQ-485-008]** WHEN a chat is selected WHILE the Options drawer is open, THE SYSTEM SHALL refresh the context badge for that chat.
- **[REQ-485-009]** THE SYSTEM SHALL behave the same on desktop and phone layouts.

## 4. Test plan (failing tests first)

Write these, run them and confirm red on qa `2cc71d1a` before any fix.

**Vitest `tests/unit/frontend/chat_session_select_485.test.js`** (node env, fetch mocked, fake timers)
1. `hydrateJobChromeFromSession` with a journey job waiting for approval calls the strip setter with `jobId`/`PARKED` and the inline setter with its phases (REQ-003).
2. A journey with no jobs leaves the strip hidden, and a journey error soft-fails (REQ-004).
3. A late journey result for a chat that is no longer active is ignored (REQ-007).
4. `watchSessionStatus` with `is_running: true` calls `setBusy(true)` and polls every 2 s (fake timers) (REQ-005).
5. The next poll with `is_running: false` calls `setBusy(false)`, reloads messages and approvals, and stops the timer (REQ-006).
6. Switching chats stops the poll, and there are never two checks in flight (REQ-007).
7. The select helper re-renders the list with the new active id: the rendered item for the chosen chat has the active classes (REQ-001).
8. Click selection collapses the drawer; the automatic select at load does not (REQ-002, D1).
9. The CARD-295 contract, strengthened: `selectSession` calls the journey hydrate (a behaviour check replacing the name-only regex at `chat_hitl_journey_295.test.js` L104).

**Smoke (`tests/e2e/smoke.spec.js`, scratch server, intercept `/journey` and `/status`), each for desktop and phone:**
- TC-24: seed 3 chats, open the drawer, click the oldest. It is highlighted, the drawer closes and its messages show.
- TC-25: journey for the clicked chat returns a job waiting for approval. The job strip is visible with the job id.
- TC-26: status returns `is_running: true` and then `false`. Stop shows, then Send returns and the messages reload.
- TC-27: status says running for chat A; switch to chat B. B shows Send and A's poll stops (no more `/status` for A).

**Regression:** full Vitest (known CARD-456 5), smoke 35/35 (TC-7 flake CARD-481 allowed), `tests/unit` (CARD-454), `tests/integration`, `chat.js` ≤1,045 lines.

## 5. Runbook (Jacob, after build; desktop http://127.0.0.1:8000, phone http://192.168.1.99:8000)

1. Desktop: open the sessions drawer (top-left button) and click an older chat. It becomes the highlighted one, the drawer closes and its messages show at the bottom.
2. Phone: same. The drawer closes by itself after the tap.
3. Open a chat where you ran a multi-step job before. The job strip under the header shows that job (id, phase, status) without sending anything.
4. Start a longer reply on the phone, then open the same chat on the desktop. The desktop shows Stop instead of Send, and the reply appears when the phone's reply finishes. Stop's server side is CARD-486.
5. Switch to another chat while one is busy. The other chat shows Send normally.

## 6. Overlap

- **CARD-473** (phone return): shares the status helper. Build CARD-485 first; CARD-473 then calls `watchSessionStatus` and reloads on `visibilitychange`/`focus`. No conflict.
- **CARD-466** (New chat into + Options): no conflict. New chat goes through `createNewSession` → `selectSession`, which gets the highlight via CARD-476's re-render. D1 keeps the drawer untouched on automatic selects, so moving the button doesn't matter.
- **CARD-471** (Options drawer wiring): only REQ-485-008 touches the drawer (one context refresh call). The close paths, Compact and tools modal stay in CARD-471.
- **CARD-476** (done): its list re-render after load and create stays. This card adds the re-render on click.
