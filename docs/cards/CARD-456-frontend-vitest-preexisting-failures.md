---
id: CARD-456
title: "qa baseline: 3 stale Vitest tests and ESLint errors"
type: bug
status: In Review
priority: P1
milestone: M22
needs_decision: none
related: [CARD-454, CARD-451, CARD-412, CARD-153, CARD-196]
proof:
  journeys: []
  checks:
    - tests/unit/frontend/per_agent_model_config.test.js
    - tests/unit/frontend/system_updates.test.js
    - npm run lint:frontend (0 errors, 0 warnings)
branch: fix/card-454-456-clean-baseline
log: {minutes: 10, qa_runs: 0, findings: 0}
created: 2026-09-24
---

# CARD-456 qa baseline: 3 stale Vitest tests and ESLint errors

## Problem
3 Vitest tests failed on qa (carried as `it.fails`), and `npm run lint:frontend` had 5 errors and 6 warnings (carried as KNOWN).

## Cause
All three tests were stale, not app regressions:
- `per_agent_model_config` REQ-MODEL-005 forbade any `/api/settings/matrix` in settings.js, but CARD-412 (OC-1) re-added one call on purpose: Save Provider persists the default context window through it. The purpose-matrix editor itself is gone.
- `system_updates` expected `systemPlatform`, `updateRepoUrlInput`, `updateBranchInput`, `saveUpdateConfigBtn`; CARD-451 removed them on purpose (REQ-451-016 read-only `origin`, REQ-451-021 branch picker).
- ESLint: `no-useless-assignment` initializers, unused catch bindings, dead `currentSystemVersion`, unused `before` in the card-520 journey.

## Change
- REQ-MODEL-005 test keeps "no saveMatrixBtn / .matrix-select" and now asserts exactly one matrix call, inside the context-window save.
- `system_updates` tests assert the CARD-451 markup (commit subject, ahead/behind, last fetch; read-only origin; branch picker) and that the free-text inputs stay gone.
- ESLint fixes in education_operator.js, education_players.js, settings.js, study_entry.js, chat_stop_486.test.js, card-520 journey.
- Removed the `it.fails(CARD-456)` markers and the ESLint `KNOWN_LINT` entry.

## What dies
`it.fails` markers, the ESLint `KNOWN_LINT` entry, dead `currentSystemVersion`.

## Proof
- Checks: Vitest 0 failed; lint:frontend 0 errors, 0 warnings; negative assertions (no free-text repo URL, no matrix editor).

## Plan and decisions
Per test: stale (contract changed on purpose by CARD-412 / CARD-451), so the test side was fixed; no valid assertion was dropped.

## Findings
- none

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| (none) | - | - | Frontend-only test and lint fixes; covered by Vitest, ESLint and smoke. |

- `preflight.py --fast --base qa`: GREEN in 41 s, no KNOWN, no XFAIL (guard 192, changed 63, mapped 10, vitest 955).
- `preflight.py --full`: GREEN in 1004 s, no KNOWN (ruff 0, eslint 0, unit 2122 passed / 11 skipped, integration 103, honesty, vitest 955, smoke 73).

## Release note
Fixed: Vitest and ESLint are clean on qa (stale CARD-196/153 tests moved to the CARD-451/412 contracts).

## Legacy notes (pre-CARD-559 format)

### [CARD-456] Fix pre-existing frontend Vitest failures and ESLint errors on qa

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
4. `npm run lint:frontend` fails with 4 errors and 5 warnings (e.g. `no-useless-assignment`) in `education_operator.js`, `education_players.js`, `settings.js` and `study_entry.js`.
3. `system_updates` (CARD-196): expects `id="systemPlatform"` and `id="updateRepoUrlInput"`, which the CARD-451 Settings redesign removed. The test is stale against the new contract.

### Beat 3: What will change

1. (Child card: **CARD-499**.) Decompose `chat.js` / `chat/render.js` under the caps, or re-baseline the caps with Jacob's agreement.
2. Remove the dead matrix call from `settings.js`, or update REQ-MODEL-005.
3. Rewrite `system_updates.test.js` to the CARD-451 markup contract.
4. Fix the ESLint errors so the preflight ESLint stage is green.

### Beat 4: What dies today

A red frontend suite that hides new failures.

---

## 2. Acceptance criteria (EARS)

- **[REQ-456-001]** WHEN `npx vitest run` runs on `qa`, THE SYSTEM SHALL report 0 failed tests.
- **[REQ-456-003]** WHEN `npm run lint:frontend` runs on `qa`, THE SYSTEM SHALL report 0 errors.
- **[REQ-456-002]** THE `system_updates` frontend test SHALL assert the CARD-451 Settings markup, not removed ids.
