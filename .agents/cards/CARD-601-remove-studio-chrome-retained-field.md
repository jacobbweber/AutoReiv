---
id: CARD-601
title: "Remove the stale studio_chrome_retained field from the education APIs"
status: In Review
created: 2026-10-01
branch: feat/card-601-remove-studio-chrome-retained
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

> **Status**: In Review (2026-10-02)
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

## Change

- Removed `studio_chrome_retained` from `progress_summary.py` (ok and failure payloads), `education_tools.py`, the `routers/education.py` docstring, `study_entry.js`, and the CARD-441 test assertion. No UI code read it.
- New test `test_progress_summary_has_no_studio_chrome_flag_card601` (ok and failure payloads carry no studio-chrome flag; `studio_required` stays false).
- `app.js?v=2.0.98` (asset bump, same as CARD-484, so the two merge cleanly).

## Results

| Check | Result | Notes |
|---|---|---|
| `rg studio_chrome_retained src tests` | PASS | no matches |
| Education unit tests | PASS | 217 passed |
| Full pytest | PASS | 2304 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2304/12 skipped, vitest 944, smoke 76 |

Engineering-only card: no live check.

## Release note

The education progress APIs no longer return the always-true `studio_chrome_retained` field.
