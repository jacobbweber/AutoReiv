---
id: CARD-452
title: "Settings updates card frontend first-paint + Vitest contract"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-451
labels:
  - type:test
  - area:settings
  - area:frontend
  - P3
---

# [CARD-452] Settings updates card frontend first-paint + Vitest contract

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-451 build — UI IDs rewritten (`#updateBranchSelect`, `#autoUpdateEnabled`, history list) but no template first-paint / Vitest chrome contract yet
> **Related**: CARD-451

## Intent

Lock the CARD-451 Settings System & Software Updates DOM contract so pruned free-text URL/tracked-branch inputs cannot return and new controls stay present on first paint.

## Acceptance (EARS)

- **[REQ-452-001]** THE SYSTEM SHALL assert `index.html` contains `#settingsSystemUpdatesCard`, `#updateBranchSelect`, `#autoUpdateEnabled`, `#updateHistoryList`, and `#applyUpdateBtn`.
- **[REQ-452-002]** THE SYSTEM SHALL assert obsolete IDs `updateRepoUrlInput`, `updateBranchInput`, `saveUpdateConfigBtn` are absent from the template.
- **[REQ-452-003]** WHERE frontend unit tests run, THE SYSTEM SHALL cover Settings update helpers (banner kind / history render) without Playwright volume.

## Reply phrases

- Start: say **build**.
