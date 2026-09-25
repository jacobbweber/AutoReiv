---
id: CARD-486
title: "Stop no longer tells the server to stop: the abort call was lost in the CARD-397 split"
status: In Review
created: 2026-09-25
branch: qa
related:
  - CARD-397
  - CARD-259
  - CARD-154
  - CARD-485
  - CARD-488
  - CARD-489
  - CARD-490
  - CARD-491
  - CARD-492
labels:
  - type:bug
  - area:chat
  - area:frontend
  - area:backend
  - P2
---

# [CARD-486] Stop no longer tells the server to stop: the abort call was lost in the CARD-397 split

> **Status**: In Review (build 2026-09-25 ET on `feat/card-486-stop-aborts-server`; D1-D7 accepted as recommended)
> **Created**: 2026-09-25
> **Observed during**: CARD-485 planning (scratch server, Playwright `scratch/c485_stop.cjs`)
> **Related**: CARD-397 (split), CARD-259 (kill/resume mid-LLM), CARD-154 (work survives disconnect), CARD-485 (busy state), CARD-488, follow-ups CARD-489 / CARD-490 / CARD-491
> **Labels**: `type:bug`, `area:chat`, `area:frontend`, `area:backend`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first on `feat/card-486-stop-aborts-server` |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means
When I press Stop, the agent really stops: the model stops generating, nothing keeps getting written into the chat, and I can send the next message straight away. The same goes when the reply was started on my phone and I press Stop on the desktop.

### Beat 2: What AutoReiv does now (evidence, qa `e40fcaa0`)

**Frontend**
- **Pre-split Stop** (`7b563003^` `chat.js` L3528-3556) did the following:
  - cleared the status poll;
  - aborted the fetch;
  - POSTed `/api/chat/stream/{activeSessionId}/abort`;
  - set `isStreaming` false, restored Send and reloaded messages;
  - showed the toast "Generation stopped".
- **Now:** `onCancelStream` (`src/web/static/modules/studios/chat.js` L916-922) only calls `activeAbortController.abort()` and shows the toast "Generation cancelled". It is wired from `chat/composer.js` L394-400. No file in `src/web/static` calls `/abort`.
- The `catch` block of `executeChatTurn` ignores `AbortError`, and its `finally` restores Send and Stop (L895-905). The chat is not reloaded.
- **Busy elsewhere** (CARD-485, `chat/session_select.js` `setSessionBusy` L115-127): Stop is shown, but `activeAbortController` is null, so pressing Stop does nothing. Busy stays on, and the 2 s watcher (`createSessionStatusWatcher` L137+) keeps it on.

**Backend** (`src/web/routers/chat.py`)
- `POST /api/chat/stream/{session_id}/abort` (L2442-2520) still exists and is keyed only by the session id. The busy-elsewhere tab already has that id (`state.activeSessionId`), so no job or stream id lookup is needed. The endpoint does four things:
  1. It pops `_active_stream_tasks` / `_active_stream_agents`.
  2. It checkpoints with `orch.checkpoint_mid_llm_kill(session_id)`. In the orchestrator (`job_phase_orchestrator.py` L961-1057), a RUNNING phase goes to QUEUED plus a checkpoint, a WAITING_APPROVAL phase stays parked, and terminal phases are left alone.
  3. It cancels the task and waits up to 5 s.
  4. It returns `{status: aborted, task_cancelled, checkpointed, resumable: true, job_id, phase_id}`.

  Existing coverage: `tests/unit/web/test_stream_resilience.py::test_abort_stream_endpoint_cancels_active_task` and `tests/unit/orchestration/test_card259_kill_resume.py::test_req_killr_002_*`.
- **Client disconnect:**
  - The stream worker is `asyncio.create_task(worker())` (L2383).
  - `event_generator` (L2387-2400) only logs "Background worker shielded" when the browser goes away (CARD-154 design). The worker keeps calling the model to the end and saves the full reply.
- **Upstream cancel:** only a task cancel closes the model request. The adapters stream with `httpx` `async with client.stream(...)`:
  - `ollama_adapter.py` L227
  - `openai_stream_tool_calls.py` L109-117
  - `anthropic_adapter.py` L263-272

  `CancelledError` exits that block and closes the HTTP connection, and vLLM/Ollama stop generating when the client disconnects.
- **Generation slots:** the gateway allows **1** concurrent generation by default (`generation_semaphore.py`, `app.py` L244-248). A reply that keeps running after Stop holds the only slot.
- **`/api/sessions/{id}/status`** (L2414-2439) returns `is_running` true when any job for the session has status `running`/`in_progress`. The kill checkpoint leaves the **job RUNNING with its phase QUEUED** (`job_phase_orchestrator.py` L995-1000). So after a Stop in a job chat, `/status` still says running.

**Repro** (scratch server `scripts/smoke_server.py --port 8767`, slow fake Ollama `scratch/c486_fake_gateway.py` streaming 1 word per 0.5 s for 60 words; drivers `scratch/c486_driver.py` and `scratch/c486_driver2.py`; no real AppData):

| Scenario | Model after "Stop" | Next message in another chat | Stopped chat afterwards |
|---|---|---|---|
| **Client-only Stop** (what the UI does today: drop the stream after 3 s) | kept streaming: 11 more words in 6 s, all 60 words finished | first word after **27.4 s** (waited for the ignored reply) | full 60-word reply saved; `/status` running until it finished |
| **Server abort** (`POST /abort` after 3 s) | request cancelled 0.3 s after the abort (`req1 CANCELLED by server after chunk 5`); abort answered in 0.01 s | first word after **0.06 s** | only the user message saved (partial reply dropped); `/status` not running |

- **Job chat, scratch pytest** (`scratch/test_c486_status_after_abort.py`): the abort returns `checkpointed: true`, leaving the job RUNNING and the phase QUEUED. `/status` then gives `is_running: true`, so the test **fails**.
- **Parked HITL job:** the abort returns `task_cancelled: false, checkpointed: true`. The job and phase stay WAITING_APPROVAL and `/status` gives `is_running: false`, which is correct.

### Beat 3: What will change
1. A new small module, `chat/stop.js`, exports `createStopHandler(state, deps)`. This keeps `chat.js` under its 1,045-line cap; it is 1,008 lines today. Pressing Stop does this:
   1. aborts this tab's fetch, if there is one;
   2. `POST /api/chat/stream/{activeSessionId}/abort` once. This runs whether the stream is our own or the chat is busy elsewhere (`state.sessionBusy`). A second press while the POST is in flight does nothing;
   3. stops the status watcher, clears busy, restores Send and hides Stop;
   4. reloads the chat's messages and re-checks status once;
   5. toasts **"Stopped"**. If the POST fails or returns non-200, it shows the warning toast **"Couldn't reach the server to stop the reply. It may still finish."** and still restores Send.
2. **Backend `/status`:** `is_running` is true only when a stream task for the session is alive **or** a job has a phase that is actually RUNNING. An open job whose phases are all QUEUED (kill-checkpointed, resumable) or WAITING_APPROVAL is not running. Without this, Stop in a job chat would show busy forever through the CARD-485 watcher.
3. HITL: a parked approval stays parked (existing orchestrator behaviour), and its approval card keeps working after Stop.

### Beat 4: What dies
- A Stop button that only hides the words while the model keeps working, fills the chat and blocks the next message.
- A Stop button that does nothing when the reply is running on another device.
- `/status` calling a stopped, resumable job "running".

---

## 2. Decisions (recommendations in bold)

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | What does Stop mean? | (a) server abort + checkpoint (pre-split); (b) client-only | **(a)**: the repro shows (b) wastes the only generation slot (27 s wait) and saves text Jacob rejected |
| D2 | Stop on a chat busy elsewhere (phone started it) | (a) abort it, no confirm; (b) confirm dialog; (c) hide Stop | **(a)**: Jacob pressed Stop on purpose, it matches the pre-split single path, and a confirm adds a step on the phone. Revisit if accidental stops happen |
| D3 | Fix `/status` here or split it out? | (a) here; (b) follow-up | **(a)**: a one-function backend change, required for REQ-486-004; otherwise the CARD-485 busy state never clears after Stop in job chats |
| D4 | The partial reply after Stop | (a) keep pre-split behaviour: it disappears on reload; (b) save the words already shown | **(a) in this card**, (b) filed as **CARD-489** (needs a backend save-partial decision) |
| D5 | Resume after Stop | (a) no UI (today: the next message or a HITL resume continues the job); (b) a "Stopped · Resume" note | **(a) here**, (b) filed as **CARD-490** |
| D6 | Parked HITL on Stop | stays parked / cancel it | **Stays parked** (orchestrator L961-1033 already does this; test it) |
| D7 | Toast wording | "Generation cancelled" / "Stopped" | **"Stopped"** (plain words) |

---

## 3. Acceptance criteria (EARS)

- **[REQ-486-001]** WHEN the user presses Stop WHILE this tab is streaming a reply, THE SYSTEM SHALL abort the fetch AND send `POST /api/chat/stream/{session_id}/abort` for the open chat exactly once.
- **[REQ-486-002]** WHEN the user presses Stop WHILE the open chat is busy with a reply running elsewhere (`state.sessionBusy`), THE SYSTEM SHALL send `POST /api/chat/stream/{session_id}/abort` for that chat exactly once.
- **[REQ-486-003]** WHEN the abort request succeeds, THE SYSTEM SHALL stop the status watcher, clear busy, restore Send, hide Stop, reload the chat's messages and show "Stopped".
- **[REQ-486-004]** WHILE a session has no live stream task AND none of its job phases is RUNNING, THE SYSTEM SHALL report `is_running: false` from `GET /api/sessions/{id}/status`, including for a kill-checkpointed job (job RUNNING, phase QUEUED) and a parked job (WAITING_APPROVAL).
- **[REQ-486-005]** IF the abort request fails or returns a non-200 status, THEN THE SYSTEM SHALL show a warning toast and still restore Send and hide Stop.
- **[REQ-486-006]** WHEN the server aborts a running reply, THE SYSTEM SHALL cancel the upstream model request (no more chunks are read from the gateway after the abort returns).
- **[REQ-486-007]** WHEN Stop is pressed while a phase is WAITING_APPROVAL, THE SYSTEM SHALL leave the phase parked and its approval actionable.
- **[REQ-486-008]** WHILE an abort request is in flight, THE SYSTEM SHALL ignore further Stop presses.

---

## 4. Failing-tests-first plan (commit 2, confirmed red before the fix)

**Vitest:** `tests/unit/web/chat/card486_stop_aborts_server.test.js` (new), against `chat/stop.js`
1. Own stream: the handler calls `controller.abort()` then `fetch('/api/chat/stream/S1/abort', {method:'POST'})` once (REQ-001).
2. `state.sessionBusy` with no controller: POSTs `/abort` for `state.activeSessionId` (REQ-002).
3. Success: `stopWatching`, `setBusy(false)`, Send shown, Stop hidden, `loadMessages('S1')`, toast "Stopped" (REQ-003).
4. Fetch rejects / 500: warning toast, Send restored (REQ-005).
5. A double press while pending sends 1 POST (REQ-008).
6. No active session: no POST, no throw.
7. Wiring guard: `chat.js` passes `onCancelStream` from `createStopHandler` (source check, like the existing 397 guards).

**pytest:** `tests/unit/web/test_card486_status_after_abort.py` (new)
1. Job chat: start phase, register a dummy task, POST `/abort`, then `/status` → `is_running False` (**red today**, repro above) (REQ-004).
2. Phase RUNNING with no stream task → `is_running True` (keeps CARD-154 phone-return behaviour).
3. Parked job: POST `/abort` keeps WAITING_APPROVAL, and `/status` is false (REQ-004/007; green today, guards the change).
4. Upstream cancel: a fake adapter whose stream sleeps between chunks. The stream is started, `/abort` is posted, and the test asserts that the adapter's stream context exited (a `finally` flag) and no chunk was read after the abort (REQ-006; expected green, guards against regressions).

**Playwright smoke** (`tests/e2e/smoke.spec.js`, TC-28/29)
- TC-28: route `/api/chat/stream` to hang and count `/abort` requests. Send, press Stop: exactly 1 `/abort` request with the session id, Send is back, and the toast "Stopped" shows (**red today: 0 requests**).
- TC-29: route `/api/sessions/*/status` to `is_running:true` until `/abort` is hit, then false. Open the chat, and busy (Stop shown) appears. Press Stop: 1 `/abort` request, Send is back and stays back after the next 2 s poll.

**Gates**
- Full Vitest: the known 5 CARD-456 failures only.
- `pytest tests/unit`: the known CARD-454 failure only.
- `pytest tests/integration`
- ESLint baseline
- `chat.js` ≤ 1,045 lines

## 5. Build order
1. Card In Progress (branch `feat/card-486-stop-aborts-server`).
2. Failing tests (above).
3. Fix:
   - `chat/stop.js`
   - `chat.js` wiring (≤ +6 lines)
   - `session_select.js`: expose `setBusy(false)` / `recheck`
   - `chat.py` `get_session_status` phase-aware check
4. CHANGELOG `[Unreleased] ### Fixed`: "Stop now stops the reply on the server too, including a reply started on another device."
5. Merge: Done, merge note, `--no-ff`, re-run tests, push, restart serve.

## 6. Runbook (Jacob, on Jarvis after `merge to qa`)
1. **Own reply:**
   1. Ask for something long ("write a 1,500-word story").
   2. After a few lines, press Stop.
   3. Expect: the words stop, Send comes back, and the toast says "Stopped".
   4. Wait 30 s and reload. The reply did not keep growing, and no long answer appears later.
2. **Next message is fast:** straight after step 1, send "hi". It starts answering right away and doesn't wait for the old reply.
3. **Phone then desktop:**
   1. Start a long answer on the phone (192.168.1.99:8000) and lock the phone.
   2. Open the same chat on the desktop. It shows busy, with Stop visible.
   3. Press Stop. Send comes back within 2 s and stays.
   4. Unlock the phone. That reply stopped too.
4. **Job chat:** in a chat that runs a plan (job strip visible), press Stop mid-phase. Busy clears and the job strip stays (resumable). Sending the next message continues the same job.
5. **Approval waiting:** when an approval card is showing, pressing Stop leaves the card, and Approve still works.
6. **Server down:** stop the server and press Stop during a reply. A warning toast shows, and Send comes back.

## 7. Risks / out of scope
- Background tasks started by the turn (memory extraction `chat.py` L1285 / L2335 via `asyncio.create_task`) are not cancelled by abort. See **CARD-491**.
- Work not started by a chat stream (for example routines) is not in `_active_stream_tasks`. `/abort` would checkpoint its RUNNING phase without stopping the real task. See **CARD-491**.
- CARD-488 (switching chats during your own stream) is separate. After this card, Stop still acts on `state.activeSessionId` only.

---

## Note (2026-09-25 ET, CARD-485 build)

CARD-485 added a busy state for a reply running elsewhere (`state.sessionBusy`, `chat/session_select.js` `setSessionBusy`). Stop is visible then, but `onCancelStream` has no fetch to abort, so it does nothing. When this card is built, Stop must POST `/abort` for the active chat in both cases (own stream or `state.sessionBusy`) and then call `sessionSelect.stopWatching()` / re-check status. This is covered by REQ-486-002/003 above.


---

## Build note (2026-09-25 ET, `feat/card-486-stop-aborts-server`, In Review)

**Commits**
- `cd697816` card In Progress
- `535802d3` failing tests, confirmed red:
  - Vitest 7/7 red (no `chat/stop.js`);
  - pytest `/status`-after-abort red, the other 3 green as guards;
  - smoke TC-28/29 desktop+phone 4/4 red (0 `/abort` requests)
- `82a839cf` fix
- `9ad37e8b` test fixtures lint (F811)
- `86e6c7d0` CHANGELOG
- this commit: In Review

**What changed**
- New `src/web/static/modules/studios/chat/stop.js`: `createStopHandler`, `postStreamAbort`, `abortUrl`, `STOPPED_TOAST`, `STOP_FAILED_TOAST`.
- `chat.js` builds `stopHandler` and passes `onCancelStream: stopHandler.stop`. It is now 1,009 lines (cap 1,045). `composer.js` is unchanged; it already calls `onCancelStream` on click.
- `session_select.js`: `createSessionSelect()` also returns `setBusy`.
- `src/web/routers/chat.py`: new `_job_has_running_phase`. `/status` counts an open job only when a phase is RUNNING. Stores without `list_phases_for_job` keep the old answer.
- The REQ-486-008 test had a self-hang: the third press needed its own release. It was fixed in the fix commit, and the assertion is unchanged.

**Tests (on the branch)**

| Suite | Result |
|---|---|
| `chat_stop_486.test.js` | 7/7 |
| `chat_session_select_485.test.js` | 9/9 |
| `test_card486_status_after_abort.py` + `test_stream_resilience.py` + `test_card259_kill_resume.py` | 18/18 |
| Full Vitest | 877 pass, 5 fail (known CARD-456) |
| `pytest tests/unit` | 2045 pass, 11 skip, 1 fail (known CARD-454) |
| `pytest tests/integration` | 107 pass |
| Full smoke | 39/39 (TC-28/29 desktop+phone included) |
| ESLint | baseline 4 errors / 5 warnings |
| ruff | baseline 9 |

**Scratch repro** (`scripts/smoke_server.py --port 8767` + `scratch/c486_fake_gateway.py`, 1 word / 0.5 s, 60 words; no real AppData)
- Real browser Stop (`scratch/c486_ui.cjs`):
  - 1 `/abort` request;
  - the model request was cancelled **58 ms** after the click (`req1 CANCELLED by server after chunk 4`);
  - 0 chunks in the next 3 s;
  - Send back, "Stopped" toast;
  - the next message's first words showed after **173 ms**.
- API comparison (`scratch/c486_driver2.py`):
  - dropping the browser connection only: the model finished all 60 words, and the next message waited **27.3 s**;
  - server abort: cut after chunk 5, next message **0.06 s**.

**Follow-ups:** CARD-492 (the device that started a reply isn't told it was stopped). Note added to CARD-488 (Stop after switching chats targets the open chat).
