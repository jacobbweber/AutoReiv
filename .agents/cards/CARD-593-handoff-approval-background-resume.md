---
id: CARD-593
title: "Hand-off approval resumes the child in the background; the approval card polls (phone-safe)"
status: In Review
created: 2026-09-30
branch: card/593-handoff-approval-background-resume
related:
  - CARD-563
  - CARD-592
  - CARD-530
  - CARD-470
labels:
  - type:bug
  - area:hitl
  - area:web
  - P1
needs_decision: none
milestone: M24
---

# [CARD-593] Hand-off approval resumes the child in the background; the approval card polls (phone-safe)

> **Status**: In Review
> **Found in**: docs/findings.md 2026-09-29 (battery ar-17): approving inside a hand-off ran the child's next turn
> inside `POST /api/approvals/{id}/decision` (35-140 s); clients timed out at 60 s.

## Beat 1: What Jacob means

Approving something inside a hand-off (or approving the hand-off itself) should never make the page wait. The work
carries on on the server even if my phone sleeps; the card tells me when it is done, and the chat carries on then.

## Beat 2: What AutoReiv did

- `src/web/routers/hitl.py` `resolve_approval_endpoint` awaited `handoff_engine.resume_nested_child(...)` for an
  approval in a `_child_` session, and awaited `tool_reg.execute(...)` for an approved `hand_off_card` /
  `handoff_to_agent` (a whole Developer run) before answering.
- `hitl.js` read `body.nested.status` from that long response.

## Beat 3: What changed

1. `src/application/orchestration/background_resume.py`: `BackgroundResumes` runs the follow-up work as a task on the
   server loop and keeps its state (running / completed / failed / approval_required, summary) for 6 h.
2. The decision endpoint returns at once. An approved hand-off tool (`PARENT_HANDOFF_TOOLS`) runs in the background
   and writes its TOOL row when it finishes; a parked child's resume runs in the background. The response carries
   `nested: {"status": "running", "resume_id", "poll_url"}` and `execution.background: true`.
3. `GET /api/approvals/{id}/resume` returns the state (404 when unknown, e.g. after a restart).
4. `hitl.js`: `pollBackgroundResume` polls every 3 s (network errors retried, 404 -> `lost`), the card says
   "Working in the background; you can leave this page", then "The hand-off finished / needs another approval /
   failed"; the chat resume waits for the end state (never while `running` or `lost`).
5. Ordinary tool approvals still run inline (short).

## Beat 4: What dies

- The awaited `resume_nested_child` and awaited hand-off `execute` inside the decision request.

## Tests

- `tests/unit/web/test_card593_background_handoff_resume.py` (slow child returns < 1.2 s then completes; approved
  hand-off runs in background and writes its row; ordinary approvals inline; tracker failure + outcomes).
- `tests/unit/web/test_hitl_web_api.py` nested tests poll the resume endpoint.
- `tests/unit/frontend/card_593_background_handoff_resume.test.js`.

## Known limits

- If the tab is closed, the parent chat's follow-up turn starts when Jacob next opens or sends in that chat (as
  before); the child's work itself is not lost.
- Background work lives in the server process; a restart mid-hand-off loses it (the card says so).
