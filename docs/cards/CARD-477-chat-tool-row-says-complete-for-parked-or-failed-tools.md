---
id: CARD-477
title: "Chat tool rows say \"Complete\" for tools that were parked for approval or failed"
status: Ready
created: 2026-09-25
branch: qa
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
---

# [CARD-477] Chat tool rows say "Complete" for tools that were parked for approval or failed

> **Status**: Ready
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

Do not write product code until Jacob says **build** on this card.

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
