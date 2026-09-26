---
id: CARD-530
title: "Approving a HITL card while the Developer turn is still streaming cancels the turn, resumes it from checkpoint, and ends with 'Cannot complete phase ... still queued'"
status: In Review
created: 2026-09-26
branch: feat/card-530-approve-mid-stream
related:
  - CARD-520
  - CARD-470
  - CARD-259
  - CARD-219
  - CARD-486
  - CARD-485
  - CARD-213
  - CARD-532
  - CARD-534
  - CARD-535
  - CARD-536
labels:
  - type:bug
  - area:jobs
  - area:chat
  - P1
---

# [CARD-530] Approve during a live reply kills and resumes the turn; the phase is left queued and the job stuck

> **Status**: In Review (built 2026-09-26 on `feat/card-530-approve-mid-stream` from qa `7b19ae1d`, D1-D9 accepted as recommended; not merged). Previously: Ready, refined 2026-09-26 ~4:55 PM ET from qa `51ee3460` (`continue`). Reproduced live on a scratch clone (port 8767, real vLLM) and with a deterministic harness. Waiting for `build` with the decisions below.
> **Found**: CARD-520 live test round 2, step 7, 2026-09-26 ~2:32 PM ET, serve `93a1d4fe`. Not caused by CARD-520: the Ask Developer helper sent once.
> **Related**: CARD-470 (inline Approve resumes the turn), CARD-259 (kill/resume checkpoint), CARD-219 (resume an open job), CARD-485/488 (session watcher, own stream), CARD-213 (orphan tool messages are dropped before the model call), CARD-532 (journey runner reuses this card's journey), CARD-534 (resume runs on the parent session)
> **Labels**: `type:bug`, `area:jobs`, `area:chat`, `P1`

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code (this pass) |
| **`build`** | Build test-first on `feat/card-530-approve-mid-stream`, with the decisions as accepted |
| **`merge to qa`** | After In Review, and after the runbook passes on scratch and serve |

---

## 1. Four Beats

- **What Jacob means:** clicking Approve while the Developer is still replying must not break anything. The reply keeps going and finishes once, the job ends `done` (or honestly `failed`), there is no red "Reply failed", no message appears twice, and the job strip says what actually happened.
- **What AutoReiv does now:**
  1. `propose_tool` (and `propose_skill` / `propose_workflow`) does not park the turn: it returns `status: "draft"` with an `approval_id` and the model keeps calling tools. The approval shows in the pinned tray, which surfaces phase-child approvals even while the parent is streaming (`shouldSkipPendingHitlCard`).
  2. Approve posts the decision, then `wireHitlCardButtons` calls `shouldResumeChatAfterHitl`, which only looks at session ids (not `state.isStreaming`, not whether the turn parked), so it starts a second `executeChatTurn('', {isResume: true})`.
  3. The server's `/api/chat/stream` cancels whatever worker is running for the session (`chat.py` ~L2375, "Cancel any previous task") and starts a new worker at once, without waiting for the old one to finish cancelling.
  4. The new worker runs `resume_after_crash` (phase `running` -> `queued`, event `resumed_from_checkpoint`), then `start_phase` (-> `running`) and a new model turn.
  5. The old worker only now handles `CancelledError` and calls `checkpoint_mid_llm_kill_phase`, which sees `running` and re-queues the phase (event `kill_checkpointed`, checkpoint `operator_kill_mid_llm`). It re-queues a phase that the new worker owns.
  6. The new turn finishes; `complete_phase` raises `InvalidPhaseTransitionError: still queued` (`job_phase_orchestrator.py` ~L339). The generic handler saves "Error: ..." as a second assistant message. Nothing fails the phase or the job: the job stays `running`, Formulate `queued` with `react_state` DONE, Execute `queued`, forever.
  7. The decision endpoint (`routers/hitl.py`) also writes the "tool accepted" text as a TOOL message into both the phase session (a second result for a call that already has one) and the parent session (a TOOL row with no tool call before it). That is the "stored twice". CARD-213 drops the orphan before model calls, so it is a display duplicate, not a model error.
  8. The strip shows "Job running | Resumed (resumed_from_checkpoint)", "Phase 1/2 Formulate", "DONE": `react_state` DONE came from the turn, `job_status` stayed `running`, and the `error` event does not touch the strip.
- **What will change:** Approve during a live reply only records the decision; a resume happens only for a turn that actually parked and only after this tab's stream has ended. The server refuses a second stream while a turn is running (409) instead of silently killing it, and a stale worker can no longer re-queue a phase another run owns. If a turn's phase cannot be completed, the phase and job fail honestly instead of hanging in `running`. A decision on a proposal that did not park writes one visible decision note, not TOOL rows. The strip shows Failed with the reason on error. A startup reconciler repairs jobs already stuck this way (Jacob's `job_3bdef1802655`).
- **What gets removed:** the silent "cancel any previous task" in `/api/chat/stream`; the unconditional resume after Approve in `wireHitlCardButtons`; TOOL-row writes for decisions on proposals whose tool call already returned.

## 2. Evidence

**Jacob's data (session `d09a88dd-f6d0-4161-b41e-229ebfd4fceb`, job `job_3bdef1802655`, times ET):**
- 2:32:49 PM `propose_tool` returns `{"approval_id": "appr_236947ee5c83", "status": "draft"}` in phase session `...::phase::phase_4298aa95cc81`; the model keeps going (two `scaffold_agent_pack` calls at 2:32:52 and 2:32:54).
- 2:32:55 PM Approve (`POST /api/approvals/appr_236947ee5c83/decision`), then a second `POST /api/chat/stream`. "tool accepted ..." saved at .880 (phase session) and .885 (parent).
- 2:32:55 PM `resumed_from_checkpoint`; 2:32:56.005 PM checkpoint `jpc_63a89f87850a` `operator_kill_mid_llm` (after the resume).
- 2:33:06-2:33:15 PM the resumed turn (in the parent session, see CARD-534) registers `get_weather`, replies, then "Error: Cannot complete phase phase_4298aa95cc81: still queued."
- Now: job `running`, Formulate `queued`/DONE, Execute `queued`.

**Live reproduction on a scratch clone (2026-09-26 ~4:49 PM ET, port 8767, `scratch\c530` = copy of Jacob's AppData without the vault key, real vLLM `nemotron-3.5-lightning`):** `scratch\c530_live_repro.py` opens a Developer chat through Talk (`get_moon_phase`), streams the turn, approves the `propose_tool` approval as soon as it appears, and sends `resume: true` while the first stream is live.
- Stream 1: `job_created` ... `tool_output` (propose_tool draft `appr_794381439fa6`) at 20.6 s, then `turn_end {"status": "aborted", "reason": "kill_checkpointed"}` at 21.0 s.
- Stream 2: `resumed_from_checkpoint` at 0.1 s, `phase_start`, `register_native_tool` ok, `react_state DONE`, reply, then `error: Cannot complete phase phase_67d088b57a55: still queued.`
- Journey events in order: `resumed_from_checkpoint` then `kill_checkpointed` (same second). Job `running`, Formulate `queued`/DONE, Execute `queued`; "tool accepted" in both sessions. Identical to Jacob's.
- Side result: `get_moon_phase` was registered with `grant_agent_ids: ["autoreiv"]`, so CARD-520 REQ-520-016 works live.

**Deterministic harness (`scratch\c530_race_harness.py`, no model):** `start_phase` -> `resume_after_crash` (-> queued) -> `start_phase` (-> running) -> `checkpoint_mid_llm_kill_phase` (stale worker, -> queued) -> `complete_phase` raises "still queued"; job `running`, both phases `queued`. This is the unit-test seed.

## 3. What must keep working (the regression fence)

- CARD-259: Stop (`POST /api/chat/stream/{id}/abort`) mid-LLM checkpoints and leaves the same job resumable; the next send/resume continues it (`resumed_from_checkpoint`).
- CARD-470: an inline Approve on a turn that **parked** (`approval_required`, turn ended) still resumes the chat turn once.
- CARD-251: no orphan job minted while a parked job owns the session.
- Nested child approvals (`_child_` sessions) still resume via `resume_nested_child`; routine approvals still resume the routine session.
- CARD-154: a client disconnect (phone locked) does not cancel the worker.
- The pinned tray still shows phase-child approvals while the parent streams.

## 4. Acceptance criteria (EARS)

- **REQ-530-001 (no resume during a live reply):** WHEN the operator approves or rejects a card WHILE this tab's stream for that session is live, THE chat SHALL NOT start a resume stream at that moment.
- **REQ-530-002 (resume only a parked turn, after it ends):** WHEN the approved card belongs to a turn that parked (`approval_required` / phase `waiting_approval`), THE chat SHALL resume once, after the live stream (if any) has ended. WHEN the tool did not park (propose_* returned a draft and the turn went on), THE chat SHALL NOT resume.
- **REQ-530-003 (server refuses, never kills):** WHEN `/api/chat/stream` arrives for a session whose worker is still running, THE server SHALL answer 409 `{"reason": "turn_running"}` AND SHALL NOT cancel the running worker. Only the abort endpoint (Stop) cancels a worker.
- **REQ-530-004 (a stale worker cannot re-queue a phase it no longer owns):** WHEN a cancelled worker checkpoints its phase, THE orchestrator SHALL re-queue the phase only if that worker's run still owns it; a phase started by a newer run SHALL stay `running`. A resume that follows an abort SHALL wait for the cancelled worker to finish (bounded, as abort already does) before `resume_after_crash`.
- **REQ-530-005 (no stuck job):** IF `complete_phase` refuses a phase at the end of a turn, THEN THE phase SHALL be marked `failed` with a plain reason, THE job SHALL leave `running` (`failed`), AND the chat SHALL show one honest message (not a raw exception) with SSE `phase_complete` status `failed`.
- **REQ-530-006 (one decision record):** WHEN a decision is made on a proposal whose tool call already returned (not parked), THE server SHALL NOT write TOOL messages to the phase or parent session; it SHALL save one decision note in the session the operator sees. WHEN the approval session already holds a TOOL result for that `tool_call_id`, a second one SHALL NOT be written.
- **REQ-530-007 (strip tells the truth):** WHEN a turn ends with an `error` event or a failed phase, THE job strip SHALL show Failed and the reason and SHALL NOT show DONE; the "Resumed" tag SHALL clear once the resumed phase completes.
- **REQ-530-008 (repair already-stuck jobs):** WHEN the server starts, THE reconciler SHALL find jobs with status `running` whose current phase is `queued` with `react_state` DONE (a finished turn whose completion was refused), mark that phase `failed` ("Interrupted by a second run while approving (CARD-530); re-run the request"), mark the job `failed`, and save a journey event `reconciled_stuck_phase`. Jobs that are resumable after Stop (phase `queued`, `react_state` empty) SHALL be untouched. A second start SHALL change nothing.

## 5. Decisions (recommendations in bold; waiting for `build`)

- **D1 Approve mid-stream: defer the resume or inject into the running turn?** **Defer.** A turn that did not park never needs a resume: the running turn goes on, and the decision is recorded (`commit_skill_pack` already checks the proposal is approved). A parked turn is resumed after the stream ends. Injecting a message into a live model turn needs a new kernel channel and is not needed for this bug.
- **D2 Second `/api/chat/stream` while a turn runs:** **409 `turn_running` for both resume and new messages; Stop is the only kill.** The composer is already disabled while streaming, so this mainly guards resume races and a second device. Alternative: 409 only for `resume: true` and keep "new message replaces the turn". Not recommended: it keeps the silent kill.
- **D3 Phase ownership:** **an in-memory run token per phase in the orchestrator (single process), set by `start_phase` and checked by `checkpoint_mid_llm_kill_phase`,** plus the new worker awaiting the cancelled one (5 s, the abort endpoint's bound). A DB column is not needed while serve is one process.
- **D4 A refused `complete_phase`:** **fail the phase and job honestly (REQ-530-005); do not loosen the state machine** (no "complete a queued phase").
- **D5 Decision note for non-parked proposals:** **one message in the operator's session rendered as the existing resolved-HITL card ("Approved: propose_tool get_weather"), not a TOOL row.** The exact role/marker is chosen at build to match how `hitl.js` renders resolved cards. The phase session gets nothing new: the running turn already has the draft result.
- **D6 Jacob's stuck `job_3bdef1802655`:** **startup reconciler (REQ-530-008), not a one-shot migration.** It fixes this job and any future one with the same signature, it is idempotent, and it needs no DB schema change. It sets `failed` (honest: Execute never ran, and the registered tool was never checked by a run), not `done`.
- **D7 The duplicate "tool accepted" rows already in Jacob's chat:** **leave them.** Chat history is not rewritten; CARD-213 already drops the orphan TOOL row before model calls. New decisions stop writing them (REQ-530-006).
- **D8 How the strip shows state:** **show the server's job status, not the turn's `react_state`, once the turn ends:** Running / Waiting for approval / Done / Failed (reason). An `error` event sets Failed. "Resumed" shows only while the resumed phase runs.
- **D9 Resumed phase runs on the parent session, not its `::phase::` session:** **out of scope, filed as CARD-534** (every resume path does this, not only this bug).

## 6. Failing-tests-first plan

Commit the failing tests first, confirm red, then implement.

1. `tests/unit/orchestration/test_card530_concurrent_resume.py`
   - the harness interleaving: after the fix the stale worker's checkpoint leaves the phase `running`, `complete_phase` succeeds, the job advances (REQ-530-004);
   - Stop-then-resume (CARD-259) still re-queues and resumes (fence);
   - `complete_phase` refused at turn end -> phase `failed`, job `failed`, honest SSE (REQ-530-005; drive `_stream_turn_bound` with a fake kernel);
   - reconciler: seeded job with the `job_3bdef1802655` signature -> failed plus journey event; a Stop-resumable job untouched; second run no change (REQ-530-008).
2. `tests/unit/web/test_card530_stream_guard.py`: with a fake kernel blocked on an event, a second `POST /api/chat/stream` (resume true and false) -> 409 `turn_running`; the first worker is still alive and finishes (REQ-530-003).
3. `tests/unit/web/test_card530_hitl_decision.py`: approving a `propose_tool` approval whose phase session already has the draft result writes no TOOL row to the phase or parent session and one decision note; a parked-tool approval still writes its TOOL result once (REQ-530-006, CARD-470 fence).
4. `tests/unit/frontend/card_530_approve_mid_stream.test.js`
   - `wireHitlCardButtons` with `state.isStreaming` true: `onResumeTurn` not called; called once after the stream ends when the card came from a parked turn; never for a draft proposal (REQ-530-001/002);
   - `applyJobPhaseEvent` / `formatJobPhaseStrip`: `error` -> Failed with reason, no DONE; Resumed clears on `phase_complete` (REQ-530-007).
5. **Smoke TC-new** (fake LLM on the smoke server): a phase turn emits a draft approval, the test clicks Approve in the tray while streaming; expect no second `/api/chat/stream`, one reply, no "Reply failed", strip Done.
6. **Journey note for CARD-532** (`tests/e2e/journeys/card-530-approve-mid-stream`): real model on the 8770 environment. Steps: open Tools Studio Talk (create `get_moon_phase`, pure computation) -> wait for an approval card in the tray while the reply streams -> click Approve -> assert: no `/api/chat/stream` request after the click until `turn_done`, no console error, no "Reply failed" banner, strip ends Done or honest Failed, DB job `done`, exactly one decision note, zero duplicate TOOL rows. Screenshot after each step. `scratch\c530_live_repro.py` is the API-level version of the same journey.

## 7. Runbook (after build)

1. **Scratch (real model):** refresh `scratch\c530` from Jacob's AppData (no vault key), `powershell -ExecutionPolicy Bypass -File scratch\c505_run.ps1 -Data c530 -Tag c530`, run `.venv\Scripts\python.exe scratch\c530_live_repro.py 90`. Expect: stream 2 gets **409 turn_running**; stream 1 is not aborted and finishes; job `done` (or `failed` with a reason, never `running`); one decision note, no duplicate TOOL rows.
2. **Scratch reconciler:** the clone contains `job_3bdef1802655`; after the restart it is `failed` with the CARD-530 reason and a `reconciled_stuck_phase` event; restart again: no change. The CARD-259 fence: start a Developer turn, press Stop, send again: resumes (`resumed_from_checkpoint`), job completes.
3. **Serve (Jacob, desktop):** Ctrl+F5 (new app.js `?v=`). Tools Studio or Teach -> Ask Developer for a small tool. When an approval card appears while the Developer is still replying, click **Approve** at once. Expect: the reply keeps streaming and ends once; no red banner; the strip ends Done (or Failed with a reason); the card shows Approved; no second "tool accepted" row.
4. **Serve, old job:** open session `d09a88dd-...` ("Tools Studio create: get_weather"): the strip / job shows Failed with the CARD-530 reason instead of running.
5. **Phone** (`http://192.168.1.99:8000`): repeat step 3.
6. Restart serve (`scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`); health 200 on 127.0.0.1 and 192.168.1.99.

## 8. Definition of done

All REQ-530 tests green; preflight at baseline (known CARD-454 unit, CARD-456 Vitest, ESLint 4+5, ruff 7); smoke with the new TC passes; the runbook passes on scratch and serve; CHANGELOG line; app.js `?v=` bumped.

## What stays out of scope

- CARD-534 (resumed phase writes to the parent session).
- Making propose_* park the turn (it stays a non-blocking draft).
- Injecting operator messages into a live turn (D1).
- CARD-531 (network-skip registration) and CARD-529 (modify-tool loop).

## Build evidence (2026-09-26, times ET)

**Commits on `feat/card-530-approve-mid-stream`:** `1a1c1801` failing tests (confirmed red: Python 12 of 14 red, the 2 fence tests green; Vitest 8 of 9 red; smoke TC-46 red against qa `hitl.js`: 2 stream posts, expected 1), `c7265cb9` implementation + smoke TC-46 + app.js 2.0.90 + CHANGELOG + roadmap CARD-534, `3c659dbf` 409 handling moved to `chat/turn_running.js` (keeps `chat.js` under the CARD-397 1000-line cap).

**What changed:** `POST /api/chat/stream` answers **409 `turn_running`** while the session has a live turn (no more cancel-and-resume); the worker only removes its own task entry; each `start_phase` mints a run token and a stale worker's `checkpoint_mid_llm_kill_phase` no longer re-queues a phase a newer run owns; a refused `complete_phase` fails the phase and job with a reason (`turn_done` `job_failed`) instead of leaving it running; startup `reconcile_stuck_phases` fails jobs left `running` with a queued-but-DONE phase (journey event `reconciled_stuck_phase`, idempotent); approving a `propose_*` draft saves one "Approved: ..." note and returns `resume_chat: false`; the UI defers any resume until the reply is idle, shows a warning toast on 409, and the strip shows "Job failed: <reason>" and clears Resumed.

**Preflight (`scratch\full_c530_*`, after `c7265cb9`; Vitest/ESLint rerun after `3c659dbf`):**

| Suite | qa baseline (m520) | CARD-530 |
|---|---|---|
| Unit (pytest) | 1992 passed / 11 skipped / 1 failed | 2006 passed / 11 skipped / 1 failed (CARD-454 only) |
| Integration | 103 passed | 103 passed |
| Vitest | 914 passed / 3 failed | 924 passed / 3 failed (CARD-456 only) |
| ESLint | 4 errors + 5 warnings | 4 errors + 5 warnings |
| ruff | 7 errors | 7 errors |
| Smoke | 71 passed | 73 passed (TC-46 desktop + phone new) |

**Startup repair, Jacob's DB:** before restart `job_3bdef1802655` running, Formulate queued/DONE, Execute queued, 3 journey events, 1 running job. After `restart_serve.ps1` (5:30:49 PM ET): job failed, Formulate failed/FAILED, event `reconciled_stuck_phase` ("Interrupted by a second run while approving (CARD-530): this step finished but could not be recorded. Send the request again to re-run it."), 0 running jobs. Second restart: `updated_at` still `21:30:49Z`, still 4 events: no change.

**Live repro on the fixed code** (`scratch\c530_live_repro.py 120`, scratch 8767, real vLLM, ~5:13 PM ET): the mid-stream resume got **HTTP 409**; stream 1 was not aborted and finished both phases; job `job_ccff2e09672b` done; one `hitl_decision` note, no duplicate TOOL rows.

**Browser check (Playwright, scratch 8767, real vLLM, ~5:20 PM ET):** desktop 1280x800 and phone 390x844, Tools Studio -> Talk to developer -> Approve on the `propose_tool` card while the reply streams: 1 stream POST, 0 resume POSTs, reply kept streaming and finished, strip "Job done ... Phase 2/2 Execute DONE", 0 error banners, 0 console errors, 0 failed responses. Screenshots in `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-530\`.

**Found while building:** CARD-535 (after approving a draft once the turn has ended, the Developer does not continue; Execute can file a second draft), CARD-536 (reopening a failed job's chat shows Failed without the reason and names the last queued phase).
