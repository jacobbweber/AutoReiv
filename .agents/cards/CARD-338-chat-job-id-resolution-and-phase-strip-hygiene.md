# [CARD-338] Chat Job ID Resolution and Phase Strip Hygiene

> **Status**: Done
> **Created**: 2026-09-16
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `domain:chat`, `domain:orchestration`

---

## 1. Why / Intent

In Chat Studio, conversational turns currently display a top status strip with `Job unknown | Phase autoreiv | DONE`.

### The Three Beats
1. **What Jacob means**: When having a regular chat with AutoReiv, the chat header shows `Job unknown`. Either there is no job (so it shouldn't say `Job unknown`), or if a job was minted, it should show the real Job ID so he can inspect or reference it.
2. **What AutoReiv does now**: In `chat.js`, whenever `react_state` fires (such as `DONE` at the end of a plain ReAct turn), `jobPhaseStatusStrip` unhides. Because plain turns have no job in scope (`job_id=null`, `job_status=null`, `phase_name=null`), `formatJobPhaseStrip` defaults `jobStatus` to `"unknown"`, creating `Job unknown`, and falls back to `Phase <agent_id>`. This creates misleading UI theatre.
3. **What will change**:
   - For plain conversational turns without a standing Job, `#jobPhaseStatusStrip` remains hidden or cleanly indicates conversational mode without showing `Job unknown`.
   - When a standing multi-step Job *is* minted (via catalog resolve or workflow), the real `job_id` is reliably bound, propagated via SSE, and displayed with a working click-to-copy button.
   - Clean up fallback logic in `formatJobPhaseStrip` so fake phase names (`Phase <agent_id>`) are eliminated.

---

## 2. What to Build

### 1. Frontend Job Phase Strip Hygiene (`src/web/static/modules/studios/chat.js`)
- Update `renderJobPhaseStrip()`:
  - Guard condition: Do not display `#jobPhaseStatusStrip` solely because `reactState` is `DONE` or `THINKING` if there is no `jobId` and no active standing phase.
  - If `jobId` is absent and `jobStatus` is not explicitly set, hide the strip.
- Update `formatJobPhaseStrip(state)`:
  - Never generate `Job unknown`. If `state.jobStatus` is missing or unknown, do not synthesize a job status label unless a real `jobId` is present.
  - Do not use `agentId` as a fallback `phaseName`.
  - Display the real `jobId` with the copy action whenever a standing job is in scope.

### 2. Backend Job ID Binding & SSE Forwarding (`src/web/routers/chat.py`)
- When a standing Job is minted (`create_job_from_catalog_resolve`), ensure `job_created`, `phase_start`, and subsequent `react_state` events include the real `job_id` and `job_status`.
- For session resume or open parked HITL jobs (`latest_open_job_for_session`), bind the active `job_id` to outgoing event payloads so the frontend immediately knows the job ID.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] Plain conversational turns in Chat Studio do not display `Job unknown` or fake phase pills (`Phase <agent_id>`).
- [x] `#jobPhaseStatusStrip` only renders when there is a real standing Job or active multi-phase workflow.
- [x] When a standing Job is minted, the real Job ID (e.g. `job_abc123`) is displayed in the chat header with a functional click-to-copy button.
- [x] Unit tests in `tests/unit/frontend/chat_job_phase_strip_338.test.js` verifying `formatJobPhaseStrip` and `renderJobPhaseStrip` with and without `jobId`.
- [x] Backend tests verifying SSE events and UI contract via `tests/unit/web/test_chat_job_phase_ui.py`.
- [x] All frontend (`npm run lint:frontend`, `npm run test:unit:frontend`) and backend (`ruff check`, `pytest`) tests pass with zero errors.

---

## 4. Constraints & Honor Flags

- Zero UI theatre: never display placeholder or "unknown" identifiers when no job exists.
- Clean separation: plain chat ReAct turns remain fast and unencumbered; standing jobs remain fully trackable.
- Work conducted on dedicated feature branch `fix/CARD-338-chat-job-id-resolution` cut from `qa`.


