---
id: CARD-499
title: "chat/render.js (836) and chat.js (1,012) are over the CARD-397 line caps"
status: Ready
created: 2026-09-25
branch: qa
parent: CARD-456
related:
  - CARD-456
  - CARD-397
  - CARD-496
labels:
  - type:refactor
  - area:chat
  - area:frontend
  - P3
---

# [CARD-499] chat/render.js (836) and chat.js (1,012) are over the CARD-397 line caps

> **Status**: Ready
> **Created**: 2026-09-25
> **Parent**: CARD-456 (item 1: `chat_monolith_decomposition_397` pre-existing failures)
> **Related**: CARD-397, CARD-496 (removes about 90 Factory lines from `render.js`)
> **Labels**: `type:refactor`, `area:chat`, `area:frontend`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** The chat code stays in the small files CARD-397 promised, and the size test passes again.

**Beat 2: What AutoReiv does now.** `tests/unit/frontend/chat_monolith_decomposition_397.test.js` asserts `chat.js` < 1,000 lines and every `chat/*.js` < 800. On qa `6bedb5b0`, `chat.js` is 1,012 and `chat/render.js` is 836. Both tests fail and are carried as known failures under CARD-456.

**Beat 3: What will change.**
- `render.js`: move `openArtifactModal` (L102-233; after CARD-472 no chat path calls it, so delete it if CARD-496 confirms nothing else does) and `renderSkillProposalCard` (L234-395) into `chat/skill_proposal.js`. CARD-496 also removes L760-850.
- `chat.js`: move the job-chrome glue or the agent header helpers into existing submodules until it is under 1,000.
- No behaviour change. The re-exports stay.

**Beat 4: What dies.** Two long-standing known failures in CARD-456.

## 2. Acceptance criteria (EARS)

- **[REQ-499-001]** THE SYSTEM SHALL keep `chat.js` under 1,000 lines and every `chat/*.js` under 800 lines (existing test green).
- **[REQ-499-002]** Existing chat re-exports and smoke tests SHALL pass unchanged.

## 3. Tests

The existing cap test is the red test. Run the full Vitest and smoke suites.

## 4. Runbook

Chat works as before (send, Workbench, Teach, HITL). Vitest shows `chat_monolith_decomposition_397` green.
