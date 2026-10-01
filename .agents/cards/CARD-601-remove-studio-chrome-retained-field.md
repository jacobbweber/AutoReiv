---
id: CARD-601
title: "Remove the stale studio_chrome_retained field from the education APIs"
status: Ready
created: 2026-10-01
branch: qa
related:
  - CARD-441
  - CARD-463
labels:
  - type:enhancement
  - area:education
  - area:api
  - P3
needs_decision: none
milestone: M22
---

# [CARD-601] Remove the stale studio_chrome_retained field from the education APIs

> **Status**: Ready (filed 2026-10-01)
> **Labels**: `type:enhancement`, `area:education`, `area:api`, `P3`

## Why

`studio_chrome_retained: true` is always true and means nothing since CARD-463 removed the legacy Education Studio panels. It is still returned and asserted in:
- `progress_summary.py` (2 places);
- `education_tools.py:786`;
- the `routers/education.py` docstring;
- `study_entry.js:511`;
- `test_card441_progress_you_can_trust_non_studio_surface.py:98`.

## Scope

Remove the field and its assertions, and check that no UI code reads it.

## Acceptance criteria

- `rg studio_chrome_retained src tests` finds nothing.
- The education unit tests and vitest are green.
- Fast preflight is green.
