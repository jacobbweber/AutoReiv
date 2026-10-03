---
id: CARD-477
title: "Chat tool rows say \"Complete\" for tools that were parked for approval or failed"
status: In Review
created: 2026-09-25
branch: feat/card-606-477-chat-row-status
related:
  - CARD-470
  - CARD-343
  - CARD-456
labels:
  - type:bug
  - area:chat
  - area:hitl
  - area:frontend
  - P2
needs_decision: none
milestone: M24
---

# [CARD-477] Chat tool rows say "Complete" for tools that were parked for approval or failed

> **Status**: In Review (2026-10-03)
> **Created**: 2026-09-25
> **Observed during**: the CARD-470 live-test diagnosis (2026-09-25 ~12:20 AM ET).
> - A parked `wiki_note_create` was saved as the tool message `Tool Error: approval_required:appr_…`.
> - The thread rendered it as `Tool: wiki_note_create ✓ Complete`, both live on Jarvis (sessions `ffcb7e81…`, `18ef9a3f…`) and on the scratch server.
> **Related**: CARD-470, CARD-343, CARD-456
> **Labels**: `type:bug`, `area:chat`, `area:hitl`, `area:frontend`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. **Still no product code** |
| **`build`** | Fix test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

### Beat 1: What Jacob means
A tool row should say what actually happened:
- waiting for approval
- rejected
- failed
- done

It should never show a green "Complete" for a tool that did not run.

### Beat 2: What AutoReiv does now
`src/web/static/modules/studios/chat/render.js` (generic tool result, about L650-670) always prints `✓ Complete` in emerald, whatever `msg.content` says.

This is **not** a CARD-397 split loss: pre-split `chat.js` L1829 had the same hard-coded label. It became visible now that CARD-470 makes approval parks common.

`render.js` is at its 800-line cap (CARD-456), so the fix needs a small helper module.

### Beat 3: What will change
Add a pure `toolRowStatus(msg)` helper, for example in `chat/tool_status.js`. It maps:

| Tool message content | Label |
|---|---|
| `Tool Error: approval_required:` or a `"status": "parked"` JSON | ⏸ Waiting for approval (amber) |
| `Tool Error:` or `tool_policy_blocked` | ✗ Failed (rose) |
| anything else | ✓ Complete |

`render.js` uses it.

Tests first:
- Vitest for the helper
- a source contract that `render.js` no longer hard-codes `✓ Complete`
- smoke: a parked tool row reads "Waiting for approval"

### Beat 4: What dies
The hard-coded green "Complete" label.

## 2. Acceptance criteria (EARS)
- **[REQ-477-001]** WHEN a tool message records an approval park, THE SYSTEM SHALL label the row "Waiting for approval" in amber.
- **[REQ-477-002]** WHEN a tool message records an error or policy block, THE SYSTEM SHALL label the row "Failed".
- **[REQ-477-003]** OTHERWISE THE SYSTEM SHALL label the row "Complete".

## Change

Shared branch with CARD-606: `feat/card-606-477-chat-row-status`.

- New `chat/tool_status.js` (`toolContentStatus`, `toolRowStatus`):
  - Waiting for approval (amber): `Tool Error: approval_required:` or a parked / approval_required JSON result.
  - Failed (rose): `Tool Error:`, `tool_policy_blocked`, or JSON with `success: false` or status error/failed.
  - Rejected (rose): "Rejected. Tool did not run." or status rejected.
  - Not run (slate): "Not run: ..." results (CARD-600 clarification skip, CARD-605 look-up budget).
  - Complete (emerald): anything else.
  - A park row whose call has a later row in the thread reads "Asked for approval".
- `render.js` uses it; the label carries `data-tool-status`. No hard-coded Complete. 767 lines (cap 800).
- Vitest `card_477_tool_row_status.test.js` (6). Smoke TC-49: a stubbed thread with park, park + rejected, error and success rows.

## Results

| Check | Result | Notes |
|---|---|---|
| Vitest | PASS | 964 passed |
| Full pytest | PASS | 2321 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2321, vitest 964, smoke 78 (TC-49 new, TC-48 extended). One earlier run failed TC-5 on net::ERR_NO_BUFFER_SPACE while live runs were going; the clean rerun passed |
| Live, desktop and phone | PASS | AutoReiv, approval mode ask, "Read the note 00_Inbox/zz-missing-note.md, then create a new inbox note titled 'Harbor list'...": wiki_note_read = Failed (its result is `{"success": false, ...}`), wiki_note_create = Waiting for approval. After Reject: Failed + Rejected. |

Screenshots in `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003\` (copies in `D:\Projects\Active\AutoReiv\scratch\ui1003\`): `477-desktop-tool-rows-waiting-failed.png`, `477-phone-tool-rows-waiting-failed.png`, `477-desktop-tool-rows-failed-rejected.png`, `477-phone-tool-rows-failed-rejected.png`.

## Found while testing

- After an approval decision the server replaces the parked row (same tool call id) with the decision row, so "Asked for approval" is not reached in live threads today. It stays for threads that hold both rows.
- A tool-calling step whose text is empty shows as an agent bubble with only "Thinking Process" and the action buttons (Teach / Workbench / Copy / Save to Wiki), as seen in the phone shots. Older than this card.

## Release note

Chat tool rows now say Waiting for approval, Failed, Rejected or Not run when that is what happened, instead of always Complete.
