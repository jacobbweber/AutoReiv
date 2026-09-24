---
id: CARD-456
title: "Fix 5 pre-existing frontend Vitest failures on qa"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-397
  - CARD-153
  - CARD-196
  - CARD-451
labels:
  - type:test
  - area:frontend
  - P2
---

# [CARD-456] Fix 5 pre-existing frontend Vitest failures on qa

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-450 build on Jarvis (`feat/card-450-studio-platform-pack-reset`)
> **Labels**: `type:test`, `area:frontend`, `P2`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine scope - **still no product code** |
| **`build`** | Implement this card test-first |
| **`merge to qa`** | After the acceptance criteria are proven |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

`npx vitest run` should be green on `qa` so frontend regressions are visible.

### Beat 2: What AutoReiv does now

On `qa` `e54021ff`, with no CARD-450 changes (verified by stashing), 5 tests fail:

1. `chat_monolith_decomposition_397`: `chat.js` has 1034 lines (cap 1000), and `chat/render.js` has 837 lines (cap 800).
2. `per_agent_model_config` (REQ-MODEL-005): `settings.js` still contains `/api/settings/matrix`.
3. `system_updates` (CARD-196): expects `id="systemPlatform"` and `id="updateRepoUrlInput"`, which the CARD-451 Settings redesign removed. The test is stale against the new contract.

### Beat 3: What will change

1. Decompose `chat.js` / `chat/render.js` under the caps, or re-baseline the caps with Jacob's agreement.
2. Remove the dead matrix call from `settings.js`, or update REQ-MODEL-005.
3. Rewrite `system_updates.test.js` to the CARD-451 markup contract.

### Beat 4: What dies today

A red frontend suite that hides new failures.

---

## 2. Acceptance criteria (EARS)

- **[REQ-456-001]** WHEN `npx vitest run` runs on `qa`, THE SYSTEM SHALL report 0 failed tests.
- **[REQ-456-002]** THE `system_updates` frontend test SHALL assert the CARD-451 Settings markup, not removed ids.
