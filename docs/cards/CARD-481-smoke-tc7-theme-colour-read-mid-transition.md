---
id: CARD-481
title: "Smoke TC-7 reads the Update button colour mid-transition and fails intermittently"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-209
  - CARD-475
labels:
  - type:test
  - area:frontend
  - P3
---

# [CARD-481] Smoke TC-7 reads the Update button colour mid-transition and fails intermittently

> **Status**: Ready
> **Created**: 2026-09-25
> **Observed during**: the CARD-475 build preflight.
> **Related**: CARD-209 (theme skinning), CARD-475
> **Labels**: `type:test`, `area:frontend`, `P3`

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
A green smoke run should mean the app works. A test that fails at random hides real failures.

### Beat 2: What AutoReiv does now
`tests/e2e/smoke.spec.js` TC-7 picks the Amber Phosphor theme, then immediately reads `getComputedStyle(#checkForUpdatesBtn).backgroundColor` and expects `rgb(196, 163, 90)`. The button has a CSS colour transition, so the read lands mid-fade: seen values `rgb(143, 130, 172)`, `rgb(166, 144, 136)`. It failed 4 of 5 runs on 2026-09-25, on the CARD-475 branch and on the unchanged test commit `0c762880` alike, and passed once. The theme itself applies correctly (the root tokens assert first and pass).

### Beat 3: What will change
Replace the one-shot read with `await expect.poll(() => computedBg).toBe('rgb(196, 163, 90)')`, or disable transitions for the test (`page.emulateMedia({ reducedMotion: 'reduce' })` if the CSS honours it, else inject `* { transition: none !important }`). No product change.

### Beat 4: What dies
A random red smoke run.

## 2. Acceptance criteria (EARS)
- **[REQ-481-001]** WHEN TC-7 runs 10 times in a row (`--repeat-each 10`), THE smoke suite SHALL pass every time.
