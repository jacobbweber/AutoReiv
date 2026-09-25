---
id: CARD-476
title: "First Chat message with no active session fails with HTTP 422 (session auto-create lost in the CARD-397 split)"
status: In Progress
created: 2026-09-24
branch: qa
related:
  - CARD-397
  - CARD-469
  - CARD-473
  - CARD-466
  - CARD-484
labels:
  - type:bug
  - area:chat
  - area:frontend
  - P2
---

# [CARD-476] First Chat message with no active session fails with HTTP 422 (session auto-create lost in the CARD-397 split)

> **Status**: In Progress (build started 2026-09-25 ET on `feat/card-476-session-auto-create-restore`; Jacob accepted D1-D5 as recommended)
> **Created**: 2026-09-24
> **Observed during**: CARD-469 reproduction on the scratch smoke server. With no active session (fresh data), pressing Enter produced `POST /api/chat/stream` **422 Unprocessable Entity**.
> **Related**: CARD-397 (split), CARD-469, CARD-473 (phone catch-up), CARD-466 (New chat into + Options), CARD-484 (typed text lost on failed send)
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first on a `feature/CARD-476-*` branch off qa |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

Chat should always have a conversation ready. If there is none (fresh install, all chats deleted, new agent), typing and pressing Enter should just work, and AutoReiv should make the session itself. When I reopen the app on a device, it should put me back in the conversation I was last in on that device, not quietly switch to a different one.

### Beat 2: What AutoReiv does now (evidence at qa `ecbc0e7a`)

**Before the split (`7b563003^`, `src/web/static/modules/chat.js`):**
- On load, `loadSessions` kept the active session if it was still listed, else picked the newest (`sessions[0]`). **If the list was empty it called `createNewSession()`** (~L1498-1518).
- On submit it also guarded: `if (!state.activeSessionId) await createNewSession();` (L3038-3040).
- It never saved or read a "last session" key. `autoreiv_active_session_id` did not exist yet (`git log -S` shows it arrives in `7b563003` (the split) and `9259da63` (CARD-422)).

**Now:**
1. **The empty-list create is unwired.** `chat/chrome.js` `loadSessions` still has the create branch (L143-145: `else if (createNewSessionFn) await createNewSessionFn()`), but the `chat.js` wrapper (L601-607) calls `loadSessionsDirect(state, { sessionList, onSelectSession: selectSession, showToastFn })` **without `createNewSessionFn`**, so it never fires. A fresh or emptied agent sits with `state.activeSessionId === null` (`state/store.js` L42).
2. **The send path has no guard.** `chat/composer.js` `setupComposerControls` (L349-385) clears the composer and calls `onExecuteTurn`. `chat.js` `executeChatTurn` (L712+) posts `session_id: state.activeSessionId` (L727/L804), which is `null`. `ChatStreamRequest.session_id: str` (`src/web/routers/chat.py` ~L1378) rejects it: **422 `string_type` on `body.session_id`**. `chat.js` L819 throws `Stream error: HTTP 422`, and L917 toasts "Chat turn failed: Stream error: HTTP 422". The message is lost (the composer was already cleared; see CARD-484).
3. **Race on load.** Even when sessions exist, a send before `loadAgents` → `loadSessions` (`chat.js` L988 → L501-516) finishes also posts `null`.
4. **The last session is not restored; the newest always wins.** `selectSession` (L622-631) and `openDeveloperSession` (L963-964) **write** `autoreiv_active_session_id`, but nothing reads it. On load `activeSessionId` is `null`, so `chrome.js` L140-142 selects `sessions[0]` and overwrites the stored id. The same code runs on desktop and phone (localStorage is per device/browser).
5. Attachments picked before a session exists upload under `attachments/global` (`composer.js` `wireComposer` L327-347, `getSessionId()` → null).

**Scratch repro (2026-09-25 ET, `scripts/smoke_server.py --port 8767`, Playwright `scratch/c476_repro.cjs`, no AppData touched):**

| Case | Desktop 1280x800 | Phone 390x844 |
|------|------------------|---------------|
| A. Fresh data, type "hi" + Enter | 0 sessions, none created; POST `session_id:null` → **422**; toast "Chat turn failed: Stream error: HTTP 422" | same |
| D. Two sessions, `localStorage.autoreiv_active_session_id` = the older one, reload | opens the **newer** one; stored id overwritten; send uses newer id | same |
| D2. Stored id points at a deleted session | opens newest (acceptable fallback) | same |
| E. Sessions exist, send at 0 ms after load | POST `session_id:null` → 422 | same |
| Direct API `POST /api/chat/stream {session_id:null}` | 422 `string_type` `body.session_id` | n/a |

**Correction to the 2026-09-25 addendum below:** the stored id "not restored" is not a regression. Pre-split never restored it either; it picked the newest. The null send in that addendum was case E (send before the session list loaded) or an empty list, not a failed restore.

### Beat 3: What will change

1. **Restore the empty-list create (pre-split behaviour).** Pass `createNewSessionFn: createNewSession` from the `chat.js` `loadSessions` wrapper. An agent with no sessions gets one on load and on agent switch.
2. **Send guard.** New helper `ensureActiveSession()` in a new module `chat/session_guard.js`, handed to `setupComposerControls` as `ensureSession`:
   - if a session is active, return it;
   - else await the in-flight `loadSessions` promise (tracked as `state.sessionsLoading`);
   - else create one (single-flight: concurrent calls share one create);
   - if it still has none (create failed), do not send, toast "Couldn't start a new chat", and keep the typed text.
   The guard runs **before** the composer is cleared. The paperclip upload (`onBeforeAttach`) uses the same guard, so attachments land in the session folder.
3. **Restore this device's last session.** In `chrome.js` `loadSessions`, when nothing is active, prefer the stored `autoreiv_active_session_id` if it is in this agent's list, else fall back to the newest. The key is already written on every select, so this makes it meaningful. Desktop and phone each restore their own last chat (per-device localStorage). No server-side "last session".
4. The backend stays strict: `session_id` stays required (422 is the correct contract; the frontend just never sends null).
5. Line budget: `chat.js` is at 1,032/1,045. The change there is limited to wiring (about 3-5 lines); the logic lives in `session_guard.js` and `chrome.js`.

### Beat 4: What dies

- The 422 "Chat turn failed" on the first message of a fresh or emptied chat.
- The dead end of an empty chat with no session until you click **New chat**.
- The load race that sends `session_id: null`.
- The write-only `autoreiv_active_session_id`: it is now read, and reopening the app no longer silently jumps to the newest chat.
- The unused `createNewSessionFn` branch in `chrome.js` comes back to life (not deleted).

## 2. Decisions (recommendations in bold)

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| D1 | When is a session created for an empty agent? | (a) on load/agent switch **plus** a send guard (pre-split); (b) lazily, only on first send | **(a)**: matches pre-split, and the list always shows a chat. The guard covers the race. |
| D2 | Which session opens on load? | (a) **this device's last session if it still exists, else newest**; (b) keep "newest wins" (pre-split and current) | **(a)**: Jacob's words "saved session isn't restored". Per-device, so the phone keeps its own last chat. |
| D3 | Should the backend accept `session_id: null` and create one? | (a) **no, keep 422, fix the frontend**; (b) backend auto-create | **(a)**: one owner of session creation, and the API contract stays explicit. |
| D4 | Keep typed text when a send fails? | Fix here vs. separate card | **Separate: CARD-484** (applies to every failure, not just 422). This card's guard only keeps text when the guard itself fails. |
| D5 | Should an agent switch also restore a per-agent last session? | single key vs. per-agent key | **Single key (existing)**: only restore when the stored id is in the current agent's list, else newest. Per-agent memory can be a later card if wanted. |

## 3. Acceptance criteria (EARS)

- **[REQ-476-001]** WHEN the user sends a message WHILE no session is active, THE SYSTEM SHALL create a session and send the message in it.
- **[REQ-476-002]** WHEN the Chat session list loads (page load or agent switch) AND the agent has no sessions, THE SYSTEM SHALL create one session and make it active.
- **[REQ-476-003]** WHEN the user sends WHILE the session list is still loading, THE SYSTEM SHALL wait for the load and send in the resulting session. It SHALL NOT post `session_id: null`.
- **[REQ-476-004]** WHEN the session list loads WHILE no session is active AND the stored `autoreiv_active_session_id` is in the list, THE SYSTEM SHALL open that session. Otherwise it SHALL open the newest.
- **[REQ-476-005]** WHEN two sends or a send and an attach race with no active session, THE SYSTEM SHALL create exactly one session.
- **[REQ-476-006]** IF creating the session fails, THEN THE SYSTEM SHALL NOT send, SHALL show an error toast, and SHALL leave the typed text in the composer.
- **[REQ-476-007]** WHEN a file is attached WHILE no session is active, THE SYSTEM SHALL ensure a session first, so the upload goes to that session's folder, not `attachments/global`.
- **[REQ-476-008]** THE SYSTEM SHALL behave the same on desktop and phone layouts. Each device restores its own last session.

## 4. Test plan (failing tests first)

Write these first, run them, and confirm they **fail on qa `ecbc0e7a`** before any fix.

**Vitest `tests/frontend/chat_session_guard_476.test.js`** (jsdom, fetch mocked)
1. `ensureActiveSession` returns the current id without any POST when a session is active.
2. With no session and a pending `state.sessionsLoading`, it awaits the load and returns the id it selected; no create POST (REQ-476-003).
3. With no session and no load pending, it POSTs `/api/sessions` once and returns the new id (REQ-476-001).
4. Two concurrent calls produce exactly one create POST (REQ-476-005).
5. Create fails (500): returns null (REQ-476-006).
6. `setupComposerControls` submit with no session calls `ensureSession` before `onExecuteTurn`. If `ensureSession` returns null, `onExecuteTurn` is not called and the composer text is kept.
7. `chrome.js` `loadSessions` with an empty list and `createNewSessionFn` calls it (REQ-476-002). Source contract: the `chat.js` wrapper passes `createNewSessionFn`.
8. Restore: stored id in the list → that session selected, not `sessions[0]`. Stored id missing or for another agent → `sessions[0]` (REQ-476-004).
9. `onBeforeAttach` with no session awaits the guard (REQ-476-007).

**Smoke (`scripts/smoke_*`, scratch server only; intercept `/api/chat/stream` to capture the body and return a stub SSE)**
- TC-476-A fresh data, desktop and phone: page load shows 1 session; type "hi" + Enter → the captured body has a string `session_id` that exists in `GET /api/sessions`; no "HTTP 422" toast.
- TC-476-B seed two sessions, set localStorage to the older one, reload (desktop and phone) → the older one is active and the send uses its id.
- TC-476-C send at 0 ms after `goto` → the body `session_id` is non-null.
- TC-476-D stored id for a deleted session → the newest opens, no error.

**Regression:** `tests/unit`, `tests/integration`, full Vitest (known failures only: CARD-454, CARD-456, CARD-481), `chat.js` ≤1,045 lines.

## 5. Runbook (Jacob, after build, http://192.168.1.99:8000)

1. **Desktop:** open Chat, delete every chat for the agent (or pick an agent with none). A new empty chat appears by itself. Type "hi" + Enter: it sends, no red "HTTP 422" toast.
2. **Desktop restore:** open an older chat (not the top one), reload the page. The same older chat is open.
3. **Phone (same Wi-Fi):** open an older chat there, close the tab, reopen. The phone reopens its own last chat (it may differ from the desktop; that's expected).
4. **Fast send:** reload, and type + Enter as soon as the composer appears. It sends into the open chat.
5. **Attach first:** with a brand-new empty chat, attach an image before typing, then send. The image shows in that chat.

## 6. Overlap

- **CARD-473** (phone visibility/focus catch-up): independent. It resyncs the active session. Once this card lands there is always one, so its "no session → do nothing" branch becomes rare. No shared code beyond reading `state.activeSessionId`.
- **CARD-466** (New chat into + Options): no code conflict. Its Beat 2 says automatic creation on an empty list works (`chrome.js` ~L144). **It doesn't today**; this card restores it, which is what makes CARD-466 REQ-466-005 true. A note has been added to CARD-466.
- **CARD-484** (new): a failed send clears the typed text.

---

## Addendum (2026-09-25 ET, CARD-470 diagnosis)

Reproduced again on the scratch server. The page was loaded with `localStorage.autoreiv_active_session_id` already set to an existing `autoreiv` session, yet the first send still posted `session_id: null`, giving 422 `string_type` on `body.session_id`. So the stored active session is not restored either, not just missing auto-create. Clicking **New chat** first works.

Jacob's CARD-470 live test did **not** hit this: both of his sends had fresh sessions.

> *Superseded by §1 Beat 2 (2026-09-25 planning): the stored key was never read, not even pre-split; newest wins. The null send came from the load race or an empty list.*
