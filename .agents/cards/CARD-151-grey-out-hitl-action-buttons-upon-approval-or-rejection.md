# [CARD-151] Grey Out HITL Action Buttons Upon Approval or Rejection

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:bugfix`, `type:ux`, `AutoReiv.Web`, `AutoReiv.Chat`

---

## 1. Why / Intent

When a Human-In-The-Loop (HITL) approval card (such as for `cli_exec` or agent delegation) is approved or rejected, the `Approve` and `Reject` buttons currently retain their bright green (`bg-emerald-700`) and bright red (`bg-rose-800`) styling.

Although the HTML buttons are set to `disabled = true` in JavaScript, the lack of visual disabled styling makes them appear clickable. Users cannot easily tell at a glance that the action has already been taken, leading to confusion and accidental repeat clicks.

Users need both action buttons to visually grey out immediately upon clicking (e.g. muted slate background, dimmed text, subtle border, `cursor-not-allowed`) so it is immediately obvious that the action has already been completed.

---

## 2. What to Build

1. **Frontend HITL Button Disabled & Resolved Styling (`src/web/static/modules/studios/chat.js`)**:
   - Update `buildHitlCardInnerHtml` and `plan-review-actions` button markup to include Tailwind disabled variants:
     ```html
     disabled:opacity-40 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500 disabled:border-slate-700
     ```
   - In `submitHitlDecision()`:
     - On click, immediately disable both buttons and apply muted disabled styling so they visually dim during network transit.
     - On successful response (approval or rejection), permanently strip active saturated color classes (`bg-emerald-700`, `bg-rose-800`, hover states) and apply persistent resolved greyed-out classes (`bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50`).
   - In message re-rendering / session reload:
     - Check if the approval has already been resolved or tool execution completed; if so, render the buttons pre-disabled and pre-greyed.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-HITL-001]`: Upon clicking `Approve` or `Reject`, both buttons immediately visually transition to a greyed-out disabled state.
- [x] `[REQ-HITL-002]`: Hover and active pointer events are disabled (`cursor-not-allowed`, no background hover shifts).
- [x] `[REQ-HITL-003]`: Resolved approvals reloaded from history or when switching sessions render in the greyed-out disabled state.
- [x] `[REQ-HITL-004]`: The status text (e.g. "Approved. Tool ran." or "Rejected.") remains clearly readable next to the greyed buttons.
- [x] `[REQ-HITL-005]`: Automated unit tests and frontend tests pass cleanly via `pytest` and `npm test`.
- [x] `[REQ-HITL-006]`: Zero linting errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero regressions to HITL approval/rejection API payload or SSE resume logic.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
