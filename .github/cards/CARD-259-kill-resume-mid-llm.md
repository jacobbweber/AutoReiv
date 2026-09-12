# [CARD-259] Kill / Resume Mid-LLM (FF blocker on CP wave tip)

> **Status**: Ready
> **Created**: 2026-09-12
> **Spec Reference**: Architect Done bars after CARD-258 stress scenario #6 `kill_resume_mid_job` class=other (`job_9836e6ddd4a2`). Abort cancelled mid-Formulate (`task_cancelled=True`); job failed in ~2s; resume did not complete the same `job_id`. Timeout badge is CARD-258 (shipped). This card is the remaining FF blocker: kill mid-LLM must checkpoint, not fail/cancel. Tip: feat/self-scaffold-queue-e2e-255 @ 476785b (258 included). Do NOT reopen CARD-258. Do NOT merge grok/qa/main.
> **Labels**: type:bug, P0, ControlPlane, KillResume, AntiTheatre, FF-blocker
> **Branch**: `feat/self-scaffold-queue-e2e-255` (work ON tip; push; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Live stress `job_9836e6ddd4a2` died as class=other: abort mid-Formulate cancelled the worker and marked the Job/phase cancelled/failed. Resume did not finish the **same** `job_id`.
2. Operator kill mid-LLM is a **checkpoint**, not a death. Resume must continue Formulate then Execute on that `job_id` through DONE — or honest HITL park. Never mint an orphan Job.
3. Silent SSE death while a shielded worker still runs is the bug class: abort must stop the worker (no orphan) **and** leave the Job resumable. Client-disconnect shield (CARD-154 phone-lock) stays; explicit abort is not shield-and-forget.
4. Honesty class stays zero — never Done-on-FAILED. Kill must not `fail_phase` / cancel the Job just to look tidy.
5. This card is ONLY kill/resume mid-LLM. Do not reopen CARD-258 budget/retry. Do not merge grok/qa/main.

### Beat 2: What AutoReiv Does Now
1. `POST /api/chat/stream/{session_id}/abort` cancels the asyncio task **and** writes Job/phase status `cancelled` (terminal). `latest_open_job_for_session` then cannot see the Job.
2. `_stream_turn_bound` / routine executor `CancelledError` calls `fail_phase(..., "phase_cancelled_during_llm")` — Job becomes FAILED. CARD-219 `resume_after_crash` only recovers RUNNING / WAITING_APPROVAL, not FAILED/CANCELLED.
3. SSE `event_generator` shields the worker on client disconnect (CARD-154). Abort + shield race: SSE ends, worker may still be winding down, Job already terminal — resume cannot continue.
4. CARD-219 crash-resume and CARD-251 Forge Approve same-`job_id` exist; operator abort is the missing standing path.

### Beat 3: What Will Change
1. **Kill = checkpoint**: abort / mid-LLM `CancelledError` writes a durable checkpoint (`last_fail_reason=operator_kill_mid_llm`), resets RUNNING → QUEUED, keeps Job RUNNING (not cancelled, not failed).
2. **Abort stops the worker** (await cancel) so there is no orphan after SSE ends. Return `checkpointed` + `resumable` + `job_id` while keeping `status=aborted` for API compat.
3. **Resume same `job_id`**: `resume_after_crash` treats kill-checkpointed queued phases as interrupt recovery (`resumed_from_checkpoint=true`) and Chat continues Formulate → Execute to DONE or honest park.
4. **Honesty**: kill never Done-on-FAILED; `turn_end` reason `kill_checkpointed`. CARD-257 FAILED honesty stays for real failures only.
5. TDD red→green + live Jarvis proof under Ollama. Artifact `notes/marathon-card259-live-smoke.json` + kill/resume smoke (refresh 258 scenario #6 or write `notes/marathon-card259-kill-resume-smoke.json`). CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [ ] **[REQ-KILLR-001]**: Mid-phase kill → durable checkpoint → resume **same** `job_id` to Formulate/Execute completion (or honest park).
- [ ] **[REQ-KILLR-002]**: No orphan worker / silent SSE death. Abort cancels the worker; Job stays resumable. SSE ending while a shielded worker still runs is the bug class.
- [ ] **[REQ-KILLR-003]**: Live proof = stress scenario kill/resume green (was `job_9836e6ddd4a2` class other). Artifact `notes/marathon-card259-live-smoke.json` and refresh 258 scenario #6 or `notes/marathon-card259-kill-resume-smoke.json`.
- [ ] **[REQ-KILLR-004]**: Honesty class stays zero — never Done-on-FAILED. Kill does not `fail_phase` / cancel the Job.
- [ ] **[REQ-KILLR-005]**: Tests red→green; CHANGELOG; push on `feat/self-scaffold-queue-e2e-255` only — never qa/main; do not merge to grok. Do **not** reopen CARD-258.

## 3. Constraints

- Work ON `feat/self-scaffold-queue-e2e-255` @ 476785b tip. feat-off-grok only; never qa/main; never merge grok.
- Do not reopen CARD-258 (budget/retry stays). Do not invent a second orchestrator — extend CARD-219 checkpoint + Chat abort.
- CARD-154 client-disconnect shield stays for phone-lock; explicit abort is checkpoint + stop worker.
- Honesty never Done-on-FAILED (CARD-257). Quality > speed.

## 4. Modules Likely Touched

- `src/application/orchestration/kill_resume.py` (new: reason constant + classify/payload)
- `src/application/orchestration/job_phase_orchestrator.py` (`checkpoint_mid_llm_kill` + resume treats kill-checkpoint)
- `src/application/orchestration/crash_resume.py` (optional label)
- `src/web/routers/chat.py` (abort endpoint + `CancelledError` checkpoints, does not `fail_phase`)
- `src/application/routines/executor.py` (same `CancelledError` policy)
- `tests/unit/orchestration/test_card259_kill_resume.py` (new)
- `tests/unit/web/test_stream_resilience.py` (abort no longer cancels the Job)
- `CHANGELOG.md`, `notes/marathon-card259-live-smoke.json`, kill/resume smoke notes

## 5. CoS smoke prompt

```
Write a short Wiki note in 00_Inbox about AutoReiv kill/resume mid-Job. Done-when: I can open that note via wiki_note_read. Keep it under 120 words.
```

Kill mid-Formulate (after `job_id` exists), then `resume: true` on the same session. Same `job_id` must reach DONE or honest park.

## 6. Marathon Build Lock

- Architect Done bars locked — Builder implements now.
- TDD where practical; live Jarvis proof required.
- Do NOT merge to grok/qa/main. Do NOT reopen CARD-258.
