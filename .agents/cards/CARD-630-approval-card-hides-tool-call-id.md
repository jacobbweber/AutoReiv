---
id: CARD-630
title: "The approval card shows the internal _tool_call_id in the arguments box"
type: bug
status: Ready
priority: P3
milestone: M24
needs_decision: none
proof:
  journeys: [card-630-approval-card-hides-tool-call-id]
  checks: [tests/unit/frontend/card630_hitl_args_hide_tool_call_id.test.js]
branch: feat/card-630-approval-card-hides-tool-call-id
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-04
related:
  - CARD-545
  - CARD-470
  - CARD-295
---

# CARD-630 The approval card shows the internal _tool_call_id in the arguments box

## Problem
In the CARD-545 live chat check (2026-10-04, :8770, Spark Nemotron), "Use the c545_note_save tool to save the note "buy milk"" parked the call. The approval card's arguments box shows the tool's real argument and an internal id Jacob has no use for:
```
{
  "text": "buy milk",
  "_tool_call_id": "chatcmpl-tool-b222298df2d1e9dc"
}
```
It is on both the inline card in the reply and the pinned approval tray, at desktop and phone width. Screenshots `autoreiv-qa\ui1003l\545-chat-note-desktop.png` and `545-chat-note-phone.png`. Every parked tool call shows it, not only Developer-built tools.

## Cause
`HITLEngine.park_tool_call` (`src/application/kernel/hitl_engine.py`) stores the model's tool call id inside the approval's `arguments` as `_tool_call_id`, so the resume in `src/web/routers/hitl.py` can answer the same tool call. `GET /api/approvals/pending` and the `approval_required` event pass those arguments through unchanged, and `formatHitlArgs` in `src/web/static/modules/studios/chat/hitl.js` prints every key.

## Change
- `formatHitlArgs` leaves out `_tool_call_id` (and any other key that starts with `_`, which are internal) before it formats the arguments. Both the inline card (`renderInlineHitlCard`) and the tray (`renderPendingHitlCards`) use it.
- The stored arguments do not change: the resume still reads `_tool_call_id`. No API change.
- When building, `rg -n "arguments" src/web/static` for any other view that prints approval arguments (routine run view, job strip) and use the same helper there.

## What dies
The `_tool_call_id` line in approval cards.

## Proof
- Journey `card-630-approval-card-hides-tool-call-id`: on :8770 with a write tool that asks, the inline card and the pinned tray show `"text": "buy milk"` and no `_tool_call_id`; Approve still resumes the same tool call and the reply finishes.
- Checks: `tests/unit/frontend/card630_hitl_args_hide_tool_call_id.test.js` (failing first): an object, and a JSON string, with `_tool_call_id` format without it and keep the other keys; a code/command argument still gets its primary-key layout; arguments that are only `_tool_call_id` give an empty box. Negative: a user key such as `tool_call_id` (no underscore) is still shown.
- The resume tests in `tests/unit` for `hitl.py` stay green (the id is still stored).

## Plan and decisions
- Hide it at display time rather than moving it out of `arguments`: one front-end change, and the stored row and resume path stay as they are.

## Findings
- (from the CARD-545 live chat check, 2026-10-04; noted on CARD-545)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-630\...`

## Release note
Approval cards show only the tool's own arguments; the internal tool call id is hidden.
