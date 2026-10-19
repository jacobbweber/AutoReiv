---
id: CARD-726
title: "Card Status CLI Milestone/Priority Support, Smoke TC-7 Transition Wait, and Stale knownBug Cleanup"
type: bug
status: Ready
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-726-card-cli-and-theme-transition]
  checks:
    - tests/unit/skills/test_card726_list_card_status.py
branch: feat/card-726-card-cli-and-theme-transition
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-18
---

# CARD-726 Card Status CLI Milestone/Priority Support, Smoke TC-7 Transition Wait, and Stale knownBug Cleanup

## Problem
Three tooling and E2E test hygiene bugs from `docs/findings.md`:
1. `.agents/skills/card/scripts/list_card_status.py` has no `--milestone` filter or `PRIORITY` / `MILESTONE` columns in its table output, and prints legacy status strings (`Complete`, `Completed`, `Done (Absorbed)`, `Done (Superseded...)`) as separate raw statuses instead of normalizing them to `Done` or `Superseded`.
2. In `tests/e2e/smoke.spec.js` (`TC-7`, lines 366–369), after clicking the `amber-phosphor` theme preset, the test immediately reads `window.getComputedStyle(el).backgroundColor` on `#checkForUpdatesBtn` in a single `.evaluate()` call while the CSS colour transition is still in flight, causing intermittent failures.
3. `tests/e2e/journeys/card-520-teach-needs-tool.mjs` step 4 still carries `knownBug: 'CARD-535'`, even though `CARD-535` was closed as obsolete in `CARD-577`.

## Cause
1. `parse_card()` in `.agents/skills/card/scripts/list_card_status.py` never extracts `priority` or `milestone` from YAML frontmatter or blockquote headers, `normalize_status()` does not exist, and `main()` has no `--milestone` argument.
2. `tests/e2e/smoke.spec.js` line 366 uses a one-shot `evaluate(() => getComputedStyle(el).backgroundColor)` instead of Playwright's auto-retrying `expect(locator).toHaveCSS('background-color', ...)` (unlike lines 383–390 which wait for the transition).
3. `card-520-teach-needs-tool.mjs` line 98 was not updated when `CARD-535` was closed in `CARD-577`.

## Change
- Update `.agents/skills/card/scripts/list_card_status.py` to:
  - Parse `priority` and `milestone` from YAML frontmatter (and markdown blockquotes if present).
  - Normalize legacy closed statuses (`Complete`, `Completed`, `Done (Absorbed)` -> `Done`; `Done (Superseded...)` -> `Superseded`).
  - Add `--milestone` (e.g. `--milestone M31`) and `--priority` CLI filters, and include `PRI` and `MILESTONE` columns in the table output.
- In `tests/e2e/smoke.spec.js` (`TC-7`), replace the one-shot `evaluate(getComputedStyle)` checks on `#checkForUpdatesBtn` and `.desktop-win-icon` with Playwright's auto-retrying `await expect(...).toHaveCSS(...)`.
- In `tests/e2e/journeys/card-520-teach-needs-tool.mjs`, remove the obsolete `knownBug: 'CARD-535'` property from step 4.

## What dies
One-shot mid-transition `getComputedStyle` evaluation in `smoke.spec.js` `TC-7`, unnormalized `Complete`/`Completed`/`Done (Absorbed)` status display in `list_card_status.py`, and stale `knownBug: 'CARD-535'` in `card-520-teach-needs-tool.mjs`.

## Proof
- Journey `card-726-card-cli-and-theme-transition`: verifies theme switching in Settings Studio (`amber-phosphor` and `emerald-matrix`) transitions `#checkForUpdatesBtn` cleanly on desktop and mobile viewports.
- Checks: `tests/unit/skills/test_card726_list_card_status.py`.

## Plan and decisions
- Normalize any status containing `superseded` to `Superseded`, and any status starting with `complete`/`completed`/`done` (without `superseded`) to `Done`.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `/tmp/autoreiv-qa/card-726/...`

## Release note
Added `--milestone` and `--priority` support plus status normalization to `list_card_status.py`, fixed the mid-transition CSS race in smoke test `TC-7`, and removed the stale `CARD-535` `knownBug` marker from `card-520`.
