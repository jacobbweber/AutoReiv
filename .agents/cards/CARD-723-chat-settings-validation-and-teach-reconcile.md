---
id: CARD-723
title: "Chat and Settings API Validation, Teach Card Reconciliation, and Drawer Session Refresh"
type: bug
status: Done
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-723-chat-settings-validation-and-teach-reconcile]
  checks:
    - tests/unit/web/test_card723_validation_and_teach_reconcile.py
branch: feat/card-723-chat-settings-validation-and-teach-reconcile
log: {minutes: 25, qa_runs: 2, findings: 0}
created: 2026-10-18
completed: 2026-10-18
---

# CARD-723 Chat and Settings API Validation, Teach Card Reconciliation, and Drawer Session Refresh

## Problem
Four related operator/API bugs from `docs/findings.md`:
1. `POST /api/settings/matrix` silently converts out-of-range or invalid `max_concurrent_generations` (outside `1..3`, e.g. `4` or `0`) to `1` and returns HTTP `200` with no error.
2. `POST /api/chat/stream` accepts any arbitrary `approval_mode` string (e.g. `"auto"` or `"invalid"`) and silently treats anything other than `"run"` as `"ask"`, so callers get unexpected approval parks with no validation error.
3. Reloaded Teach (`SKILL_PROPOSAL`) cards in Chat continue to display `"On for <agent>."` even after the skill has been deleted, archived, or unticked from that agent.
4. Opening the Chat sessions drawer (`#toggleSidebarBtn`) does not refresh `loadSessions()`, so sessions created via `POST /api/sessions` after initial page load (or when `#agentSelect` is already on the target agent, as in `openSessionByTitle` for `tutor`) do not appear in `#sessionList`.

## Cause
1. In `src/web/routers/settings.py` (`update_purpose_matrix`, lines 360–367), `max_concurrent_generations` catches `TypeError`/`ValueError` or `slots < 1 or slots > 3` and silently assigns `slots = 1` instead of raising `HTTPException(status_code=400, ...)`.
2. In `src/web/routers/chat.py` (`ChatStreamRequest` and `chat_stream`), `req.approval_mode` is not validated against allowed modes (`ask`, `run`, `strict`, `balanced`, `hands_off`) before streaming begins.
3. In `src/web/routers/skills.py` (`post_adopt_skill`), adopting a skill writes `"adoption_state": "adopted"` into the persisted `SKILL_PROPOSAL` message JSON, and `serialize_session_messages` in `src/application/kernel/compaction_verifier.py` returns that static JSON without checking whether `skill_id` still exists and is ticked on `target_agent_id`.
4. In `src/web/static/modules/studios/chat/scroll.js` and `src/web/static/modules/studios/chat.js`, clicking `#toggleSidebarBtn` opens `#chatSessionsDrawer` without triggering `loadSessions()`.

## Change
- Validate `max_concurrent_generations` in `POST /api/settings/matrix` (`src/web/routers/settings.py`): raise `HTTPException(status_code=400, detail="max_concurrent_generations must be an integer between 1 and 3")` when provided and outside `1..3` or non-integer (boolean/string/etc.).
- Validate `approval_mode` in `POST /api/chat/stream` (`src/web/routers/chat.py`): accept `"ask"`, `"run"`, and canonical `ApprovalMode` values (`"strict"`, `"balanced"`, `"hands_off"`), normalizing `"hands_off"` to `"run"` and `"strict"`/`"balanced"` to `"ask"`, and raising `HTTPException(status_code=400, ...)` on any other value (such as `"auto"` or `"invalid"`).
- In `serialize_session_messages` (`src/application/kernel/compaction_verifier.py`) and `get_session_messages` (`src/web/routers/chat.py`), reconcile `SKILL_PROPOSAL` messages whose `adoption_state == "adopted"` against the live agent registry (`allowed_skill`) and user skill catalog so removed/unticked skills serialize with `adoption_state = "pending"`.
- In `src/web/static/modules/studios/chat.js` / `scroll.js`, refresh `loadSessions()` when `#toggleSidebarBtn` opens the sessions drawer.

## What dies
Silent fallback of invalid `max_concurrent_generations` to `1` and silent fallback of invalid `approval_mode` strings on `/api/chat/stream` to `"ask"`.

## Proof
- Journey `card-723-chat-settings-validation-and-teach-reconcile`: verifies `POST /api/settings/matrix` rejects `max_concurrent_generations=4`, `POST /api/chat/stream` rejects `approval_mode="auto"`, a reloaded Teach proposal card reverts from `"On for autoreiv"` to actionable after skill removal, and `openSessionByTitle` opens an API-created `tutor` session via `#toggleSidebarBtn`.
- Checks: `tests/unit/web/test_card723_validation_and_teach_reconcile.py`.

## Plan and decisions
- Return HTTP `400` with a clear message when `max_concurrent_generations` is outside `1..3` or when `/api/chat/stream` receives an unknown `approval_mode`, matching the existing `approval_mode` validation on `POST /api/settings/matrix`.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-723-chat-settings-validation-and-teach-reconcile` | desktop | PASS | 3/3 steps pass (matrix/stream 400 validation, Tutor drawer refresh, Teach card adoption & post-delete reconciliation) |
| `card-723-chat-settings-validation-and-teach-reconcile` | phone | PASS | 3/3 steps pass |

Screenshots:
- `/tmp/autoreiv-qa/card-723/card-723-chat-settings-validation-and-teach-reconcile-desktop-02-opensessionbytitle-opens-an-api-created-tutor-ch.png`
- `/tmp/autoreiv-qa/card-723/card-723-chat-settings-validation-and-teach-reconcile-desktop-03-adopt-a-teach-lesson-on-autoreiv-remove-the-skil.png`
- `/tmp/autoreiv-qa/card-723/card-723-chat-settings-validation-and-teach-reconcile-phone-03-adopt-a-teach-lesson-on-autoreiv-remove-the-skil.png`

## Release note
Validated `max_concurrent_generations` (`1..3`) on `POST /api/settings/matrix` and `approval_mode` on `POST /api/chat/stream`, reconciled reloaded Teach card adoption state when a skill is removed, and refreshed the Chat sessions drawer on open.
