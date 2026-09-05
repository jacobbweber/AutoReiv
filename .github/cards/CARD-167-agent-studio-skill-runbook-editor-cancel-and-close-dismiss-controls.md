# [CARD-167] Agent Studio Skill Runbook Editor Cancel and Close Dismiss Controls

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/control-plane-data-dir/requirements.md
> **Labels**: `type:fix`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Skills`

---

## 1. Why / Intent

When an operator clicks "Edit" on a skill row in Agent Studio (Card 5: Skills & Tools), the runbook editor panel (`#studioRunbookEditor`) unhides to allow editing the runbook name, short blurb description, and `SKILL.md` body.

However, the editor currently lacks both a top-right `x` close button and a bottom `[Cancel]` button. The operator has no way to exit the editor without saving changes or refreshing the page.

Adding dedicated close and cancel controls restores standard modal/drawer dismiss behavior.

---

## 2. What to Build

### A. Template Controls (`src/web/templates/index.html`)
- Inside `#studioRunbookEditor`:
  - Add a header row with title "Edit Skill Runbook" and a close button (`#studioRunbookCloseBtn`) with `<i data-lucide="x"></i>`.
  - Add a `[Cancel]` button (`#studioRunbookCancelBtn`) in the bottom action bar next to `#studioRunbookSaveBtn`.

### B. Event Wiring (`src/web/static/modules/studios/forge.js`)
- Attach click event listeners to `#studioRunbookCloseBtn` and `#studioRunbookCancelBtn` to call `hideRunbookEditor()`.
- Reset form fields, reset active runbook id/archived state, and hide `#studioRunbookEditor`.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] [REQ-DATA-019] `#studioRunbookEditor` renders `#studioRunbookCloseBtn` in its header and `#studioRunbookCancelBtn` in its bottom actions.
- [x] [REQ-DATA-020] Clicking `#studioRunbookCloseBtn` or `#studioRunbookCancelBtn` calls `hideRunbookEditor()`, returning the operator to the skills list.
- [x] Automated Vitest frontend tests in `tests/unit/frontend/forge_runbook_editor.test.js` pass cleanly.
- [x] Zero lint errors via `ruff check .` and `npm run test:unit:frontend`.

---

## 4. Constraints & Honor Flags

- Zero third-party product names in card, UI, or repo artifacts.
- Preserve existing `hideRunbookEditor()` behavior and reset flows.
